"""LanceDB Vector Store for Course Embeddings.

Provides hybrid search capabilities combining vector similarity with
metadata filters for career goals, departments, and course attributes.

Features:
- Course-specific vector storage with 384-dimensional embeddings
- Hybrid search: vector similarity + metadata filtering
- Career-based course discovery
- Efficient batch operations for course catalogs
- Persistent storage to LanceDB format

Usage:
    >>> from src.vector.course_store import CourseVectorStore
    >>> store = CourseVectorStore()
    >>> await store.initialize()
    >>> 
    >>> # Add a course
    >>> await store.add_course(
    ...     course_id="cs-101",
    ...     embedding=[0.1, 0.2, ...],  # 384 dims
    ...     metadata={
    ...         "name": "Computer Science",
    ...         "department": "cs",
    ...         "math_intensity": 0.75,
    ...         "career_paths": ["software_engineer"],
    ...     }
    ... )
    >>> 
    >>> # Search by vector
    >>> results = await store.search_similar(
    ...     embedding=query_embedding,
    ...     top_k=5
    ... )
    >>> 
    >>> # Search by career goal
    >>> results = await store.search_by_career(
    ...     career_goal="software_engineer",
    ...     top_k=5
    ... )
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import numpy as np

from src.config import get_settings
from src.logging_config import get_logger
from src.security import InputValidator, get_validator

logger = get_logger(__name__)


@dataclass
class CourseVectorRecord:
    """A course vector record with metadata."""
    course_id: str
    name: str
    department: str
    embedding: List[float]
    math_intensity: float
    humanities_intensity: float
    career_paths: List[str]
    credits: int = 0
    description: str = ""
    additional_metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    score: Optional[float] = None
    
    def to_metadata_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "name": self.name,
            "department": self.department,
            "math_intensity": self.math_intensity,
            "humanities_intensity": self.humanities_intensity,
            "career_paths": self.career_paths,
            "credits": self.credits,
            "description": self.description,
            **self.additional_metadata,
        }
    
    @classmethod
    def from_metadata_dict(
        cls,
        course_id: str,
        embedding: List[float],
        metadata: Dict[str, Any],
        created_at: datetime,
        score: Optional[float] = None,
    ) -> CourseVectorRecord:
        """Create from stored metadata dictionary."""
        # Extract known fields
        known_fields = {
            "name", "department", "math_intensity", "humanities_intensity",
            "career_paths", "credits", "description",
        }
        
        additional = {k: v for k, v in metadata.items() if k not in known_fields}
        
        return cls(
            course_id=course_id,
            name=metadata.get("name", ""),
            department=metadata.get("department", ""),
            embedding=embedding,
            math_intensity=metadata.get("math_intensity", 0.0),
            humanities_intensity=metadata.get("humanities_intensity", 0.0),
            career_paths=metadata.get("career_paths", []),
            credits=metadata.get("credits", 0),
            description=metadata.get("description", ""),
            additional_metadata=additional,
            created_at=created_at,
            score=score,
        )


@dataclass
class CourseSearchResult:
    """Result from a course search."""
    course_id: str
    name: str
    department: str
    similarity_score: float
    vector_score: float
    metadata_score: float
    math_intensity: float
    humanities_intensity: float
    career_paths: List[str]
    credits: int
    description: str
    matched_careers: List[str] = field(default_factory=list)


class CourseVectorStore:
    """LanceDB-backed vector store for course embeddings.
    
    Provides course-specific operations including hybrid search
    that combines vector similarity with metadata filtering.
    
    Attributes:
        uri: Path to LanceDB storage directory
        dimension: Embedding dimension (default 384)
        index_type: Vector index type (IVF_PQ, HNSW, NONE)
        _db: LanceDB connection
        _table: LanceDB table reference
        _is_ready: Whether store is initialized
    
    Example:
        >>> store = CourseVectorStore(uri="./artifacts/course_vectors.lance")
        >>> await store.initialize()
        >>> 
        >>> # Add courses
        >>> for course in courses:
        ...     await store.add_course(
        ...         course_id=course.id,
        ...         embedding=course.embedding,
        ...         metadata={
        ...             "name": course.name,
        ...             "department": course.department,
        ...             "career_paths": course.career_paths,
        ...         }
        ...     )
        >>> 
        >>> # Search
        >>> results = await store.search_similar(query_embedding, top_k=5)
    """
    
    def __init__(
        self,
        uri: Optional[str] = None,
        dimension: int = 384,
        index_type: str = "IVF_PQ",
    ) -> None:
        """Initialize CourseVectorStore.
        
        Args:
            uri: Path to LanceDB storage (default from settings)
            dimension: Vector dimension (must match embedding model)
            index_type: Index type (IVF_PQ, HNSW, NONE)
        """
        settings = get_settings()
        self.uri = Path(uri or "artifacts/course_vectors.lance")
        self.dimension = dimension
        self.index_type = index_type
        
        self._db: Optional[Any] = None
        self._table: Optional[Any] = None
        self._is_ready = False

        # Security validator
        settings = get_settings()
        self._validator: InputValidator = get_validator()
        self._enable_validation: bool = settings.enable_query_validation
        self._max_query_length: int = settings.max_query_length

        # Fallback storage if LanceDB unavailable
        self._fallback_vectors: Dict[str, np.ndarray] = {}
        self._fallback_metadata: Dict[str, Dict] = {}
        self._use_fallback = False
    
    async def initialize(self) -> None:
        """Initialize LanceDB connection and create table.
        
        Creates the course_embeddings table with appropriate schema.
        Builds vector index if configured.
        """
        try:
            import lancedb
            import pyarrow as pa
            
            # Ensure directory exists
            self.uri.parent.mkdir(parents=True, exist_ok=True)
            
            # Connect to LanceDB
            self._db = await lancedb.connect_async(str(self.uri))
            
            # Define schema for course embeddings
            schema = pa.schema([
                ("course_id", pa.string()),
                ("vector", pa.list_(pa.float32(), self.dimension)),
                ("name", pa.string()),
                ("department", pa.string()),
                ("math_intensity", pa.float32()),
                ("humanities_intensity", pa.float32()),
                ("career_paths", pa.string()),  # JSON encoded list
                ("credits", pa.int32()),
                ("description", pa.string()),
                ("metadata", pa.string()),  # Additional JSON metadata
                ("created_at", pa.timestamp("us")),
            ])
            
            # Open or create table
            table_name = "course_embeddings"
            try:
                self._table = await self._db.open_table(table_name)
                logger.info("Opened existing course embeddings table", table=table_name)
            except FileNotFoundError:
                self._table = await self._db.create_table(
                    table_name,
                    schema=schema,
                )
                logger.info("Created new course embeddings table", table=table_name)
            
            # Create vector index if not exists and configured
            if self.index_type != "NONE":
                await self._create_index()
            
            self._is_ready = True
            logger.info(
                "CourseVectorStore initialized",
                uri=str(self.uri),
                dimension=self.dimension,
            )
            
        except ImportError:
            logger.warning(
                "LanceDB not installed, using fallback storage",
                uri=str(self.uri),
            )
            self._use_fallback = True
            self._is_ready = True
            
        except Exception as exc:
            logger.error("Failed to initialize CourseVectorStore", error=str(exc))
            self._use_fallback = True
            self._is_ready = True
    
    async def _create_index(self) -> None:
        """Create vector index for efficient search."""
        if not self._table:
            return
        
        try:
            # Check if index exists
            existing_indices = await self._table.list_indices()
            if existing_indices:
                logger.debug("Vector index already exists")
                return
            
            # Create IVF-PQ index (good balance of speed/recall)
            await self._table.create_index(
                column="vector",
                index_type=self.index_type,
                metric="cosine",
                num_partitions=64,  # Smaller for course catalogs
                num_sub_vectors=16,
            )
            logger.info("Created vector index", type=self.index_type)
            
        except Exception as exc:
            logger.warning("Failed to create vector index", error=str(exc))
    
    async def add_course(
        self,
        course_id: str,
        embedding: List[float],
        metadata: Dict[str, Any],
    ) -> None:
        """Add a course to the vector store.
        
        Args:
            course_id: Unique course identifier
            embedding: 384-dimensional embedding vector
            metadata: Course metadata including name, department, career_paths
        
        Example:
            >>> await store.add_course(
            ...     course_id="cs-101",
            ...     embedding=[0.1, 0.2, ...],  # 384 dims
            ...     metadata={
            ...         "name": "Computer Science",
            ...         "department": "cs",
            ...         "math_intensity": 0.75,
            ...         "humanities_intensity": 0.20,
            ...         "career_paths": ["software_engineer", "tech_lead"],
            ...         "credits": 4,
            ...         "description": "Study of computation...",
            ...     }
            ... )
        """
        if not self._is_ready:
            raise RuntimeError("CourseVectorStore not initialized")
        
        # Validate dimension
        if len(embedding) != self.dimension:
            raise ValueError(
                f"Embedding dimension {len(embedding)} doesn't match "
                f"store dimension {self.dimension}"
            )
        
        # Extract course fields from metadata
        name = metadata.get("name", "")
        department = metadata.get("department", "")
        math_intensity = metadata.get("math_intensity", 0.0)
        humanities_intensity = metadata.get("humanities_intensity", 0.0)
        career_paths = metadata.get("career_paths", [])
        credits = metadata.get("credits", 0)
        description = metadata.get("description", "")
        
        # Store additional metadata (excluding known fields)
        known_fields = {
            "name", "department", "math_intensity", "humanities_intensity",
            "career_paths", "credits", "description",
        }
        additional_metadata = {k: v for k, v in metadata.items() if k not in known_fields}
        
        if self._use_fallback:
            # Fallback to in-memory storage
            self._fallback_vectors[course_id] = np.array(embedding, dtype=np.float32)
            self._fallback_metadata[course_id] = {
                "name": name,
                "department": department,
                "math_intensity": math_intensity,
                "humanities_intensity": humanities_intensity,
                "career_paths": career_paths,
                "credits": credits,
                "description": description,
                "metadata": additional_metadata,
                "created_at": datetime.utcnow(),
            }
            return
        
        # Add to LanceDB
        try:
            import pyarrow as pa
            
            batch = pa.table({
                "course_id": [course_id],
                "vector": [embedding],
                "name": [name],
                "department": [department],
                "math_intensity": [float(math_intensity)],
                "humanities_intensity": [float(humanities_intensity)],
                "career_paths": [json.dumps(career_paths)],
                "credits": [int(credits)],
                "description": [description[:500]],  # Limit description length
                "metadata": [json.dumps(additional_metadata)],
                "created_at": [datetime.utcnow()],
            })
            
            await self._table.add(batch)
            logger.debug("Course added to vector store", course_id=course_id, name=name)
            
        except Exception as exc:
            logger.error("Failed to add course", course_id=course_id, error=str(exc))
            raise
    
    async def add_courses_batch(
        self,
        courses: List[Dict[str, Any]],
    ) -> None:
        """Add multiple courses in a batch operation.
        
        More efficient than individual add_course() calls.
        
        Args:
            courses: List of course dictionaries with keys:
                - course_id: str
                - embedding: List[float]
                - metadata: Dict[str, Any]
        
        Example:
            >>> courses = [
            ...     {
            ...         "course_id": "cs-101",
            ...         "embedding": [...],
            ...         "metadata": {...},
            ...     },
            ...     ...
            ... ]
            >>> await store.add_courses_batch(courses)
        """
        if not self._is_ready:
            raise RuntimeError("CourseVectorStore not initialized")
        
        if not courses:
            return
        
        if self._use_fallback:
            for course in courses:
                await self.add_course(
                    course_id=course["course_id"],
                    embedding=course["embedding"],
                    metadata=course.get("metadata", {}),
                )
            return
        
        try:
            import pyarrow as pa
            
            # Build batch data
            course_ids = []
            vectors = []
            names = []
            departments = []
            math_intensities = []
            humanities_intensities = []
            career_paths_list = []
            credits_list = []
            descriptions = []
            metadata_list = []
            created_ats = []
            
            for course in courses:
                metadata = course.get("metadata", {})
                known_fields = {
                    "name", "department", "math_intensity", "humanities_intensity",
                    "career_paths", "credits", "description",
                }
                additional = {k: v for k, v in metadata.items() if k not in known_fields}
                
                course_ids.append(course["course_id"])
                vectors.append(course["embedding"])
                names.append(metadata.get("name", ""))
                departments.append(metadata.get("department", ""))
                math_intensities.append(float(metadata.get("math_intensity", 0.0)))
                humanities_intensities.append(float(metadata.get("humanities_intensity", 0.0)))
                career_paths_list.append(json.dumps(metadata.get("career_paths", [])))
                credits_list.append(int(metadata.get("credits", 0)))
                descriptions.append(metadata.get("description", "")[:500])
                metadata_list.append(json.dumps(additional))
                created_ats.append(datetime.utcnow())
            
            batch = pa.table({
                "course_id": course_ids,
                "vector": vectors,
                "name": names,
                "department": departments,
                "math_intensity": math_intensities,
                "humanities_intensity": humanities_intensities,
                "career_paths": career_paths_list,
                "credits": credits_list,
                "description": descriptions,
                "metadata": metadata_list,
                "created_at": created_ats,
            })
            
            await self._table.add(batch)
            logger.debug("Batch courses added", count=len(courses))
            
        except Exception as exc:
            logger.error("Failed to add batch courses", count=len(courses), error=str(exc))
            raise
    
    async def search_similar(
        self,
        embedding: List[float],
        top_k: int = 5,
        department_filter: Optional[str] = None,
        min_math_intensity: Optional[float] = None,
        max_math_intensity: Optional[float] = None,
    ) -> List[CourseSearchResult]:
        """Search for courses by vector similarity.
        
        Performs cosine similarity search on course embeddings with
        optional metadata filters for department and math intensity.
        
        Args:
            embedding: Query embedding (384 dimensions)
            top_k: Number of results to return
            department_filter: Optional department to filter by
            min_math_intensity: Optional minimum math intensity (0-1)
            max_math_intensity: Optional maximum math intensity (0-1)
        
        Returns:
            List of CourseSearchResult ordered by similarity
        
        Example:
            >>> results = await store.search_similar(
            ...     embedding=query_embedding,
            ...     top_k=5,
            ...     department_filter="engineering",
            ...     min_math_intensity=0.7,
            ... )
            >>> for r in results:
            ...     print(f"{r.name}: {r.similarity_score:.3f}")
        """
        if not self._is_ready:
            raise RuntimeError("CourseVectorStore not initialized")

        # Validate embedding dimension
        if len(embedding) != self.dimension:
            raise ValueError(
                f"Query dimension {len(embedding)} doesn't match store dimension {self.dimension}"
            )

        # Validate inputs if security is enabled
        if self._enable_validation:
            self._validator.validate_vector_dimension(embedding, self.dimension)
            self._validator.validate_input_length(embedding)
            if department_filter:
                self._validator.validate_input_length(department_filter, 100)
            # Validate numeric ranges
            if min_math_intensity is not None:
                if not 0.0 <= min_math_intensity <= 1.0:
                    raise ValueError("min_math_intensity must be between 0.0 and 1.0")
            if max_math_intensity is not None:
                if not 0.0 <= max_math_intensity <= 1.0:
                    raise ValueError("max_math_intensity must be between 0.0 and 1.0")

        if self._use_fallback:
            return self._fallback_search(
                embedding=embedding,
                top_k=top_k,
                department_filter=department_filter,
                min_math_intensity=min_math_intensity,
                max_math_intensity=max_math_intensity,
            )

        try:
            # Build query with filters
            query = self._table.search(embedding).metric("cosine")

            # Apply department filter with proper escaping to prevent injection
            # LanceDB uses SQL-like syntax but we need to be careful
            if department_filter:
                # Sanitize department filter - only allow alphanumeric, dash, underscore
                import re
                safe_dept = re.sub(r'[^a-zA-Z0-9_-]', '', department_filter)
                if safe_dept:
                    query = query.where(f"department = '{safe_dept}'")

            # Apply math intensity filters (numeric values, safe from injection)
            if min_math_intensity is not None:
                query = query.where(f"math_intensity >= {float(min_math_intensity)}")
            if max_math_intensity is not None:
                query = query.where(f"math_intensity <= {float(max_math_intensity)}")

            # Execute search
            results = await query.limit(top_k).to_arrow()
            
            # Convert to CourseSearchResult
            search_results = []
            for row in results.to_pylist():
                # Convert cosine distance to similarity (1 - distance)
                vector_score = 1.0 - row.get("_distance", 0.0)
                
                career_paths = json.loads(row.get("career_paths", "[]"))
                
                search_results.append(CourseSearchResult(
                    course_id=row["course_id"],
                    name=row["name"],
                    department=row["department"],
                    similarity_score=vector_score,
                    vector_score=vector_score,
                    metadata_score=0.0,  # Pure vector search
                    math_intensity=row.get("math_intensity", 0.0),
                    humanities_intensity=row.get("humanities_intensity", 0.0),
                    career_paths=career_paths,
                    credits=row.get("credits", 0),
                    description=row.get("description", ""),
                ))
            
            return search_results
            
        except Exception as exc:
            logger.error("Search failed", error=str(exc))
            # Fallback to brute force
            return self._fallback_search(
                embedding=embedding,
                top_k=top_k,
                department_filter=department_filter,
                min_math_intensity=min_math_intensity,
                max_math_intensity=max_math_intensity,
            )
    
    async def search_by_career(
        self,
        career_goal: str,
        top_k: int = 5,
        embedding: Optional[List[float]] = None,
        vector_weight: float = 0.5,
    ) -> List[CourseSearchResult]:
        """Hybrid search by career goal with optional vector similarity.
        
        Combines career path matching with vector similarity for
        optimal course recommendations.
        
        Args:
            career_goal: Career path to search for (e.g., "software_engineer")
            top_k: Number of results to return
            embedding: Optional query embedding for vector similarity
            vector_weight: Weight for vector score (0-1), metadata score gets (1-weight)
        
        Returns:
            List of CourseSearchResult with combined scores
        
        Example:
            >>> # Pure career-based search
            >>> results = await store.search_by_career(
            ...     career_goal="aerospace_engineer",
            ...     top_k=5
            ... )
            >>> 
            >>> # Hybrid search with vector
            >>> results = await store.search_by_career(
            ...     career_goal="software_engineer",
            ...     embedding=student_embedding,
            ...     vector_weight=0.6,
            ...     top_k=5
            ... )
        """
        if not self._is_ready:
            raise RuntimeError("CourseVectorStore not initialized")
        
        if self._use_fallback:
            return self._fallback_career_search(
                career_goal=career_goal,
                top_k=top_k,
                embedding=embedding,
                vector_weight=vector_weight,
            )
        
        try:
            # First, get all courses (we'll filter and score in Python)
            # This is necessary because LanceDB doesn't support text search on JSON arrays
            results = await self._table.to_arrow()
            
            search_results = []
            query_vec = np.array(embedding, dtype=np.float32) if embedding else None
            
            for row in results.to_pylist():
                career_paths = json.loads(row.get("career_paths", "[]"))
                
                # Calculate career match score
                if career_goal in career_paths:
                    career_score = 1.0
                else:
                    # Check for partial matches
                    career_score = max(
                        (0.5 if career_goal in cp or cp in career_goal else 0.0)
                        for cp in career_paths
                    ) if career_paths else 0.0
                
                if career_score == 0 and embedding is None:
                    continue  # Skip non-matching courses if no vector search
                
                # Calculate vector score if embedding provided
                vector_score = 0.0
                if query_vec is not None:
                    course_vec = np.array(row["vector"], dtype=np.float32)
                    vector_score = self._cosine_similarity(query_vec, course_vec)
                
                # Combined score
                if embedding is not None:
                    combined_score = vector_weight * vector_score + (1 - vector_weight) * career_score
                else:
                    combined_score = career_score
                
                if combined_score > 0:
                    search_results.append(CourseSearchResult(
                        course_id=row["course_id"],
                        name=row["name"],
                        department=row["department"],
                        similarity_score=combined_score,
                        vector_score=vector_score,
                        metadata_score=career_score,
                        math_intensity=row.get("math_intensity", 0.0),
                        humanities_intensity=row.get("humanities_intensity", 0.0),
                        career_paths=career_paths,
                        credits=row.get("credits", 0),
                        description=row.get("description", ""),
                        matched_careers=[career_goal] if career_score > 0 else [],
                    ))
            
            # Sort by combined score and return top_k
            search_results.sort(key=lambda x: x.similarity_score, reverse=True)
            return search_results[:top_k]
            
        except Exception as exc:
            logger.error("Career search failed", error=str(exc))
            return self._fallback_career_search(
                career_goal=career_goal,
                top_k=top_k,
                embedding=embedding,
                vector_weight=vector_weight,
            )
    
    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return float(np.dot(a, b) / (norm_a * norm_b))
    
    def _fallback_search(
        self,
        embedding: List[float],
        top_k: int,
        department_filter: Optional[str],
        min_math_intensity: Optional[float],
        max_math_intensity: Optional[float],
    ) -> List[CourseSearchResult]:
        """Brute-force search using numpy (fallback)."""
        if not self._fallback_vectors:
            return []
        
        query_vec = np.array(embedding, dtype=np.float32)
        
        results = []
        for course_id, vector in self._fallback_vectors.items():
            metadata = self._fallback_metadata.get(course_id, {})
            
            # Apply filters
            if department_filter:
                if metadata.get("department") != department_filter:
                    continue
            
            math_intensity = metadata.get("math_intensity", 0.0)
            if min_math_intensity is not None and math_intensity < min_math_intensity:
                continue
            if max_math_intensity is not None and math_intensity > max_math_intensity:
                continue
            
            # Calculate similarity
            similarity = self._cosine_similarity(query_vec, vector)
            
            career_paths = metadata.get("career_paths", [])
            
            results.append(CourseSearchResult(
                course_id=course_id,
                name=metadata.get("name", ""),
                department=metadata.get("department", ""),
                similarity_score=similarity,
                vector_score=similarity,
                metadata_score=0.0,
                math_intensity=math_intensity,
                humanities_intensity=metadata.get("humanities_intensity", 0.0),
                career_paths=career_paths if isinstance(career_paths, list) else [],
                credits=metadata.get("credits", 0),
                description=metadata.get("description", ""),
            ))
        
        # Sort by similarity and return top_k
        results.sort(key=lambda x: x.similarity_score, reverse=True)
        return results[:top_k]
    
    def _fallback_career_search(
        self,
        career_goal: str,
        top_k: int,
        embedding: Optional[List[float]],
        vector_weight: float,
    ) -> List[CourseSearchResult]:
        """Brute-force career search (fallback)."""
        if not self._fallback_vectors:
            return []
        
        query_vec = np.array(embedding, dtype=np.float32) if embedding else None
        
        results = []
        for course_id, vector in self._fallback_vectors.items():
            metadata = self._fallback_metadata.get(course_id, {})
            career_paths = metadata.get("career_paths", [])
            
            # Calculate career match score
            if career_goal in career_paths:
                career_score = 1.0
            else:
                career_score = max(
                    (0.5 if career_goal in cp or cp in career_goal else 0.0)
                    for cp in career_paths
                ) if career_paths else 0.0
            
            if career_score == 0 and embedding is None:
                continue
            
            # Calculate vector score
            vector_score = 0.0
            if query_vec is not None:
                vector_score = self._cosine_similarity(query_vec, vector)
            
            # Combined score
            if embedding is not None:
                combined_score = vector_weight * vector_score + (1 - vector_weight) * career_score
            else:
                combined_score = career_score
            
            if combined_score > 0:
                results.append(CourseSearchResult(
                    course_id=course_id,
                    name=metadata.get("name", ""),
                    department=metadata.get("department", ""),
                    similarity_score=combined_score,
                    vector_score=vector_score,
                    metadata_score=career_score,
                    math_intensity=metadata.get("math_intensity", 0.0),
                    humanities_intensity=metadata.get("humanities_intensity", 0.0),
                    career_paths=career_paths if isinstance(career_paths, list) else [],
                    credits=metadata.get("credits", 0),
                    description=metadata.get("description", ""),
                    matched_careers=[career_goal] if career_score > 0 else [],
                ))
        
        # Sort by combined score
        results.sort(key=lambda x: x.similarity_score, reverse=True)
        return results[:top_k]
    
    async def get_course_count(self) -> int:
        """Get the total number of courses in the store."""
        if self._use_fallback:
            return len(self._fallback_vectors)
        
        try:
            results = await self._table.to_arrow()
            return len(results)
        except Exception:
            return 0
    
    async def delete_course(self, course_id: str) -> bool:
        """Delete a course from the store.

        Args:
            course_id: Course identifier to delete

        Returns:
            True if deleted, False if not found
        """
        # Validate course_id
        if self._enable_validation:
            try:
                self._validator.validate_node_id(course_id)
            except ValueError as e:
                logger.warning("Invalid course_id in delete_course", error=str(e))
                return False

        if self._use_fallback:
            if course_id in self._fallback_vectors:
                del self._fallback_vectors[course_id]
                del self._fallback_metadata[course_id]
                return True
            return False

        try:
            # Use parameterized delete to prevent injection
            # Sanitize course_id - only allow alphanumeric, dash, underscore
            import re
            safe_course_id = re.sub(r'[^a-zA-Z0-9_-]', '', course_id)
            if not safe_course_id:
                logger.warning("Invalid course_id after sanitization", course_id=course_id)
                return False

            await self._table.delete(f"course_id = '{safe_course_id}'")
            return True
        except Exception as exc:
            logger.error("Failed to delete course", course_id=course_id, error=str(exc))
            return False
