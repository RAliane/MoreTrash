#!/bin/bash
# Render Health Check Script for AI Agent Stack
# Verifies all services are healthy and accessible

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
API_URL="${API_URL:-}"
DIRECTUS_URL="${DIRECTUS_URL:-}"
NEO4J_URI="${NEO4J_URI:-}"
DATABASE_URL="${DATABASE_URL:-}"
TIMEOUT=30

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[FAIL]${NC} $1"
}

# Check PostgreSQL connection
check_postgres() {
    log_info "Checking PostgreSQL connection..."

    if [[ -z "$DATABASE_URL" ]]; then
        log_warn "DATABASE_URL not set, skipping PostgreSQL check"
        return 0
    fi

    # Try to connect using psql
    if command -v psql &> /dev/null; then
        if psql "$DATABASE_URL" -c "SELECT 1;" > /dev/null 2>&1; then
            log_success "PostgreSQL connection"
            return 0
        fi
    fi

    # Fallback: check via API health endpoint
    if [[ -n "$API_URL" ]]; then
        local health_response
        health_response=$(curl -s -o /dev/null -w "%{http_code}" "${API_URL}/health" 2>/dev/null || echo "000")
        if [[ "$health_response" == "200" ]]; then
            log_success "PostgreSQL (via API health)"
            return 0
        fi
    fi

    log_error "PostgreSQL connection failed"
    return 1
}

# Check Neo4j connection
check_neo4j() {
    log_info "Checking Neo4j connection..."

    if [[ -z "$NEO4J_URI" ]]; then
        log_warn "NEO4J_URI not set, skipping Neo4j check"
        return 0
    fi

    # Try HTTP endpoint if available
    if curl -sSf "${NEO4J_URI/neo4j+ss/http}/db/manage/server/jmx/domain/org.neo4j/instance%3Dkernel%230%2Cname%3DDiagnostics" > /dev/null 2>&1; then
        log_success "Neo4j HTTP connection"
        return 0
    fi

    # Check via API health endpoint
    if [[ -n "$API_URL" ]]; then
        local health_response
        health_response=$(curl -s -o /dev/null -w "%{http_code}" "${API_URL}/health" 2>/dev/null || echo "000")
        if [[ "$health_response" == "200" ]]; then
            log_success "Neo4j (via API health)"
            return 0
        fi
    fi

    log_error "Neo4j connection failed"
    return 1
}

# Check Directus health
check_directus() {
    log_info "Checking Directus health..."

    if [[ -z "$DIRECTUS_URL" ]]; then
        log_warn "DIRECTUS_URL not set, skipping Directus check"
        return 0
    fi

    local health_response
    health_response=$(curl -s -o /dev/null -w "%{http_code}" "${DIRECTUS_URL}/server/health" 2>/dev/null || echo "000")

    if [[ "$health_response" == "200" ]]; then
        log_success "Directus health check"
        return 0
    fi

    log_error "Directus health check failed (HTTP $health_response)"
    return 1
}

# Check API health endpoint
check_api() {
    log_info "Checking API health endpoint..."

    if [[ -z "$API_URL" ]]; then
        log_warn "API_URL not set, skipping API check"
        return 0
    fi

    local health_response
    health_response=$(curl -s -o /dev/null -w "%{http_code}" "${API_URL}/health" 2>/dev/null || echo "000")

    if [[ "$health_response" == "200" ]]; then
        log_success "API health endpoint"
        return 0
    fi

    log_error "API health check failed (HTTP $health_response)"
    return 1
}

# Check API documentation
check_api_docs() {
    log_info "Checking API documentation..."

    if [[ -z "$API_URL" ]]; then
        log_warn "API_URL not set, skipping docs check"
        return 0
    fi

    local docs_response
    docs_response=$(curl -s -o /dev/null -w "%{http_code}" "${API_URL}/docs" 2>/dev/null || echo "000")

    if [[ "$docs_response" == "200" ]]; then
        log_success "API documentation"
        return 0
    fi

    log_warn "API documentation not accessible (HTTP $docs_response)"
    return 0  # Non-critical
}

# Check critical endpoints
check_endpoints() {
    log_info "Checking critical API endpoints..."

    if [[ -z "$API_URL" ]]; then
        log_warn "API_URL not set, skipping endpoint checks"
        return 0
    fi

    local endpoints=("/health" "/docs" "/openapi.json")
    local failed=0

    for endpoint in "${endpoints[@]}"; do
        local response
        response=$(curl -s -o /dev/null -w "%{http_code}" "${API_URL}${endpoint}" 2>/dev/null || echo "000")

        if [[ "$response" == "200" ]]; then
            log_success "Endpoint $endpoint"
        else
            log_error "Endpoint $endpoint (HTTP $response)"
            ((failed++)) || true
        fi
    done

    if [[ $failed -eq 0 ]]; then
        return 0
    fi

    return 1
}

# Main health check
main() {
    echo "=========================================="
    echo "  AI Agent Health Check"
    echo "=========================================="
    echo ""

    local failed=0

    # Run all checks
    check_postgres || ((failed++)) || true
    check_neo4j || ((failed++)) || true
    check_directus || ((failed++)) || true
    check_api || ((failed++)) || true
    check_api_docs || true  # Non-critical
    check_endpoints || ((failed++)) || true

    echo ""
    echo "=========================================="

    if [[ $failed -eq 0 ]]; then
        echo -e "${GREEN}All health checks passed!${NC}"
        echo "=========================================="
        exit 0
    else
        echo -e "${RED}$failed health check(s) failed${NC}"
        echo "=========================================="
        exit 1
    fi
}

# Run main function
main "$@"
