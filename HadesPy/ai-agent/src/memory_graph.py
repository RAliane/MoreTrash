"""Graph-enhanced memory system with Neo4j backend.

Extends CogneeMemory with a Neo4j relationship layer for contextual
memory traversal. Combines vector similarity (via parent class) with
graph relationships for richer memory retrieval.

Architecture:
- Vector embeddings: Stored in SQLite (inherited from CogneeMemory)
- Graph relationships: Stored in Neo4j (semantic, temporal, causal)
- Hybrid queries: Vector search → Graph expansion

Usage:
    >>> memory = GraphMemory(neo4j_uri="bolt://localhost:7687")
    >>> await memory.add("Important fact", metadata={"source": "conversation"})
    >>> context = await memory.get_context_graph("related query")
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.config import get_settings
from src.logging_config import get_logger
from src.memory import CogneeMemory, MemoryChunk

logger = get_logger(__name__)


class GraphMemory(CogneeMemory):
    """Cognee memory with Neo4j relationship layer.
    
    Extends the base CogneeMemory (SQLite + sentence-transformers)
    with Neo4j graph storage for relationship modeling.
    
    Attributes:
        neo4j_uri: Neo4j connection URI
        neo4j_driver: Async Neo4j driver instance
        _is_graph_ready: Whether Neo4j connection is initialized
    """
    
    def __init__(
        self,
        embedding_model: Optional[str] = None,
        vector_store_path: Optional[str] = None,
        neo4j_uri: Optional[str] = None,
        neo4j_user: Optional[str] = None,
        neo4j_password: Optional[str] = None,
    ) -> None:
        """Initialize graph memory with Neo4j backend.
        
        Args:
            embedding_model: SentenceTransformer model name
            vector_store_path: Path to SQLite vector store
            neo4j_uri: Neo4j connection URI
            neo4j_user: Neo4j username
            neo4j_password: Neo4j password
        """
        super().__init__(embedding_model, vector_store_path)
        
        settings = get_settings()
        self.neo4j_uri = neo4j_uri or settings.neo4j_uri
        self.neo4j_user = neo4j_user or settings.neo4j_user
        self.neo4j_password = neo4j_password or settings.neo4j_password
        self.neo4j_database = settings.neo4j_database
        
        self._driver: Optional[Any] = None
        self._is_graph_ready = False
    
    async def initialize(self) -> None:
        """Initialize both vector store and Neo4j connection.
        
        This method is called automatically during lifespan startup.
        """
        # Initialize parent (vector store) in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._ensure_schema)
        
        # Initialize Neo4j
        try:
            from neo4j import AsyncGraphDatabase
            
            self._driver = AsyncGraphDatabase.driver(
                self.neo4j_uri,
                auth=(self.neo4j_user, self.neo4j_password),
            )
            await self._driver.verify_connectivity()
            
            # Create graph indexes and constraints
            await self._create_graph_schema()
            
            self._is_graph_ready = True
            logger.info(
                "Graph memory initialized",
                neo4j_uri=self.neo4j_uri,
                vector_store=self.vector_store_path,
            )
            
        except Exception as exc:
            logger.error("Failed to initialize graph memory", error=str(exc))
            # Vector store is still usable even if Neo4j fails
            self._is_graph_ready = False
    
    async def _create_graph_schema(self) -> None:
        """Create Neo4j schema for memory graph.
        
        Creates:
        - Constraints for MemoryChunk id uniqueness
        - Indexes for efficient lookups
        """
        if not self._driver:
            return
        
        schema_queries = [
            # Constraint: MemoryChunk id must be unique
            """
            CREATE CONSTRAINT memory_chunk_id IF NOT EXISTS
            FOR (m:MemoryChunk) REQUIRE m.id IS UNIQUE
            """,
            # Index: Session lookups
            """
            CREATE INDEX memory_session IF NOT EXISTS
            FOR (m:MemoryChunk) ON (m.session_id)
            """,
            # Index: Source type lookups
            """
            CREATE INDEX memory_source IF NOT EXISTS
            FOR (m:MemoryChunk) ON (m.source_type)
            """,
            # Index: Timestamp range queries
            """
            CREATE INDEX memory_created IF NOT EXISTS
            FOR (m:MemoryChunk) ON (m.created_at)
            """,
        ]
        
        async with self._driver.session(database=self.neo4j_database) as session:
            for query in schema_queries:
                try:
                    await session.run(query)
                except Exception as exc:
                    # Constraints/indexes may already exist
                    logger.debug("Schema query skipped", query=query[:50], error=str(exc))
    
    async def close(self) -> None:
        """Close Neo4j connection."""
        if self._driver:
            await self._driver.close()
            self._driver = None
            self._is_graph_ready = False
            logger.info("Graph memory closed")
    
    async def add(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MemoryChunk:
        """Add memory with graph node creation.
        
        Process:
        1. Store vector embedding in SQLite (parent class)
        2. Create graph node in Neo4j
        3. Link to semantically similar memories
        
        Args:
            text: Text content to store
            metadata: Optional metadata (source_type, session_id, etc.)
        
        Returns:
            MemoryChunk with id and embedding
        """
        # 1. Store in vector store (parent class)
        chunk = await super().add(text, metadata)
        
        # 2. Create graph node if Neo4j is available
        if self._is_graph_ready and self._driver:
            try:
                await self._create_memory_node(chunk, text, metadata)
                
                # 3. Link to similar memories
                await self._link_similar_memories(chunk, text)
                
            except Exception as exc:
                logger.warning(
                    "Failed to create graph node",
                    chunk_id=chunk.id,
                    error=str(exc),
                )
                # Don't fail the operation if graph creation fails
        
        return chunk
    
    async def _create_memory_node(
        self,
        chunk: MemoryChunk,
        text: str,
        metadata: Optional[Dict[str, Any]],
    ) -> None:
        """Create Neo4j node for memory chunk."""
        if not self._driver:
            return
        
        meta = metadata or {}
        text_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
        
        query = """
            CREATE (m:MemoryChunk {
                id: $id,
                text_hash: $hash,
                text_preview: $preview,
                created_at: datetime(),
                last_accessed: datetime(),
                access_count: 0,
                source_type: $source_type,
                session_id: $session_id,
                embedding_model: $model
            })
            RETURN m.id as id
        """
        
        params = {
            "id": str(chunk.id),
            "hash": text_hash,
            "preview": text[:200],  # First 200 chars for display
            "source_type": meta.get("source_type", "unknown"),
            "session_id": meta.get("session_id", "default"),
            "model": self.embedding_model_name,
        }
        
        async with self._driver.session(database=self.neo4j_database) as session:
            await session.run(query, params)
            logger.debug("Memory node created", chunk_id=chunk.id)
    
    async def _link_similar_memories(
        self,
        chunk: MemoryChunk,
        text: str,
    ) -> None:
        """Create SEMANTICALLY_SIMILAR relationships to existing memories."""
        if not self._driver:
            return
        
        # Find similar memories via vector search
        # Use parent class search (async) since we're in async context
        similar = await self.search(text, top_k=3)
        
        for sim in similar:
            if sim.id == chunk.id:
                continue  # Don't link to self
            
            try:
                await self._create_similarity_link(chunk.id, sim.id, sim.score or 0.0)
            except Exception as exc:
                logger.debug(
                    "Failed to create similarity link",
                    from_id=chunk.id,
                    to_id=sim.id,
                    error=str(exc),
                )
    
    async def _create_similarity_link(
        self,
        from_id: str,
        to_id: str,
        score: float,
    ) -> None:
        """Create bidirectional similarity relationship."""
        if not self._driver:
            return
        
        query = """
            MATCH (m1:MemoryChunk {id: $from_id})
            MATCH (m2:MemoryChunk {id: $to_id})
            MERGE (m1)-[r:SEMANTICALLY_SIMILAR]->(m2)
            ON CREATE SET r.score = $score, r.created_at = datetime()
            ON MATCH SET r.score = $score, r.updated_at = datetime()
        """
        
        async with self._driver.session(database=self.neo4j_database) as session:
            await session.run(query, {
                "from_id": str(from_id),
                "to_id": str(to_id),
                "score": score,
            })
    
    async def get_context_graph(
        self,
        query: str,
        depth: int = 2,
        top_k: int = 3,
    ) -> Dict[str, Any]:
        """Retrieve memory context with relationship expansion.
        
        This is the key differentiator from base CogneeMemory:
        - Base: Returns vector-similar chunks only
        - Graph: Expands via relationships for richer context
        
        Args:
            query: Search query text
            depth: Graph traversal depth (1-3 recommended)
            top_k: Number of seed memories from vector search
        
        Returns:
            Dict with 'seeds' (vector results) and 'related' (graph expansion)
        """
        # 1. Get seed memories via vector search
        seeds = await self.search(query, top_k=top_k)
        
        if not self._is_graph_ready or not self._driver:
            # Fallback to vector-only results
            return {
                "seeds": seeds,
                "related": [],
                "graph_expansion": False,
            }
        
        # 2. Expand via graph traversal
        seed_ids = [str(s.id) for s in seeds if s.id]
        
        try:
            related = await self._traverse_graph(seed_ids, depth)
            
            return {
                "seeds": seeds,
                "related": related,
                "graph_expansion": True,
                "traversal_depth": depth,
            }
            
        except Exception as exc:
            logger.warning("Graph traversal failed", error=str(exc))
            return {
                "seeds": seeds,
                "related": [],
                "graph_expansion": False,
                "error": str(exc),
            }
    
    async def _traverse_graph(
        self,
        seed_ids: List[str],
        depth: int,
    ) -> List[Dict[str, Any]]:
        """Traverse graph from seed memories."""
        if not self._driver or not seed_ids:
            return []
        
        # Use variable-length path matching
        query = """
            MATCH (seed:MemoryChunk)
            WHERE seed.id IN $seed_ids
            MATCH path = (seed)-[:SEMANTICALLY_SIMILAR|TEMPORALLY_FOLLOWS*1..$depth]-(related)
            WHERE related.id NOT IN $seed_ids
            WITH related, min(length(path)) as distance, 
                 sum(relationships(path)[-1].score) as total_score
            ORDER BY distance ASC, total_score DESC
            LIMIT 20
            RETURN related.id as id,
                   related.text_preview as preview,
                   related.source_type as source,
                   distance,
                   total_score
        """
        
        async with self._driver.session(database=self.neo4j_database) as session:
            result = await session.run(query, {
                "seed_ids": seed_ids,
                "depth": depth,
            })
            records = await result.data()
        
        return [
            {
                "id": r["id"],
                "text_preview": r["preview"],
                "source_type": r["source"],
                "graph_distance": r["distance"],
                "relationship_score": r["total_score"],
            }
            for r in records
        ]
    
    async def record_access(self, chunk_id: str) -> None:
        """Record that a memory was accessed (for LRU tracking).
        
        Updates access_count and last_accessed in Neo4j.
        
        Args:
            chunk_id: ID of accessed memory chunk
        """
        if not self._is_graph_ready or not self._driver:
            return
        
        query = """
            MATCH (m:MemoryChunk {id: $id})
            SET m.access_count = coalesce(m.access_count, 0) + 1,
                m.last_accessed = datetime()
        """
        
        try:
            async with self._driver.session(database=self.neo4j_database) as session:
                await session.run(query, {"id": str(chunk_id)})
        except Exception as exc:
            logger.debug("Failed to record access", chunk_id=chunk_id, error=str(exc))
    
    async def get_memory_stats(self) -> Dict[str, Any]:
        """Get combined stats from vector store and graph.
        
        Returns:
            Dict with vector_count, graph_count, relationship_count
        """
        # Get vector store stats (parent class method is async)
        vector_stats = await self.get_stats()
        
        graph_stats = {
            "node_count": 0,
            "relationship_count": 0,
            "indexed": False,
        }
        
        if self._is_graph_ready and self._driver:
            try:
                async with self._driver.session(database=self.neo4j_database) as session:
                    # Count nodes
                    node_result = await session.run(
                        "MATCH (m:MemoryChunk) RETURN count(m) as count"
                    )
                    node_record = await node_result.single()
                    graph_stats["node_count"] = node_record["count"] if node_record else 0
                    
                    # Count relationships
                    rel_result = await session.run(
                        "MATCH ()-[r:SEMANTICALLY_SIMILAR|TEMPORALLY_FOLLOWS]->() "
                        "RETURN count(r) as count"
                    )
                    rel_record = await rel_result.single()
                    graph_stats["relationship_count"] = rel_record["count"] if rel_record else 0
                    graph_stats["indexed"] = True
                    
            except Exception as exc:
                logger.warning("Failed to get graph stats", error=str(exc))
        
        return {
            "vector_store": vector_stats,
            "graph": graph_stats,
            "graph_ready": self._is_graph_ready,
        }


# Singleton instance for application use
_graph_memory_instance: Optional[GraphMemory] = None


async def get_graph_memory() -> GraphMemory:
    """Get singleton GraphMemory instance.
    
    Returns:
        Initialized GraphMemory instance
    """
    global _graph_memory_instance
    
    if _graph_memory_instance is None:
        settings = get_settings()
        
        if settings.use_graph_memory:
            _graph_memory_instance = GraphMemory()
        else:
            # Fall back to base CogneeMemory
            from src.memory import get_memory
            return get_memory()
    
    return _graph_memory_instance


async def init_graph_memory() -> None:
    """Initialize graph memory on application startup."""
    settings = get_settings()
    
    if not settings.use_graph_memory:
        logger.info("Graph memory disabled (USE_GRAPH_MEMORY=false)")
        return
    
    memory = await get_graph_memory()
    await memory.initialize()
    logger.info("Graph memory initialized")


async def close_graph_memory() -> None:
    """Close graph memory on application shutdown."""
    global _graph_memory_instance
    
    if _graph_memory_instance is not None:
        await _graph_memory_instance.close()
        _graph_memory_instance = None
        logger.info("Graph memory closed")
