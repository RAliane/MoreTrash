-- Pre-Migration SQLite Schema Snapshot
-- Date: 2026-03-01
-- Source: ai-agent pre-migration state

-- =====================================================
-- Database: artifacts/data.db (Directus Client)
-- =====================================================

-- Dynamic collection tables created by DirectusClient._ensure_table()
-- Each collection has the following schema:
CREATE TABLE IF NOT EXISTS {collection_name} (
    id TEXT PRIMARY KEY,
    data TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Note: Collections are created dynamically at runtime based on usage.
-- Known collections in use: determined by application logic

-- =====================================================
-- Database: artifacts/embeddings.db (Cognee Memory/Vector Store)
-- =====================================================

CREATE TABLE IF NOT EXISTS memory_chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT NOT NULL,
    embedding BLOB NOT NULL,
    metadata TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_memory_chunks_created 
ON memory_chunks(created_at);

-- =====================================================
-- Notes:
-- - These databases are created at runtime on first use
-- - Schema extracted from src/memory.py and src/directus_client.py
-- - Migration target: PostgreSQL (Directus) + Neo4j (Graph) + LanceDB (Vectors)
-- =====================================================
