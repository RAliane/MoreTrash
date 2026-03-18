#!/bin/bash
#
# Directus Bootstrap Script with PostgreSQL and pgvector
#
# This script:
# 1. Starts PostgreSQL with pgvector extension
# 2. Creates Directus database and user
# 3. Enables pgvector extension
# 4. Starts Directus CMS
# 5. Seeds courses with embeddings
# 6. Syncs to Neo4j
#
# Usage:
#   chmod +x scripts/setup-directus.sh
#   ./scripts/setup-directus.sh
#
# Or with podman/docker:
#   ./scripts/setup-directus.sh --container
#

set -euo pipefail

# ============================================
# CONFIGURATION
# ============================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DIRECTUS_DIR="${PROJECT_ROOT}/directus"

# Load environment variables
if [[ -f "${PROJECT_ROOT}/.env" ]]; then
    set -a
    source "${PROJECT_ROOT}/.env"
    set +a
elif [[ -f "${PROJECT_ROOT}/.env.example" ]]; then
    set -a
    source "${PROJECT_ROOT}/.env.example"
    set +a
fi

# Database configuration
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_DATABASE="${DB_DATABASE:-directus}"
DB_USER="${DB_USER:-directus}"
DB_PASSWORD="${DB_PASSWORD:-directus}"
POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-postgres}"

# Directus configuration
DIRECTUS_URL="${DIRECTUS_URL:-http://localhost:8055}"
DIRECTUS_ADMIN_EMAIL="${DIRECTUS_ADMIN_EMAIL:-admin@example.com}"
DIRECTUS_ADMIN_PASSWORD="${DIRECTUS_ADMIN_PASSWORD:-$(openssl rand -base64 32)}"
DIRECTUS_PORT="${DIRECTUS_PORT:-8055}"

# Neo4j configuration
NEO4J_URI="${NEO4J_URI:-bolt://localhost:7687}"
NEO4J_USER="${NEO4J_USER:-neo4j}"
NEO4J_PASSWORD="${NEO4J_PASSWORD:-$(openssl rand -base64 32)}"

# Container configuration
USE_CONTAINER="${USE_CONTAINER:-false}"
CONTAINER_RUNTIME="${CONTAINER_RUNTIME:-podman}"
POSTGRES_IMAGE="${POSTGRES_IMAGE:-pgvector/pgvector:pg16}"
DIRECTUS_IMAGE="${DIRECTUS_IMAGE:-directus/directus:10.8.0}"
NEO4J_IMAGE="${NEO4J_IMAGE:-neo4j:5.15-community}"
NETWORK_NAME="${PODMAN_NETWORK_DB:-db_net}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================
# UTILITY FUNCTIONS
# ============================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

wait_for_service() {
    local host="$1"
    local port="$2"
    local service_name="$3"
    local max_attempts="${4:-30}"
    local attempt=1

    log_info "Waiting for $service_name at $host:$port..."
    
    while ! timeout 2 bash -c "</dev/tcp/$host/$port" 2>/dev/null; do
        if [[ $attempt -ge $max_attempts ]]; then
            log_error "$service_name did not start within ${max_attempts} attempts"
            return 1
        fi
        echo -n "."
        sleep 1
        ((attempt++))
    done
    echo
    log_success "$service_name is ready"
}

# ============================================
# CONTAINER MANAGEMENT
# ============================================

start_postgres_container() {
    log_info "Starting PostgreSQL with pgvector..."
    
    # Check if container already exists
    if $CONTAINER_RUNTIME ps -a --format "{{.Names}}" | grep -q "^directus-postgres$"; then
        if $CONTAINER_RUNTIME ps --format "{{.Names}}" | grep -q "^directus-postgres$"; then
            log_warning "PostgreSQL container already running"
            return 0
        else
            log_info "Starting existing PostgreSQL container"
            $CONTAINER_RUNTIME start directus-postgres
            return 0
        fi
    fi
    
    # Create network if needed
    if [[ "$USE_CONTAINER" == "true" ]]; then
        if ! $CONTAINER_RUNTIME network ls --format "{{.Name}}" | grep -q "^${NETWORK_NAME}$"; then
            log_info "Creating network: $NETWORK_NAME"
            $CONTAINER_RUNTIME network create "$NETWORK_NAME"
        fi
    fi
    
    # Run PostgreSQL container
    $CONTAINER_RUNTIME run -d \
        --name directus-postgres \
        --network "$NETWORK_NAME" \
        -e POSTGRES_USER="$POSTGRES_USER" \
        -e POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
        -e POSTGRES_DB="$DB_DATABASE" \
        -p "$DB_PORT:5432" \
        -v directus-postgres-data:/var/lib/postgresql/data \
        "$POSTGRES_IMAGE"
    
    log_success "PostgreSQL container started"
}

start_neo4j_container() {
    log_info "Starting Neo4j..."
    
    # Check if container already exists
    if $CONTAINER_RUNTIME ps -a --format "{{.Names}}" | grep -q "^directus-neo4j$"; then
        if $CONTAINER_RUNTIME ps --format "{{.Names}}" | grep -q "^directus-neo4j$"; then
            log_warning "Neo4j container already running"
            return 0
        else
            log_info "Starting existing Neo4j container"
            $CONTAINER_RUNTIME start directus-neo4j
            return 0
        fi
    fi
    
    $CONTAINER_RUNTIME run -d \
        --name directus-neo4j \
        --network "$NETWORK_NAME" \
        -e NEO4J_AUTH="${NEO4J_USER}/${NEO4J_PASSWORD}" \
        -e NEO4J_PLUGINS='["apoc", "gds"]' \
        -p "7474:7474" \
        -p "7687:7687" \
        -v directus-neo4j-data:/data \
        "$NEO4J_IMAGE"
    
    log_success "Neo4j container started"
}

# ============================================
# DATABASE SETUP
# ============================================

setup_database() {
    log_info "Setting up PostgreSQL database..."
    
    # Wait for PostgreSQL to be ready
    wait_for_service "$DB_HOST" "$DB_PORT" "PostgreSQL"
    
    # Install pgvector (if not using pgvector image)
    log_info "Ensuring pgvector extension is available..."
    
    # Create database user if not exists
    PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$POSTGRES_USER" -d postgres <<EOF
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '${DB_USER}') THEN
        CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASSWORD}';
    END IF;
END
\$\$;

-- Create database if not exists
SELECT 'CREATE DATABASE ${DB_DATABASE}' 
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '${DB_DATABASE}')\gexec

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE ${DB_DATABASE} TO ${DB_USER};
EOF
    
    # Enable pgvector extension
    PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$POSTGRES_USER" -d "$DB_DATABASE" <<EOF
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Verify extension
SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';
EOF
    
    # Grant schema permissions
    PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$POSTGRES_USER" -d "$DB_DATABASE" <<EOF
GRANT ALL ON SCHEMA public TO ${DB_USER};
ALTER USER ${DB_USER} WITH SUPERUSER;
EOF
    
    log_success "Database setup complete"
}

# ============================================
# DIRECTUS SETUP
# ============================================

start_directus() {
    log_info "Starting Directus CMS..."
    
    if [[ "$USE_CONTAINER" == "true" ]]; then
        start_directus_container
    else
        start_directus_local
    fi
}

start_directus_container() {
    # Check if container already exists
    if $CONTAINER_RUNTIME ps -a --format "{{.Names}}" | grep -q "^directus$"; then
        if $CONTAINER_RUNTIME ps --format "{{.Names}}" | grep -q "^directus$"; then
            log_warning "Directus container already running"
            return 0
        else
            log_info "Starting existing Directus container"
            $CONTAINER_RUNTIME start directus
            wait_for_service "$DB_HOST" "$DIRECTUS_PORT" "Directus"
            return 0
        fi
    fi
    
    $CONTAINER_RUNTIME run -d \
        --name directus \
        --network "$NETWORK_NAME" \
        -p "${DIRECTUS_PORT}:8055" \
        -e DB_CLIENT="pg" \
        -e DB_HOST="directus-postgres" \
        -e DB_PORT="5432" \
        -e DB_DATABASE="$DB_DATABASE" \
        -e DB_USER="$DB_USER" \
        -e DB_PASSWORD="$DB_PASSWORD" \
        -e ADMIN_EMAIL="$DIRECTUS_ADMIN_EMAIL" \
        -e ADMIN_PASSWORD="$DIRECTUS_ADMIN_PASSWORD" \
        -e SECRET="${SECRET_KEY:-$(openssl rand -base64 48)}" \
        -v "${DIRECTUS_DIR}/uploads:/directus/uploads" \
        "$DIRECTUS_IMAGE"
    
    wait_for_service "$DB_HOST" "$DIRECTUS_PORT" "Directus" 60
    log_success "Directus container started"
}

start_directus_local() {
    # Check if Directus is already running
    if curl -s "${DIRECTUS_URL}/server/health" > /dev/null 2>&1; then
        log_warning "Directus is already running at $DIRECTUS_URL"
        return 0
    fi
    
    # Check if Directus CLI is available
    if ! command -v npx &> /dev/null; then
        log_error "npx not found. Please install Node.js and npm."
        exit 1
    fi
    
    log_info "Starting Directus locally..."
    
    # Create Directus directory if needed
    mkdir -p "${DIRECTUS_DIR}/uploads"
    
    # Set environment variables for Directus
    export DB_CLIENT="pg"
    export DB_HOST="$DB_HOST"
    export DB_PORT="$DB_PORT"
    export DB_DATABASE="$DB_DATABASE"
    export DB_USER="$DB_USER"
    export DB_PASSWORD="$DB_PASSWORD"
    export ADMIN_EMAIL="$DIRECTUS_ADMIN_EMAIL"
    export ADMIN_PASSWORD="$DIRECTUS_ADMIN_PASSWORD"
    export SECRET="${SECRET_KEY:-$(openssl rand -base64 48)}"
    export PORT="$DIRECTUS_PORT"
    
    # Install Directus if not present
    if [[ ! -d "${DIRECTUS_DIR}/node_modules" ]]; then
        log_info "Installing Directus..."
        cd "$DIRECTUS_DIR"
        npm init -y
        npm install directus@10.8.0
        cd - > /dev/null
    fi
    
    # Start Directus in background
    cd "$DIRECTUS_DIR"
    npx directus start > "${DIRECTUS_DIR}/directus.log" 2>&1 &
    DIRECTUS_PID=$!
    cd - > /dev/null
    
    # Save PID for cleanup
    echo "$DIRECTUS_PID" > "/tmp/directus.pid"
    
    wait_for_service "$DB_HOST" "$DIRECTUS_PORT" "Directus" 60
    log_success "Directus started (PID: $DIRECTUS_PID)"
}

apply_schema() {
    log_info "Applying Directus schema..."
    
    # Wait for Directus to be fully ready
    sleep 5
    
    # Login to get token
    local token_response
    token_response=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "{\"email\":\"${DIRECTUS_ADMIN_EMAIL}\",\"password\":\"${DIRECTUS_ADMIN_PASSWORD}\"}" \
        "${DIRECTUS_URL}/auth/login")
    
    local access_token
    access_token=$(echo "$token_response" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
    
    if [[ -z "$access_token" ]]; then
        log_warning "Could not get access token, schema may need to be applied manually"
        return 0
    fi
    
    # Apply schema using Directus CLI or API
    # Note: Directus doesn't have a built-in schema apply API
    # Collections will be created through seed script SQL
    
    log_success "Schema application check complete"
}

# ============================================
# SEEDING
# ============================================

seed_courses() {
    log_info "Seeding courses with embeddings..."
    
    # Check if Node.js dependencies are installed
    if [[ ! -d "${DIRECTUS_DIR}/node_modules" ]]; then
        log_info "Installing seeding dependencies..."
        cd "$DIRECTUS_DIR"
        npm install asyncpg pg crypto
        cd - > /dev/null
    fi
    
    # Run seeding script
    cd "$DIRECTUS_DIR"
    node seed-courses.js
    local seed_result=$?
    cd - > /dev/null
    
    if [[ $seed_result -eq 0 ]]; then
        log_success "Course seeding complete"
    else
        log_error "Course seeding failed"
        return 1
    fi
}

# ============================================
# NEO4J SYNC
# ============================================

sync_to_neo4j() {
    log_info "Syncing data to Neo4j..."
    
    # Wait for Neo4j to be ready
    wait_for_service "${NEO4J_URI#*://}" "7687" "Neo4j"
    
    # Run Python sync script
    cd "$PROJECT_ROOT"
    python -m src.integrations.directus_neo4j_bridge sync
    local sync_result=$?
    
    if [[ $sync_result -eq 0 ]]; then
        log_success "Neo4j sync complete"
    else
        log_error "Neo4j sync failed"
        return 1
    fi
}

# ============================================
# VERIFICATION
# ============================================

verify_setup() {
    log_info "Verifying setup..."
    
    local errors=0
    
    # Check PostgreSQL
    if ! timeout 2 bash -c "</dev/tcp/${DB_HOST}/${DB_PORT}" 2>/dev/null; then
        log_error "PostgreSQL is not accessible"
        ((errors++))
    else
        log_success "PostgreSQL is running"
    fi
    
    # Check Directus
    if curl -s "${DIRECTUS_URL}/server/health" > /dev/null 2>&1; then
        log_success "Directus is running"
    else
        log_error "Directus is not accessible"
        ((errors++))
    fi
    
    # Check Neo4j
    if timeout 2 bash -c "</dev/tcp/${NEO4J_URI#*://}/7687" 2>/dev/null; then
        log_success "Neo4j is running"
    else
        log_error "Neo4j is not accessible"
        ((errors++))
    fi
    
    # Verify data
    log_info "Checking seeded data..."
    local course_count
    course_count=$(PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_DATABASE" -t -c "SELECT COUNT(*) FROM courses;" 2>/dev/null | xargs)
    
    if [[ "$course_count" -eq 5 ]]; then
        log_success "All 5 courses seeded"
    else
        log_warning "Expected 5 courses, found ${course_count:-0}"
    fi
    
    return $errors
}

# ============================================
# CLEANUP
# ============================================

cleanup() {
    log_info "Cleaning up..."
    
    # Stop Directus if we started it
    if [[ -f "/tmp/directus.pid" ]]; then
        local pid
        pid=$(cat "/tmp/directus.pid")
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid"
            log_info "Stopped Directus (PID: $pid)"
        fi
        rm -f "/tmp/directus.pid"
    fi
}

trap cleanup EXIT INT TERM

# ============================================
# MAIN
# ============================================

main() {
    log_info "============================================"
    log_info "Directus Bootstrap with PostgreSQL"
    log_info "============================================"
    echo
    
    # Parse arguments
    for arg in "$@"; do
        case $arg in
            --container)
                USE_CONTAINER="true"
                shift
                ;;
            --docker)
                CONTAINER_RUNTIME="docker"
                USE_CONTAINER="true"
                shift
                ;;
            --podman)
                CONTAINER_RUNTIME="podman"
                USE_CONTAINER="true"
                shift
                ;;
            --skip-containers)
                SKIP_CONTAINERS="true"
                shift
                ;;
            --help|-h)
                echo "Usage: $0 [OPTIONS]"
                echo
                echo "Options:"
                echo "  --container         Use containers for all services"
                echo "  --docker            Use Docker (implies --container)"
                echo "  --podman            Use Podman (implies --container)"
                echo "  --skip-containers   Skip container startup (use existing services)"
                echo "  --help, -h          Show this help message"
                echo
                echo "Environment Variables:"
                echo "  DB_HOST, DB_PORT, DB_DATABASE, DB_USER, DB_PASSWORD"
                echo "  DIRECTUS_URL, DIRECTUS_ADMIN_EMAIL, DIRECTUS_ADMIN_PASSWORD"
                echo "  NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD"
                exit 0
                ;;
        esac
    done
    
    # Start services
    if [[ "${SKIP_CONTAINERS:-false}" != "true" ]]; then
        if [[ "$USE_CONTAINER" == "true" ]]; then
            start_postgres_container
            start_neo4j_container
        fi
    fi
    
    # Setup database
    setup_database
    
    # Start Directus
    start_directus
    
    # Apply schema
    apply_schema
    
    # Seed courses
    seed_courses
    
    # Sync to Neo4j
    sync_to_neo4j
    
    # Verify
    echo
    log_info "============================================"
    log_info "Verifying Installation"
    log_info "============================================"
    echo
    
    if verify_setup; then
        echo
        log_success "============================================"
        log_success "Directus Bootstrap Complete!"
        log_success "============================================"
        echo
        echo "Services:"
        echo "  Directus:    ${DIRECTUS_URL}"
        echo "  PostgreSQL:  ${DB_HOST}:${DB_PORT} (database: ${DB_DATABASE})"
        echo "  Neo4j:       ${NEO4J_URI}"
        echo
        echo "Admin Credentials:"
        echo "  Email:    ${DIRECTUS_ADMIN_EMAIL}"
        echo "  Password: ${DIRECTUS_ADMIN_PASSWORD}"
        echo
        echo "Seeded Courses:"
        PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_DATABASE" -c "SELECT name, department, math_intensity, humanities_intensity FROM courses ORDER BY name;" 2>/dev/null || echo "  (Run verification manually)"
        echo
        echo "Next steps:"
        echo "  - Access Directus UI at ${DIRECTUS_URL}/admin"
        echo "  - Run 'python -m src.integrations.directus_neo4j_bridge stats' to check sync"
        echo "  - View Neo4j Browser at http://localhost:7474"
        echo
    else
        log_error "Setup verification failed. Check logs above."
        exit 1
    fi
}

# Run main function
main "$@"
