-- Matchgorithm Database Indexes and Performance Optimization
-- Version: 002
-- Description: Add performance indexes and constraints

-- Additional spatial indexes for better geospatial queries
CREATE INDEX IF NOT EXISTS idx_items_location_gist ON items USING GIST(location);
CREATE INDEX IF NOT EXISTS idx_items_location_spgist ON items USING SPGIST(location);

-- Partial indexes for active items
CREATE INDEX IF NOT EXISTS idx_items_active_location ON items USING GIST(location)
WHERE status = 'active';

-- Composite indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_items_status_created ON items(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_matches_status_score ON matches(status, score DESC);
CREATE INDEX IF NOT EXISTS idx_optimization_requests_user_status ON optimization_requests(user_id, status);

-- JSONB indexes for metadata queries
CREATE INDEX IF NOT EXISTS idx_items_metadata_gin ON items USING GIN(metadata);
CREATE INDEX IF NOT EXISTS idx_items_constraints_gin ON items USING GIN(constraints);
CREATE INDEX IF NOT EXISTS idx_matches_metadata_gin ON matches USING GIN(metadata);

-- Full-text search indexes
CREATE INDEX IF NOT EXISTS idx_items_name_fts ON items USING GIN(to_tsvector('english', name));
CREATE INDEX IF NOT EXISTS idx_users_name_fts ON users USING GIN(to_tsvector('english', first_name || ' ' || last_name));

-- Unique constraints
ALTER TABLE items ADD CONSTRAINT unique_item_name UNIQUE (name) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE optimization_requests ADD CONSTRAINT unique_request_id UNIQUE (request_id);

-- Check constraints for data validation
ALTER TABLE items ADD CONSTRAINT valid_location CHECK (ST_IsValid(location::geometry));
ALTER TABLE items ADD CONSTRAINT positive_embedding CHECK (array_length(embedding, 1) > 0);
ALTER TABLE matches ADD CONSTRAINT valid_score_range CHECK (score >= 0 AND score <= 1);

-- Foreign key constraints with cascading deletes
-- (Already defined in 001_init_schema.sql)

-- Create materialized view for performance analytics
CREATE MATERIALIZED VIEW IF NOT EXISTS daily_stats AS
SELECT
    DATE(created_at) as date,
    COUNT(*) as total_items,
    COUNT(*) FILTER (WHERE status = 'active') as active_items,
    COUNT(*) FILTER (WHERE status = 'matched') as matched_items,
    AVG(execution_time) FILTER (WHERE execution_time IS NOT NULL) as avg_optimization_time
FROM items
LEFT JOIN optimization_requests ON DATE(items.created_at) = DATE(optimization_requests.created_at)
WHERE items.created_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(created_at)
ORDER BY date DESC;

-- Refresh function for materialized view
CREATE OR REPLACE FUNCTION refresh_daily_stats()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY daily_stats;
END;
$$ LANGUAGE plpgsql;

-- Create a function to calculate item similarity based on embeddings
CREATE OR REPLACE FUNCTION calculate_similarity(item_id1 INTEGER, item_id2 INTEGER)
RETURNS REAL AS $$
DECLARE
    emb1 vector(384);
    emb2 vector(384);
    similarity REAL;
BEGIN
    SELECT embedding INTO emb1 FROM items WHERE id = item_id1;
    SELECT embedding INTO emb2 FROM items WHERE id = item_id2;

    IF emb1 IS NULL OR emb2 IS NULL THEN
        RETURN 0.0;
    END IF;

    -- Cosine similarity
    similarity := 1 - (emb1 <=> emb2);
    RETURN similarity;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Create a function for location-based distance calculation
CREATE OR REPLACE FUNCTION calculate_distance_km(item_id1 INTEGER, item_id2 INTEGER)
RETURNS REAL AS $$
DECLARE
    loc1 GEOGRAPHY;
    loc2 GEOGRAPHY;
    distance REAL;
BEGIN
    SELECT location INTO loc1 FROM items WHERE id = item_id1;
    SELECT location INTO loc2 FROM items WHERE id = item_id2;

    IF loc1 IS NULL OR loc2 IS NULL THEN
        RETURN NULL;
    END IF;

    -- Distance in kilometers
    distance := ST_Distance(loc1, loc2) / 1000;
    RETURN distance;
END;
$$ LANGUAGE plpgsql IMMUTABLE;