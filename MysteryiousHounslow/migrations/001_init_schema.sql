-- Matchgorithm Database Schema Migration
-- Version: 001
-- Description: Initialize core tables for items, matches, and users

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS vector;

-- Items table (core business entities)
CREATE TABLE IF NOT EXISTS items (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    location GEOGRAPHY(POINT, 4326),
    embedding vector(384), -- OpenAI ada-002 embedding dimension
    metadata JSONB,
    constraints JSONB,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'active', 'inactive', 'matched')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Matches table (optimization results)
CREATE TABLE IF NOT EXISTS matches (
    id SERIAL PRIMARY KEY,
    item_id INTEGER REFERENCES items(id) ON DELETE CASCADE,
    matched_with INTEGER REFERENCES items(id) ON DELETE CASCADE,
    score REAL CHECK (score >= 0 AND score <= 1),
    status TEXT DEFAULT 'optimized' CHECK (status IN ('optimized', 'rejected', 'manual')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB,
    CONSTRAINT different_items CHECK (item_id != matched_with)
);

-- Users table (authentication and profiles)
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT DEFAULT 'user' CHECK (role IN ('user', 'admin', 'moderator')),
    first_name TEXT,
    last_name TEXT,
    preferences JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Optimization requests table (async processing)
CREATE TABLE IF NOT EXISTS optimization_requests (
    request_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    request_data JSONB NOT NULL,
    result_data JSONB,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    progress REAL DEFAULT 0 CHECK (progress >= 0 AND progress <= 1),
    current_stage TEXT,
    execution_time REAL,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Microtasks table (detailed optimization steps)
CREATE TABLE IF NOT EXISTS microtasks (
    task_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    request_id UUID REFERENCES optimization_requests(request_id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    task_type TEXT NOT NULL,
    parameters JSONB,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    result_data JSONB,
    error_message TEXT,
    execution_time REAL,
    dependencies JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Analytics table (usage metrics)
CREATE TABLE IF NOT EXISTS analytics (
    id SERIAL PRIMARY KEY,
    event_type TEXT NOT NULL,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    event_data JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_items_location ON items USING GIST(location);
CREATE INDEX IF NOT EXISTS idx_items_status ON items(status);
CREATE INDEX IF NOT EXISTS idx_items_embedding ON items USING ivfflat(embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_matches_item_id ON matches(item_id);
CREATE INDEX IF NOT EXISTS idx_matches_matched_with ON matches(matched_with);
CREATE INDEX IF NOT EXISTS idx_matches_score ON matches(score DESC);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_optimization_requests_status ON optimization_requests(status);
CREATE INDEX IF NOT EXISTS idx_optimization_requests_user ON optimization_requests(user_id);
CREATE INDEX IF NOT EXISTS idx_microtasks_request ON microtasks(request_id);
CREATE INDEX IF NOT EXISTS idx_analytics_event_type ON analytics(event_type);
CREATE INDEX IF NOT EXISTS idx_analytics_created_at ON analytics(created_at DESC);

-- Create triggers for updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_items_updated_at BEFORE UPDATE ON items FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert initial data
INSERT INTO users (email, password_hash, role, first_name, last_name)
VALUES ('admin@matchgorithm.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LeXt3dJQvO8hZvQwO', 'admin', 'System', 'Administrator')
ON CONFLICT (email) DO NOTHING;