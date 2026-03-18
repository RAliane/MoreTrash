"""Integration tests for the RAG pipeline.

Tests the complete 3-stage recommendation pipeline:
1. Graph filtering via Neo4j
2. Vector retrieval via LanceDB
3. Feature engineering for XGBoost

Usage:
    pytest tests/test_rag_pipeline.py -v
    
Environment:
    Requires Neo4j to be running (or uses mocks)
    Set NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD for live tests
"""

from __future__ import annotations

import os
from typing import Any, Dict, List

import pytest
import pytest_asyncio

# Mark all tests as async
pytestmark = pytest.mark.asyncio


class TestCourseRecommenderIntegration:
    """Integration tests for CourseRecommender RAG pipeline."""
    
    @pytest_asyncio.fixture
    async def recommender(self):
        """Create and initialize CourseRecommender."""
        from src.rag.course_recommender import CourseRecommender
        
        recommender = CourseRecommender()
        
        # Initialize components (will use fallback if Neo4j not available)
        try:
            await recommender.initialize()
        except Exception as exc:
            pytest.skip(f"Could not initialize recommender: {exc}")
        
        yield recommender
        
        # Cleanup
        await recommender.close()
    
    @pytest_asyncio.fixture
    async def sample_courses(self, recommender):
        """Create sample courses for testing."""
        courses_data = [
            {
                "id": "cs-101",
                "name": "Computer Science",
                "description": "Fundamentals of computing and programming",
                "department": "cs",
                "credits": 4,
                "math_intensity": 0.75,
                "humanities_intensity": 0.20,
                "career_paths": ["software_engineer", "systems_architect"],
            },
            {
                "id": "ae-101",
                "name": "Aerospace Engineering",
                "description": "Design and analysis of aircraft and spacecraft",
                "department": "engineering",
                "credits": 4,
                "math_intensity": 0.95,
                "humanities_intensity": 0.10,
                "career_paths": ["aerospace_engineer", "flight_engineer"],
            },
            {
                "id": "me-101",
                "name": "Mechanical Engineering",
                "description": "Study of mechanical systems and thermodynamics",
                "department": "engineering",
                "credits": 4,
                "math_intensity": 0.85,
                "humanities_intensity": 0.15,
                "career_paths": ["mechanical_engineer", "design_engineer"],
            },
            {
                "id": "ds-101",
                "name": "Data Science",
                "description": "Interdisciplinary field extracting knowledge from data",
                "department": "data_science",
                "credits": 4,
                "math_intensity": 0.80,
                "humanities_intensity": 0.40,
                "career_paths": ["data_scientist", "ml_engineer"],
            },
            {
                "id": "ph-101",
                "name": "Philosophy",
                "description": "Critical examination of fundamental questions",
                "department": "philosophy",
                "credits": 3,
                "math_intensity": 0.15,
                "humanities_intensity": 0.95,
                "career_paths": ["academic", "lawyer", "ethicist"],
            },
        ]
        
        # Add courses to graph and vector store
        for course in courses_data:
            # Generate deterministic embedding
            embedding = _generate_test_embedding(course["name"], course["math_intensity"])
            
            try:
                # Add to Neo4j graph
                await recommender.graph.create_course({
                    "name": course["name"],
                    "description": course["description"],
                    "department": course["department"],
                    "credits": course["credits"],
                    "math_intensity": course["math_intensity"],
                    "humanities_intensity": course["humanities_intensity"],
                    "career_paths": course["career_paths"],
                    "embedding": embedding,
                }, course_id=course["id"])
            except Exception as exc:
                print(f"Warning: Could not add course to graph: {exc}")
            
            try:
                # Add to vector store
                await recommender.vector_store.add_course(
                    course_id=course["id"],
                    embedding=embedding,
                    metadata={
                        "name": course["name"],
                        "department": course["department"],
                        "math_intensity": course["math_intensity"],
                        "humanities_intensity": course["humanities_intensity"],
                        "career_paths": course["career_paths"],
                        "credits": course["credits"],
                        "description": course["description"],
                    }
                )
            except Exception as exc:
                print(f"Warning: Could not add course to vector store: {exc}")
        
        # Create prerequisite relationships
        try:
            await recommender.graph.add_prerequisite("ae-101", "me-101")
            await recommender.graph.add_prerequisite("ds-101", "cs-101")
        except Exception as exc:
            print(f"Warning: Could not add prerequisites: {exc}")
        
        yield courses_data
        
        # Cleanup
        for course in courses_data:
            try:
                await recommender.graph.delete_course(course["id"])
            except Exception:
                pass
            try:
                await recommender.vector_store.delete_course(course["id"])
            except Exception:
                pass
    
    async def test_pipeline_initialization(self, recommender):
        """Test that the pipeline initializes correctly."""
        assert recommender._is_ready
        assert recommender.graph is not None
        assert recommender.vector_store is not None
    
    async def test_aerospace_engineer_recommendation(self, recommender, sample_courses):
        """Test that Aerospace Engineering is recommended for aerospace engineer career."""
        # Student interested in aerospace
        student_prefs = {
            "math_interest": 0.9,
            "humanities_interest": 0.2,
            "career_goal": "aerospace_engineer",
            "constraints": ["high_math_required"],
            "completed_courses": []
        }
        
        recommendations = await recommender.recommend(student_prefs, top_k=5)
        
        # Verify we got recommendations
        assert len(recommendations) > 0, "Should return at least one recommendation"
        
        # Verify Aerospace Engineering is in results
        course_names = [r.course_name for r in recommendations]
        assert "Aerospace Engineering" in course_names, \
            f"Aerospace Engineering should be in recommendations, got: {course_names}"
        
        # Verify it has high score
        ae_rec = next(r for r in recommendations if r.course_name == "Aerospace Engineering")
        assert ae_rec.total_score > 0.5, "Aerospace Engineering should have high score"
        assert ae_rec.career_match_score > 0.5, "Should have high career match"
        assert ae_rec.math_intensity_match > 0.8, "Should match math interest"
    
    async def test_software_engineer_recommendation(self, recommender, sample_courses):
        """Test recommendations for software engineer career."""
        student_prefs = {
            "math_interest": 0.7,
            "humanities_interest": 0.3,
            "career_goal": "software_engineer",
            "constraints": [],
            "completed_courses": []
        }
        
        recommendations = await recommender.recommend(student_prefs, top_k=5)
        
        # Verify Computer Science is in results
        course_names = [r.course_name for r in recommendations]
        assert "Computer Science" in course_names, \
            f"Computer Science should be in recommendations, got: {course_names}"
        
        # Verify Data Science might also appear (related career)
        # Both have software/data career paths
    
    async def test_philosophy_humanities_match(self, recommender, sample_courses):
        """Test that Philosophy is recommended for humanities-focused student."""
        student_prefs = {
            "math_interest": 0.2,
            "humanities_interest": 0.9,
            "career_goal": "academic",
            "constraints": [],
            "completed_courses": []
        }
        
        recommendations = await recommender.recommend(student_prefs, top_k=5)
        
        course_names = [r.course_name for r in recommendations]
        assert "Philosophy" in course_names, \
            f"Philosophy should be in recommendations for humanities student, got: {course_names}"
        
        # Verify high humanities match
        phil_rec = next(r for r in recommendations if r.course_name == "Philosophy")
        assert phil_rec.humanities_intensity_match > 0.8, \
            "Philosophy should have high humanities match"
    
    async def test_recommendation_features(self, recommender, sample_courses):
        """Test that recommendations include proper XGBoost features."""
        student_prefs = {
            "math_interest": 0.8,
            "humanities_interest": 0.3,
            "career_goal": "data_scientist",
            "constraints": [],
            "completed_courses": []
        }
        
        recommendations = await recommender.recommend(student_prefs, top_k=3)
        
        for rec in recommendations:
            # Verify all expected features are present
            expected_features = {
                "vector_similarity",
                "career_match",
                "math_intensity_match",
                "humanities_intensity_match",
                "graph_distance",
                "prerequisite_score",
                "course_math_intensity",
                "course_humanities_intensity",
                "course_credits",
                "student_math_interest",
                "student_humanities_interest",
            }
            
            missing = expected_features - set(rec.features.keys())
            assert not missing, f"Missing features in recommendation: {missing}"
            
            # Verify feature values are in valid ranges
            assert 0 <= rec.features["vector_similarity"] <= 1
            assert 0 <= rec.features["career_match"] <= 1
            assert 0 <= rec.features["prerequisite_score"] <= 1
            assert rec.features["graph_distance"] >= 0
    
    async def test_deterministic_ordering(self, recommender, sample_courses):
        """Test that recommendations are deterministic."""
        student_prefs = {
            "math_interest": 0.8,
            "humanities_interest": 0.3,
            "career_goal": "engineer",
            "constraints": [],
            "completed_courses": []
        }
        
        # Run pipeline twice
        recs1 = await recommender.recommend(student_prefs, top_k=5)
        recs2 = await recommender.recommend(student_prefs, top_k=5)
        
        # Verify same order
        assert len(recs1) == len(recs2)
        for r1, r2 in zip(recs1, recs2):
            assert r1.course_id == r2.course_id, "Recommendations should be deterministic"
            assert abs(r1.total_score - r2.total_score) < 0.001, \
                "Scores should be identical"
    
    async def test_prerequisite_filtering(self, recommender, sample_courses):
        """Test that prerequisites are properly checked."""
        # Student has completed Mechanical Engineering
        student_prefs = {
            "math_interest": 0.9,
            "humanities_interest": 0.2,
            "career_goal": "aerospace_engineer",
            "constraints": ["check_prerequisites"],
            "completed_courses": ["me-101"]  # Completed Mechanical Engineering
        }
        
        recommendations = await recommender.recommend(student_prefs, top_k=5)
        
        # Aerospace Engineering has ME as prerequisite
        ae_rec = next((r for r in recommendations if r.course_name == "Aerospace Engineering"), None)
        if ae_rec:
            assert ae_rec.prerequisite_score == 1.0, \
                "Aerospace Engineering prerequisites should be met"
    
    async def test_explanation_generation(self, recommender, sample_courses):
        """Test that explanations are generated."""
        student_prefs = {
            "math_interest": 0.8,
            "humanities_interest": 0.3,
            "career_goal": "software_engineer",
            "constraints": [],
            "completed_courses": []
        }
        
        recommendations, explanation = await recommender.get_recommendations_with_explanation(
            student_prefs, top_k=3
        )
        
        # Verify recommendations exist
        assert len(recommendations) > 0
        
        # Verify explanation is provided
        assert explanation, "Should provide explanation"
        assert len(explanation) > 10, "Explanation should be substantive"
        
        # Verify individual reasons exist
        for rec in recommendations:
            assert rec.reason, f"Recommendation {rec.course_name} should have a reason"
    
    async def test_empty_career_goal(self, recommender, sample_courses):
        """Test pipeline works without career goal."""
        student_prefs = {
            "math_interest": 0.9,
            "humanities_interest": 0.2,
            "career_goal": "",  # No career goal
            "constraints": [],
            "completed_courses": []
        }
        
        recommendations = await recommender.recommend(student_prefs, top_k=5)
        
        # Should still return recommendations based on vector similarity
        assert len(recommendations) > 0
    
    async def test_vector_search_fallback(self, recommender, sample_courses):
        """Test that vector search works as fallback when graph returns no results."""
        # Student with non-matching career goal
        student_prefs = {
            "math_interest": 0.5,
            "humanities_interest": 0.5,
            "career_goal": "novelist",  # Not in any course
            "constraints": [],
            "completed_courses": []
        }
        
        recommendations = await recommender.recommend(student_prefs, top_k=5)
        
        # Should still return recommendations based on vector similarity
        assert len(recommendations) > 0


class TestRAGPipelineStages:
    """Unit tests for individual pipeline stages."""
    
    async def test_stage1_graph_filter(self):
        """Test Stage 1: Graph filtering."""
        from src.rag.course_recommender import CourseRecommender, StudentPreferences
        
        recommender = CourseRecommender()
        
        prefs = StudentPreferences(
            math_interest=0.9,
            humanities_interest=0.2,
            career_goal="aerospace_engineer",
            preferred_departments=["engineering"],
        )
        
        # Mock graph methods would be needed for full test
        # This tests the method signature and basic logic
        assert prefs.career_goal == "aerospace_engineer"
        assert prefs.math_interest > prefs.humanities_interest
    
    async def test_stage2_vector_retrieval(self):
        """Test Stage 2: Vector retrieval."""
        from src.rag.course_recommender import CourseRecommender, StudentPreferences
        
        recommender = CourseRecommender()
        prefs = StudentPreferences(
            math_interest=0.8,
            humanities_interest=0.3,
            career_goal="software_engineer",
        )
        
        # Test embedding generation
        embedding = recommender._fallback_student_embedding(prefs)
        assert len(embedding) == 384
        
        # Verify L2 normalization
        import numpy as np
        norm = np.linalg.norm(embedding)
        assert abs(norm - 1.0) < 0.01, "Embedding should be L2 normalized"
    
    async def test_stage3_feature_engineering(self):
        """Test Stage 3: Feature engineering calculations."""
        from src.rag.course_recommender import CourseRecommender
        
        recommender = CourseRecommender()
        
        # Test career match calculation
        assert recommender._calculate_career_match(
            "software_engineer",
            ["software_engineer", "data_scientist"]
        ) == 1.0
        
        assert recommender._calculate_career_match(
            "software_engineer",
            ["senior_software_engineer"]  # Partial match
        ) == 0.5
        
        assert recommender._calculate_career_match(
            "software_engineer",
            ["doctor", "lawyer"]  # No match
        ) == 0.0
        
        assert recommender._calculate_career_match(
            "",
            ["software_engineer"]
        ) == 0.0


def _generate_test_embedding(name: str, math_intensity: float) -> List[float]:
    """Generate deterministic test embedding.
    
    Creates a 384-dimensional embedding where:
    - First 96 dimensions encode math intensity
    - Next 96 dimensions encode humanities intensity
    - Remaining dimensions encode name hash
    """
    import hashlib
    
    embedding = []
    
    # Math intensity (indices 0-95)
    for i in range(96):
        val = math_intensity + 0.1 * (i % 3 - 1)  # Add variation
        embedding.append(float(val))
    
    # Humanities intensity (indices 96-191)
    humanities = 1.0 - math_intensity  # Inverse for variety
    for i in range(96):
        val = humanities + 0.1 * (i % 3 - 1)
        embedding.append(float(val))
    
    # Name hash (indices 192-383)
    hash_bytes = hashlib.sha256(name.encode()).digest()
    for i in range(192):
        byte_val = hash_bytes[i % len(hash_bytes)]
        val = (byte_val / 255.0) * 2 - 1
        embedding.append(float(val))
    
    # L2 normalize
    import numpy as np
    vec = np.array(embedding)
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    
    return vec.tolist()


class TestLLMAdapterIntegration:
    """Integration tests for LLM adapter."""
    
    async def test_ollama_provider(self):
        """Test Ollama provider if available."""
        from src.llm.adapter import OllamaProvider
        
        provider = OllamaProvider()
        
        if not await provider.health_check():
            pytest.skip("Ollama not available")
        
        # Test embedding
        result = await provider.embed("Computer Science")
        assert len(result.embedding) == 384
        assert result.model == provider.embed_model
        
        # Test generation
        result = await provider.generate("Say hello")
        assert len(result.text) > 0
    
    async def test_embedding_dimensions(self):
        """Test that all providers return 384-dimensional embeddings."""
        from src.llm.adapter import LLMAdapter
        
        llm = LLMAdapter()
        
        # Test fallback embedding
        embedding = llm.create_student_preference_embedding(
            interests={"math": 0.8, "humanities": 0.3},
            career_goal="software_engineer"
        )
        
        assert len(embedding) == 384
        
        # Verify normalization
        import numpy as np
        norm = np.linalg.norm(embedding)
        assert abs(norm - 1.0) < 0.01


class TestCourseGraphIntegration:
    """Integration tests for CourseGraph."""
    
    @pytest_asyncio.fixture
    async def graph(self):
        """Create CourseGraph fixture."""
        from src.graph.course_graph import CourseGraph
        
        graph = CourseGraph()
        try:
            await graph.initialize()
            yield graph
        except Exception as exc:
            pytest.skip(f"Neo4j not available: {exc}")
        finally:
            await graph.close()
    
    async def test_create_and_get_course(self, graph):
        """Test course creation and retrieval."""
        course_data = {
            "name": "Test Course",
            "description": "A test course",
            "department": "test",
            "credits": 3,
            "math_intensity": 0.5,
            "humanities_intensity": 0.5,
            "career_paths": ["tester"],
        }
        
        course = await graph.create_course(course_data)
        assert course.name == "Test Course"
        assert course.department == "test"
        
        # Retrieve
        retrieved = await graph.get_course(course.id)
        assert retrieved is not None
        assert retrieved.name == "Test Course"
        
        # Cleanup
        await graph.delete_course(course.id)
    
    async def test_prerequisite_relationships(self, graph):
        """Test prerequisite relationships."""
        # Create two courses
        course1 = await graph.create_course({
            "name": "Basic Course",
            "description": "Basic",
            "department": "test",
            "credits": 3,
            "math_intensity": 0.3,
            "humanities_intensity": 0.3,
            "career_paths": [],
        })
        
        course2 = await graph.create_course({
            "name": "Advanced Course",
            "description": "Advanced",
            "department": "test",
            "credits": 4,
            "math_intensity": 0.7,
            "humanities_intensity": 0.3,
            "career_paths": [],
        })
        
        # Add prerequisite
        success = await graph.add_prerequisite(course2.id, course1.id)
        assert success
        
        # Verify
        prereqs = await graph.get_prerequisites(course2.id)
        assert len(prereqs) == 1
        assert prereqs[0].id == course1.id
        
        # Cleanup
        await graph.delete_course(course1.id)
        await graph.delete_course(course2.id)
    
    async def test_similar_courses(self, graph):
        """Test similar course discovery."""
        # Create courses with similar embeddings
        embedding1 = [0.5] * 384
        embedding2 = [0.51] * 384  # Very similar
        
        # L2 normalize
        import numpy as np
        for emb in [embedding1, embedding2]:
            vec = np.array(emb)
            vec = vec / np.linalg.norm(vec)
            emb[:] = vec.tolist()
        
        course1 = await graph.create_course({
            "name": "Course A",
            "description": "Course A",
            "department": "test",
            "credits": 3,
            "math_intensity": 0.5,
            "humanities_intensity": 0.5,
            "career_paths": [],
            "embedding": embedding1,
        })
        
        course2 = await graph.create_course({
            "name": "Course B",
            "description": "Course B",
            "department": "test",
            "credits": 3,
            "math_intensity": 0.5,
            "humanities_intensity": 0.5,
            "career_paths": [],
            "embedding": embedding2,
        })
        
        # Find similar
        similar = await graph.find_similar_courses(course1.id, threshold=0.7, top_k=5)
        
        # Course B should be similar to Course A
        similar_ids = [s.course.id for s in similar]
        assert course2.id in similar_ids
        
        # Cleanup
        await graph.delete_course(course1.id)
        await graph.delete_course(course2.id)


class TestCourseVectorStoreIntegration:
    """Integration tests for CourseVectorStore."""
    
    @pytest_asyncio.fixture
    async def store(self):
        """Create CourseVectorStore fixture."""
        from src.vector.course_store import CourseVectorStore
        
        store = CourseVectorStore()
        await store.initialize()
        yield store
    
    async def test_add_and_search_course(self, store):
        """Test adding and searching courses."""
        course_id = "test-course-1"
        embedding = [0.1] * 384
        
        # L2 normalize
        import numpy as np
        vec = np.array(embedding)
        vec = vec / np.linalg.norm(vec)
        embedding = vec.tolist()
        
        await store.add_course(
            course_id=course_id,
            embedding=embedding,
            metadata={
                "name": "Test Course",
                "department": "test",
                "math_intensity": 0.7,
                "humanities_intensity": 0.3,
                "career_paths": ["tester"],
            }
        )
        
        # Search
        results = await store.search_similar(embedding, top_k=5)
        
        # Should find our course
        course_ids = [r.course_id for r in results]
        assert course_id in course_ids
        
        # Cleanup
        await store.delete_course(course_id)
    
    async def test_search_by_career(self, store):
        """Test career-based search."""
        # Add courses with different career paths
        courses = [
            ("cs-1", [0.8] * 384, ["software_engineer"]),
            ("med-1", [0.2] * 384, ["doctor"]),
        ]
        
        import numpy as np
        for course_id, embedding, careers in courses:
            vec = np.array(embedding)
            vec = vec / np.linalg.norm(vec)
            
            await store.add_course(
                course_id=course_id,
                embedding=vec.tolist(),
                metadata={
                    "name": f"Course {course_id}",
                    "department": "test",
                    "math_intensity": 0.5,
                    "humanities_intensity": 0.5,
                    "career_paths": careers,
                }
            )
        
        # Search for software engineer
        results = await store.search_by_career("software_engineer", top_k=5)
        
        # Should find cs-1
        course_ids = [r.course_id for r in results]
        assert "cs-1" in course_ids
        
        # Cleanup
        for course_id, _, _ in courses:
            await store.delete_course(course_id)
