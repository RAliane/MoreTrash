"""Directus-Neo4j Bridge for Bidirectional Sync.

This module provides synchronization between Directus (PostgreSQL + pgvector)
and Neo4j graph database. It syncs courses, students, and their relationships.

Features:
- Sync courses from Directus to Neo4j as nodes with embeddings
- Create PREREQUISITE relationships in Neo4j
- Sync student embeddings to Neo4j
- Bidirectional sync methods

Usage:
    >>> from src.integrations.directus_neo4j_bridge import DirectusNeo4jBridge
    >>> bridge = DirectusNeo4jBridge()
    >>> await bridge.sync_all()
"""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

import asyncpg
from neo4j import AsyncGraphDatabase, AsyncDriver

from src.config import get_settings
from src.logging_config import get_logger
from src.security import InputValidator, get_validator

logger = get_logger(__name__)


@dataclass
class Course:
    """Course entity from Directus."""
    id: str
    name: str
    description: str
    department: str
    credits: int
    math_intensity: float
    humanities_intensity: float
    career_paths: List[str]
    embedding: Optional[List[float]] = None


@dataclass
class Student:
    """Student entity from Directus."""
    id: str
    name: str
    preferences: Dict[str, Any]
    career_goal: Optional[str]
    embedding: Optional[List[float]] = None


@dataclass
class Prerequisite:
    """Prerequisite relationship."""
    course_id: str
    prerequisite_id: str


class DirectusNeo4jBridge:
    """Bridge for syncing data between Directus and Neo4j.
    
    Attributes:
        pg_pool: Async PostgreSQL connection pool
        neo4j_driver: Async Neo4j driver
        batch_size: Number of records to process per batch
    """
    
    def __init__(
        self,
        pg_host: Optional[str] = None,
        pg_port: Optional[int] = None,
        pg_database: Optional[str] = None,
        pg_user: Optional[str] = None,
        pg_password: Optional[str] = None,
        neo4j_uri: Optional[str] = None,
        neo4j_user: Optional[str] = None,
        neo4j_password: Optional[str] = None,
        batch_size: int = 100,
    ):
        """Initialize the bridge.
        
        Args:
            pg_host: PostgreSQL host
            pg_port: PostgreSQL port
            pg_database: PostgreSQL database name
            pg_user: PostgreSQL user
            pg_password: PostgreSQL password
            neo4j_uri: Neo4j connection URI
            neo4j_user: Neo4j username
            neo4j_password: Neo4j password
            batch_size: Number of records per batch
        """
        settings = get_settings()
        
        # PostgreSQL configuration
        self.pg_host = pg_host or os.getenv("DB_HOST", "localhost")
        self.pg_port = pg_port or int(os.getenv("DB_PORT", "5432"))
        self.pg_database = pg_database or os.getenv("DB_DATABASE", "directus")
        self.pg_user = pg_user or os.getenv("DB_USER", "directus")
        self.pg_password = pg_password or os.getenv("DB_PASSWORD", "directus")
        
        # Neo4j configuration
        self.neo4j_uri = neo4j_uri or os.getenv(
            "NEO4J_URI", 
            os.getenv("PG_NEO4J_URI", "bolt://localhost:7687")
        )
        self.neo4j_user = neo4j_user or os.getenv(
            "NEO4J_USER", 
            os.getenv("PG_NEO4J_USER", "neo4j")
        )
        self.neo4j_password = neo4j_password or os.getenv(
            "NEO4J_PASSWORD",
            os.getenv("PG_NEO4J_PASSWORD", "password")
        )
        
        self.batch_size = batch_size
        self._pg_pool: Optional[asyncpg.Pool] = None
        self._neo4j_driver: Optional[AsyncDriver] = None

        # Security validator
        settings = get_settings()
        self._validator: InputValidator = get_validator()
        self._enable_validation: bool = settings.enable_query_validation
        self._webhook_secret: Optional[str] = settings.webhook_secret
        self._enable_webhook_verification: bool = settings.enable_webhook_signature_verification
    
    async def _get_pg_pool(self) -> asyncpg.Pool:
        """Get or create PostgreSQL connection pool."""
        if self._pg_pool is None:
            self._pg_pool = await asyncpg.create_pool(
                host=self.pg_host,
                port=self.pg_port,
                database=self.pg_database,
                user=self.pg_user,
                password=self.pg_password,
                min_size=2,
                max_size=10,
            )
            logger.info("PostgreSQL connection pool created")
        return self._pg_pool
    
    async def _get_neo4j_driver(self) -> AsyncDriver:
        """Get or create Neo4j driver."""
        if self._neo4j_driver is None:
            self._neo4j_driver = AsyncGraphDatabase.driver(
                self.neo4j_uri,
                auth=(self.neo4j_user, self.neo4j_password)
            )
            # Verify connectivity
            await self._neo4j_driver.verify_connectivity()
            logger.info("Neo4j driver connected")
        return self._neo4j_driver
    
    async def close(self):
        """Close all connections."""
        if self._pg_pool:
            await self._pg_pool.close()
            self._pg_pool = None
            logger.info("PostgreSQL connection pool closed")
        
        if self._neo4j_driver:
            await self._neo4j_driver.close()
            self._neo4j_driver = None
            logger.info("Neo4j driver closed")
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    # ============================================
    # DIRECTUS → NEO4J SYNC
    # ============================================
    
    async def fetch_courses(self) -> List[Course]:
        """Fetch all courses from Directus PostgreSQL.
        
        Returns:
            List of Course entities with embeddings
        """
        pool = await self._get_pg_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT 
                    id::text,
                    name,
                    description,
                    department,
                    credits,
                    math_intensity,
                    humanities_intensity,
                    career_paths,
                    embedding::text
                FROM courses
                WHERE status = 'published'
                ORDER BY name;
            """)
            
            courses = []
            for row in rows:
                embedding = None
                if row['embedding']:
                    # Parse vector string "[0.1, 0.2, ...]" to list
                    embedding_str = row['embedding'].strip('[]')
                    if embedding_str:
                        embedding = [float(x) for x in embedding_str.split(',')]
                
                career_paths = row['career_paths']
                if isinstance(career_paths, str):
                    career_paths = json.loads(career_paths)
                
                courses.append(Course(
                    id=row['id'],
                    name=row['name'],
                    description=row['description'] or '',
                    department=row['department'],
                    credits=row['credits'],
                    math_intensity=row['math_intensity'],
                    humanities_intensity=row['humanities_intensity'],
                    career_paths=career_paths or [],
                    embedding=embedding
                ))
            
            logger.info(f"Fetched {len(courses)} courses from Directus")
            return courses
    
    async def fetch_students(self) -> List[Student]:
        """Fetch all students from Directus PostgreSQL.
        
        Returns:
            List of Student entities with embeddings
        """
        pool = await self._get_pg_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT 
                    id::text,
                    name,
                    preferences,
                    career_goal,
                    embedding::text
                FROM students
                ORDER BY name;
            """)
            
            students = []
            for row in rows:
                embedding = None
                if row['embedding']:
                    embedding_str = row['embedding'].strip('[]')
                    if embedding_str:
                        embedding = [float(x) for x in embedding_str.split(',')]
                
                preferences = row['preferences']
                if isinstance(preferences, str):
                    preferences = json.loads(preferences)
                
                students.append(Student(
                    id=row['id'],
                    name=row['name'],
                    preferences=preferences or {},
                    career_goal=row['career_goal'],
                    embedding=embedding
                ))
            
            logger.info(f"Fetched {len(students)} students from Directus")
            return students
    
    async def fetch_prerequisites(self) -> List[Prerequisite]:
        """Fetch all prerequisite relationships from Directus.
        
        Returns:
            List of Prerequisite relationships
        """
        pool = await self._get_pg_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT 
                    course_id::text,
                    prerequisite_id::text
                FROM courses_prerequisites
                ORDER BY course_id;
            """)
            
            prerequisites = [
                Prerequisite(
                    course_id=row['course_id'],
                    prerequisite_id=row['prerequisite_id']
                )
                for row in rows
            ]
            
            logger.info(f"Fetched {len(prerequisites)} prerequisite relationships")
            return prerequisites
    
    async def sync_courses_to_neo4j(self, courses: Optional[List[Course]] = None):
        """Sync courses to Neo4j as Course nodes.
        
        Args:
            courses: List of courses to sync (fetches if None)
        """
        if courses is None:
            courses = await self.fetch_courses()
        
        driver = await self._get_neo4j_driver()
        
        async with driver.session() as session:
            for course in courses:
                # Create Course node with properties
                await session.run("""
                    MERGE (c:Course {id: $id})
                    SET c.name = $name,
                        c.description = $description,
                        c.department = $department,
                        c.credits = $credits,
                        c.mathIntensity = $math_intensity,
                        c.humanitiesIntensity = $humanities_intensity,
                        c.careerPaths = $career_paths,
                        c.updatedAt = datetime(),
                        c.source = 'directus'
                    WITH c
                    WHERE $embedding IS NOT NULL
                    CALL db.create.setNodeVectorProperty(c, 'embedding', $embedding)
                    RETURN c;
                """, {
                    'id': course.id,
                    'name': course.name,
                    'description': course.description,
                    'department': course.department,
                    'credits': course.credits,
                    'math_intensity': course.math_intensity,
                    'humanities_intensity': course.humanities_intensity,
                    'career_paths': course.career_paths,
                    'embedding': course.embedding
                })
            
            logger.info(f"Synced {len(courses)} courses to Neo4j")
    
    async def sync_students_to_neo4j(self, students: Optional[List[Student]] = None):
        """Sync students to Neo4j as Student nodes.
        
        Args:
            students: List of students to sync (fetches if None)
        """
        if students is None:
            students = await self.fetch_students()
        
        driver = await self._get_neo4j_driver()
        
        async with driver.session() as session:
            for student in students:
                # Create Student node with properties
                await session.run("""
                    MERGE (s:Student {id: $id})
                    SET s.name = $name,
                        s.preferences = $preferences,
                        s.careerGoal = $career_goal,
                        s.updatedAt = datetime(),
                        s.source = 'directus'
                    WITH s
                    WHERE $embedding IS NOT NULL
                    CALL db.create.setNodeVectorProperty(s, 'embedding', $embedding)
                    RETURN s;
                """, {
                    'id': student.id,
                    'name': student.name,
                    'preferences': json.dumps(student.preferences),
                    'career_goal': student.career_goal,
                    'embedding': student.embedding
                })
            
            logger.info(f"Synced {len(students)} students to Neo4j")
    
    async def sync_prerequisites_to_neo4j(
        self, 
        prerequisites: Optional[List[Prerequisite]] = None
    ):
        """Sync prerequisite relationships to Neo4j.
        
        Creates (Course)-[:PREREQUISITE]->(Course) relationships.
        
        Args:
            prerequisites: List of prerequisites to sync (fetches if None)
        """
        if prerequisites is None:
            prerequisites = await self.fetch_prerequisites()
        
        driver = await self._get_neo4j_driver()
        
        async with driver.session() as session:
            for prereq in prerequisites:
                await session.run("""
                    MATCH (c:Course {id: $course_id})
                    MATCH (p:Course {id: $prerequisite_id})
                    MERGE (c)-[r:PREREQUISITE]->(p)
                    SET r.createdAt = datetime(),
                        r.source = 'directus'
                    RETURN r;
                """, {
                    'course_id': prereq.course_id,
                    'prerequisite_id': prereq.prerequisite_id
                })
            
            logger.info(f"Synced {len(prerequisites)} prerequisite relationships to Neo4j")
    
    async def create_similarity_relationships(self, threshold: float = 0.7):
        """Create SIMILAR_TO relationships based on embedding similarity.
        
        Args:
            threshold: Minimum cosine similarity threshold (0-1)
        """
        driver = await self._get_neo4j_driver()
        
        async with driver.session() as session:
            # Find similar courses based on embedding similarity
            result = await session.run("""
                MATCH (c1:Course)
                WHERE c1.embedding IS NOT NULL
                MATCH (c2:Course)
                WHERE c2.embedding IS NOT NULL
                  AND c1.id < c2.id
                WITH c1, c2,
                     // Calculate dot product
                     reduce(dot = 0.0, i in range(0, size(c1.embedding)-1) | dot + c1.embedding[i] * c2.embedding[i])
                     /
                     // Divide by magnitudes
                     (sqrt(reduce(s = 0.0, x in c1.embedding | s + x^2)) * sqrt(reduce(s = 0.0, x in c2.embedding | s + x^2)))
                     AS similarity
                WHERE similarity >= $threshold
                MERGE (c1)-[r:SIMILAR_TO]->(c2)
                SET r.similarity = similarity,
                    r.createdAt = datetime()
                RETURN count(r) AS relationships_created;
            """, {'threshold': threshold})
            
            record = await result.single()
            count = record['relationships_created'] if record else 0
            logger.info(f"Created {count} SIMILAR_TO relationships")
    
    async def create_department_relationships(self):
        """Create Department nodes and BELONGS_TO relationships."""
        driver = await self._get_neo4j_driver()
        
        async with driver.session() as session:
            # Create Department nodes and relationships
            result = await session.run("""
                MATCH (c:Course)
                WHERE c.department IS NOT NULL
                MERGE (d:Department {name: c.department})
                MERGE (c)-[r:BELONGS_TO]->(d)
                SET r.createdAt = datetime()
                RETURN count(DISTINCT d) AS departments, count(r) AS relationships;
            """)
            
            record = await result.single()
            if record:
                logger.info(
                    f"Created {record['departments']} departments, "
                    f"{record['relationships']} BELONGS_TO relationships"
                )
    
    # ============================================
    # NEO4J → DIRECTUS SYNC
    # ============================================
    
    async def fetch_courses_from_neo4j(self) -> List[Dict[str, Any]]:
        """Fetch courses from Neo4j.
        
        Returns:
            List of course dictionaries
        """
        driver = await self._get_neo4j_driver()
        
        async with driver.session() as session:
            result = await session.run("""
                MATCH (c:Course)
                RETURN c.id AS id,
                       c.name AS name,
                       c.description AS description,
                       c.department AS department,
                       c.credits AS credits,
                       c.mathIntensity AS math_intensity,
                       c.humanitiesIntensity AS humanities_intensity,
                       c.careerPaths AS career_paths;
            """)
            
            courses = []
            async for record in result:
                courses.append({
                    'id': record['id'],
                    'name': record['name'],
                    'description': record['description'],
                    'department': record['department'],
                    'credits': record['credits'],
                    'math_intensity': record['math_intensity'],
                    'humanities_intensity': record['humanities_intensity'],
                    'career_paths': record['career_paths']
                })
            
            logger.info(f"Fetched {len(courses)} courses from Neo4j")
            return courses
    
    async def update_course_in_directus(
        self,
        course_id: str,
        updates: Dict[str, Any]
    ):
        """Update a course in Directus PostgreSQL.

        Args:
            course_id: Course UUID
            updates: Dictionary of fields to update
        """
        pool = await self._get_pg_pool()

        # Validate course_id
        if self._enable_validation:
            try:
                self._validator.validate_uuid(course_id)
            except ValueError as e:
                logger.warning("Invalid course_id format", course_id=course_id, error=str(e))
                return

        # Build dynamic update query with hardcoded column mapping
        # This prevents SQL injection by not using user input in column names
        column_mapping = {
            'name': 'name',
            'description': 'description',
            'department': 'department',
            'credits': 'credits',
            'math_intensity': 'math_intensity',
            'humanities_intensity': 'humanities_intensity',
            'career_paths': 'career_paths',
        }

        set_clauses = []
        values = []
        param_idx = 1

        for key, value in updates.items():
            if key in column_mapping:
                # Validate column name through mapping (not direct user input)
                column = column_mapping[key]
                # Validate the value length
                if self._enable_validation:
                    self._validator.validate_input_length(str(value), 5000)
                set_clauses.append(f"{column} = ${param_idx}")
                if key == 'career_paths':
                    values.append(json.dumps(value))
                else:
                    values.append(value)
                param_idx += 1

        if not set_clauses:
            return

        # Always update the timestamp
        set_clauses.append("updated_at = NOW()")
        # Add course_id as the last parameter for WHERE clause
        values.append(course_id)

        # Build query with safe column names (from hardcoded mapping, not user input)
        query = f"""
            UPDATE courses
            SET {', '.join(set_clauses)}
            WHERE id = ${param_idx};
        """

        async with pool.acquire() as conn:
            await conn.execute(query, *values)
            logger.info("Updated course in Directus", course_id=course_id)
    
    async def sync_courses_from_neo4j(
        self, 
        course_ids: Optional[List[str]] = None
    ):
        """Sync courses from Neo4j back to Directus.
        
        Args:
            course_ids: Specific course IDs to sync (all if None)
        """
        courses = await self.fetch_courses_from_neo4j()
        
        if course_ids:
            courses = [c for c in courses if c['id'] in course_ids]
        
        for course in courses:
            await self.update_course_in_directus(course['id'], {
                'name': course['name'],
                'description': course['description'],
                'department': course['department'],
                'credits': course['credits'],
                'math_intensity': course['math_intensity'],
                'humanities_intensity': course['humanities_intensity'],
                'career_paths': course['career_paths']
            })
        
        logger.info(f"Synced {len(courses)} courses from Neo4j to Directus")
    
    # ============================================
    # FULL SYNC OPERATIONS
    # ============================================
    
    async def sync_all_to_neo4j(self):
        """Perform full sync from Directus to Neo4j."""
        logger.info("Starting full sync: Directus → Neo4j")
        
        # Sync courses first (needed for prerequisites)
        courses = await self.fetch_courses()
        await self.sync_courses_to_neo4j(courses)
        
        # Sync students
        students = await self.fetch_students()
        await self.sync_students_to_neo4j(students)
        
        # Sync prerequisites
        prerequisites = await self.fetch_prerequisites()
        await self.sync_prerequisites_to_neo4j(prerequisites)
        
        # Create derived relationships
        await self.create_department_relationships()
        await self.create_similarity_relationships()
        
        logger.info("Full sync completed: Directus → Neo4j")
    
    async def sync_all(self):
        """Perform bidirectional sync."""
        await self.sync_all_to_neo4j()
        # Optionally sync back from Neo4j if needed
        # await self.sync_courses_from_neo4j()
    
    # ============================================
    # UTILITY METHODS
    # ============================================
    
    async def get_sync_stats(self) -> Dict[str, int]:
        """Get synchronization statistics.
        
        Returns:
            Dictionary with counts for courses, students, relationships
        """
        pool = await self._get_pg_pool()
        driver = await self._get_neo4j_driver()
        
        stats = {}
        
        # Directus counts
        async with pool.acquire() as conn:
            stats['directus_courses'] = await conn.fetchval(
                "SELECT COUNT(*) FROM courses WHERE status = 'published';"
            )
            stats['directus_students'] = await conn.fetchval(
                "SELECT COUNT(*) FROM students;"
            )
            stats['directus_prerequisites'] = await conn.fetchval(
                "SELECT COUNT(*) FROM courses_prerequisites;"
            )
        
        # Neo4j counts
        async with driver.session() as session:
            result = await session.run("""
                MATCH (c:Course) RETURN count(c) AS count;
            """)
            record = await result.single()
            stats['neo4j_courses'] = record['count'] if record else 0
            
            result = await session.run("""
                MATCH (s:Student) RETURN count(s) AS count;
            """)
            record = await result.single()
            stats['neo4j_students'] = record['count'] if record else 0
            
            result = await session.run("""
                MATCH ()-[r:PREREQUISITE]->() RETURN count(r) AS count;
            """)
            record = await result.single()
            stats['neo4j_prerequisites'] = record['count'] if record else 0
        
        return stats
    
    async def verify_consistency(self) -> Tuple[bool, List[str]]:
        """Verify data consistency between Directus and Neo4j.
        
        Returns:
            Tuple of (is_consistent, list_of_issues)
        """
        stats = await self.get_sync_stats()
        issues = []
        
        if stats['directus_courses'] != stats['neo4j_courses']:
            issues.append(
                f"Course count mismatch: "
                f"Directus={stats['directus_courses']}, "
                f"Neo4j={stats['neo4j_courses']}"
            )
        
        if stats['directus_students'] != stats['neo4j_students']:
            issues.append(
                f"Student count mismatch: "
                f"Directus={stats['directus_students']}, "
                f"Neo4j={stats['neo4j_students']}"
            )
        
        if stats['directus_prerequisites'] != stats['neo4j_prerequisites']:
            issues.append(
                f"Prerequisite count mismatch: "
                f"Directus={stats['directus_prerequisites']}, "
                f"Neo4j={stats['neo4j_prerequisites']}"
            )
        
        is_consistent = len(issues) == 0
        return is_consistent, issues

    # ============================================
    # SECURITY METHODS
    # ============================================

    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """Verify Directus webhook signature.

        Args:
            payload: Raw webhook payload bytes
            signature: Signature header from webhook request

        Returns:
            True if signature is valid
        """
        if not self._enable_webhook_verification:
            return True

        if not self._webhook_secret:
            logger.warning("Webhook verification enabled but no secret configured")
            return True

        try:
            import hmac
            import hashlib

            expected = hmac.new(
                self._webhook_secret.encode(),
                payload,
                hashlib.sha256
            ).hexdigest()

            # Use constant-time comparison to prevent timing attacks
            return hmac.compare_digest(expected, signature)
        except Exception as e:
            logger.error("Webhook signature verification failed", error=str(e))
            return False

    def sanitize_webhook_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize Directus webhook payload.

        Removes potentially dangerous fields and validates data types.

        Args:
            payload: Webhook payload dictionary

        Returns:
            Sanitized payload
        """
        if not isinstance(payload, dict):
            return {}

        sanitized = {}

        # Allowed top-level fields
        allowed_fields = {
            'event', 'collection', 'id', 'payload', 'query',
            'action', 'key', 'keys', 'data'
        }

        for key, value in payload.items():
            if key not in allowed_fields:
                continue

            # Validate key name (prevent injection)
            if not key.isalnum() and '_' not in key:
                continue

            # Sanitize based on field type
            if key == 'collection':
                # Collection names should be alphanumeric + underscore
                if isinstance(value, str) and value.isidentifier():
                    sanitized[key] = value
            elif key == 'id':
                # IDs should be valid UUIDs or integers
                if isinstance(value, (str, int)):
                    sanitized[key] = value
            elif key == 'payload':
                # Recursively sanitize nested payload
                if isinstance(value, dict):
                    sanitized[key] = self._sanitize_nested_dict(value)
                else:
                    sanitized[key] = value
            else:
                sanitized[key] = value

        return sanitized

    def _sanitize_nested_dict(self, data: Dict[str, Any], depth: int = 0) -> Dict[str, Any]:
        """Recursively sanitize a nested dictionary.

        Args:
            data: Dictionary to sanitize
            depth: Current recursion depth

        Returns:
            Sanitized dictionary
        """
        if depth > 5:  # Limit recursion depth
            return {}

        if not isinstance(data, dict):
            return {}

        sanitized = {}

        for key, value in data.items():
            # Skip keys with dangerous patterns
            if not isinstance(key, str):
                continue

            # Sanitize key
            safe_key = ''.join(c for c in key if c.isalnum() or c == '_')
            if not safe_key:
                continue

            # Sanitize value based on type
            if isinstance(value, dict):
                sanitized[safe_key] = self._sanitize_nested_dict(value, depth + 1)
            elif isinstance(value, list):
                sanitized[safe_key] = [
                    self._sanitize_nested_dict(item, depth + 1) if isinstance(item, dict) else item
                    for item in value[:100]  # Limit array size
                ]
            elif isinstance(value, (str, int, float, bool)):
                # Truncate long strings
                if isinstance(value, str) and len(value) > 10000:
                    value = value[:10000]
                sanitized[safe_key] = value
            else:
                # Convert other types to string
                sanitized[safe_key] = str(value)[:1000]

        return sanitized

    def validate_cypher_query(self, query: str) -> bool:
        """Validate a Cypher query for dangerous patterns.

        Args:
            query: Cypher query string

        Returns:
            True if query is safe

        Raises:
            ValueError: If query contains dangerous patterns
        """
        if not query:
            raise ValueError("Query cannot be empty")

        # Check query length
        if len(query) > self._validator.MAX_QUERY_LENGTH:
            raise ValueError(f"Query too long: {len(query)} characters")

        # Check for dangerous keywords
        dangerous_patterns = [
            'CALL dbms.security.changePassword',
            'CALL dbms.security.createUser',
            'CALL dbms.security.deleteUser',
            'apoc.export',
            'apoc.load',
            'apoc.systemdb',
        ]

        upper_query = query.upper()
        for pattern in dangerous_patterns:
            if pattern.upper() in upper_query:
                raise ValueError(f"Query contains dangerous pattern: {pattern}")

        return True


# ============================================
# CLI INTERFACE
# ============================================

async def main():
    """Main CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Directus-Neo4j Bridge Sync Tool"
    )
    parser.add_argument(
        'command',
        choices=['sync', 'stats', 'verify', 'courses', 'students', 'prereqs'],
        help='Command to execute'
    )
    parser.add_argument(
        '--direction',
        choices=['to-neo4j', 'from-neo4j', 'both'],
        default='to-neo4j',
        help='Sync direction'
    )
    
    args = parser.parse_args()
    
    async with DirectusNeo4jBridge() as bridge:
        if args.command == 'sync':
            if args.direction in ['to-neo4j', 'both']:
                await bridge.sync_all_to_neo4j()
            if args.direction in ['from-neo4j', 'both']:
                await bridge.sync_courses_from_neo4j()
        
        elif args.command == 'stats':
            stats = await bridge.get_sync_stats()
            print("\n=== Sync Statistics ===")
            print(f"Directus Courses:      {stats['directus_courses']}")
            print(f"Directus Students:     {stats['directus_students']}")
            print(f"Directus Prereqs:      {stats['directus_prerequisites']}")
            print(f"Neo4j Courses:         {stats['neo4j_courses']}")
            print(f"Neo4j Students:        {stats['neo4j_students']}")
            print(f"Neo4j Prereqs:         {stats['neo4j_prerequisites']}")
        
        elif args.command == 'verify':
            is_consistent, issues = await bridge.verify_consistency()
            if is_consistent:
                print("✓ Data is consistent between Directus and Neo4j")
            else:
                print("✗ Consistency issues found:")
                for issue in issues:
                    print(f"  - {issue}")
        
        elif args.command == 'courses':
            courses = await bridge.fetch_courses()
            print(f"\n=== {len(courses)} Courses ===")
            for c in courses:
                print(f"  {c.name} ({c.department})")
        
        elif args.command == 'students':
            students = await bridge.fetch_students()
            print(f"\n=== {len(students)} Students ===")
            for s in students:
                print(f"  {s.name} - Goal: {s.career_goal}")
        
        elif args.command == 'prereqs':
            prereqs = await bridge.fetch_prerequisites()
            print(f"\n=== {len(prereqs)} Prerequisites ===")
            for p in prereqs:
                print(f"  {p.course_id} requires {p.prerequisite_id}")


if __name__ == "__main__":
    asyncio.run(main())
