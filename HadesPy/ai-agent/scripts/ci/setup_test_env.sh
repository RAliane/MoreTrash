#!/bin/bash
# Setup PostgreSQL with pgvector and Neo4j with APOC for CI testing
# 
# This script prepares the test environment for integration tests
# It assumes PostgreSQL and Neo4j services are already running
#
# Usage:
#     ./setup_test_env.sh

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration with defaults for CI
POSTGRES_HOST="${POSTGRES_HOST:-postgres}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_DB="${POSTGRES_DB:-test}"
POSTGRES_USER="${POSTGRES_USER:-test}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-test}"
NEO4J_URI="${NEO4J_URI:-bolt://neo4j:7687}"
NEO4J_USER="${NEO4J_USER:-neo4j}"
NEO4J_PASSWORD="${NEO4J_PASSWORD:-test}"

echo "=========================================="
echo "CI Test Environment Setup"
echo "=========================================="
echo ""

# Function to log with color
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Wait for PostgreSQL to be ready
wait_for_postgres() {
    log_info "Waiting for PostgreSQL at $POSTGRES_HOST:$POSTGRES_PORT..."
    
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if nc -z "$POSTGRES_HOST" "$POSTGRES_PORT" 2>/dev/null; then
            log_info "PostgreSQL is ready!"
            return 0
        fi
        
        echo "  Attempt $attempt/$max_attempts: PostgreSQL not ready yet, waiting..."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    log_error "PostgreSQL failed to become ready after $max_attempts attempts"
    return 1
}

# Wait for Neo4j to be ready
wait_for_neo4j() {
    log_info "Waiting for Neo4j at $NEO4J_URI..."
    
    local max_attempts=30
    local attempt=1
    
    # Extract host from bolt://host:port format
    local neo4j_host="${NEO4J_URI#bolt://}"
    neo4j_host="${neo4j_host%:*}"
    local neo4j_port="${NEO4J_URI##*:}"
    
    while [ $attempt -le $max_attempts ]; do
        if nc -z "$neo4j_host" "$neo4j_port" 2>/dev/null; then
            log_info "Neo4j is ready!"
            return 0
        fi
        
        echo "  Attempt $attempt/$max_attempts: Neo4j not ready yet, waiting..."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    log_error "Neo4j failed to become ready after $max_attempts attempts"
    return 1
}

# Setup PostgreSQL with pgvector
setup_postgres() {
    log_info "Setting up PostgreSQL..."
    
    # Export password for psql
    export PGPASSWORD="$POSTGRES_PASSWORD"
    
    # Create pgvector extension
    log_info "Creating pgvector extension..."
    if psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
            -c "CREATE EXTENSION IF NOT EXISTS vector;" 2>/dev/null; then
        log_info "✓ pgvector extension created/verified"
    else
        log_warn "Could not create pgvector extension (may already exist or need superuser)"
    fi
    
    # Verify pgvector is installed
    if psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
            -c "SELECT extversion FROM pg_extension WHERE extname = 'vector';" 2>/dev/null | grep -q "[0-9]"; then
        log_info "✓ pgvector extension is active"
    else
        log_warn "pgvector extension may not be active"
    fi
    
    # Create schema_migrations table if not exists
    log_info "Creating schema_migrations table..."
    psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" <<'EOF'
CREATE TABLE IF NOT EXISTS schema_migrations (
    id SERIAL PRIMARY KEY,
    version VARCHAR(255) NOT NULL UNIQUE,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    description TEXT,
    checksum VARCHAR(64),
    execution_time_ms INTEGER
);
EOF
    log_info "✓ Schema migrations table ready"
    
    # Grant permissions
    log_info "Granting permissions..."
    psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" <<EOF
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO "$POSTGRES_USER";
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO "$POSTGRES_USER";
EOF
    log_info "✓ Permissions granted"
    
    unset PGPASSWORD
}

# Setup Neo4j with constraints
setup_neo4j() {
    log_info "Setting up Neo4j..."
    
    # Check if cypher-shell is available
    if ! command -v cypher-shell &> /dev/null; then
        log_warn "cypher-shell not available, skipping Neo4j setup"
        return 0
    fi
    
    # Create constraints
    log_info "Creating Neo4j constraints..."
    
    local cypher_commands="
CREATE CONSTRAINT course_id IF NOT EXISTS
FOR (c:Course) REQUIRE c.id IS UNIQUE;

CREATE CONSTRAINT department_name IF NOT EXISTS
FOR (d:Department) REQUIRE d.name IS UNIQUE;

CREATE CONSTRAINT career_path_name IF NOT EXISTS
FOR (cp:CareerPath) REQUIRE cp.name IS UNIQUE;

CREATE INDEX course_department IF NOT EXISTS
FOR (c:Course) ON (c.department);

CREATE INDEX course_math_intensity IF NOT EXISTS
FOR (c:Course) ON (c.math_intensity);
"
    
    if echo "$cypher_commands" | cypher-shell -a "$NEO4J_URI" -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" 2>/dev/null; then
        log_info "✓ Neo4j constraints created"
    else
        log_warn "Some Neo4j constraints may already exist or creation failed"
    fi
}

# Seed test data
seed_test_data() {
    log_info "Seeding test data..."
    
    export PGPASSWORD="$POSTGRES_PASSWORD"
    
    # Seed sample courses into PostgreSQL
    psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" <<'EOF'
-- Insert test courses if not exists
INSERT INTO courses (course_id, course_code, title, description, department, credits, math_intensity, humanities_intensity, career_paths, prerequisites, created_at, updated_at)
VALUES 
    ('cs-101', 'CS101', 'Introduction to Computer Science', 'Fundamentals of computing and programming', 'Computer Science', 4, 0.75, 0.20, ARRAY['software_engineer', 'systems_architect'], ARRAY[]::TEXT[], NOW(), NOW()),
    ('ae-101', 'AE101', 'Aerospace Engineering', 'Design and analysis of aircraft and spacecraft', 'Engineering', 4, 0.95, 0.10, ARRAY['aerospace_engineer', 'flight_engineer'], ARRAY['math-101']::TEXT[], NOW(), NOW()),
    ('me-101', 'ME101', 'Mechanical Engineering', 'Study of mechanical systems and thermodynamics', 'Engineering', 4, 0.85, 0.15, ARRAY['mechanical_engineer', 'design_engineer'], ARRAY['math-101']::TEXT[], NOW(), NOW()),
    ('ds-101', 'DS101', 'Data Science', 'Interdisciplinary field extracting knowledge from data', 'Data Science', 4, 0.80, 0.40, ARRAY['data_scientist', 'ml_engineer'], ARRAY['cs-101', 'math-101']::TEXT[], NOW(), NOW()),
    ('ph-101', 'PH101', 'Philosophy', 'Critical examination of fundamental questions', 'Philosophy', 3, 0.15, 0.95, ARRAY['philosopher', 'teacher'], ARRAY[]::TEXT[], NOW(), NOW()),
    ('math-101', 'MATH101', 'Calculus I', 'Introduction to differential calculus', 'Mathematics', 4, 0.95, 0.05, ARRAY['mathematician', 'data_scientist'], ARRAY[]::TEXT[], NOW(), NOW())
ON CONFLICT (course_id) DO NOTHING;
EOF
    
    local inserted=$(psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
        -t -c "SELECT COUNT(*) FROM courses;" 2>/dev/null | tr -d ' ')
    log_info "✓ Seeded $inserted courses"
    
    unset PGPASSWORD
}

# Run migration runner
run_migrations() {
    log_info "Running database migrations..."
    
    local script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local migrations_dir="$script_dir/../../migrations"
    
    if [ -f "$migrations_dir/runner.py" ]; then
        cd "$script_dir/../.."
        python migrations/runner.py migrate || log_warn "Migration runner had issues (may be already applied)"
        log_info "✓ Migrations executed"
    else
        log_warn "Migration runner not found at $migrations_dir/runner.py"
    fi
}

# Verify setup
verify_setup() {
    log_info "Verifying setup..."
    
    export PGPASSWORD="$POSTGRES_PASSWORD"
    
    # Check PostgreSQL tables
    local table_count=$(psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
        -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | tr -d ' ')
    log_info "✓ PostgreSQL has $table_count tables"
    
    # Check course count
    local course_count=$(psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
        -t -c "SELECT COUNT(*) FROM courses;" 2>/dev/null | tr -d ' ')
    log_info "✓ $course_count courses in database"
    
    unset PGPASSWORD
    
    log_info "✓ Test environment setup complete!"
}

# Main execution
main() {
    log_info "Starting CI test environment setup..."
    
    # Wait for services
    wait_for_postgres || exit 1
    wait_for_neo4j || log_warn "Neo4j not available, continuing..."
    
    # Setup services
    setup_postgres
    setup_neo4j || log_warn "Neo4j setup had issues"
    
    # Seed data
    seed_test_data
    
    # Run migrations
    run_migrations
    
    # Verify
    verify_setup
    
    echo ""
    echo "=========================================="
    log_info "Setup complete! Ready for testing."
    echo "=========================================="
}

# Run main
main "$@"
