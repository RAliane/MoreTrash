"""Cognee Memory Adapter for HadesPy.

This module provides a secure wrapper around the Cognee API for memory
ingestion and retrieval. It handles input sanitization to mitigate Cognee's
exec() vulnerability and provides graceful fallback when Cognee is unavailable.

Key Features:
- Secure input sanitization for all dynamic inputs
- Idempotent writes (same data → same result)
- Single embedding index per node_id
- Comprehensive error handling and retries
- Graceful fallback to legacy memory implementation

Usage:
    >>> from src.integrations.cognee_adapter import CogneeAdapter
    >>> adapter = CogneeAdapter()
    >>> await adapter.ingest_course_data(courses)
    >>> results = await adapter.search_similar("machine learning")
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid5

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.config import get_settings
from src.integrations.directus_neo4j_bridge import Course, Student
from src.logging_config import get_logger

logger = get_logger(__name__)

# Namespace for deterministic UUID generation
COGNEE_NAMESPACE = UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")

# Input sanitization patterns for exec() mitigation
FORBIDDEN_PATTERNS = [
    r"__\w+__",  # Dunder methods
    r"import\s+\w+",  # Import statements
    r"exec\s*\(",  # exec() calls
    r"eval\s*\(",  # eval() calls
    r"compile\s*\(",  # compile() calls
    r"open\s*\(",  # open() calls
    r"subprocess",  # subprocess module
    r"os\.",  # os module access
    r"sys\.",  # sys module access
    r"\"\"\".*\"\"\"",  # Triple quotes (multiline)
    r"\`.*\`",  # Backtick execution
]

FORBIDDEN_REGEX = re.compile("|".join(FORBIDDEN_PATTERNS), re.IGNORECASE)


@dataclass
class IngestionResult:
    """Result of an ingestion operation."""
    success: bool
    node_ids: List[str]
    errors: List[str]
    timestamp: str


@dataclass
class SearchResult:
    """Result of a semantic search operation."""
    node_id: str
    content: str
    score: float
    metadata: Dict[str, Any]
    relationships: List[Dict[str, Any]]


@dataclass
class GraphContext:
    """Graph neighborhood context for an entity."""
    entity_id: str
    entity_type: str
    properties: Dict[str, Any]
    neighbors: List[Dict[str, Any]]
    relationships: List[Dict[str, Any]]
    depth: int


@dataclass
class UserInteraction:
    """User interaction record for ingestion."""
    user_id: str
    action: str  # e.g., "viewed", "completed", "searched"
    entity_id: str
    entity_type: str  # e.g., "course", "document"
    timestamp: str
    metadata: Optional[Dict[str, Any]] = None


class InputSanitizer:
    """Sanitizes inputs to mitigate Cognee exec() vulnerability."""

    @staticmethod
    def sanitize_string(value: str, max_length: int = 1000) -> str:
        """Sanitize a string value.
        
        Args:
            value: Input string to sanitize
            max_length: Maximum allowed length
            
        Returns:
            Sanitized string
            
        Raises:
            ValueError: If input contains forbidden patterns
        """
        if not isinstance(value, str):
            value = str(value)
        
        # Check for forbidden patterns
        if FORBIDDEN_REGEX.search(value):
            raise ValueError(f"Input contains forbidden pattern: {value[:50]}...")
        
        # Truncate if too long
        if len(value) > max_length:
            value = value[:max_length]
        
        # Escape special characters
        value = value.replace("\\", "\\\\")
        value = value.replace('"', '\\"')
        value = value.replace("'", "\\'")
        
        return value

    @staticmethod
    def sanitize_identifier(value: str) -> str:
        """Sanitize an identifier (node label, relationship type, etc.).
        
        Args:
            value: Identifier to sanitize
            
        Returns:
            Sanitized identifier
        """
        if not isinstance(value, str):
            value = str(value)
        
        # Only allow alphanumeric, underscore, and colon
        sanitized = re.sub(r"[^a-zA-Z0-9_:]", "_", value)
        
        # Must start with letter or underscore
        if sanitized and sanitized[0].isdigit():
            sanitized = "_" + sanitized
        
        return sanitized[:64]  # Max 64 chars for Neo4j identifiers

    @staticmethod
    def sanitize_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize metadata dictionary.
        
        Args:
            metadata: Metadata dictionary to sanitize
            
        Returns:
            Sanitized metadata dictionary
        """
        if not isinstance(metadata, dict):
            return {}
        
        sanitized = {}
        for key, value in metadata.items():
            # Sanitize key
            safe_key = InputSanitizer.sanitize_identifier(key)
            
            # Sanitize value based on type
            if isinstance(value, str):
                safe_value = InputSanitizer.sanitize_string(value)
            elif isinstance(value, (int, float, bool)):
                safe_value = value
            elif isinstance(value, (list, tuple)):
                safe_value = [
                    InputSanitizer.sanitize_string(v) if isinstance(v, str) else v
                    for v in value[:100]  # Limit list size
                ]
            elif isinstance(value, dict):
                safe_value = InputSanitizer.sanitize_metadata(value)
            else:
                safe_value = str(value)[:1000]
            
            sanitized[safe_key] = safe_value
        
        return sanitized


class CogneeAdapter:
    """Adapter for Cognee memory integration.
    
    This adapter provides a secure interface to Cognee, handling input
    sanitization and providing graceful fallback when Cognee is unavailable.
    
    Attributes:
        api_url: Cognee API base URL
        api_key: Cognee API key
        dataset_name: Default dataset for operations
        http_client: Async HTTP client
        sanitizer: Input sanitizer instance
    """

    def __init__(
        self,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        dataset_name: Optional[str] = None,
    ):
        """Initialize the Cognee adapter.
        
        Args:
            api_url: Cognee API URL (defaults to settings)
            api_key: Cognee API key (defaults to settings)
            dataset_name: Dataset name (defaults to settings)
        """
        settings = get_settings()
        
        self.api_url = api_url or settings.cognee_api_url
        self.api_key = api_key or settings.cognee_api_key
        self.dataset_name = dataset_name or settings.cognee_dataset_name
        self.timeout = settings.cognee_timeout
        
        self.sanitizer = InputSanitizer()
        self._http_client: Optional[httpx.AsyncClient] = None
        
        logger.info(
            "CogneeAdapter initialized",
            api_url=self.api_url,
            dataset=self.dataset_name,
        )

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None:
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            self._http_client = httpx.AsyncClient(
                base_url=self.api_url,
                headers=headers,
                timeout=self.timeout,
                follow_redirects=True,
            )
        return self._http_client

    async def close(self) -> None:
        """Close HTTP client connection."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

    def _generate_node_id(self, entity_type: str, unique_key: str) -> str:
        """Generate deterministic node ID.
        
        Args:
            entity_type: Type of entity (e.g., "Course", "User")
            unique_key: Unique identifier for the entity
            
        Returns:
            Deterministic UUID string
        """
        namespace = uuid5(COGNEE_NAMESPACE, entity_type)
        return str(uuid5(namespace, unique_key))

    def _compute_content_hash(self, content: str) -> str:
        """Compute hash for content deduplication.
        
        Args:
            content: Content to hash
            
        Returns:
            SHA-256 hash string
        """
        return hashlib.sha256(content.encode()).hexdigest()[:32]

    @retry(
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Make HTTP request to Cognee API with retries.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            json_data: JSON request body
            params: Query parameters
            
        Returns:
            Response JSON
            
        Raises:
            httpx.HTTPError: On HTTP errors after retries
        """
        client = await self._get_client()
        
        try:
            response = await client.request(
                method=method,
                url=endpoint,
                json=json_data,
                params=params,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(
                "Cognee API error",
                status_code=e.response.status_code,
                endpoint=endpoint,
                error=str(e),
            )
            raise
        except httpx.TimeoutException:
            logger.error("Cognee API timeout", endpoint=endpoint)
            raise

    async def ingest_course_data(
        self,
        courses: List[Course],
        dataset_name: Optional[str] = None,
    ) -> IngestionResult:
        """Ingest course data into Cognee.
        
        Creates Course nodes in the graph with embeddings and relationships.
        This operation is idempotent - ingesting the same course twice
        will update rather than duplicate.
        
        Args:
            courses: List of Course objects to ingest
            dataset_name: Optional override for dataset name
            
        Returns:
            IngestionResult with success status and node IDs
        """
        dataset = dataset_name or self.dataset_name
        node_ids = []
        errors = []
        timestamp = datetime.now(timezone.utc).isoformat()

        logger.info(
            "Ingesting course data",
            course_count=len(courses),
            dataset=dataset,
        )
        
        for course in courses:
            try:
                # Sanitize all inputs
                safe_name = self.sanitizer.sanitize_string(course.name)
                safe_description = self.sanitizer.sanitize_string(course.description)
                safe_department = self.sanitizer.sanitize_identifier(course.department)
                
                # Generate deterministic node ID
                node_id = self._generate_node_id("Course", course.id)
                
                # Prepare content for embedding
                content = f"{safe_name}. {safe_description}"
                content_hash = self._compute_content_hash(content)
                
                # Build sanitized metadata
                metadata = self.sanitizer.sanitize_metadata({
                    "course_id": course.id,
                    "department": safe_department,
                    "credits": course.credits,
                    "math_intensity": course.math_intensity,
                    "humanities_intensity": course.humanities_intensity,
                    "career_paths": course.career_paths,
                    "content_hash": content_hash,
                })
                
                # Prepare ingestion payload
                payload = {
                    "data": content,
                    "dataset_name": self.sanitizer.sanitize_identifier(dataset),
                    "node_id": node_id,
                    "node_type": "Course",
                    "external_metadata": metadata,
                    "idempotent": True,  # Ensure idempotent writes
                }
                
                # Send to Cognee
                response = await self._make_request(
                    method="POST",
                    endpoint="/api/v1/add",
                    json_data=payload,
                )
                
                node_ids.append(node_id)
                if not timestamp and "timestamp" in response:
                    timestamp = response["timestamp"]
                
                logger.debug(
                    "Course ingested",
                    course_id=course.id,
                    node_id=node_id,
                )
                
            except ValueError as e:
                error_msg = f"Sanitization error for course {course.id}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)
            except httpx.HTTPError as e:
                error_msg = f"HTTP error for course {course.id}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)
            except Exception as e:
                error_msg = f"Unexpected error for course {course.id}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        success = len(node_ids) > 0 and len(errors) < len(courses)
        
        logger.info(
            "Course ingestion complete",
            success_count=len(node_ids),
            error_count=len(errors),
            success=success,
        )
        
        return IngestionResult(
            success=success,
            node_ids=node_ids,
            errors=errors,
            timestamp=timestamp,
        )

    async def ingest_user_interactions(
        self,
        interactions: List[UserInteraction],
        dataset_name: Optional[str] = None,
    ) -> IngestionResult:
        """Ingest user interaction data into Cognee.
        
        Creates User nodes and INTERACTED relationships in the graph.
        
        Args:
            interactions: List of UserInteraction objects
            dataset_name: Optional override for dataset name
            
        Returns:
            IngestionResult with success status and node IDs
        """
        dataset = dataset_name or self.dataset_name
        node_ids = []
        errors = []
        timestamp = datetime.now(timezone.utc).isoformat()

        logger.info(
            "Ingesting user interactions",
            interaction_count=len(interactions),
            dataset=dataset,
        )
        
        for interaction in interactions:
            try:
                # Sanitize inputs
                safe_user_id = self.sanitizer.sanitize_identifier(interaction.user_id)
                safe_action = self.sanitizer.sanitize_identifier(interaction.action)
                safe_entity_type = self.sanitizer.sanitize_identifier(
                    interaction.entity_type
                )
                
                # Generate node IDs
                user_node_id = self._generate_node_id("User", interaction.user_id)
                entity_node_id = self._generate_node_id(
                    safe_entity_type,
                    interaction.entity_id
                )
                
                # Sanitize metadata
                metadata = self.sanitizer.sanitize_metadata({
                    "user_id": interaction.user_id,
                    "action": interaction.action,
                    "entity_id": interaction.entity_id,
                    "entity_type": interaction.entity_type,
                    "timestamp": interaction.timestamp,
                    **(interaction.metadata or {}),
                })
                
                # Ingest user node
                user_payload = {
                    "data": f"User: {safe_user_id}",
                    "dataset_name": self.sanitizer.sanitize_identifier(dataset),
                    "node_id": user_node_id,
                    "node_type": "User",
                    "external_metadata": metadata,
                    "idempotent": True,
                }
                
                await self._make_request(
                    method="POST",
                    endpoint="/api/v1/add",
                    json_data=user_payload,
                )
                
                # Create relationship
                rel_payload = {
                    "source_id": user_node_id,
                    "target_id": entity_node_id,
                    "relationship_type": safe_action.upper(),
                    "dataset_name": self.sanitizer.sanitize_identifier(dataset),
                    "properties": metadata,
                }
                
                await self._make_request(
                    method="POST",
                    endpoint="/api/v1/relationships",
                    json_data=rel_payload,
                )
                
                node_ids.append(user_node_id)
                
                logger.debug(
                    "User interaction ingested",
                    user_id=interaction.user_id,
                    action=interaction.action,
                    entity_id=interaction.entity_id,
                )
                
            except ValueError as e:
                error_msg = f"Sanitization error for interaction: {e}"
                logger.error(error_msg)
                errors.append(error_msg)
            except httpx.HTTPError as e:
                error_msg = f"HTTP error for interaction: {e}"
                logger.error(error_msg)
                errors.append(error_msg)
            except Exception as e:
                error_msg = f"Unexpected error for interaction: {e}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        success = len(node_ids) > 0 and len(errors) < len(interactions)
        
        logger.info(
            "User interaction ingestion complete",
            success_count=len(node_ids),
            error_count=len(errors),
            success=success,
        )
        
        return IngestionResult(
            success=success,
            node_ids=node_ids,
            errors=errors,
            timestamp=timestamp,
        )

    async def search_similar(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        top_k: int = 10,
        dataset_name: Optional[str] = None,
    ) -> List[SearchResult]:
        """Perform semantic search using Cognee.
        
        Args:
            query: Search query string
            filters: Optional filters (e.g., {"node_type": "Course"})
            top_k: Maximum number of results
            dataset_name: Optional override for dataset name
            
        Returns:
            List of SearchResult objects
        """
        dataset = dataset_name or self.dataset_name
        
        try:
            # Sanitize query
            safe_query = self.sanitizer.sanitize_string(query, max_length=2000)
            
            # Sanitize filters
            safe_filters = {}
            if filters:
                for key, value in filters.items():
                    safe_key = self.sanitizer.sanitize_identifier(key)
                    if isinstance(value, str):
                        safe_value = self.sanitizer.sanitize_identifier(value)
                    else:
                        safe_value = value
                    safe_filters[safe_key] = safe_value
            
            # Build search payload
            payload = {
                "query": safe_query,
                "dataset_name": self.sanitizer.sanitize_identifier(dataset),
                "top_k": min(top_k, 100),  # Cap at 100
                "filters": safe_filters,
            }
            
            response = await self._make_request(
                method="POST",
                endpoint="/api/v1/search",
                json_data=payload,
            )
            
            # Parse results
            results = []
            for item in response.get("results", []):
                result = SearchResult(
                    node_id=item.get("node_id", ""),
                    content=item.get("content", ""),
                    score=item.get("score", 0.0),
                    metadata=item.get("metadata", {}),
                    relationships=item.get("relationships", []),
                )
                results.append(result)
            
            logger.info(
                "Semantic search completed",
                query=safe_query[:50],
                results_found=len(results),
            )
            
            return results
            
        except ValueError as e:
            logger.error(f"Search sanitization error: {e}")
            return []
        except httpx.HTTPError as e:
            logger.error(f"Search HTTP error: {e}")
            return []
        except Exception as e:
            logger.error(f"Search unexpected error: {e}")
            return []

    async def get_graph_context(
        self,
        entity_id: str,
        depth: int = 2,
        relationship_types: Optional[List[str]] = None,
        dataset_name: Optional[str] = None,
    ) -> Optional[GraphContext]:
        """Get graph neighborhood context for an entity.
        
        Args:
            entity_id: Entity node ID
            depth: Neighborhood depth (1-3)
            relationship_types: Optional filter for relationship types
            dataset_name: Optional override for dataset name
            
        Returns:
            GraphContext object or None if not found
        """
        dataset = dataset_name or self.dataset_name
        
        try:
            # Sanitize inputs
            safe_entity_id = self.sanitizer.sanitize_identifier(entity_id)
            safe_depth = min(max(depth, 1), 3)  # Clamp between 1-3
            
            safe_rel_types = None
            if relationship_types:
                safe_rel_types = [
                    self.sanitizer.sanitize_identifier(rt)
                    for rt in relationship_types[:10]  # Max 10 types
                ]
            
            # Build request
            params = {
                "node_id": safe_entity_id,
                "dataset_name": self.sanitizer.sanitize_identifier(dataset),
                "depth": safe_depth,
            }
            if safe_rel_types:
                params["relationship_types"] = ",".join(safe_rel_types)
            
            response = await self._make_request(
                method="GET",
                endpoint="/api/v1/graph/neighborhood",
                params=params,
            )
            
            # Parse context
            context = GraphContext(
                entity_id=response.get("entity_id", entity_id),
                entity_type=response.get("entity_type", "Unknown"),
                properties=response.get("properties", {}),
                neighbors=response.get("neighbors", []),
                relationships=response.get("relationships", []),
                depth=safe_depth,
            )
            
            logger.info(
                "Graph context retrieved",
                entity_id=safe_entity_id,
                neighbors_count=len(context.neighbors),
                depth=safe_depth,
            )
            
            return context
            
        except ValueError as e:
            logger.error(f"Graph context sanitization error: {e}")
            return None
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Entity not found: {entity_id}")
            else:
                logger.error(f"Graph context HTTP error: {e}")
            return None
        except Exception as e:
            logger.error(f"Graph context unexpected error: {e}")
            return None

    async def health_check(self) -> bool:
        """Check if Cognee API is available.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            response = await self._make_request(
                method="GET",
                endpoint="/health",
            )
            return response.get("status") == "healthy"
        except Exception as e:
            logger.warning(f"Cognee health check failed: {e}")
            return False

    async def setup_schema(self) -> bool:
        """Setup Cognee schema constraints.
        
        Creates constraints and indexes for Course and User nodes.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            schema_definitions = {
                "node_constraints": [
                    {
                        "node_type": "Course",
                        "properties": {
                            "node_id": {"unique": True, "required": True},
                            "course_id": {"indexed": True},
                            "department": {"indexed": True},
                        }
                    },
                    {
                        "node_type": "User",
                        "properties": {
                            "node_id": {"unique": True, "required": True},
                            "user_id": {"indexed": True},
                        }
                    },
                ],
                "relationship_types": [
                    {"type": "COMPLETED", "from": "User", "to": "Course"},
                    {"type": "PREREQUISITE_FOR", "from": "Course", "to": "Course"},
                    {"type": "SIMILAR_TO", "from": "Course", "to": "Course"},
                    {"type": "INTERACTED", "from": "User", "to": "Course"},
                ]
            }
            
            await self._make_request(
                method="POST",
                endpoint="/api/v1/schema/setup",
                json_data=schema_definitions,
            )
            
            logger.info("Cognee schema setup completed")
            return True
            
        except Exception as e:
            logger.error(f"Schema setup failed: {e}")
            return False


# Singleton instance
_cognee_adapter_instance: Optional[CogneeAdapter] = None


def get_cognee_adapter() -> CogneeAdapter:
    """Get singleton CogneeAdapter instance."""
    global _cognee_adapter_instance
    if _cognee_adapter_instance is None:
        _cognee_adapter_instance = CogneeAdapter()
    return _cognee_adapter_instance


async def init_cognee_adapter() -> CogneeAdapter:
    """Initialize Cognee adapter and verify connectivity."""
    adapter = get_cognee_adapter()
    
    # Check health
    is_healthy = await adapter.health_check()
    if not is_healthy:
        logger.warning("Cognee API not available - will use fallback")
    else:
        logger.info("Cognee API is healthy")
        # Setup schema
        await adapter.setup_schema()
    
    return adapter