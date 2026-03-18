"""RAG Pipeline for Course Recommendations.

Implements a 4-stage Retrieval-Augmented Generation pipeline for
recommending courses to students based on their preferences.

Pipeline Stages:
    1. Graph Filter: Use Neo4j to filter by career path, prerequisites, departments
    2. Vector Retrieval: Use LanceDB to find semantically similar courses
    3. Feature Engineering: Prepare XGBoost-ready features for reranking
    4. XGBoost Ranking: Apply learning-to-rank model for final ordering

The pipeline is deterministic - same inputs always produce the same output order.

Usage:
    >>> from src.rag.course_recommender import CourseRecommender
    >>> recommender = CourseRecommender()
    >>> await recommender.initialize()
    >>> 
    >>> student_prefs = {
    ...     "math_interest": 0.9,
    ...     "humanities_interest": 0.2,
    ...     "career_goal": "aerospace_engineer",
    ...     "constraints": ["high_math_required"],
    ...     "completed_courses": ["math-101", "physics-101"]
    ... }
    >>> 
    >>> recommendations = await recommender.recommend(student_prefs, top_k=5)
    >>> for rec in recommendations:
    ...     print(f"{rec.course_name}: {rec.total_score:.3f}")

Configuration:
    Set USE_XGBOOST_RANKING=true to enable XGBoost reranking (Stage 4).
    Set XGBOOST_MODEL_PATH to specify the model file location.
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from src.config import get_settings
from src.graph.course_graph import CourseGraph, CourseNode
from src.llm.adapter import LLMAdapter
from src.logging_config import get_logger
from src.vector.course_store import CourseSearchResult, CourseVectorStore

# XGBoost ranking (optional)
try:
    from src.ranking.xgboost_ranker import CourseRanker
    XGBOOST_RANKING_AVAILABLE = True
except ImportError:
    XGBOOST_RANKING_AVAILABLE = False

logger = get_logger(__name__)

# Configuration flag for XGBoost reranking
USE_XGBOOST_RANKING = os.getenv("USE_XGBOOST_RANKING", "false").lower() == "true"


@dataclass
class CourseRecommendation:
    """A course recommendation with scores and features.
    
    Contains all features needed for XGBoost reranking.
    
    Attributes:
        course_id: Unique course identifier
        course_name: Human-readable course name
        department: Department code
        description: Course description
        career_paths: Associated career paths
        credits: Course credits
        
        # Scores
        total_score: Combined recommendation score
        vector_similarity_score: Semantic similarity score (0-1)
        career_match_score: Career path alignment (0-1)
        math_intensity_match: Math interest alignment (0-1)
        humanities_intensity_match: Humanities interest alignment (0-1)
        graph_distance: Minimum distance in course graph
        prerequisite_score: Prerequisite satisfaction (0-1)
        
        # XGBoost features
        features: Dict of features ready for XGBoost input
        
        # Context
        matched_careers: Career paths that matched
        reason: Human-readable recommendation reason
    """
    course_id: str
    course_name: str
    department: str
    description: str
    career_paths: List[str]
    credits: int
    math_intensity: float
    humanities_intensity: float
    
    # Scores
    total_score: float = 0.0
    vector_similarity_score: float = 0.0
    career_match_score: float = 0.0
    math_intensity_match: float = 0.0
    humanities_intensity_match: float = 0.0
    graph_distance: float = 0.0
    prerequisite_score: float = 1.0
    
    # XGBoost features
    features: Dict[str, float] = field(default_factory=dict)
    
    # Context
    matched_careers: List[str] = field(default_factory=list)
    reason: str = ""


@dataclass
class StudentPreferences:
    """Structured student preferences.
    
    Attributes:
        math_interest: Interest in math (0-1)
        humanities_interest: Interest in humanities (0-1)
        career_goal: Primary career goal
        constraints: List of constraints (e.g., "high_math_required")
        completed_courses: List of completed course IDs
        preferred_departments: Optional department filter
        max_credits: Maximum credits per term
    """
    math_interest: float = 0.5
    humanities_interest: float = 0.5
    career_goal: str = ""
    constraints: List[str] = field(default_factory=list)
    completed_courses: List[str] = field(default_factory=list)
    preferred_departments: List[str] = field(default_factory=list)
    max_credits: int = 18
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> StudentPreferences:
        """Create from dictionary."""
        return cls(
            math_interest=data.get("math_interest", 0.5),
            humanities_interest=data.get("humanities_interest", 0.5),
            career_goal=data.get("career_goal", ""),
            constraints=data.get("constraints", []),
            completed_courses=data.get("completed_courses", []),
            preferred_departments=data.get("preferred_departments", []),
            max_credits=data.get("max_credits", 18),
        )
    
    def to_embedding_text(self) -> str:
        """Convert to text for embedding generation."""
        return (
            f"Student interested in math at {self.math_interest:.1f} level "
            f"and humanities at {self.humanities_interest:.1f} level. "
            f"Career goal: {self.career_goal}. "
            f"Constraints: {', '.join(self.constraints)}."
        )


class CourseRecommender:
    """RAG pipeline for course recommendations.
    
    Implements a 4-stage pipeline with XGBoost as the sole ranking method:
    
    Stage 1 - Graph Filter:
        - Query Neo4j for courses matching career goals
        - Filter by department preferences
        - Check prerequisite constraints
    
    Stage 2 - Vector Retrieval:
        - Encode student preferences to embedding
        - Search LanceDB for similar courses
        - Retrieve top-k candidates
    
    Stage 3 - Feature Engineering:
        - Extract features for XGBoost ranking
        - Calculate vector_similarity_score
        - Calculate career_match_score
        - Calculate intensity matches
        - Compute graph_distance from related courses
    
    Stage 4 - XGBoost Ranking:
        - Apply learning-to-rank model for final ordering
        - Sole ranking mechanism (no weighted scoring)
    
    The pipeline is deterministic - same inputs produce the same ordered output.
    
    Attributes:
        graph: CourseGraph for Neo4j operations
        vector_store: CourseVectorStore for semantic search
        llm: LLMAdapter for embeddings
        xgboost_ranker: CourseRanker for Stage 4 ranking
        _is_ready: Whether pipeline is initialized
    
    Example:
        >>> recommender = CourseRecommender()
        >>> await recommender.initialize()
        >>>
        >>> prefs = {
        ...     "math_interest": 0.9,
        ...     "humanities_interest": 0.2,
        ...     "career_goal": "aerospace_engineer",
        ...     "constraints": ["high_math_required"]
        ... }
        >>>
        >>> recommendations = await recommender.recommend(prefs, top_k=5)
    """
    
    def __init__(
        self,
        graph: Optional[CourseGraph] = None,
        vector_store: Optional[CourseVectorStore] = None,
        llm: Optional[LLMAdapter] = None,
        xgboost_ranker: Optional[Any] = None,
    ):
        """Initialize CourseRecommender.
        
        Args:
            graph: CourseGraph instance (created if None)
            vector_store: CourseVectorStore instance (created if None)
            llm: LLMAdapter instance (created if None)
            xgboost_ranker: Pre-initialized CourseRanker instance
        """
        self.graph = graph
        self.vector_store = vector_store
        self.llm = llm
        
        # XGBoost ranking (sole ranking mechanism)
        self.xgboost_ranker = xgboost_ranker
        
        self._is_ready = False
        self._course_cache: Dict[str, CourseNode] = {}
    
    async def initialize(self) -> None:
        """Initialize all pipeline components.
        
        Initializes graph, vector store, and LLM adapter.
        Idempotent - safe to call multiple times.
        """
        # Initialize components if not provided
        if self.graph is None:
            self.graph = CourseGraph()
        if self.vector_store is None:
            self.vector_store = CourseVectorStore()
        if self.llm is None:
            self.llm = LLMAdapter()
        
        # Initialize each component
        await self.graph.initialize()
        await self.vector_store.initialize()
        
        self._is_ready = True
        
        # Initialize XGBoost ranker
        if self.xgboost_ranker is None and XGBOOST_RANKING_AVAILABLE:
            from src.ranking.xgboost_ranker import CourseRanker
            self.xgboost_ranker = CourseRanker()
        
        logger.info(
            "CourseRecommender initialized",
            xgboost_available=XGBOOST_RANKING_AVAILABLE,
            xgboost_trained=self.xgboost_ranker.is_trained if self.xgboost_ranker else False,
        )
    
    async def close(self) -> None:
        """Close all pipeline components."""
        if self.graph:
            await self.graph.close()
        # Vector store doesn't need explicit close
        self._is_ready = False
        logger.info("CourseRecommender closed")
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def recommend(
        self,
        student_prefs: Dict[str, Any],
        top_k: int = 5,
        stage1_candidates: int = 50,
        stage2_candidates: int = 20,
    ) -> List[CourseRecommendation]:
        """Run the 4-stage RAG pipeline to generate recommendations.
        
        Args:
            student_prefs: Student preferences dictionary
            top_k: Number of final recommendations
            stage1_candidates: Number of candidates from Stage 1
            stage2_candidates: Number of candidates from Stage 2
        
        Returns:
            List of CourseRecommendation, sorted by XGBoost ranking
        
        Example:
            >>> prefs = {
            ...     "math_interest": 0.9,
            ...     "humanities_interest": 0.2,
            ...     "career_goal": "aerospace_engineer",
            ...     "constraints": ["high_math_required"]
            ... }
            >>> recs = await recommender.recommend(prefs, top_k=5)
            >>> for r in recs:
            ...     print(f"{r.course_name}: {r.total_score:.3f}")
        """
        if not self._is_ready:
            raise RuntimeError("CourseRecommender not initialized")
        
        # Parse preferences
        prefs = StudentPreferences.from_dict(student_prefs)
        
        logger.info(
            "Starting recommendation pipeline",
            career_goal=prefs.career_goal,
            top_k=top_k,
        )
        
        # Stage 1: Graph Filter
        graph_candidates = await self._stage1_graph_filter(
            prefs,
            limit=stage1_candidates,
        )
        logger.info("Stage 1 complete", candidates=len(graph_candidates))
        
        # Stage 2: Vector Retrieval
        vector_candidates = await self._stage2_vector_retrieval(
            prefs,
            graph_candidates,
            limit=stage2_candidates,
        )
        logger.info("Stage 2 complete", candidates=len(vector_candidates))
        
        # Stage 3: Feature Engineering
        recommendations = await self._stage3_feature_engineering(
            prefs,
            vector_candidates,
        )
        logger.info("Stage 3 complete", recommendations=len(recommendations))
        
        # Stage 4: XGBoost Ranking (sole ranking method, deterministic)
        if self.xgboost_ranker and self.xgboost_ranker.is_trained:
            recommendations = await self.rerank_with_xgboost(recommendations)
            logger.info("Stage 4 (XGBoost) complete", recommendations=len(recommendations))
        else:
            # Fallback: sort by vector similarity with deterministic tie-breaking
            recommendations = self._ensure_deterministic_order(
                sorted(recommendations, key=lambda x: x.vector_similarity_score, reverse=True)
            )
            logger.warning("XGBoost not available, using vector similarity fallback")
        
        # Final deterministic ordering: (score DESC, course_id ASC)
        recommendations = self._ensure_deterministic_order(recommendations)
        
        return recommendations[:top_k]
    
    async def _stage1_graph_filter(
        self,
        prefs: StudentPreferences,
        limit: int = 50,
    ) -> List[CourseNode]:
        """Stage 1: Filter courses using Neo4j graph.
        
        Filters by:
        - Career path matching
        - Department preferences
        - Prerequisite constraints
        
        Args:
            prefs: Student preferences
            limit: Maximum candidates to return
        
        Returns:
            List of CourseNodes passing filters
        """
        candidates = []
        seen_ids = set()
        
        # Filter 1: Career path matching (primary filter)
        if prefs.career_goal:
            career_courses = await self.graph.find_courses_by_career_path(
                career_goal=prefs.career_goal,
                limit=limit,
            )
            for course in career_courses:
                if course.id not in seen_ids:
                    candidates.append(course)
                    seen_ids.add(course.id)
        
        # Filter 2: Department preferences
        if prefs.preferred_departments:
            for dept in prefs.preferred_departments:
                dept_courses = await self.graph.get_courses_by_department(dept)
                for course in dept_courses:
                    if course.id not in seen_ids:
                        candidates.append(course)
                        seen_ids.add(course.id)
                        
                if len(candidates) >= limit:
                    break
        
        # If no career goal or departments, get all courses
        if not candidates:
            # This would require a "get_all_courses" method
            # For now, we'll rely on vector search in stage 2
            logger.warning("No graph filters applied, relying on vector search")
        
        # Filter 3: Prerequisite constraints
        if prefs.completed_courses and "check_prerequisites" in prefs.constraints:
            filtered_candidates = []
            for course in candidates:
                all_met, missing = await self.graph.check_prerequisites_met(
                    course.id,
                    prefs.completed_courses,
                )
                if all_met:
                    filtered_candidates.append(course)
            candidates = filtered_candidates
        
        # Apply credit constraint
        if prefs.max_credits < 20:  # Only filter if reasonable limit
            candidates = [c for c in candidates if c.credits <= prefs.max_credits]
        
        # Limit results
        return candidates[:limit]
    
    async def _stage2_vector_retrieval(
        self,
        prefs: StudentPreferences,
        graph_candidates: List[CourseNode],
        limit: int = 20,
    ) -> List[CourseSearchResult]:
        """Stage 2: Retrieve similar courses using LanceDB.
        
        Encodes student preferences and searches for similar courses.
        Combines graph candidates with pure vector search for coverage.
        
        Args:
            prefs: Student preferences
            graph_candidates: Candidates from Stage 1
            limit: Maximum candidates to return
        
        Returns:
            List of CourseSearchResult from vector similarity
        """
        # Generate student preference embedding
        student_embedding = await self._get_student_embedding(prefs)
        
        # Search vector store
        vector_results = await self.vector_store.search_similar(
            embedding=student_embedding,
            top_k=limit * 2,  # Get more to combine with graph
        )
        
        # Also search by career if specified
        if prefs.career_goal:
            career_results = await self.vector_store.search_by_career(
                career_goal=prefs.career_goal,
                embedding=student_embedding,
                vector_weight=0.5,
                top_k=limit,
            )
            
            # Merge results, prioritizing career matches
            seen_ids = {r.course_id for r in vector_results}
            for result in career_results:
                if result.course_id not in seen_ids:
                    vector_results.append(result)
        
        # Boost scores for graph candidates
        graph_ids = {c.id for c in graph_candidates}
        for result in vector_results:
            if result.course_id in graph_ids:
                # Boost similarity score for graph-matched courses
                result.similarity_score = min(1.0, result.similarity_score * 1.1)
        
        # Sort by combined score
        vector_results.sort(key=lambda x: x.similarity_score, reverse=True)
        
        return vector_results[:limit]
    
    async def _stage3_feature_engineering(
        self,
        prefs: StudentPreferences,
        vector_candidates: List[CourseSearchResult],
    ) -> List[CourseRecommendation]:
        """Stage 3: Engineer features and calculate final scores.
        
        Calculates:
        - vector_similarity_score
        - career_match_score
        - math_intensity_match
        - humanities_intensity_match
        - graph_distance
        - prerequisite_score
        
        Prepares XGBoost-ready features dictionary.
        
        Args:
            prefs: Student preferences
            vector_candidates: Candidates from Stage 2
        
        Returns:
            List of CourseRecommendation with features
        """
        recommendations = []
        
        for candidate in vector_candidates:
            # Get full course details from graph if available
            course = await self.graph.get_course(candidate.course_id)
            
            if course is None:
                # Use vector store data
                course = CourseNode(
                    id=candidate.course_id,
                    name=candidate.name,
                    description=candidate.description,
                    department=candidate.department,
                    credits=candidate.credits,
                    math_intensity=candidate.math_intensity,
                    humanities_intensity=candidate.humanities_intensity,
                    career_paths=candidate.career_paths,
                )
            
            # Calculate individual scores
            vector_score = candidate.vector_score
            
            # Career match score
            career_score = self._calculate_career_match(
                prefs.career_goal,
                course.career_paths,
            )
            
            # Intensity matches
            math_match = 1.0 - abs(prefs.math_interest - course.math_intensity)
            humanities_match = 1.0 - abs(prefs.humanities_interest - course.humanities_intensity)
            
            # Graph distance (from completed courses)
            graph_dist = await self._calculate_graph_distance(
                course.id,
                prefs.completed_courses,
            )
            
            # Prerequisite score
            prereq_score = await self._calculate_prerequisite_score(
                course.id,
                prefs.completed_courses,
            )
            
            # Calculate initial total_score as vector similarity (fallback if XGBoost unavailable)
            # XGBoost will provide the final ranking score
            total_score = vector_score * prereq_score
            
            # Prepare XGBoost features
            features = {
                "vector_similarity": vector_score,
                "career_match": career_score,
                "math_intensity_match": math_match,
                "humanities_intensity_match": humanities_match,
                "graph_distance": graph_dist,
                "prerequisite_score": prereq_score,
                "course_math_intensity": course.math_intensity,
                "course_humanities_intensity": course.humanities_intensity,
                "course_credits": course.credits,
                "student_math_interest": prefs.math_interest,
                "student_humanities_interest": prefs.humanities_interest,
            }
            
            # Generate reason
            reason = self._generate_reason(
                course=course,
                career_score=career_score,
                math_match=math_match,
                vector_score=vector_score,
            )
            
            rec = CourseRecommendation(
                course_id=course.id,
                course_name=course.name,
                department=course.department,
                description=course.description,
                career_paths=course.career_paths,
                credits=course.credits,
                math_intensity=course.math_intensity,
                humanities_intensity=course.humanities_intensity,
                total_score=total_score,
                vector_similarity_score=vector_score,
                career_match_score=career_score,
                math_intensity_match=math_match,
                humanities_intensity_match=humanities_match,
                graph_distance=graph_dist,
                prerequisite_score=prereq_score,
                features=features,
                matched_careers=candidate.matched_careers if hasattr(candidate, 'matched_careers') else [],
                reason=reason,
            )
            
            recommendations.append(rec)
        
        return recommendations
    
    async def _get_student_embedding(self, prefs: StudentPreferences) -> List[float]:
        """Generate or retrieve student preference embedding.
        
        First tries LLM adapter, falls back to deterministic generation.
        
        Args:
            prefs: Student preferences
        
        Returns:
            384-dimensional embedding vector
        """
        # Try LLM first
        if self.llm:
            try:
                if await self.llm.health_check():
                    text = prefs.to_embedding_text()
                    result = await self.llm.embed(text)
                    if len(result.embedding) == 384:
                        return result.embedding
            except Exception as exc:
                logger.warning("LLM embedding failed, using fallback", error=str(exc))
        
        # Fallback to deterministic embedding
        interests = {
            "math": prefs.math_interest,
            "humanities": prefs.humanities_interest,
        }
        return self.llm.create_student_preference_embedding(
            interests=interests,
            career_goal=prefs.career_goal,
        ) if self.llm else self._fallback_student_embedding(prefs)
    
    def _fallback_student_embedding(self, prefs: StudentPreferences) -> List[float]:
        """Generate deterministic student embedding without LLM."""
        # Combine preferences into a deterministic embedding
        interest_str = f"math:{prefs.math_interest:.2f},humanities:{prefs.humanities_interest:.2f}"
        combined = f"{interest_str}|career:{prefs.career_goal}|constraints:{','.join(prefs.constraints)}"
        
        hash_bytes = hashlib.sha256(combined.encode()).digest()
        
        embedding = []
        for i in range(384):
            byte_idx = i % len(hash_bytes)
            byte_val = hash_bytes[byte_idx]
            
            # Add preference-based signals
            if i < 96:
                byte_val = int(byte_val * (0.3 + 0.7 * prefs.math_interest))
            elif i < 192:
                byte_val = int(byte_val * (0.3 + 0.7 * prefs.humanities_interest))
            
            val = (byte_val / 255.0) * 2 - 1
            val += 0.05 * np.sin(i * 0.05)
            embedding.append(float(np.clip(val, -1, 1)))
        
        # L2 normalize
        vec = np.array(embedding)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        
        return vec.tolist()
    
    def _calculate_career_match(
        self,
        career_goal: str,
        course_careers: List[str],
    ) -> float:
        """Calculate career match score.
        
        Returns 1.0 for exact match, 0.5 for partial match, 0.0 otherwise.
        """
        if not career_goal or not course_careers:
            return 0.0
        
        if career_goal in course_careers:
            return 1.0
        
        # Check for partial matches
        for cc in course_careers:
            if career_goal in cc or cc in career_goal:
                return 0.5
        
        return 0.0
    
    async def _calculate_graph_distance(
        self,
        course_id: str,
        completed_courses: List[str],
    ) -> float:
        """Calculate minimum graph distance from completed courses.
        
        Returns average distance to completed courses.
        """
        if not completed_courses:
            return 0.0
        
        distances = []
        for completed_id in completed_courses:
            try:
                subgraph = await self.graph.get_course_subgraph(
                    completed_id,
                    depth=3,
                    include_similar=True,
                )
                distance = subgraph.graph_distance.get(course_id, float('inf'))
                if distance != float('inf'):
                    distances.append(distance)
            except Exception:
                continue
        
        if not distances:
            return 3.0  # Default distance if not connected
        
        return sum(distances) / len(distances)
    
    async def _calculate_prerequisite_score(
        self,
        course_id: str,
        completed_courses: List[str],
    ) -> float:
        """Calculate prerequisite satisfaction score.
        
        Returns 1.0 if all prerequisites met, proportional otherwise.
        """
        try:
            prerequisites = await self.graph.get_prerequisites(course_id)
        except Exception:
            return 1.0  # Assume no prerequisites
        
        if not prerequisites:
            return 1.0
        
        completed_set = set(completed_courses)
        met_count = sum(1 for p in prerequisites if p.id in completed_set)
        
        return met_count / len(prerequisites)
    
    def _generate_reason(
        self,
        course: CourseNode,
        career_score: float,
        math_match: float,
        vector_score: float,
    ) -> str:
        """Generate human-readable recommendation reason."""
        reasons = []
        
        if career_score >= 0.5:
            reasons.append(f"Aligns with your career goals")
        
        if math_match > 0.8:
            reasons.append(f"Matches your interest in math")
        elif math_match < 0.3:
            reasons.append(f"Low math requirement")
        
        if vector_score > 0.8:
            reasons.append("Highly relevant to your interests")
        elif vector_score > 0.6:
            reasons.append("Moderately relevant to your interests")
        
        if not reasons:
            reasons.append("May be of interest based on your profile")
        
        return "; ".join(reasons)
    
    def _ensure_deterministic_order(
        self,
        recommendations: List[CourseRecommendation],
    ) -> List[CourseRecommendation]:
        """Ensure deterministic ordering for ties.
        
        Sorts by (score, course_id) to ensure same input = same output.
        """
        # Stable sort by score (descending), then by course_id (ascending) for ties
        return sorted(
            recommendations,
            key=lambda x: (-x.total_score, x.course_id),
        )
    
    async def get_recommendations_with_explanation(
        self,
        student_prefs: Dict[str, Any],
        top_k: int = 5,
    ) -> Tuple[List[CourseRecommendation], str]:
        """Get recommendations with a generated explanation.
        
        Args:
            student_prefs: Student preferences
            top_k: Number of recommendations
        
        Returns:
            Tuple of (recommendations, explanation_text)
        """
        recommendations = await self.recommend(student_prefs, top_k)
        
        # Generate explanation
        if self.llm and await self.llm.health_check():
            context = {
                "career_goal": student_prefs.get("career_goal", ""),
                "math_interest": student_prefs.get("math_interest", 0.5),
                "humanities_interest": student_prefs.get("humanities_interest", 0.5),
                "top_recommendations": [
                    {
                        "name": r.course_name,
                        "score": f"{r.total_score:.3f}",
                        "reason": r.reason,
                    }
                    for r in recommendations[:3]
                ],
            }
            
            prompt = (
                "Explain these course recommendations to a student. "
                "Be concise and highlight why these courses match their interests."
            )
            
            try:
                result = await self.llm.generate(prompt, context)
                explanation = result.text
            except Exception:
                explanation = self._generate_fallback_explanation(recommendations)
        else:
            explanation = self._generate_fallback_explanation(recommendations)
        
        return recommendations, explanation
    
    def _generate_fallback_explanation(
        self,
        recommendations: List[CourseRecommendation],
    ) -> str:
        """Generate a simple explanation without LLM."""
        if not recommendations:
            return "No recommendations available."
        
        lines = ["Based on your preferences, we recommend:"]
        for i, rec in enumerate(recommendations[:3], 1):
            lines.append(f"{i}. {rec.course_name} - {rec.reason}")
        
        return "\n".join(lines)
    
    async def rerank_with_xgboost(
        self,
        recommendations: List[CourseRecommendation],
    ) -> List[CourseRecommendation]:
        """Apply XGBoost learning-to-rank to rerank recommendations.
        
        Stage 4 of the pipeline. Uses the trained XGBoost model to
        rerank courses based on learned preferences.
        
        Deterministic ranking is enforced through:
        - Fixed random_state in XGBRanker
        - Deterministic tie-breaking (score DESC, entity_id ASC)
        - No stochastic post-processing
        
        Args:
            recommendations: List of CourseRecommendation from Stage 3
            
        Returns:
            Reranked list of CourseRecommendation with deterministic ordering
            
        Example:
            >>> recs = await recommender._stage3_feature_engineering(prefs, candidates)
            >>> reranked = await recommender.rerank_with_xgboost(recs)
        """
        if not self.xgboost_ranker:
            logger.warning("XGBoost ranker not initialized, skipping reranking")
            return self._ensure_deterministic_order(recommendations)
        
        if not self.xgboost_ranker.is_trained:
            logger.warning("XGBoost model not trained, skipping reranking")
            return self._ensure_deterministic_order(recommendations)
        
        # Store original scores for comparison
        for rec in recommendations:
            rec.features["original_total_score"] = rec.total_score
        
        # Apply XGBoost ranking (deterministic with fixed random_state)
        reranked = self.xgboost_ranker.rank(recommendations)
        
        # Final deterministic ordering: score DESC, course_id ASC
        reranked = self._ensure_deterministic_order(reranked)
        
        logger.debug(
            "XGBoost reranking complete",
            input_count=len(recommendations),
            output_count=len(reranked),
        )
        
        return reranked
    
    def get_ranking_comparison(
        self,
        before: List[CourseRecommendation],
        after: List[CourseRecommendation],
    ) -> Dict[str, Any]:
        """Compare rankings before and after XGBoost reranking.
        
        Args:
            before: Original recommendations (before XGBoost)
            after: Reranked recommendations (after XGBoost)
            
        Returns:
            Dictionary with comparison metrics
        """
        before_ids = {r.course_id: i for i, r in enumerate(before)}
        after_ids = {r.course_id: i for i, r in enumerate(after)}
        
        position_changes = []
        for course_id, before_pos in before_ids.items():
            after_pos = after_ids.get(course_id, len(after))
            position_changes.append({
                "course_id": course_id,
                "before": before_pos,
                "after": after_pos,
                "change": before_pos - after_pos,
            })
        
        return {
            "num_courses": len(before),
            "position_changes": sorted(
                position_changes,
                key=lambda x: abs(x["change"]),
                reverse=True,
            )[:5],  # Top 5 changes
        }
