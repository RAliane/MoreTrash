-- Pre-Migration SQLite Data Export
-- Date: 2026-03-01
-- Source: ai-agent pre-migration state

-- =====================================================
-- Data Export Status
-- =====================================================

-- No data exists in SQLite databases at this time.
-- Databases are created at runtime on first use.

-- Database locations:
--   - artifacts/data.db (Directus client collections)
--   - artifacts/embeddings.db (Cognee vector store)

-- Status:
--   - artifacts/data.db: Not yet created (created on first Directus operation)
--   - artifacts/embeddings.db: Not yet created (created on first memory operation)

-- If data existed, it would be exported here using:
--   sqlite3 <database> .dump

-- =====================================================
