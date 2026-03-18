-- Migration: 002_knn_function.sql
-- Create kNN function for vector similarity search

-- Create the main kNN function
CREATE OR REPLACE FUNCTION find_similar_items(
    query_embedding vector,
    max_distance float DEFAULT 1.0,
    max_results int DEFAULT 10,
    category_filter text DEFAULT NULL
)
RETURNS TABLE(
    id int,
    name text,
    category text,
    similarity float,
    metadata jsonb
) AS $$
BEGIN
    -- Input validation
    IF query_embedding IS NULL THEN
        RAISE EXCEPTION 'Query embedding cannot be null';
    END IF;

    IF max_results <= 0 OR max_results > 1000 THEN
        RAISE EXCEPTION 'max_results must be between 1 and 1000';
    END IF;

    -- Return similar items using cosine similarity
    RETURN QUERY
    SELECT
        i.id,
        i.name,
        i.category,
        (1 - (i.embedding <=> query_embedding))::float as similarity,
        i.metadata
    FROM items i
    WHERE
        -- Category filter (if provided)
        (category_filter IS NULL OR i.category = category_filter)
        -- Distance threshold
        AND (i.embedding <=> query_embedding) <= max_distance
    ORDER BY i.embedding <=> query_embedding ASC  -- Cosine distance (lower is better)
    LIMIT max_results;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant execute permission to app_role
GRANT EXECUTE ON FUNCTION find_similar_items(vector, float, int, text) TO app_role;

-- Create IVFFlat index for better performance (if not exists)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_items_embedding_ivfflat
    ON items USING ivfflat(embedding vector_cosine_ops)
    WITH (lists = 100);

-- Create partial index for active items only (if needed)
-- CREATE INDEX idx_items_active_embedding ON items USING ivfflat(embedding vector_cosine_ops)
-- WHERE active = true;

-- Add comment for documentation
COMMENT ON FUNCTION find_similar_items(vector, float, int, text) IS
'Find similar items using vector cosine similarity search. Returns top-k most similar items within distance threshold.';