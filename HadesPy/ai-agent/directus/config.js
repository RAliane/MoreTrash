/**
 * Directus Configuration with PostgreSQL Backend
 * 
 * This configuration enables Directus CMS with:
 * - PostgreSQL database connection
 * - pgvector extension for vector embeddings
 * - Auto-migrations on startup
 * - Admin user configuration
 * 
 * Environment Variables Required:
 * - DB_HOST: PostgreSQL host (default: localhost)
 * - DB_PORT: PostgreSQL port (default: 5432)
 * - DB_DATABASE: Database name (default: directus)
 * - DB_USER: Database user (default: directus)
 * - DB_PASSWORD: Database password (default: directus)
 * - DIRECTUS_ADMIN_EMAIL: Admin email (default: admin@example.com)
 * - DIRECTUS_ADMIN_PASSWORD: Admin password (default: admin)
 */

module.exports = {
  // Database Configuration
  db: {
    client: 'pg',
    connection: {
      host: process.env.DB_HOST || 'localhost',
      port: parseInt(process.env.DB_PORT || '5432', 10),
      database: process.env.DB_DATABASE || 'directus',
      user: process.env.DB_USER || 'directus',
      password: process.env.DB_PASSWORD || 'directus',
      ssl: process.env.DB_SSL === 'true' ? { rejectUnauthorized: false } : false,
    },
    pool: {
      min: 2,
      max: 10,
    },
    acquireConnectionTimeout: 60000,
  },

  // Server Configuration
  server: {
    port: parseInt(process.env.PORT || '8055', 10),
    host: process.env.HOST || '0.0.0.0',
  },

  // Security
  security: {
    adminEmail: process.env.DIRECTUS_ADMIN_EMAIL || 'admin@example.com',
    adminPassword: process.env.DIRECTUS_ADMIN_PASSWORD || 'admin',
    secret: process.env.SECRET_KEY || 'change-me-in-production-use-secure-random-string',
    cors: {
      enabled: true,
      origin: process.env.CORS_ORIGINS?.split(',') || [
        'http://localhost',
        'http://localhost:3000',
        'http://localhost:7860',
        'http://localhost:8501',
        'http://localhost:8000',
      ],
    },
  },

  // Extensions
  extensions: {
    enabled: true,
    autoInstall: true,
    path: './extensions',
  },

  // Migrations
  migrations: {
    enabled: true,
    autoRun: true,
    path: './migrations',
  },

  // File Storage
  storage: {
    default: 'local',
    local: {
      root: './uploads',
    },
  },

  // Logging
  logger: {
    level: process.env.LOG_LEVEL || 'info',
    console: true,
  },

  // Cache
  cache: {
    enabled: process.env.CACHE_ENABLED === 'true',
    ttl: parseInt(process.env.CACHE_TTL || '300', 10),
    store: 'memory',
  },

  // Rate Limiting
  rateLimit: {
    enabled: process.env.RATE_LIMIT_ENABLED === 'true',
    points: parseInt(process.env.RATE_LIMIT_REQUESTS || '100', 10),
    duration: parseInt(process.env.RATE_LIMIT_WINDOW || '60', 10),
  },

  // Session
  session: {
    ttl: 86400000, // 24 hours
  },

  // Telemetry (disable for privacy)
  telemetry: false,
};

/**
 * pgvector Extension Setup
 * 
 * Run this SQL in PostgreSQL before starting Directus:
 * 
 * ```sql
 * -- Enable pgvector extension
 * CREATE EXTENSION IF NOT EXISTS vector;
 * 
 * -- Verify extension is installed
 * SELECT * FROM pg_extension WHERE extname = 'vector';
 * ```
 * 
 * For Directus collections with vector fields, use the following pattern:
 * - Field type: 'float[]' or custom 'vector' via Directus interface
 * - Store embeddings as arrays
 * - Use pgvector functions for similarity search
 */

/**
 * Database Initialization Script
 * 
 * This script runs on first startup to:
 * 1. Create the database if it doesn't exist
 * 2. Enable pgvector extension
 * 3. Create necessary roles
 * 
 * Run manually or via setup-directus.sh:
 * ```bash
 * psql -U postgres -c "CREATE DATABASE directus;"
 * psql -U postgres -d directus -c "CREATE EXTENSION IF NOT EXISTS vector;"
 * psql -U postgres -c "CREATE USER directus WITH PASSWORD 'directus';"
 * psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE directus TO directus;"
 * ```
 */
