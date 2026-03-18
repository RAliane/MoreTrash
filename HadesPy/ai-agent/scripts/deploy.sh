#!/bin/bash
# Render CLI Deployment Script for AI Agent
# Usage: ./deploy.sh [--environment prod|staging] [--skip-migrations] [--skip-build]
#
# Examples:
#   ./deploy.sh --environment prod
#   ./deploy.sh --environment staging --skip-migrations
#   ./deploy.sh --environment prod --skip-build

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENVIRONMENT="prod"
SKIP_MIGRATIONS=false
SKIP_BUILD=false
RENDER_BLUEPRINT="${PROJECT_ROOT}/render.yaml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
            --skip-migrations)
                SKIP_MIGRATIONS=true
                shift
                ;;
            --skip-build)
                SKIP_BUILD=true
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

# Show help message
show_help() {
    cat << EOF
Render CLI Deployment Script for AI Agent

Usage: ./deploy.sh [OPTIONS]

Options:
  --environment <env>     Deployment environment (prod|staging) [default: prod]
  --skip-migrations       Skip database migrations
  --skip-build           Skip container image builds
  -h, --help             Show this help message

Examples:
  ./deploy.sh --environment prod
  ./deploy.sh --environment staging --skip-migrations
  ./deploy.sh --environment prod --skip-build
EOF
}

# Validate prerequisites
validate_prerequisites() {
    log_info "Validating prerequisites..."

    # Check Render CLI
    if ! command -v render &> /dev/null; then
        log_error "Render CLI is not installed"
        echo "Install with: curl -fsSL https://raw.githubusercontent.com/render-oss/cli/main/install.sh | bash"
        exit 1
    fi

    # Check Render CLI authentication
    if ! render whoami &> /dev/null; then
        log_error "Not authenticated with Render CLI"
        echo "Run: render login"
        exit 1
    fi

    # Check blueprint file exists
    if [[ ! -f "$RENDER_BLUEPRINT" ]]; then
        log_error "Render blueprint not found: $RENDER_BLUEPRINT"
        exit 1
    fi

    log_success "Prerequisites validated"
}

# Check environment variables
check_env_vars() {
    log_info "Checking environment variables..."

    # Check required env vars for deployment
    local required_vars=("RENDER_API_KEY")
    local missing_vars=()

    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            missing_vars+=("$var")
        fi
    done

    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        log_warn "Missing environment variables: ${missing_vars[*]}"
        log_info "Some features may not work correctly"
    fi

    log_success "Environment check complete"
}

# Validate blueprint
validate_blueprint() {
    log_info "Validating render.yaml blueprint..."

    cd "$PROJECT_ROOT"

    # Check YAML syntax
    if ! python3 -c "import yaml; yaml.safe_load(open('$RENDER_BLUEPRINT'))" 2>/dev/null; then
        log_error "Invalid YAML syntax in render.yaml"
        exit 1
    fi

    log_success "Blueprint validation passed"
}

# Build container images
build_images() {
    if [[ "$SKIP_BUILD" == true ]]; then
        log_info "Skipping image builds (--skip-build)"
        return 0
    fi

    log_info "Building container images..."

    cd "$PROJECT_ROOT"

    # Build Neo4j image
    log_info "Building Neo4j image..."
    docker build -f deploy/neo4j/Dockerfile -t ai-agent-neo4j:latest . || {
        log_error "Neo4j image build failed"
        exit 1
    }

    # Build Directus image
    log_info "Building Directus image..."
    docker build -f deploy/directus/Dockerfile -t ai-agent-directus:latest . || {
        log_error "Directus image build failed"
        exit 1
    }

    log_success "Container images built successfully"
}

# Deploy to Render
deploy_to_render() {
    log_info "Deploying to Render ($ENVIRONMENT environment)..."

    cd "$PROJECT_ROOT"

    # Apply blueprint
    log_info "Applying Render blueprint..."
    render blueprint apply "$RENDER_BLUEPRINT" || {
        log_error "Blueprint application failed"
        exit 1
    }

    log_success "Deployment initiated"
}

# Wait for services to be ready
wait_for_services() {
    log_info "Waiting for services to be ready..."

    local max_attempts=30
    local attempt=1

    while [[ $attempt -le $max_attempts ]]; do
        log_info "Checking service status (attempt $attempt/$max_attempts)..."

        # Get service status
        local services_ready=true

        # Check main API service
        if ! render services list | grep -q "ai-agent-api.*running"; then
            services_ready=false
        fi

        # Check Directus service
        if ! render services list | grep -q "ai-agent-directus.*running"; then
            services_ready=false
        fi

        # Check Neo4j service
        if ! render services list | grep -q "ai-agent-neo4j.*running"; then
            services_ready=false
        fi

        if [[ "$services_ready" == true ]]; then
            log_success "All services are running"
            return 0
        fi

        sleep 30
        ((attempt++))
    done

    log_error "Services failed to become ready within timeout"
    return 1
}

# Run database migrations
run_migrations() {
    if [[ "$SKIP_MIGRATIONS" == true ]]; then
        log_info "Skipping database migrations (--skip-migrations)"
        return 0
    fi

    log_info "Running database migrations..."

    # Get database connection info from Render
    local db_url
    db_url=$(render services env get ai-agent-api DATABASE_URL --format value 2>/dev/null || echo "")

    if [[ -z "$db_url" ]]; then
        log_warn "Could not retrieve DATABASE_URL from Render"
        log_info "Migrations may need to be run manually"
        return 0
    fi

    # Export for Python script
    export DATABASE_URL="$db_url"

    # Run migrations
    cd "$PROJECT_ROOT"
    python3 -m migrations.runner --direction up || {
        log_error "Database migrations failed"
        exit 1
    }

    log_success "Database migrations completed"
}

# Enable pgvector extension
enable_pgvector() {
    log_info "Enabling pgvector extension..."

    # This needs to be done manually or via Render's SQL interface
    # for the initial database setup
    log_warn "pgvector extension must be enabled manually via Render dashboard"
    log_info "SQL to run: CREATE EXTENSION IF NOT EXISTS vector;"
}

# Run health checks
run_health_checks() {
    log_info "Running health checks..."

    cd "$PROJECT_ROOT"

    # Execute health check script
    if [[ -f "${SCRIPT_DIR}/render-health-check.sh" ]]; then
        bash "${SCRIPT_DIR}/render-health-check.sh" || {
            log_error "Health checks failed"
            exit 1
        }
    else
        log_warn "Health check script not found, skipping"
    fi

    log_success "Health checks passed"
}

# Output deployment information
output_deployment_info() {
    log_info "Deployment complete! Service URLs:"

    echo ""
    echo "=========================================="
    echo "  AI Agent Deployment Summary"
    echo "=========================================="
    echo ""

    # Try to get service URLs from Render
    local api_url directus_url
    api_url=$(render services info ai-agent-api --format json 2>/dev/null | grep -o '"url":"[^"]*"' | cut -d'"' -f4 || echo "pending...")
    directus_url=$(render services info ai-agent-directus --format json 2>/dev/null | grep -o '"url":"[^"]*"' | cut -d'"' -f4 || echo "pending...")

    echo -e "${GREEN}API Service:${NC}        $api_url"
    echo -e "${GREEN}Directus CMS:${NC}       $directus_url"
    echo -e "${GREEN}Neo4j (Private):${NC}    ai-agent-neo4j (internal)"
    echo ""
    echo "Health Check:        ${api_url}/health"
    echo "API Documentation:   ${api_url}/docs"
    echo ""
    echo "=========================================="
    echo ""

    log_info "Next steps:"
    echo "  1. Verify pgvector extension is enabled in PostgreSQL"
    echo "  2. Configure Directus admin credentials"
    echo "  3. Seed initial course data if needed"
    echo "  4. Configure LLM provider settings"
    echo ""
}

# Cleanup on error
cleanup() {
    local exit_code=$?
    if [[ $exit_code -ne 0 ]]; then
        log_error "Deployment failed with exit code $exit_code"
        echo ""
        echo "Troubleshooting:"
        echo "  - Check Render dashboard for service logs"
        echo "  - Verify environment variables are set correctly"
        echo "  - Run: render services logs <service-name>"
    fi
}

trap cleanup EXIT

# Main function
main() {
    echo "=========================================="
    echo "  AI Agent Render Deployment"
    echo "=========================================="
    echo ""

    parse_args "$@"

    log_info "Environment: $ENVIRONMENT"
    log_info "Skip migrations: $SKIP_MIGRATIONS"
    log_info "Skip build: $SKIP_BUILD"
    echo ""

    # Execute deployment steps
    validate_prerequisites
    check_env_vars
    validate_blueprint
    build_images
    deploy_to_render
    wait_for_services
    enable_pgvector
    run_migrations
    run_health_checks
    output_deployment_info

    log_success "Deployment completed successfully!"
}

# Run main function
main "$@"
