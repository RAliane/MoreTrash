#!/bin/bash

# Matchgorithm Database Migration Script
# Runs PostgreSQL migrations in correct order and validates extensions

set -e

# Configuration
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-matchgorithm}"
DB_USER="${DB_USER:-postgres}"
MIGRATION_DIR="./db/migrations"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}" >&2
}

warn() {
    echo -e "${YELLOW}[WARN] $1${NC}"
}

# Check if psql is available
check_dependencies() {
    if ! command -v psql &> /dev/null; then
        error "psql command not found. Please install PostgreSQL client tools."
        exit 1
    fi
}

# Wait for database to be ready
wait_for_db() {
    log "Waiting for database to be ready..."
    local retries=30
    local count=0

    while [ $count -lt $retries ]; do
        if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" &> /dev/null; then
            log "Database is ready!"
            return 0
        fi
        count=$((count + 1))
        warn "Database not ready, retrying in 2 seconds... ($count/$retries)"
        sleep 2
    done

    error "Database failed to become ready after $retries attempts"
    exit 1
}

# Run a single migration file
run_migration() {
    local migration_file="$1"
    local migration_name=$(basename "$migration_file" .sql)

    if [ ! -f "$migration_file" ]; then
        error "Migration file not found: $migration_file"
        return 1
    fi

    log "Running migration: $migration_name"

    if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$migration_file"; then
        log "Migration $migration_name completed successfully"
        return 0
    else
        error "Migration $migration_name failed"
        return 1
    fi
}

# Validate extensions and basic functionality
validate_extensions() {
    log "Validating PostgreSQL extensions..."

    # Check if extensions are installed
    local extensions=("postgis" "vector" "uuid-ossp")
    for ext in "${extensions[@]}"; do
        if ! psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1 FROM pg_extension WHERE extname = '$ext';" | grep -q "1"; then
            error "Extension $ext is not installed"
            return 1
        fi
    done

    # Test PostGIS functionality
    log "Testing PostGIS functionality..."
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "
        SELECT PostGIS_Version();
        SELECT ST_AsText(ST_SetSRID(ST_MakePoint(-0.1, 51.5), 4326)) as test_point;
    " > /dev/null

    # Test pgvector functionality
    log "Testing pgvector functionality..."
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "
        CREATE TEMP TABLE test_vectors (id serial, embedding vector(3));
        INSERT INTO test_vectors (embedding) VALUES ('[1,2,3]'), ('[4,5,6]');
        SELECT embedding <=> '[1,2,3]' as distance FROM test_vectors ORDER BY embedding <=> '[1,2,3]' LIMIT 1;
    " > /dev/null

    log "All extensions validated successfully"
}

# Main migration process
main() {
    log "Starting Matchgorithm database migrations"

    check_dependencies
    wait_for_db

    # Define migration files in order
    local migrations=(
        "$MIGRATION_DIR/001_init_schema.sql"
        "$MIGRATION_DIR/002_add_indexes.sql"
        "$MIGRATION_DIR/003_add_pgvector_postgis.sql"
    )

    # Run migrations
    for migration in "${migrations[@]}"; do
        if ! run_migration "$migration"; then
            error "Migration failed. Stopping."
            exit 1
        fi
    done

    # Validate extensions and functionality
    if ! validate_extensions; then
        error "Extension validation failed"
        exit 1
    fi

    log "All migrations completed successfully!"
    log "Database is ready for use."
}

# Run main function
main "$@"