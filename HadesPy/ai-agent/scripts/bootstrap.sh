#!/bin/bash
# =============================================================================
# Bootstrap Script
# Initialize AI Agent Full Stack
# =============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ARTIFACTS_DIR="$PROJECT_DIR/artifacts"
LOGS_DIR="$PROJECT_DIR/logs"

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# =============================================================================
# Prerequisites Check
# =============================================================================
check_prerequisites() {
    log_step "Checking prerequisites..."

    local missing=()

    # Check for required commands
    if ! command -v python3 &> /dev/null; then
        missing+=("python3")
    fi

    if ! command -v uv &> /dev/null; then
        log_warn "UV not found. Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
        missing+=("uv")
    fi

    if ! command -v podman &> /dev/null; then
        log_warn "Podman not found. Install with your package manager."
        missing+=("podman")
    fi

    if ! command -v podman-compose &> /dev/null; then
        log_warn "podman-compose not found. Install with: pip install podman-compose"
        missing+=("podman-compose")
    fi

    if [ ${#missing[@]} -ne 0 ]; then
        log_error "Missing prerequisites: ${missing[*]}"
        exit 1
    fi

    log_info "All prerequisites satisfied"
}

# =============================================================================
# Directory Setup
# =============================================================================
setup_directories() {
    log_step "Setting up directories..."

    mkdir -p "$ARTIFACTS_DIR"
    mkdir -p "$LOGS_DIR"
    mkdir -p "$PROJECT_DIR/secrets"

    log_info "Directories created:"
    log_info "  - $ARTIFACTS_DIR"
    log_info "  - $LOGS_DIR"
    log_info "  - $PROJECT_DIR/secrets"
}

# =============================================================================
# Environment Setup
# =============================================================================
setup_environment() {
    log_step "Setting up environment..."

    if [ ! -f "$PROJECT_DIR/.env" ]; then
        if [ -f "$PROJECT_DIR/.env.example" ]; then
            cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
            log_info "Created .env from .env.example"
            log_warn "Please edit .env and configure your settings!"
        else
            log_error ".env.example not found"
            exit 1
        fi
    else
        log_info ".env already exists"
    fi
}

# =============================================================================
# Python Dependencies
# =============================================================================
install_dependencies() {
    log_step "Installing Python dependencies..."

    cd "$PROJECT_DIR"

    if command -v uv &> /dev/null; then
        log_info "Using UV for dependency management"
        uv sync
        uv pip install -e ".[dev]"
    else
        log_info "Using pip for dependency management"
        pip install -e ".[dev]"
    fi

    log_info "Dependencies installed"
}

# =============================================================================
# Database Initialization
# =============================================================================
init_database() {
    log_step "Initializing database..."

    # Create SQLite database directory
    mkdir -p "$ARTIFACTS_DIR"

    # Bootstrap Directus collections if models.json exists
    if [ -f "$ARTIFACTS_DIR/models.json" ]; then
        log_info "Found models.json - collections will be bootstrapped on first run"
    else
        log_warn "models.json not found - creating default"
        cat > "$ARTIFACTS_DIR/models.json" << 'EOF'
{
  "collections": [
    {
      "collection": "messages",
      "meta": { "icon": "chat" },
      "schema": { "name": "messages" }
    },
    {
      "collection": "memory_chunks",
      "meta": { "icon": "storage" },
      "schema": { "name": "memory_chunks" }
    }
  ]
}
EOF
    fi

    log_info "Database initialization prepared"
}

# =============================================================================
# Podman Network Setup
# =============================================================================
setup_podman_networks() {
    log_step "Setting up Podman networks..."

    # Create triple-layer networks
    networks=("edge_net" "app_net" "db_net")
    subnets=("172.20.0.0/24" "172.20.1.0/24" "172.20.2.0/24")

    for i in "${!networks[@]}"; do
        network="${networks[$i]}"
        subnet="${subnets[$i]}"

        if podman network exists "$network"; then
            log_info "Network $network already exists"
        else
            log_info "Creating network $network ($subnet)"
            podman network create --subnet "$subnet" "$network"
        fi
    done
}

# =============================================================================
# Secrets Setup
# =============================================================================
setup_secrets() {
    log_step "Setting up secrets..."

    secrets_dir="$PROJECT_DIR/secrets"

    # Create secrets if they don't exist
    if [ ! -f "$secrets_dir/directus_token" ]; then
        log_info "Creating Directus token secret"
        openssl rand -hex 32 > "$secrets_dir/directus_token"
    fi

    if [ ! -f "$secrets_dir/openai_api_key" ]; then
        log_info "Creating placeholder OpenAI API key secret"
        echo "sk-placeholder" > "$secrets_dir/openai_api_key"
        log_warn "Please update secrets/openai_api_key with your actual API key!"
    fi

    # Create Podman secrets
    if command -v podman &> /dev/null; then
        log_info "Creating Podman secrets..."

        # Remove existing secrets if they exist
        podman secret rm directus_token 2>/dev/null || true
        podman secret rm openai_api_key 2>/dev/null || true

        # Create new secrets
        podman secret create directus_token "$secrets_dir/directus_token"
        podman secret create openai_api_key "$secrets_dir/openai_api_key"
    fi
}

# =============================================================================
# SSL Certificates (Development)
# =============================================================================
setup_ssl_dev() {
    log_step "Setting up SSL certificates for development..."

    ssl_dir="$PROJECT_DIR/deploy/nginx/ssl"
    mkdir -p "$ssl_dir"

    if [ ! -f "$ssl_dir/localhost.crt" ]; then
        log_info "Generating self-signed certificate for development"
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout "$ssl_dir/localhost.key" \
            -out "$ssl_dir/localhost.crt" \
            -subj "/C=US/ST=State/L=City/O=AI Agent/OU=Development/CN=localhost"
        log_warn "Using self-signed certificate - browsers will show warnings"
    else
        log_info "SSL certificates already exist"
    fi
}

# =============================================================================
# Pre-flight Checks
# =============================================================================
preflight_checks() {
    log_step "Running pre-flight checks..."

    cd "$PROJECT_DIR"

    # Check Python syntax
    log_info "Checking Python syntax..."
    python3 -m py_compile src/main.py
    python3 -m py_compile src/config.py
    log_info "Python syntax OK"

    # Run ruff if available
    if command -v ruff &> /dev/null; then
        log_info "Running linting checks..."
        ruff check src/ || log_warn "Linting issues found"
    fi

    log_info "Pre-flight checks completed"
}

# =============================================================================
# Usage
# =============================================================================
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Bootstrap AI Agent Full Stack

OPTIONS:
    -h, --help          Show this help message
    --skip-deps         Skip dependency installation
    --skip-networks     Skip Podman network setup
    --production        Production mode (no dev tools)
    --quick             Quick mode (minimal setup)

EXAMPLES:
    $0                  Full setup
    $0 --quick          Minimal setup for development
    $0 --production     Production deployment setup

EOF
}

# =============================================================================
# Main
# =============================================================================
main() {
    local skip_deps=false
    local skip_networks=false
    local production=false
    local quick=false

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                usage
                exit 0
                ;;
            --skip-deps)
                skip_deps=true
                shift
                ;;
            --skip-networks)
                skip_networks=true
                shift
                ;;
            --production)
                production=true
                shift
                ;;
            --quick)
                quick=true
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done

    log_info "========================================"
    log_info "AI Agent Full Stack - Bootstrap"
    log_info "========================================"
    log_info ""

    check_prerequisites
    setup_directories
    setup_environment

    if [ "$quick" = false ]; then
        if [ "$skip_deps" = false ]; then
            install_dependencies
        fi
        init_database
        setup_ssl_dev
    fi

    if [ "$skip_networks" = false ]; then
        setup_podman_networks
    fi

    setup_secrets
    preflight_checks

    log_info ""
    log_info "========================================"
    log_info "Bootstrap completed successfully!"
    log_info "========================================"
    log_info ""
    log_info "Next steps:"
    log_info "  1. Edit .env with your configuration"
    log_info "  2. Update secrets/ with actual API keys"
    log_info "  3. Run: podman-compose up -d"
    log_info "  4. Access: http://localhost:8000/health"
    log_info ""
    log_info "Or start locally:"
    log_info "  uv run uvicorn src.main:app --reload"
    log_info ""
}

# Run main function
main "$@"
