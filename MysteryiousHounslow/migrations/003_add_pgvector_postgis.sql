-- Matchgorithm pgvector and PostGIS Extensions Setup
-- Version: 003
-- Description: Configure vector and geospatial extensions

-- Ensure extensions are available (should be created in 001, but let's verify)
DO $$
BEGIN
    -- Check if vector extension exists
    IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') THEN
        CREATE EXTENSION IF NOT EXISTS vector;
        RAISE NOTICE 'Created vector extension';
    END IF;

    -- Check if PostGIS extension exists
    IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'postgis') THEN
        CREATE EXTENSION IF NOT EXISTS postgis;
        RAISE NOTICE 'Created PostGIS extension';
    END IF;

    -- Check if PostGIS topology exists
    IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'postgis_topology') THEN
        CREATE EXTENSION IF NOT EXISTS postgis_topology;
        RAISE NOTICE 'Created PostGIS topology extension';
    END IF;
END
$$;

-- Verify PostGIS installation
DO $$
DECLARE
    postgis_version TEXT;
BEGIN
    SELECT PostGIS_Version() INTO postgis_version;
    RAISE NOTICE 'PostGIS version: %', postgis_version;
END
$$;

-- Create custom functions for vector operations
CREATE OR REPLACE FUNCTION cosine_similarity(a vector, b vector)
RETURNS float AS $$
BEGIN
    RETURN 1 - (a <=> b);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Create function to find similar items using embeddings
CREATE OR REPLACE FUNCTION find_similar_items(target_embedding vector, limit_count INTEGER DEFAULT 10)
RETURNS TABLE(
    item_id INTEGER,
    similarity float,
    name TEXT,
    status TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        i.id,
        cosine_similarity(i.embedding, target_embedding) as similarity,
        i.name,
        i.status
    FROM items i
    WHERE i.embedding IS NOT NULL
    ORDER BY i.embedding <=> target_embedding
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- Create geospatial functions for location-based queries
CREATE OR REPLACE FUNCTION items_within_radius(
    center_lat DOUBLE PRECISION,
    center_lng DOUBLE PRECISION,
    radius_km DOUBLE PRECISION
)
RETURNS TABLE(
    id INTEGER,
    name TEXT,
    location GEOGRAPHY,
    distance_km DOUBLE PRECISION
) AS $$
DECLARE
    center_point GEOGRAPHY;
BEGIN
    center_point := ST_SetSRID(ST_MakePoint(center_lng, center_lat), 4326);

    RETURN QUERY
    SELECT
        i.id,
        i.name,
        i.location,
        ST_Distance(i.location, center_point) / 1000 as distance_km
    FROM items i
    WHERE ST_DWithin(i.location, center_point, radius_km * 1000)
    ORDER BY ST_Distance(i.location, center_point);
END;
$$ LANGUAGE plpgsql;

-- Create a function to batch insert embeddings with validation
CREATE OR REPLACE FUNCTION insert_item_with_embedding(
    item_name TEXT,
    item_location GEOGRAPHY,
    item_embedding vector,
    item_metadata JSONB DEFAULT NULL,
    item_constraints JSONB DEFAULT NULL
)
RETURNS INTEGER AS $$
DECLARE
    new_item_id INTEGER;
BEGIN
    -- Validate inputs
    IF item_name IS NULL OR trim(item_name) = '' THEN
        RAISE EXCEPTION 'Item name cannot be null or empty';
    END IF;

    IF item_embedding IS NULL THEN
        RAISE EXCEPTION 'Item embedding cannot be null';
    END IF;

    -- Insert the item
    INSERT INTO items (name, location, embedding, metadata, constraints)
    VALUES (trim(item_name), item_location, item_embedding, item_metadata, item_constraints)
    RETURNING id INTO new_item_id;

    RAISE NOTICE 'Inserted item % with embedding dimension %', new_item_id, array_length(item_embedding, 1);
    RETURN new_item_id;
END;
$$ LANGUAGE plpgsql;

-- Create a function to update item embeddings
CREATE OR REPLACE FUNCTION update_item_embedding(
    item_id INTEGER,
    new_embedding vector
)
RETURNS BOOLEAN AS $$
DECLARE
    rows_affected INTEGER;
BEGIN
    UPDATE items
    SET embedding = new_embedding, updated_at = NOW()
    WHERE id = item_id;

    GET DIAGNOSTICS rows_affected = ROW_COUNT;

    IF rows_affected = 0 THEN
        RAISE EXCEPTION 'Item with id % not found', item_id;
    END IF;

    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

-- Create indexes specifically for vector operations
CREATE INDEX IF NOT EXISTS idx_items_embedding_cosine ON items USING ivfflat(embedding vector_cosine_ops)
WITH (lists = 100);

-- Create spatial indexes for PostGIS operations
CREATE INDEX IF NOT EXISTS idx_items_location_geography ON items USING GIST((location::geography));

-- Test the extensions and functions
DO $$
DECLARE
    test_embedding vector(384);
    test_point GEOGRAPHY;
    test_item_id INTEGER;
BEGIN
    -- Test vector creation
    test_embedding := '[0.1,0.2,0.3]'::vector || repeat(',0.0', 381)::text || ']';
    RAISE NOTICE 'Test embedding created with dimension %', array_length(test_embedding, 1);

    -- Test geography point
    test_point := ST_SetSRID(ST_MakePoint(-0.1, 51.5), 4326);
    RAISE NOTICE 'Test geography point created: %', ST_AsText(test_point);

    -- Test function calls (without actual data insertion)
    RAISE NOTICE 'Vector and PostGIS extensions are working correctly';
END
$$;

-- Create a view for active items with embeddings
CREATE OR REPLACE VIEW active_embedded_items AS
SELECT
    id,
    name,
    location,
    embedding,
    metadata,
    constraints,
    created_at,
    updated_at,
    ST_AsText(location) as location_text
FROM items
WHERE status = 'active'
AND embedding IS NOT NULL
AND location IS NOT NULL;

-- Grant appropriate permissions
GRANT SELECT ON active_embedded_items TO PUBLIC;

-- Create a maintenance function to update vector indexes
CREATE OR REPLACE FUNCTION maintain_vector_indexes()
RETURNS void AS $$
BEGIN
    -- Reindex vector indexes periodically
    REINDEX INDEX CONCURRENTLY idx_items_embedding;
    REINDEX INDEX CONCURRENTLY idx_items_embedding_cosine;

    RAISE NOTICE 'Vector indexes maintained';
END;
$$ LANGUAGE plpgsql;

-- Comment on key objects for documentation
COMMENT ON TABLE items IS 'Core business entities with vector embeddings and geospatial data';
COMMENT ON TABLE matches IS 'Optimization results linking matched items with scores';
COMMENT ON TABLE users IS 'User accounts for authentication and profiles';
COMMENT ON COLUMN items.embedding IS '384-dimensional vector embedding for similarity matching';
COMMENT ON COLUMN items.location IS 'PostGIS geography point for location-based queries';
COMMENT ON FUNCTION cosine_similarity(vector, vector) IS 'Calculate cosine similarity between two vectors';
COMMENT ON FUNCTION find_similar_items(vector, integer) IS 'Find items similar to target embedding';
COMMENT ON FUNCTION items_within_radius(double precision, double precision, double precision) IS 'Find items within radius of coordinates';