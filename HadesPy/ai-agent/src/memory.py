"""Cognee RAG memory system for the AI agent.

This module provides memory management with dual-mode operation:
1. Legacy mode: SQLite-based vector store (default)
2. Cognee mode: Graph-based memory via CogneeAdapter (when USE_COGNEE_MEMORY=true)

The system gracefully falls back to legacy mode if Cognee is unavailable.

Usage:
    >>> from src.memory import get_memory, init_memory
    >>> memory = await init_memory()
    >>> await memory.add("Important information")
    >>> results = await memory.search("query")
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from sentence_transformers import SentenceTransformer

from src.config import get_settings
from src.integrations.cognee_adapter import CogneeAdapter, get_cognee_adapter
from src.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class MemoryChunk:
    """A chunk of memory with embedding."""
    id: Optional[str]
    text: str
    embedding: Optional[List[float]] = None
    metadata: Optional[Dict[str, Any]] = None
    score: Optional[float] = None


class CogneeMemory:
    """Cognee RAG-based memory system with dual-mode operation.
    
    This class provides a unified interface for memory operations,
    delegating to CogneeAdapter when USE_COGNEE_MEMORY is enabled,
    otherwise using the legacy SQLite-based vector store.
    
    Attributes:
        settings: Application settings
        embedding_model_name: Name of the sentence transformer model
        vector_store_path: Path to SQLite vector store (legacy mode)
        _model: Lazy-loaded embedding model
        _dimension: Embedding dimension
        _cognee_adapter: Cognee adapter instance (when enabled)
        _use_cognee: Whether to use Cognee integration
    """

    def __init__(
        self,
        embedding_model: Optional[str] = None,
        vector_store_path: Optional[str] = None,
    ):
        self.settings = get_settings()
        self.embedding_model_name = embedding_model or self.settings.cognee_embedding_model
        self.vector_store_path = vector_store_path or self.settings.cognee_vector_store
        self._model: Optional[SentenceTransformer] = None
        self._dimension: Optional[int] = None
        self._cognee_adapter: Optional[CogneeAdapter] = None
        self._use_cognee = self.settings.use_cognee_memory
        
        logger.info(
            "CogneeMemory initialized",
            use_cognee=self._use_cognee,
            embedding_model=self.embedding_model_name,
        )

    def _get_model(self) -> SentenceTransformer:
        """Lazy load the embedding model."""
        if self._model is None:
            logger.info(
                "Loading embedding model",
                model=self.embedding_model_name,
            )
            self._model = SentenceTransformer(self.embedding_model_name)
            self._dimension = self._model.get_sentence_embedding_dimension()
            logger.info(
                "Embedding model loaded",
                model=self.embedding_model_name,
                dimension=self._dimension,
            )
        return self._model

    @contextmanager
    def _get_db_connection(self):
        """Get SQLite database connection for vector store."""
        Path(self.vector_store_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.vector_store_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _ensure_schema(self) -> None:
        """Ensure vector store schema exists."""
        with self._get_db_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    text TEXT NOT NULL,
                    embedding BLOB NOT NULL,
                    metadata TEXT,
                    content_hash TEXT UNIQUE,  -- For idempotent writes
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memory_chunks_created 
                ON memory_chunks(created_at)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memory_chunks_hash 
                ON memory_chunks(content_hash)
            """)
            conn.commit()

    def _encode_text(self, text: str) -> List[float]:
        """Encode text to embedding vector."""
        model = self._get_model()
        embedding = model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def _embedding_to_bytes(self, embedding: List[float]) -> bytes:
        """Convert embedding list to bytes."""
        return np.array(embedding, dtype=np.float32).tobytes()

    def _bytes_to_embedding(self, data: bytes) -> List[float]:
        """Convert bytes to embedding list."""
        arr = np.frombuffer(data, dtype=np.float32)
        return arr.tolist()

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        a_arr = np.array(a)
        b_arr = np.array(b)
        dot = np.dot(a_arr, b_arr)
        norm_a = np.linalg.norm(a_arr)
        norm_b = np.linalg.norm(b_arr)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(dot / (norm_a * norm_b))

    def _compute_content_hash(self, text: str, metadata: Optional[Dict] = None) -> str:
        """Compute hash for idempotent writes."""
        import hashlib
        content = text + json.dumps(metadata or {}, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:32]

    async def _get_cognee_adapter(self) -> Optional[CogneeAdapter]:
        """Get Cognee adapter if enabled and available."""
        if not self._use_cognee:
            return None
        
        if self._cognee_adapter is None:
            try:
                self._cognee_adapter = get_cognee_adapter()
                # Check if Cognee is healthy
                is_healthy = await self._cognee_adapter.health_check()
                if not is_healthy:
                    logger.warning("Cognee unavailable, falling back to legacy mode")
                    self._cognee_adapter = None
            except Exception as e:
                logger.warning(f"Failed to initialize Cognee adapter: {e}")
                self._cognee_adapter = None
        
        return self._cognee_adapter

    async def add(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MemoryChunk:
        """Add a memory chunk to the store.
        
        In Cognee mode, delegates to CogneeAdapter.
        In legacy mode, uses SQLite with idempotent writes.
        
        Args:
            text: Text content to store
            metadata: Optional metadata dictionary
            
        Returns:
            MemoryChunk with ID and embedding
        """
        # Try Cognee mode first if enabled
        adapter = await self._get_cognee_adapter()
        if adapter:
            try:
                from src.integrations.cognee_adapter import UserInteraction
                interaction = UserInteraction(
                    user_id=metadata.get("user_id", "anonymous") if metadata else "anonymous",
                    action="stored",
                    entity_id=metadata.get("entity_id", "memory_chunk") if metadata else "memory_chunk",
                    entity_type="MemoryChunk",
                    timestamp=metadata.get("timestamp", "") if metadata else "",
                    metadata={"text": text, **(metadata or {})},
                )
                result = await adapter.ingest_user_interactions([interaction])
                if result.success and result.node_ids:
                    return MemoryChunk(
                        id=result.node_ids[0],
                        text=text,
                        metadata=metadata,
                    )
            except Exception as e:
                logger.warning(f"Cognee ingestion failed, falling back: {e}")
        
        # Legacy SQLite mode
        self._ensure_schema()
        
        embedding = self._encode_text(text)
        embedding_bytes = self._embedding_to_bytes(embedding)
        metadata_json = json.dumps(metadata) if metadata else None
        content_hash = self._compute_content_hash(text, metadata)

        with self._get_db_connection() as conn:
            # Check for existing entry (idempotent)
            cursor = conn.execute(
                "SELECT id FROM memory_chunks WHERE content_hash = ?",
                (content_hash,),
            )
            existing = cursor.fetchone()
            
            if existing:
                # Return existing chunk
                logger.debug("Memory chunk already exists, returning existing", hash=content_hash)
                return MemoryChunk(
                    id=str(existing["id"]),
                    text=text,
                    embedding=embedding,
                    metadata=metadata,
                )
            
            # Insert new chunk
            cursor = conn.execute(
                """
                INSERT INTO memory_chunks (text, embedding, metadata, content_hash)
                VALUES (?, ?, ?, ?)
                """,
                (text, embedding_bytes, metadata_json, content_hash),
            )
            conn.commit()
            chunk_id = cursor.lastrowid

        logger.info(
            "Memory chunk added",
            chunk_id=chunk_id,
            text_length=len(text),
        )

        return MemoryChunk(
            id=str(chunk_id),
            text=text,
            embedding=embedding,
            metadata=metadata,
        )

    async def add_batch(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
    ) -> List[MemoryChunk]:
        """Add multiple memory chunks in batch.

        Uses batch encoding for performance while maintaining idempotency
        through content hash checks.

        Args:
            texts: List of text contents
            metadatas: Optional list of metadata dictionaries

        Returns:
            List of MemoryChunk objects
        """
        if metadatas is None:
            metadatas = [None] * len(texts)

        # Use batch encoding for performance (single model call)
        model = self._get_model()
        embeddings = await asyncio.to_thread(model.encode, texts, convert_to_numpy=True)

        # Process each item individually for idempotency
        chunks = []
        for text, embedding_arr, metadata in zip(texts, embeddings, metadatas):
            chunk = await self._add_with_embedding(text, embedding_arr.tolist(), metadata)
            chunks.append(chunk)

        logger.info(
            "Memory chunks added in batch",
            count=len(chunks),
        )

        return chunks

    async def _add_with_embedding(
        self,
        text: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MemoryChunk:
        """Add a memory chunk with pre-computed embedding (idempotent).

        Internal method used by add_batch to avoid re-encoding.

        Args:
            text: Text content to store
            embedding: Pre-computed embedding vector
            metadata: Optional metadata dictionary

        Returns:
            MemoryChunk with ID and embedding
        """
        # Try Cognee mode first if enabled
        adapter = await self._get_cognee_adapter()
        if adapter:
            try:
                from src.integrations.cognee_adapter import UserInteraction
                timestamp = metadata.get("timestamp") if metadata else None
                if not timestamp:
                    timestamp = datetime.now(timezone.utc).isoformat()
                interaction = UserInteraction(
                    user_id=metadata.get("user_id", "anonymous") if metadata else "anonymous",
                    action="stored",
                    entity_id=metadata.get("entity_id", "memory_chunk") if metadata else "memory_chunk",
                    entity_type="MemoryChunk",
                    timestamp=timestamp,
                    metadata={"text": text, **(metadata or {})},
                )
                result = await adapter.ingest_user_interactions([interaction])
                if result.success and result.node_ids:
                    return MemoryChunk(
                        id=result.node_ids[0],
                        text=text,
                        metadata=metadata,
                    )
            except Exception as e:
                logger.warning(f"Cognee ingestion failed, falling back: {e}")

        # Legacy SQLite mode
        self._ensure_schema()

        embedding_bytes = self._embedding_to_bytes(embedding)
        metadata_json = json.dumps(metadata) if metadata else None
        content_hash = self._compute_content_hash(text, metadata)

        with self._get_db_connection() as conn:
            # Check for existing entry (idempotent)
            cursor = conn.execute(
                "SELECT id FROM memory_chunks WHERE content_hash = ?",
                (content_hash,),
            )
            existing = cursor.fetchone()

            if existing:
                # Return existing chunk
                logger.debug("Memory chunk already exists, returning existing", hash=content_hash)
                return MemoryChunk(
                    id=str(existing["id"]),
                    text=text,
                    embedding=embedding,
                    metadata=metadata,
                )

            # Insert new chunk
            cursor = conn.execute(
                """
                INSERT INTO memory_chunks (text, embedding, metadata, content_hash)
                VALUES (?, ?, ?, ?)
                """,
                (text, embedding_bytes, metadata_json, content_hash),
            )
            conn.commit()
            chunk_id = cursor.lastrowid

        return MemoryChunk(
            id=str(chunk_id),
            text=text,
            embedding=embedding,
            metadata=metadata,
        )

    async def search(
        self,
        query: str,
        top_k: int = 5,
        threshold: Optional[float] = None,
    ) -> List[MemoryChunk]:
        """Search for similar memory chunks.
        
        In Cognee mode, uses semantic search via CogneeAdapter.
        In legacy mode, uses cosine similarity on SQLite store.
        
        Args:
            query: Search query
            top_k: Maximum results to return
            threshold: Similarity threshold (0-1)
            
        Returns:
            List of MemoryChunk objects sorted by similarity
        """
        threshold = threshold or self.settings.cognee_similarity_threshold
        
        # Try Cognee mode first if enabled
        adapter = await self._get_cognee_adapter()
        if adapter:
            try:
                results = await adapter.search_similar(
                    query=query,
                    top_k=top_k,
                )
                if results:
                    return [
                        MemoryChunk(
                            id=r.node_id,
                            text=r.content,
                            metadata=r.metadata,
                            score=r.score,
                        )
                        for r in results
                    ]
            except Exception as e:
                logger.warning(f"Cognee search failed, falling back: {e}")
        
        # Legacy SQLite mode
        self._ensure_schema()
        
        query_embedding = self._encode_text(query)

        with self._get_db_connection() as conn:
            cursor = conn.execute(
                "SELECT id, text, embedding, metadata FROM memory_chunks"
            )
            rows = cursor.fetchall()

        results = []
        for row in rows:
            embedding = self._bytes_to_embedding(row["embedding"])
            similarity = self._cosine_similarity(query_embedding, embedding)

            if similarity >= threshold:
                metadata = json.loads(row["metadata"]) if row["metadata"] else None
                results.append(MemoryChunk(
                    id=str(row["id"]),
                    text=row["text"],
                    embedding=embedding,
                    metadata=metadata,
                    score=similarity,
                ))

        # Sort by similarity score
        results.sort(key=lambda x: x.score or 0, reverse=True)

        logger.info(
            "Memory search completed",
            query_length=len(query),
            results_found=len(results),
            top_k=top_k,
        )

        return results[:top_k]

    async def get_context(
        self,
        query: str,
        max_tokens: int = 2000,
    ) -> str:
        """Get relevant context for a query, formatted for LLM consumption.
        
        Args:
            query: Query to search for context
            max_tokens: Maximum tokens to return
            
        Returns:
            Formatted context string
        """
        if not self.settings.cognee_auto_context_window:
            chunks = await self.search(query, top_k=self.settings.cognee_max_results)
        else:
            # Adaptive context window based on query complexity
            chunks = await self.search(query, top_k=self.settings.cognee_max_results)

        if not chunks:
            return ""

        context_parts = []
        current_tokens = 0
        approx_tokens_per_char = 0.25

        for chunk in chunks:
            chunk_text = chunk.text
            chunk_tokens = int(len(chunk_text) * approx_tokens_per_char)

            if current_tokens + chunk_tokens > max_tokens:
                break

            context_parts.append(chunk_text)
            current_tokens += chunk_tokens

        return "\n\n---\n\n".join(context_parts)

    async def get_graph_context(
        self,
        entity_id: str,
        depth: int = 2,
    ) -> Optional[Dict[str, Any]]:
        """Get graph neighborhood context (Cognee mode only).
        
        Args:
            entity_id: Entity node ID
            depth: Neighborhood depth (1-3)
            
        Returns:
            Graph context dictionary or None if unavailable
        """
        adapter = await self._get_cognee_adapter()
        if not adapter:
            logger.debug("Graph context not available in legacy mode")
            return None
        
        try:
            context = await adapter.get_graph_context(entity_id, depth=depth)
            if context:
                return {
                    "entity_id": context.entity_id,
                    "entity_type": context.entity_type,
                    "properties": context.properties,
                    "neighbors": context.neighbors,
                    "relationships": context.relationships,
                    "depth": context.depth,
                }
        except Exception as e:
            logger.warning(f"Failed to get graph context: {e}")
        
        return None

    async def delete(self, chunk_id: str) -> bool:
        """Delete a memory chunk by ID.
        
        Args:
            chunk_id: ID of chunk to delete
            
        Returns:
            True if deleted, False otherwise
        """
        # Note: Cognee delete not implemented in adapter yet
        # For now, only delete from legacy store
        
        with self._get_db_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM memory_chunks WHERE id = ?",
                (chunk_id,),
            )
            conn.commit()
            deleted = cursor.rowcount > 0

        if deleted:
            logger.info("Memory chunk deleted", chunk_id=chunk_id)
        return deleted

    async def clear(self) -> int:
        """Clear all memory chunks. Returns count of deleted records.
        
        Returns:
            Number of chunks deleted
        """
        with self._get_db_connection() as conn:
            cursor = conn.execute("DELETE FROM memory_chunks")
            conn.commit()
            count = cursor.rowcount

        logger.info("All memory chunks cleared", count=count)
        return count

    async def get_stats(self) -> Dict[str, Any]:
        """Get memory store statistics.
        
        Returns:
            Dictionary with statistics
        """
        with self._get_db_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) as count FROM memory_chunks")
            row = cursor.fetchone()
            total_chunks = row["count"] if row else 0

        return {
            "total_chunks": total_chunks,
            "embedding_model": self.embedding_model_name,
            "embedding_dimension": self._dimension,
            "vector_store_path": self.vector_store_path,
            "use_cognee": self._use_cognee,
            "cognee_available": self._cognee_adapter is not None,
        }


# Singleton instance
_memory_instance: Optional[CogneeMemory] = None


def get_memory() -> CogneeMemory:
    """Get singleton memory instance."""
    global _memory_instance
    if _memory_instance is None:
        _memory_instance = CogneeMemory()
    return _memory_instance


async def init_memory() -> CogneeMemory:
    """Initialize memory system.
    
    Returns:
        Initialized CogneeMemory instance
    """
    memory = get_memory()
    memory._ensure_schema()
    
    # Try to initialize Cognee if enabled
    if memory._use_cognee:
        adapter = await memory._get_cognee_adapter()
        if adapter:
            logger.info("Memory initialized with Cognee integration")
        else:
            logger.warning("Memory initialized in legacy mode (Cognee unavailable)")
    else:
        logger.info("Memory initialized in legacy mode")
    
    return memory
