"""Integrations module for external service connections.

This module provides bridges between different data stores and services:
- directus_neo4j_bridge: Sync between Directus CMS and Neo4j graph database
- cognee_adapter: Cognee memory integration with secure input handling
"""

from src.integrations.cognee_adapter import (
    CogneeAdapter,
    IngestionResult,
    SearchResult,
    GraphContext,
    UserInteraction,
    InputSanitizer,
    get_cognee_adapter,
    init_cognee_adapter,
)
from src.integrations.directus_neo4j_bridge import (
    DirectusNeo4jBridge,
    Course,
    Student,
    Prerequisite,
)

__all__ = [
    # Cognee Adapter
    "CogneeAdapter",
    "IngestionResult",
    "SearchResult",
    "GraphContext",
    "UserInteraction",
    "InputSanitizer",
    "get_cognee_adapter",
    "init_cognee_adapter",
    # Directus-Neo4j Bridge
    "DirectusNeo4jBridge",
    "Course",
    "Student",
    "Prerequisite",
]
