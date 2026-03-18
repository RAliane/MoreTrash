-- PostgreSQL Schema Migration
-- Phase 1: SQLite to PostgreSQL with pgvector
-- Date: 2026-03-01
-- Source: ai-agent pre-migration state

-- =====================================================
-- Step 1: Enable Required Extensions
-- =====================================================

-- Enable pgvector for vector operations
CREATE EXTENSION IF NOT EXISTS pgvector;

-- Enable UUID extension for better primary key generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =====================================================
-- Step 2: Create Schema Versions Table
-- =====================================================

CREATE TABLE IF NOT EXISTS schema_migrations (
    id SERIAL PRIMARY KEY,
    version VARCHAR(255) NOT NULL UNIQUE,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    description TEXT,
    checksum VARCHAR(64)
);

-- Create index for fast version lookups
CREATE INDEX IF NOT EXISTS idx_schema_migrations_version 
ON schema_migrations(version);

-- =====================================================
-- Step 3: Convert SQLite memory_chunks Table
-- =====================================================
-- Source: artifacts/embeddings.db (Cognee Memory/Vector Store)

CREATE TABLE IF NOT EXISTS memory_chunks (
    -- Convert SQLite INTEGER AUTOINCREMENT to PostgreSQL SERIAL
    id SERIAL PRIMARY KEY,
    
    -- Text content (SQLite TEXT -> PostgreSQL TEXT)
    text TEXT NOT NULL,
    
    -- Vector embedding (SQLite BLOB -> PostgreSQL vector(384))
    -- Using 384 dimensions for all-MiniLM-L6-v2 embeddings
    embedding vector(384) NOT NULL,
    
    -- Metadata as JSONB for better querying (SQLite TEXT -> PostgreSQL JSONB)
    metadata JSONB,
    
    -- Timestamps with timezone support
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Comments for documentation
COMMENT ON TABLE memory_chunks IS 'Vector embeddings storage migrated from SQLite';
COMMENT ON COLUMN memory_chunks.embedding IS '384-dimensional vector embedding using pgvector';
COMMENT ON COLUMN memory_chunks.metadata IS 'JSON metadata associated with the memory chunk';

-- =====================================================
-- Step 4: Create Indexes for Performance
-- =====================================================

-- Index on created_at for time-based queries (recreated from SQLite)
CREATE INDEX IF NOT EXISTS idx_memory_chunks_created 
ON memory_chunks(created_at);

-- Index on updated_at for tracking modifications
CREATE INDEX IF NOT EXISTS idx_memory_chunks_updated 
ON memory_chunks(updated_at);

-- GIN index for JSONB metadata queries
CREATE INDEX IF NOT EXISTS idx_memory_chunks_metadata 
ON memory_chunks USING GIN (metadata);

-- HNSW index for fast vector similarity search (pgvector)
-- Using cosine similarity for semantic search
CREATE INDEX IF NOT EXISTS idx_memory_chunks_embedding_hnsw 
ON memory_chunks USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Optional: IVFFlat index as alternative for larger datasets
-- CREATE INDEX IF NOT EXISTS idx_memory_chunks_embedding_ivfflat 
-- ON memory_chunks USING ivfflat (embedding vector_cosine_ops)
-- WITH (lists = 100);

-- =====================================================
-- Step 5: Create Directus Collections Table
-- =====================================================
-- Source: artifacts/data.db (Dynamic collection storage)
-- Note: Dynamic collection tables will be created at runtime

-- Base table for Directus collection tracking
CREATE TABLE IF NOT EXISTS directus_collections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    collection_name VARCHAR(255) NOT NULL UNIQUE,
    schema_definition JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create index for collection name lookups
CREATE INDEX IF NOT EXISTS idx_directus_collections_name 
ON directus_collections(collection_name);

-- Create GIN index for schema definition queries
CREATE INDEX IF NOT EXISTS idx_directus_collections_schema 
ON directus_collections USING GIN (schema_definition);

-- =====================================================
-- Step 6: Create Dynamic Collection Template Function
-- =====================================================

-- Function to create dynamic collection tables (replaces SQLite dynamic creation)
CREATE OR REPLACE FUNCTION create_collection_table(collection_name TEXT)
RETURNS void AS $$
BEGIN
    EXECUTE format('
        CREATE TABLE IF NOT EXISTS %I (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            data JSONB NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )', 
        collection_name
    );
    
    -- Create indexes for the new collection table
    EXECUTE format('
        CREATE INDEX IF NOT EXISTS idx_%I_created ON %I(created_at)', 
        collection_name, collection_name
    );
    
    EXECUTE format('
        CREATE INDEX IF NOT EXISTS idx_%I_updated ON %I(updated_at)', 
        collection_name, collection_name
    );
    
    EXECUTE format('
        CREATE INDEX IF NOT EXISTS idx_%I_data ON %I USING GIN (data)', 
        collection_name, collection_name
    );
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION create_collection_table IS 'Creates a new collection table matching the Directus SQLite schema';

-- =====================================================
-- Step 7: Create Trigger Function for updated_at
-- =====================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply updated_at trigger to memory_chunks
CREATE TRIGGER update_memory_chunks_updated_at
    BEFORE UPDATE ON memory_chunks
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Apply updated_at trigger to directus_collections
CREATE TRIGGER update_directus_collections_updated_at
    BEFORE UPDATE ON directus_collections
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- Step 8: Create Vector Search Function
-- =====================================================

-- Function for semantic search using vector similarity
CREATE OR REPLACE FUNCTION search_memory_chunks(
    query_embedding vector(384),
    similarity_threshold FLOAT DEFAULT 0.7,
    max_results INT DEFAULT 10
)
RETURNS TABLE (
    id INT,
    text TEXT,
    metadata JSONB,
    similarity FLOAT,
    created_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        mc.id,
        mc.text,
        mc.metadata,
        1 - (mc.embedding <=> query_embedding) AS similarity,
        mc.created_at
    FROM memory_chunks mc
    WHERE 1 - (mc.embedding <=> query_embedding) >= similarity_threshold
    ORDER BY mc.embedding <=> query_embedding
    LIMIT max_results;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION search_memory_chunks IS 'Performs semantic search on memory_chunks using cosine similarity';

-- =====================================================
-- Step 9: Create Health Check Function
-- =====================================================

CREATE OR REPLACE FUNCTION database_health_check()
RETURNS TABLE (
    status TEXT,
    pg_version TEXT,
    vector_extension_version TEXT,
    total_memory_chunks BIGINT,
    total_collections BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        'healthy'::TEXT as status,
        version()::TEXT as pg_version,
        (SELECT extversion FROM pg_extension WHERE extname = 'vector')::TEXT as vector_extension_version,
        (SELECT COUNT(*) FROM memory_chunks) as total_memory_chunks,
        (SELECT COUNT(*) FROM directus_collections) as total_collections;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION database_health_check IS 'Returns database health and statistics';

-- =====================================================
-- Migration Record
-- =====================================================

INSERT INTO schema_migrations (version, description, checksum)
VALUES ('001', 'Create PostgreSQL schema with pgvector support', 
        encode(digest(current_query(), 'sha256'), 'hex'))
ON CONFLICT (version) DO NOTHING;
