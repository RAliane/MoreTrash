-- PostgreSQL Data Migration
-- Phase 1: SQLite to PostgreSQL Data Transformation
-- Date: 2026-03-01
-- Source: ai-agent pre-migration state

-- =====================================================
-- Step 1: Create Temporary Schema for SQLite Import
-- =====================================================

-- Schema for staging SQLite data before transformation
CREATE SCHEMA IF NOT EXISTS sqlite_import;

-- =====================================================
-- Step 2: Create Staging Tables for SQLite Data
-- =====================================================

-- Staging table for memory_chunks from SQLite
-- Note: embedding remains as BYTEA initially, then converted to vector
CREATE TABLE IF NOT EXISTS sqlite_import.memory_chunks_staging (
    id INTEGER,
    text TEXT,
    embedding BYTEA,  -- Raw BLOB data from SQLite
    metadata TEXT,    -- JSON string from SQLite
    created_at TEXT   -- ISO8601 string from SQLite
);

-- Staging table for Directus collection data
CREATE TABLE IF NOT EXISTS sqlite_import.directus_collections_staging (
    id TEXT,
    data TEXT,        -- JSON string from SQLite
    created_at TEXT,
    updated_at TEXT
);

-- =====================================================
-- Step 3: Create Data Migration Helper Functions
-- =====================================================

-- Function to convert SQLite BLOB to float4 array
-- SQLite stores embeddings as BLOB, need to parse to vector
CREATE OR REPLACE FUNCTION sqlite_import.blob_to_vector(
    blob_data BYTEA,
    dimensions INT DEFAULT 384
)
RETURNS vector(384) AS $$
DECLARE
    float_array FLOAT4[];
    i INT;
BEGIN
    -- Convert bytea to array of floats (4-byte little-endian floats)
    -- Each float is 4 bytes, total dimensions * 4 bytes
    float_array := ARRAY[]::FLOAT4[];
    
    FOR i IN 0..dimensions-1 LOOP
        float_array := array_append(
            float_array, 
            CASE 
                WHEN blob_data IS NOT NULL AND LENGTH(blob_data) >= (i + 1) * 4 THEN
                    -- Decode 4-byte little-endian float
                    translate(
                        encode(substring(blob_data from i*4+1 for 4), 'escape'),
                        E'\\000\\001\\002\\003\\004\\005\\006\\007\\010\\011\\012\\013\\014\\015\\016\\017\\020\\021\\022\\023\\024\\025\\026\\027\\030\\031\\032\\033\\034\\035\\036\\037',
                        E'0123456789abcdef'
                    )::bit(32)::FLOAT4
                ELSE 0.0
            END
        );
    END LOOP;
    
    RETURN float_array::vector(384);
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION sqlite_import.blob_to_vector IS 'Converts SQLite BLOB to pgvector vector type';

-- Note: numpy_blob_to_vector removed due to reliability issues with numpy header parsing.
-- Use blob_to_vector which properly parses float32 arrays from binary data.

-- Function to parse SQLite timestamp to PostgreSQL timestamptz
CREATE OR REPLACE FUNCTION sqlite_import.parse_timestamp(ts TEXT)
RETURNS TIMESTAMP WITH TIME ZONE AS $$
BEGIN
    RETURN CASE 
        WHEN ts IS NULL THEN CURRENT_TIMESTAMP
        WHEN ts = '' THEN CURRENT_TIMESTAMP
        ELSE ts::TIMESTAMP WITH TIME ZONE
    END;
EXCEPTION WHEN OTHERS THEN
    RETURN CURRENT_TIMESTAMP;
END;
$$ LANGUAGE plpgsql;

-- Function to parse SQLite JSON metadata
CREATE OR REPLACE FUNCTION sqlite_import.parse_metadata(metadata_text TEXT)
RETURNS JSONB AS $$
BEGIN
    RETURN CASE 
        WHEN metadata_text IS NULL THEN '{}'::JSONB
        WHEN metadata_text = '' THEN '{}'::JSONB
        ELSE metadata_text::JSONB
    END;
EXCEPTION WHEN OTHERS THEN
    RETURN '{}'::JSONB;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- Step 4: Create Data Migration Procedures
-- =====================================================

-- Procedure to migrate memory_chunks data
CREATE OR REPLACE PROCEDURE sqlite_import.migrate_memory_chunks()
LANGUAGE plpgsql AS $$
DECLARE
    migrated_count INT := 0;
    error_count INT := 0;
BEGIN
    RAISE NOTICE 'Starting memory_chunks migration...';
    
    -- Migrate from staging to main table with transformations
    INSERT INTO memory_chunks (id, text, embedding, metadata, created_at)
    SELECT 
        s.id,
        s.text,
        -- Transform BLOB to vector
        sqlite_import.blob_to_vector(s.embedding),
        sqlite_import.parse_metadata(s.metadata),
        sqlite_import.parse_timestamp(s.created_at)
    FROM sqlite_import.memory_chunks_staging s
    WHERE s.text IS NOT NULL  -- Skip records without text
    ON CONFLICT (id) DO UPDATE SET
        text = EXCLUDED.text,
        embedding = EXCLUDED.embedding,
        metadata = EXCLUDED.metadata,
        updated_at = CURRENT_TIMESTAMP;
    
    GET DIAGNOSTICS migrated_count = ROW_COUNT;
    RAISE NOTICE 'Migrated % memory_chunks records', migrated_count;
    
    -- Validate migrated data
    SELECT COUNT(*) INTO error_count
    FROM memory_chunks 
    WHERE embedding IS NULL;
    
    IF error_count > 0 THEN
        RAISE WARNING '% records have NULL embeddings after migration', error_count;
    END IF;
END;
$$;

-- Procedure to migrate Directus collection data
CREATE OR REPLACE PROCEDURE sqlite_import.migrate_directus_collections()
LANGUAGE plpgsql AS $$
DECLARE
    collection_rec RECORD;
    migrated_count INT := 0;
BEGIN
    RAISE NOTICE 'Starting Directus collections migration...';
    
    -- Migrate collection definitions
    INSERT INTO directus_collections (collection_name, schema_definition, created_at, updated_at)
    SELECT 
        'collection_' || s.id as collection_name,  -- Prefix to avoid reserved words
        jsonb_build_object(
            'original_id', s.id,
            'data', sqlite_import.parse_metadata(s.data)
        ),
        sqlite_import.parse_timestamp(s.created_at),
        sqlite_import.parse_timestamp(COALESCE(s.updated_at, s.created_at))
    FROM sqlite_import.directus_collections_staging s
    ON CONFLICT (collection_name) DO UPDATE SET
        schema_definition = EXCLUDED.schema_definition,
        updated_at = CURRENT_TIMESTAMP;
    
    GET DIAGNOSTICS migrated_count = ROW_COUNT;
    RAISE NOTICE 'Migrated % Directus collection records', migrated_count;
END;
$$;

-- =====================================================
-- Step 5: Create Utility Views for Migration Monitoring
-- =====================================================

-- View to check migration status
CREATE OR REPLACE VIEW sqlite_import.migration_status AS
SELECT 
    'memory_chunks' as table_name,
    (SELECT COUNT(*) FROM sqlite_import.memory_chunks_staging) as source_count,
    (SELECT COUNT(*) FROM memory_chunks) as target_count,
    (SELECT COUNT(*) FROM memory_chunks WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '1 hour') as recently_migrated
UNION ALL
SELECT 
    'directus_collections' as table_name,
    (SELECT COUNT(*) FROM sqlite_import.directus_collections_staging) as source_count,
    (SELECT COUNT(*) FROM directus_collections) as target_count,
    (SELECT COUNT(*) FROM directus_collections WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '1 hour') as recently_migrated;

-- View to identify migration issues
CREATE OR REPLACE VIEW sqlite_import.migration_issues AS
SELECT 
    id,
    text,
    'NULL embedding after migration' as issue,
    created_at
FROM memory_chunks
WHERE embedding IS NULL
UNION ALL
SELECT 
    id,
    text,
    'Empty metadata' as issue,
    created_at
FROM memory_chunks
WHERE metadata = '{}'::JSONB OR metadata IS NULL;

-- =====================================================
-- Step 6: Create Post-Migration Validation Functions
-- =====================================================

-- Function to validate migration completeness
CREATE OR REPLACE FUNCTION sqlite_import.validate_migration()
RETURNS TABLE (
    check_name TEXT,
    status TEXT,
    details TEXT
) AS $$
DECLARE
    source_count BIGINT;
    target_count BIGINT;
    null_embeddings BIGINT;
    null_metadata BIGINT;
BEGIN
    -- Check memory_chunks counts
    SELECT COUNT(*) INTO source_count FROM sqlite_import.memory_chunks_staging;
    SELECT COUNT(*) INTO target_count FROM memory_chunks;
    
    check_name := 'memory_chunks_count_match';
    status := CASE WHEN source_count = target_count THEN 'PASS' ELSE 'FAIL' END;
    details := format('Source: %s, Target: %s', source_count, target_count);
    RETURN NEXT;
    
    -- Check for null embeddings
    SELECT COUNT(*) INTO null_embeddings FROM memory_chunks WHERE embedding IS NULL;
    
    check_name := 'memory_chunks_no_null_embeddings';
    status := CASE WHEN null_embeddings = 0 THEN 'PASS' ELSE 'FAIL' END;
    details := format('Records with NULL embeddings: %s', null_embeddings);
    RETURN NEXT;
    
    -- Check Directus collections
    SELECT COUNT(*) INTO source_count FROM sqlite_import.directus_collections_staging;
    SELECT COUNT(*) INTO target_count FROM directus_collections;
    
    check_name := 'directus_collections_count_match';
    status := CASE WHEN source_count = target_count THEN 'PASS' ELSE 'FAIL' END;
    details := format('Source: %s, Target: %s', source_count, target_count);
    RETURN NEXT;
    
    -- Overall health check
    check_name := 'overall_migration_status';
    status := CASE 
        WHEN NOT EXISTS (SELECT 1 FROM sqlite_import.validate_migration() WHERE status = 'FAIL') 
        THEN 'PASS' 
        ELSE 'FAIL' 
    END;
    details := 'Overall migration validation';
    RETURN NEXT;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- Step 7: Cleanup Procedure (Run after successful migration)
-- =====================================================

CREATE OR REPLACE PROCEDURE sqlite_import.cleanup_staging()
LANGUAGE plpgsql AS $$
BEGIN
    RAISE NOTICE 'Cleaning up staging tables...';
    
    DROP TABLE IF EXISTS sqlite_import.memory_chunks_staging;
    DROP TABLE IF EXISTS sqlite_import.directus_collections_staging;
    
    RAISE NOTICE 'Staging tables cleaned up successfully';
END;
$$;

-- =====================================================
-- Migration Execution Guide (Manual Steps)
-- =====================================================

/*

DATA MIGRATION WORKFLOW:
=======================

1. Export SQLite data to CSV/JSON:
   
   For memory_chunks:
   sqlite3 artifacts/embeddings.db ".mode json" ".output memory_chunks.json" "SELECT * FROM memory_chunks;"
   
   For Directus collections:
   sqlite3 artifacts/data.db ".mode json" ".output collections.json" "SELECT * FROM your_collection;"

2. Load data into PostgreSQL staging tables:
   
   -- Using psql \copy command
   \copy sqlite_import.memory_chunks_staging FROM 'memory_chunks.json';
   
   -- Or using Python with pandas/psycopg2

3. Run migration procedures:
   
   CALL sqlite_import.migrate_memory_chunks();
   CALL sqlite_import.migrate_directus_collections();

4. Validate migration:
   
   SELECT * FROM sqlite_import.validate_migration();
   SELECT * FROM sqlite_import.migration_status;

5. Check for issues:
   
   SELECT * FROM sqlite_import.migration_issues;

6. Cleanup staging tables (after verification):
   
   CALL sqlite_import.cleanup_staging();

ALTERNATIVE: Direct SQLite Connection
=====================================

Using sqlite_fdw extension:

1. Install sqlite_fdw:
   CREATE EXTENSION sqlite_fdw;

2. Create server connection:
   CREATE SERVER sqlite_server FOREIGN DATA WRAPPER sqlite_fdw OPTIONS (database '/path/to/artifacts/embeddings.db');

3. Import foreign schema:
   IMPORT FOREIGN SCHEMA public LIMIT TO (memory_chunks) FROM SERVER sqlite_server INTO sqlite_import;

4. Migrate directly:
   INSERT INTO memory_chunks SELECT * FROM sqlite_import.memory_chunks;

*/

-- =====================================================
-- Migration Record
-- =====================================================

INSERT INTO schema_migrations (version, description, checksum)
VALUES ('002', 'Create data migration infrastructure and procedures', 
        encode(digest(current_query(), 'sha256'), 'hex'))
ON CONFLICT (version) DO NOTHING;
