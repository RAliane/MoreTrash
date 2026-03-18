-- Migration: 001_init.sql
-- Create initial database schema for MysteryiousHounslow

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS vector;

-- Create items table with vector embeddings
CREATE TABLE items (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100),
    embedding vector(384),  -- OpenAI CLIP embedding dimension
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create spatial index for geographic queries
CREATE INDEX idx_items_geom ON items USING GIST(ST_GeomFromText('POINT(0 0)', 4326));

-- Create indexes for performance
CREATE INDEX idx_items_category ON items(category);
CREATE INDEX idx_items_created_at ON items(created_at);

-- Row Level Security (RLS) policies
ALTER TABLE items ENABLE ROW LEVEL SECURITY;

-- Policy for read access (allow authenticated users)
CREATE POLICY items_read_policy ON items
    FOR SELECT
    USING (true);  -- In production, add proper user authentication check

-- Policy for write access (restrict to admin/service role)
CREATE POLICY items_write_policy ON items
    FOR ALL
    USING (current_user = 'app_role');  -- In production, use proper role check

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to automatically update updated_at
CREATE TRIGGER update_items_updated_at
    BEFORE UPDATE ON items
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();