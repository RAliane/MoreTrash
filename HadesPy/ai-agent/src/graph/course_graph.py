"""Neo4j Course Graph Operations.

This module provides graph-based operations for courses in Neo4j,
including course node management, prerequisite relationships,
similarity relationships, and department organization.

Features:
- Course node CRUD operations with embedding support
- PREREQUISITE relationship management
- SIMILAR_TO relationships based on embedding similarity
- DEPARTMENT nodes with BELONGS_TO relationships
- Graph-based course discovery and filtering

Usage:
    >>> from src.graph.course_graph import CourseGraph
    >>> graph = CourseGraph()
    >>> await graph.initialize()
    >>> course = await graph.create_course({
    ...     "name": "Computer Science",
    ...     "department": "cs",
    ...     "math_intensity": 0.75,
    ...     "humanities_intensity": 0.20,
    ...     "career_paths": ["software_engineer"],
    ...     "embedding": [0.1, 0.2, ...]  # 384 dims
    ... })
    >>> similar = await graph.find_similar_courses(course.id, threshold=0.7)
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from neo4j import AsyncGraphDatabase, AsyncDriver

from src.config import get_settings
from src.logging_config import get_logger
from src.security import InputValidator, get_validator

logger = get_logger(__name__)


@dataclass
class CourseNode:
    """Course node representation from Neo4j."""
    id: str
    name: str
    description: str
    department: str
    credits: int
    math_intensity: float
    humanities_intensity: float
    career_paths: List[str]
    embedding: Optional[List[float]] = None
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CourseSubgraph:
    """Subgraph containing courses and their relationships."""
    courses: List[CourseNode]
    relationships: List[Dict[str, Any]]
    graph_distance: Dict[str, int]  # course_id -> distance from root


@dataclass
class SimilarityMatch:
    """Similar course match with similarity score."""
    course: CourseNode
    similarity: float


class CourseGraph:
    """Neo4j graph operations for course management.
    
    Manages Course nodes, PREREQUISITE relationships, SIMILAR_TO
    relationships, and DEPARTMENT organization in Neo4j.
    
    Attributes:
        uri: Neo4j connection URI
        user: Neo4j username
        password: Neo4j password
        database: Neo4j database name
        _driver: Async Neo4j driver instance
        _is_ready: Whether the graph is initialized
    
    Example:
        >>> graph = CourseGraph()
        >>> await graph.initialize()
        >>> # Create a course
        >>> course = await graph.create_course({...})
        >>> # Find similar courses
        >>> similar = await graph.find_similar_courses(course.id)
        >>> await graph.close()
    """
    
    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        database: str = "neo4j",
        similarity_threshold: float = 0.7,
    ) -> None:
        """Initialize CourseGraph.
        
        Args:
            uri: Neo4j URI (default from settings)
            user: Neo4j username (default from settings)
            password: Neo4j password (default from settings)
            database: Neo4j database name
            similarity_threshold: Default threshold for similarity matching
        """
        settings = get_settings()
        
        self.uri = uri or settings.neo4j_uri
        self.user = user or settings.neo4j_user
        self.password = password or settings.neo4j_password
        self.database = database
        self.similarity_threshold = similarity_threshold
        
        self._driver: Optional[AsyncDriver] = None
        self._is_ready = False

        # Security validator
        settings = get_settings()
        self._validator: InputValidator = get_validator()
        self._enable_validation: bool = settings.enable_query_validation
        self._max_query_length: int = settings.max_query_length

        # Update validator with config settings
        self._validator.allowed_relationships = set(settings.allowed_cypher_relationships_list)
    
    async def initialize(self) -> None:
        """Initialize Neo4j driver and create indexes.
        
        Creates necessary indexes for efficient course queries.
        Idempotent - safe to call multiple times.
        """
        try:
            self._driver = AsyncGraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password)
            )
            
            # Verify connectivity
            await self._driver.verify_connectivity()
            
            # Create indexes
            await self._create_indexes()
            
            self._is_ready = True
            logger.info(
                "CourseGraph initialized",
                uri=self.uri,
                database=self.database,
            )
            
        except Exception as exc:
            logger.error("Failed to initialize CourseGraph", error=str(exc))
            raise
    
    async def _create_indexes(self) -> None:
        """Create indexes for course queries."""
        if not self._driver:
            return
        
        index_queries = [
            # Course ID index
            """
            CREATE CONSTRAINT course_id_constraint IF NOT EXISTS
            FOR (c:Course) REQUIRE c.id IS UNIQUE
            """,
            # Department name index
            """
            CREATE CONSTRAINT department_name_constraint IF NOT EXISTS
            FOR (d:Department) REQUIRE d.name IS UNIQUE
            """,
            # Course name index for text search
            """
            CREATE INDEX course_name_index IF NOT EXISTS
            FOR (c:Course) ON (c.name)
            """,
            # Department index
            """
            CREATE INDEX course_department_index IF NOT EXISTS
            FOR (c:Course) ON (c.department)
            """,
            # Career paths index
            """
            CREATE INDEX course_career_paths_index IF NOT EXISTS
            FOR (c:Course) ON (c.careerPaths)
            """,
        ]
        
        async with self._driver.session(database=self.database) as session:
            for query in index_queries:
                try:
                    await session.run(query)
                except Exception as exc:
                    # Index may already exist or not be supported
                    logger.debug("Index creation skipped", query=query[:50], error=str(exc))
        
        logger.info("CourseGraph indexes created")
    
    async def close(self) -> None:
        """Close Neo4j driver connection."""
        if self._driver:
            await self._driver.close()
            self._driver = None
            self._is_ready = False
            logger.info("CourseGraph closed")
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    # ============================================
    # Course CRUD Operations
    # ============================================
    
    async def create_course(
        self,
        course_data: Dict[str, Any],
        course_id: Optional[str] = None,
    ) -> CourseNode:
        """Create or update a Course node (idempotent).
        
        Uses MERGE to ensure idempotency - if the course exists, it will be
        updated; if not, it will be created.
        
        Args:
            course_data: Dictionary with course properties
            course_id: Optional custom ID (UUID generated if not provided)
        
        Returns:
            CourseNode (created or updated)
        
        Example:
            >>> course = await graph.create_course({
            ...     "name": "Computer Science",
            ...     "description": "Study of computation",
            ...     "department": "cs",
            ...     "credits": 4,
            ...     "math_intensity": 0.75,
            ...     "humanities_intensity": 0.20,
            ...     "career_paths": ["software_engineer"],
            ...     "embedding": [0.1, 0.2, ...]  # 384 dimensions
            ... })
        """
        if not self._is_ready:
            raise RuntimeError("CourseGraph not initialized")
        
        course_id = course_id or str(uuid.uuid4())
        
        # Extract fields with defaults
        name = course_data.get("name", "")
        description = course_data.get("description", "")
        department = course_data.get("department", "")
        credits = course_data.get("credits", 0)
        math_intensity = course_data.get("math_intensity", 0.0)
        humanities_intensity = course_data.get("humanities_intensity", 0.0)
        career_paths = course_data.get("career_paths", [])
        embedding = course_data.get("embedding")
        
        async with self._driver.session(database=self.database) as session:
            # Merge course node (idempotent - updates if exists, creates if not)
            result = await session.run("""
                MERGE (c:Course {id: $id})
                ON CREATE SET c.name = $name,
                    c.description = $description,
                    c.department = $department,
                    c.credits = $credits,
                    c.mathIntensity = $math_intensity,
                    c.humanitiesIntensity = $humanities_intensity,
                    c.careerPaths = $career_paths,
                    c.createdAt = datetime()
                ON MATCH SET c.name = $name,
                    c.description = $description,
                    c.department = $department,
                    c.credits = $credits,
                    c.mathIntensity = $math_intensity,
                    c.humanitiesIntensity = $humanities_intensity,
                    c.careerPaths = $career_paths
                SET c.updatedAt = datetime()
                WITH c
                WHERE $embedding IS NOT NULL
                CALL db.create.setNodeVectorProperty(c, 'embedding', $embedding)
                RETURN c;
            """, {
                'id': course_id,
                'name': name,
                'description': description,
                'department': department,
                'credits': credits,
                'math_intensity': math_intensity,
                'humanities_intensity': humanities_intensity,
                'career_paths': career_paths,
                'embedding': embedding,
            })
            
            record = await result.single()
            
            if not record:
                raise RuntimeError(f"Failed to create course: {name}")
            
            logger.info("Course merged", course_id=course_id, name=name)
            
            return CourseNode(
                id=course_id,
                name=name,
                description=description,
                department=department,
                credits=credits,
                math_intensity=math_intensity,
                humanities_intensity=humanities_intensity,
                career_paths=career_paths,
                embedding=embedding,
            )
    
    async def get_course(self, course_id: str) -> Optional[CourseNode]:
        """Get a course by ID.
        
        Args:
            course_id: Course identifier
        
        Returns:
            CourseNode if found, None otherwise
        """
        if not self._is_ready:
            raise RuntimeError("CourseGraph not initialized")
        
        async with self._driver.session(database=self.database) as session:
            result = await session.run("""
                MATCH (c:Course {id: $id})
                RETURN c {
                    .id, .name, .description, .department, .credits,
                    .mathIntensity, .humanitiesIntensity, .careerPaths,
                    embedding: c.embedding
                } AS course
            """, {'id': course_id})
            
            record = await result.single()
            
            if not record or not record['course']:
                return None
            
            data = record['course']
            return CourseNode(
                id=data['id'],
                name=data['name'],
                description=data.get('description', ''),
                department=data.get('department', ''),
                credits=data.get('credits', 0),
                math_intensity=data.get('mathIntensity', 0.0),
                humanities_intensity=data.get('humanitiesIntensity', 0.0),
                career_paths=data.get('careerPaths', []),
                embedding=data.get('embedding'),
            )
    
    async def update_course(
        self,
        course_id: str,
        updates: Dict[str, Any],
    ) -> Optional[CourseNode]:
        """Update a course's properties.
        
        Args:
            course_id: Course identifier
            updates: Dictionary of properties to update
        
        Returns:
            Updated CourseNode if found, None otherwise
        """
        if not self._is_ready:
            raise RuntimeError("CourseGraph not initialized")

        # Validate course_id
        if self._enable_validation:
            self._validator.validate_node_id(course_id)
            self._validator.validate_input_length(updates)

        # Map field names from Python convention to Neo4j property names
        field_mapping = {
            'math_intensity': 'mathIntensity',
            'humanities_intensity': 'humanitiesIntensity',
            'career_paths': 'careerPaths',
        }

        # Build update params with sanitized keys
        update_params: Dict[str, Any] = {'id': course_id}

        # Only allow specific fields to prevent injection
        allowed_fields = {
            'name', 'description', 'department', 'credits',
            'math_intensity', 'humanities_intensity', 'career_paths',
        }

        for key, value in updates.items():
            if key == 'embedding':
                continue  # Handle separately
            if key not in allowed_fields:
                logger.warning("Ignoring unknown field in update", field=key)
                continue
            neo4j_key = field_mapping.get(key, key)
            # Sanitize the key for use as parameter name
            safe_key = self._validator.sanitize_cypher_identifier(neo4j_key)
            update_params[safe_key] = value

        if not update_params or len(update_params) <= 1:  # Only 'id' present
            # Just update the timestamp if no other fields
            update_params['update_placeholder'] = True

        async with self._driver.session(database=self.database) as session:
            # Update properties using a parameterized query
            # We use SET with individual assignments to avoid dynamic query building
            query = """
                MATCH (c:Course {id: $id})
                SET c.updatedAt = datetime()
            """

            # Add SET clauses for each field using parameterized values
            for key in updates.keys():
                if key == 'embedding' or key not in allowed_fields:
                    continue
                neo4j_key = field_mapping.get(key, key)
                safe_key = self._validator.sanitize_cypher_identifier(neo4j_key)
                # Use APOC or individual SET statements with parameters
                query += f"""
                SET c.{safe_key} = ${safe_key}"""

            query += """
                RETURN c
            """

            if len(update_params) > 1:  # Has actual updates besides id
                await session.run(query, update_params)

            # Update embedding if provided
            if 'embedding' in updates:
                await session.run("""
                    MATCH (c:Course {id: $id})
                    CALL db.create.setNodeVectorProperty(c, 'embedding', $embedding)
                    RETURN c
                """, {'id': course_id, 'embedding': updates['embedding']})

            logger.info("Course updated", course_id=course_id)

            return await self.get_course(course_id)
    
    async def delete_course(self, course_id: str) -> bool:
        """Delete a course and its relationships.
        
        Args:
            course_id: Course identifier
        
        Returns:
            True if deleted, False if not found
        """
        if not self._is_ready:
            raise RuntimeError("CourseGraph not initialized")
        
        async with self._driver.session(database=self.database) as session:
            result = await session.run("""
                MATCH (c:Course {id: $id})
                OPTIONAL MATCH (c)-[r]-()
                DELETE r, c
                RETURN count(c) AS deleted
            """, {'id': course_id})
            
            record = await result.single()
            deleted = record['deleted'] if record else 0
            
            if deleted > 0:
                logger.info("Course deleted", course_id=course_id)
                return True
            return False
    
    # ============================================
    # Prerequisite Relationships
    # ============================================
    
    async def add_prerequisite(
        self,
        course_id: str,
        prerequisite_id: str,
    ) -> bool:
        """Add a PREREQUISITE relationship between courses.
        
        Creates (Course)-[:PREREQUISITE]->(PrereqCourse) relationship.
        
        Args:
            course_id: The course that has the prerequisite
            prerequisite_id: The prerequisite course
        
        Returns:
            True if relationship created, False if courses not found
        """
        if not self._is_ready:
            raise RuntimeError("CourseGraph not initialized")
        
        async with self._driver.session(database=self.database) as session:
            result = await session.run("""
                MATCH (c:Course {id: $course_id})
                MATCH (p:Course {id: $prerequisite_id})
                MERGE (c)-[r:PREREQUISITE]->(p)
                SET r.createdAt = datetime()
                RETURN r
            """, {
                'course_id': course_id,
                'prerequisite_id': prerequisite_id,
            })
            
            record = await result.single()
            
            if record:
                logger.info(
                    "Prerequisite added",
                    course_id=course_id,
                    prerequisite_id=prerequisite_id,
                )
                return True
            return False
    
    async def remove_prerequisite(
        self,
        course_id: str,
        prerequisite_id: str,
    ) -> bool:
        """Remove a PREREQUISITE relationship.
        
        Args:
            course_id: The course that has the prerequisite
            prerequisite_id: The prerequisite course
        
        Returns:
            True if relationship removed, False if not found
        """
        if not self._is_ready:
            raise RuntimeError("CourseGraph not initialized")
        
        async with self._driver.session(database=self.database) as session:
            result = await session.run("""
                MATCH (c:Course {id: $course_id})
                      -[r:PREREQUISITE]->
                      (p:Course {id: $prerequisite_id})
                DELETE r
                RETURN count(r) AS deleted
            """, {
                'course_id': course_id,
                'prerequisite_id': prerequisite_id,
            })
            
            record = await result.single()
            deleted = record['deleted'] if record else 0
            
            return deleted > 0
    
    async def get_prerequisites(self, course_id: str) -> List[CourseNode]:
        """Get all prerequisites for a course.
        
        Args:
            course_id: Course identifier
        
        Returns:
            List of prerequisite CourseNodes
        """
        if not self._is_ready:
            raise RuntimeError("CourseGraph not initialized")
        
        async with self._driver.session(database=self.database) as session:
            result = await session.run("""
                MATCH (c:Course {id: $id})-[:PREREQUISITE]->(p:Course)
                RETURN p {
                    .id, .name, .description, .department, .credits,
                    .mathIntensity, .humanitiesIntensity, .careerPaths
                } AS prereq
            """, {'id': course_id})
            
            records = await result.data()
            
            return [
                CourseNode(
                    id=r['prereq']['id'],
                    name=r['prereq']['name'],
                    description=r['prereq'].get('description', ''),
                    department=r['prereq'].get('department', ''),
                    credits=r['prereq'].get('credits', 0),
                    math_intensity=r['prereq'].get('mathIntensity', 0.0),
                    humanities_intensity=r['prereq'].get('humanitiesIntensity', 0.0),
                    career_paths=r['prereq'].get('careerPaths', []),
                )
                for r in records if r['prereq']
            ]
    
    async def get_courses_requiring_prerequisite(self, prerequisite_id: str) -> List[CourseNode]:
        """Get all courses that require a given course as prerequisite.
        
        Args:
            prerequisite_id: Prerequisite course identifier
        
        Returns:
            List of CourseNodes that have this prerequisite
        """
        if not self._is_ready:
            raise RuntimeError("CourseGraph not initialized")
        
        async with self._driver.session(database=self.database) as session:
            result = await session.run("""
                MATCH (c:Course)-[:PREREQUISITE]->(p:Course {id: $id})
                RETURN c {
                    .id, .name, .description, .department, .credits,
                    .mathIntensity, .humanitiesIntensity, .careerPaths
                } AS course
            """, {'id': prerequisite_id})
            
            records = await result.data()
            
            return [
                CourseNode(
                    id=r['course']['id'],
                    name=r['course']['name'],
                    description=r['course'].get('description', ''),
                    department=r['course'].get('department', ''),
                    credits=r['course'].get('credits', 0),
                    math_intensity=r['course'].get('mathIntensity', 0.0),
                    humanities_intensity=r['course'].get('humanitiesIntensity', 0.0),
                    career_paths=r['course'].get('careerPaths', []),
                )
                for r in records if r['course']
            ]
    
    # ============================================
    # Similarity Relationships
    # ============================================
    
    async def find_similar_courses(
        self,
        course_id: str,
        threshold: Optional[float] = None,
        top_k: int = 5,
    ) -> List[SimilarityMatch]:
        """Find similar courses based on embedding cosine similarity.
        
        Uses Neo4j's vector similarity computation on course embeddings.
        Creates SIMILAR_TO relationships for discovered similarities.
        
        Args:
            course_id: Reference course ID
            threshold: Minimum similarity score (0-1, default from init)
            top_k: Maximum number of results
        
        Returns:
            List of SimilarityMatch with course and similarity score
        
        Example:
            >>> similar = await graph.find_similar_courses(
            ...     course_id="course-123",
            ...     threshold=0.7,
            ...     top_k=5
            ... )
            >>> for match in similar:
            ...     print(f"{match.course.name}: {match.similarity:.2f}")
        """
        if not self._is_ready:
            raise RuntimeError("CourseGraph not initialized")
        
        threshold = threshold or self.similarity_threshold
        
        async with self._driver.session(database=self.database) as session:
            # Find similar courses using vector similarity
            result = await session.run("""
                MATCH (c1:Course {id: $course_id})
                WHERE c1.embedding IS NOT NULL
                MATCH (c2:Course)
                WHERE c2.embedding IS NOT NULL
                  AND c1.id <> c2.id
                WITH c1, c2,
                     // Calculate dot product
                     reduce(dot = 0.0, i in range(0, size(c1.embedding)-1) | dot + c1.embedding[i] * c2.embedding[i])
                     /
                     // Divide by magnitudes
                     (sqrt(reduce(s = 0.0, x in c1.embedding | s + x^2)) * sqrt(reduce(s = 0.0, x in c2.embedding | s + x^2)))
                     AS similarity
                WHERE similarity >= $threshold
                RETURN c2 {
                    .id, .name, .description, .department, .credits,
                    .mathIntensity, .humanitiesIntensity, .careerPaths
                } AS course,
                similarity
                ORDER BY similarity DESC
                LIMIT $top_k
            """, {
                'course_id': course_id,
                'threshold': threshold,
                'top_k': top_k,
            })
            
            records = await result.data()
            
            matches = []
            for r in records:
                if not r['course']:
                    continue
                    
                course_data = r['course']
                matches.append(SimilarityMatch(
                    course=CourseNode(
                        id=course_data['id'],
                        name=course_data['name'],
                        description=course_data.get('description', ''),
                        department=course_data.get('department', ''),
                        credits=course_data.get('credits', 0),
                        math_intensity=course_data.get('mathIntensity', 0.0),
                        humanities_intensity=course_data.get('humanitiesIntensity', 0.0),
                        career_paths=course_data.get('careerPaths', []),
                    ),
                    similarity=r['similarity'],
                ))
            
            # Create SIMILAR_TO relationships for these matches
            for match in matches:
                await session.run("""
                    MATCH (c1:Course {id: $course_id})
                    MATCH (c2:Course {id: $similar_id})
                    MERGE (c1)-[r:SIMILAR_TO]->(c2)
                    SET r.similarity = $similarity,
                        r.createdAt = datetime()
                """, {
                    'course_id': course_id,
                    'similar_id': match.course.id,
                    'similarity': match.similarity,
                })
            
            logger.info(
                "Similar courses found",
                course_id=course_id,
                count=len(matches),
                threshold=threshold,
            )
            
            return matches
    
    async def get_similar_courses_from_relationship(
        self,
        course_id: str,
        min_similarity: Optional[float] = None,
    ) -> List[SimilarityMatch]:
        """Get similar courses from existing SIMILAR_TO relationships.
        
        Args:
            course_id: Reference course ID
            min_similarity: Minimum similarity from relationship
        
        Returns:
            List of SimilarityMatch from relationships
        """
        if not self._is_ready:
            raise RuntimeError("CourseGraph not initialized")
        
        query = """
            MATCH (c:Course {id: $course_id})-[r:SIMILAR_TO]->(s:Course)
        """
        
        if min_similarity is not None:
            query += " WHERE r.similarity >= $min_similarity"
        
        query += """
            RETURN s {
                .id, .name, .description, .department, .credits,
                .mathIntensity, .humanitiesIntensity, .careerPaths
            } AS course,
            r.similarity AS similarity
            ORDER BY r.similarity DESC
        """
        
        async with self._driver.session(database=self.database) as session:
            result = await session.run(query, {
                'course_id': course_id,
                'min_similarity': min_similarity,
            })
            
            records = await result.data()
            
            return [
                SimilarityMatch(
                    course=CourseNode(
                        id=r['course']['id'],
                        name=r['course']['name'],
                        description=r['course'].get('description', ''),
                        department=r['course'].get('department', ''),
                        credits=r['course'].get('credits', 0),
                        math_intensity=r['course'].get('mathIntensity', 0.0),
                        humanities_intensity=r['course'].get('humanitiesIntensity', 0.0),
                        career_paths=r['course'].get('careerPaths', []),
                    ),
                    similarity=r['similarity'],
                )
                for r in records if r['course']
            ]
    
    # ============================================
    # Department Organization
    # ============================================
    
    async def create_department(self, name: str, properties: Optional[Dict] = None) -> str:
        """Create a Department node.
        
        Args:
            name: Department name (unique identifier)
            properties: Optional additional properties
        
        Returns:
            Department name
        """
        if not self._is_ready:
            raise RuntimeError("CourseGraph not initialized")
        
        props = properties or {}
        
        async with self._driver.session(database=self.database) as session:
            await session.run("""
                MERGE (d:Department {name: $name})
                SET d.properties = $properties,
                    d.updatedAt = datetime()
                RETURN d
            """, {
                'name': name,
                'properties': props,
            })
            
            logger.info("Department created/updated", name=name)
            return name
    
    async def add_course_to_department(
        self,
        course_id: str,
        department_name: str,
    ) -> bool:
        """Add a course to a department.
        
        Creates Department node if it doesn't exist and
        creates (Course)-[:BELONGS_TO]->(Department) relationship.
        
        Args:
            course_id: Course identifier
            department_name: Department name
        
        Returns:
            True if successful
        """
        if not self._is_ready:
            raise RuntimeError("CourseGraph not initialized")
        
        async with self._driver.session(database=self.database) as session:
            result = await session.run("""
                MATCH (c:Course {id: $course_id})
                MERGE (d:Department {name: $department_name})
                MERGE (c)-[r:BELONGS_TO]->(d)
                SET r.createdAt = datetime()
                RETURN r
            """, {
                'course_id': course_id,
                'department_name': department_name,
            })
            
            record = await result.single()
            
            if record:
                logger.info(
                    "Course added to department",
                    course_id=course_id,
                    department=department_name,
                )
                return True
            return False
    
    async def get_courses_by_department(self, department_name: str) -> List[CourseNode]:
        """Get all courses in a department.
        
        Args:
            department_name: Department name
        
        Returns:
            List of CourseNodes in the department
        """
        if not self._is_ready:
            raise RuntimeError("CourseGraph not initialized")
        
        async with self._driver.session(database=self.database) as session:
            result = await session.run("""
                MATCH (c:Course)-[:BELONGS_TO]->(d:Department {name: $name})
                RETURN c {
                    .id, .name, .description, .department, .credits,
                    .mathIntensity, .humanitiesIntensity, .careerPaths
                } AS course
            """, {'name': department_name})
            
            records = await result.data()
            
            return [
                CourseNode(
                    id=r['course']['id'],
                    name=r['course']['name'],
                    description=r['course'].get('description', ''),
                    department=r['course'].get('department', ''),
                    credits=r['course'].get('credits', 0),
                    math_intensity=r['course'].get('mathIntensity', 0.0),
                    humanities_intensity=r['course'].get('humanitiesIntensity', 0.0),
                    career_paths=r['course'].get('careerPaths', []),
                )
                for r in records if r['course']
            ]
    
    # ============================================
    # Graph Traversal & Subgraph Extraction
    # ============================================
    
    async def get_course_subgraph(
        self,
        course_id: str,
        depth: int = 2,
        include_similar: bool = True,
    ) -> CourseSubgraph:
        """Extract a subgraph around a course.
        
        Retrieves courses within specified depth from the root course,
        including PREREQUISITE and optionally SIMILAR_TO relationships.
        
        Args:
            course_id: Root course ID
            depth: Maximum traversal depth (default 2)
            include_similar: Whether to include SIMILAR_TO relationships
        
        Returns:
            CourseSubgraph with courses, relationships, and distances
        
        Example:
            >>> subgraph = await graph.get_course_subgraph(
            ...     course_id="course-123",
            ...     depth=2,
            ...     include_similar=True
            ... )
            >>> for course in subgraph.courses:
            ...     distance = subgraph.graph_distance[course.id]
            ...     print(f"{course.name} (distance: {distance})")
        """
        if not self._is_ready:
            raise RuntimeError("CourseGraph not initialized")

        # Validate inputs
        if self._enable_validation:
            self._validator.validate_node_id(course_id)

        # Limit depth to prevent DoS
        safe_depth = min(max(depth, 1), 10)

        async with self._driver.session(database=self.database) as session:
            # Use hardcoded relationship patterns to avoid dynamic query building
            # These patterns are validated against the allowlist
            if include_similar:
                # Query with SIMILAR_TO relationships included
                result = await session.run("""
                    MATCH path = (root:Course {id: $course_id})
                        -[:PREREQUISITE|PREREQUISITE_OF|SIMILAR_TO*1..""" + str(safe_depth) + """]-
                        (connected:Course)
                    WITH root, connected,
                         min(length(path)) AS distance
                    RETURN connected {
                        .id, .name, .description, .department, .credits,
                        .mathIntensity, .humanitiesIntensity, .careerPaths
                    } AS course,
                    distance
                    ORDER BY distance
                """, {'course_id': course_id})
            else:
                # Query without SIMILAR_TO (only PREREQUISITE relationships)
                result = await session.run("""
                    MATCH path = (root:Course {id: $course_id})
                        -[:PREREQUISITE|PREREQUISITE_OF*1..""" + str(safe_depth) + """]-
                        (connected:Course)
                    WITH root, connected,
                         min(length(path)) AS distance
                    RETURN connected {
                        .id, .name, .description, .department, .credits,
                        .mathIntensity, .humanitiesIntensity, .careerPaths
                    } AS course,
                    distance
                    ORDER BY distance
                """, {'course_id': course_id})
            
            records = await result.data()
            
            courses = []
            graph_distance = {course_id: 0}  # Root has distance 0
            course_ids = {course_id}
            
            for r in records:
                if not r['course']:
                    continue
                    
                course_data = r['course']
                cid = course_data['id']
                
                if cid not in course_ids:
                    course_ids.add(cid)
                    graph_distance[cid] = r['distance']
                    courses.append(CourseNode(
                        id=cid,
                        name=course_data['name'],
                        description=course_data.get('description', ''),
                        department=course_data.get('department', ''),
                        credits=course_data.get('credits', 0),
                        math_intensity=course_data.get('mathIntensity', 0.0),
                        humanities_intensity=course_data.get('humanitiesIntensity', 0.0),
                        career_paths=course_data.get('careerPaths', []),
                    ))
            
            # Get relationships between these courses
            rel_result = await session.run("""
                MATCH (c1:Course)-[r:PREREQUISITE|SIMILAR_TO]->(c2:Course)
                WHERE c1.id IN $course_ids AND c2.id IN $course_ids
                RETURN c1.id AS from_id, type(r) AS rel_type, 
                       c2.id AS to_id, r.similarity AS similarity
            """, {'course_ids': list(course_ids)})
            
            rel_records = await rel_result.data()
            
            relationships = [
                {
                    'from': r['from_id'],
                    'to': r['to_id'],
                    'type': r['rel_type'],
                    'similarity': r.get('similarity'),
                }
                for r in rel_records
            ]
            
            logger.info(
                "Course subgraph extracted",
                root_course=course_id,
                courses=len(courses),
                relationships=len(relationships),
                depth=depth,
            )
            
            return CourseSubgraph(
                courses=courses,
                relationships=relationships,
                graph_distance=graph_distance,
            )
    
    async def find_courses_by_career_path(
        self,
        career_goal: str,
        limit: int = 10,
    ) -> List[CourseNode]:
        """Find courses that lead to a specific career path.
        
        Uses graph traversal to find courses with matching career paths.
        
        Args:
            career_goal: Career path identifier (e.g., "software_engineer")
            limit: Maximum number of results
        
        Returns:
            List of CourseNodes with matching career paths
        """
        if not self._is_ready:
            raise RuntimeError("CourseGraph not initialized")
        
        async with self._driver.session(database=self.database) as session:
            result = await session.run("""
                MATCH (c:Course)
                WHERE $career_goal IN c.careerPaths
                RETURN c {
                    .id, .name, .description, .department, .credits,
                    .mathIntensity, .humanitiesIntensity, .careerPaths
                } AS course
                ORDER BY c.mathIntensity DESC
                LIMIT $limit
            """, {
                'career_goal': career_goal,
                'limit': limit,
            })
            
            records = await result.data()
            
            return [
                CourseNode(
                    id=r['course']['id'],
                    name=r['course']['name'],
                    description=r['course'].get('description', ''),
                    department=r['course'].get('department', ''),
                    credits=r['course'].get('credits', 0),
                    math_intensity=r['course'].get('mathIntensity', 0.0),
                    humanities_intensity=r['course'].get('humanitiesIntensity', 0.0),
                    career_paths=r['course'].get('careerPaths', []),
                )
                for r in records if r['course']
            ]
    
    async def check_prerequisites_met(
        self,
        course_id: str,
        completed_course_ids: List[str],
    ) -> Tuple[bool, List[CourseNode]]:
        """Check if prerequisites are met for a course.
        
        Args:
            course_id: Course to check
            completed_course_ids: List of completed course IDs
        
        Returns:
            Tuple of (all_met: bool, missing: List[CourseNode])
        """
        if not self._is_ready:
            raise RuntimeError("CourseGraph not initialized")
        
        prerequisites = await self.get_prerequisites(course_id)
        
        missing = []
        for prereq in prerequisites:
            if prereq.id not in completed_course_ids:
                missing.append(prereq)
        
        all_met = len(missing) == 0
        
        return all_met, missing
