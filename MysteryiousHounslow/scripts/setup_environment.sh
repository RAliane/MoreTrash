#!/bin/bash

# Matchgorithm Environment Setup Script
# Creates all required secrets and environment files for production deployment

set -e

SECRETS_DIR="./secrets"
ENV_FILE=".env.production"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}" >&2
}

warn() {
    echo -e "${YELLOW}[WARN] $1${NC}"
}

info() {
    echo -e "${BLUE}[INFO] $1${NC}"
}

# Generate secure random string
generate_secret() {
    openssl rand -base64 32 | tr -d "=+/" | cut -c1-32
}

# Create secrets directory
create_secrets_dir() {
    log "Creating secrets directory..."
    mkdir -p "$SECRETS_DIR"
    chmod 700 "$SECRETS_DIR"
}

# Generate database credentials
generate_db_secrets() {
    info "Generating database secrets..."

    # PostgreSQL user
    if [ ! -f "$SECRETS_DIR/postgres_user.txt" ]; then
        echo "matchgorithm" > "$SECRETS_DIR/postgres_user.txt"
        log "Created postgres_user.txt"
    fi

    # PostgreSQL password
    if [ ! -f "$SECRETS_DIR/postgres_password.txt" ]; then
        generate_secret > "$SECRETS_DIR/postgres_password.txt"
        log "Created postgres_password.txt"
    fi

    # PostgreSQL database name
    if [ ! -f "$SECRETS_DIR/postgres_db.txt" ]; then
        echo "matchgorithm" > "$SECRETS_DIR/postgres_db.txt"
        log "Created postgres_db.txt"
    fi
}

# Generate Hasura secrets
generate_hasura_secrets() {
    info "Generating Hasura secrets..."

    if [ ! -f "$SECRETS_DIR/hasura_admin_secret.txt" ]; then
        generate_secret > "$SECRETS_DIR/hasura_admin_secret.txt"
        log "Created hasura_admin_secret.txt"
    fi
}

# Generate Directus secrets
generate_directus_secrets() {
    info "Generating Directus secrets..."

    if [ ! -f "$SECRETS_DIR/directus_secret.txt" ]; then
        generate_secret > "$SECRETS_DIR/directus_secret.txt"
        log "Created directus_secret.txt"
    fi

    if [ ! -f "$SECRETS_DIR/directus_admin_email.txt" ]; then
        echo "admin@matchgorithm.com" > "$SECRETS_DIR/directus_admin_email.txt"
        log "Created directus_admin_email.txt"
    fi

    if [ ! -f "$SECRETS_DIR/directus_admin_password.txt" ]; then
        generate_secret > "$SECRETS_DIR/directus_admin_password.txt"
        log "Created directus_admin_password.txt"
    fi

    if [ ! -f "$SECRETS_DIR/directus_api_key.txt" ]; then
        generate_secret > "$SECRETS_DIR/directus_api_key.txt"
        log "Created directus_api_key.txt"
    fi
}

# Generate JWT keys
generate_jwt_secrets() {
    info "Generating JWT keys..."

    if [ ! -f "$SECRETS_DIR/jwt_private_key.pem" ]; then
        openssl genrsa -out "$SECRETS_DIR/jwt_private_key.pem" 2048
        log "Created jwt_private_key.pem"
    fi

    if [ ! -f "$SECRETS_DIR/jwt_public_key.pem" ]; then
        openssl rsa -in "$SECRETS_DIR/jwt_private_key.pem" -pubout -out "$SECRETS_DIR/jwt_public_key.pem"
        log "Created jwt_public_key.pem"
    fi
}

# Generate API keys and URLs
generate_api_secrets() {
    info "Generating API secrets..."

    # URLs
    if [ ! -f "$SECRETS_DIR/directus_url.txt" ]; then
        echo "http://directus:8055" > "$SECRETS_DIR/directus_url.txt"
        log "Created directus_url.txt"
    fi

    if [ ! -f "$SECRETS_DIR/directus_token.txt" ]; then
        generate_secret > "$SECRETS_DIR/directus_token.txt"
        log "Created directus_token.txt"
    fi

    if [ ! -f "$SECRETS_DIR/hasura_endpoint.txt" ]; then
        echo "http://hasura:8080" > "$SECRETS_DIR/hasura_endpoint.txt"
        log "Created hasura_endpoint.txt"
    fi

    if [ ! -f "$SECRETS_DIR/database_url.txt" ]; then
        DB_USER=$(cat "$SECRETS_DIR/postgres_user.txt")
        DB_PASS=$(cat "$SECRETS_DIR/postgres_password.txt")
        DB_NAME=$(cat "$SECRETS_DIR/postgres_db.txt")
        echo "postgresql://$DB_USER:$DB_PASS@postgres:5432/$DB_NAME" > "$SECRETS_DIR/database_url.txt"
        log "Created database_url.txt"
    fi

    # External API keys (placeholders)
    if [ ! -f "$SECRETS_DIR/groq_api_key.txt" ]; then
        echo "your-groq-api-key-here" > "$SECRETS_DIR/groq_api_key.txt"
        warn "Created groq_api_key.txt with placeholder - UPDATE REQUIRED"
    fi

    if [ ! -f "$SECRETS_DIR/google_client_id.txt" ]; then
        echo "your-google-client-id" > "$SECRETS_DIR/google_client_id.txt"
        warn "Created google_client_id.txt with placeholder - UPDATE REQUIRED"
    fi

    if [ ! -f "$SECRETS_DIR/google_client_secret.txt" ]; then
        echo "your-google-client-secret" > "$SECRETS_DIR/google_client_secret.txt"
        warn "Created google_client_secret.txt with placeholder - UPDATE REQUIRED"
    fi

    if [ ! -f "$SECRETS_DIR/github_client_id.txt" ]; then
        echo "your-github-client-id" > "$SECRETS_DIR/github_client_id.txt"
        warn "Created github_client_id.txt with placeholder - UPDATE REQUIRED"
    fi

    if [ ! -f "$SECRETS_DIR/github_client_secret.txt" ]; then
        echo "your-github-client-secret" > "$SECRETS_DIR/github_client_secret.txt"
        warn "Created github_client_secret.txt with placeholder - UPDATE REQUIRED"
    fi

    # n8n webhooks (placeholders)
    if [ ! -f "$SECRETS_DIR/n8n_webhook_url.txt" ]; then
        echo "http://n8n:5678/webhook/your-webhook-id" > "$SECRETS_DIR/n8n_webhook_url.txt"
        warn "Created n8n_webhook_url.txt with placeholder - UPDATE REQUIRED"
    fi

    if [ ! -f "$SECRETS_DIR/n8n_api_url.txt" ]; then
        echo "http://n8n:5678" > "$SECRETS_DIR/n8n_api_url.txt"
        log "Created n8n_api_url.txt"
    fi

    # SMTP password for password reset emails
    if [ ! -f "$SECRETS_DIR/smtp_password.txt" ]; then
        echo "your-smtp-app-password-here" > "$SECRETS_DIR/smtp_password.txt"
        warn "Created smtp_password.txt with placeholder - UPDATE REQUIRED"
    fi
}

# Create Podman secrets
create_podman_secrets() {
    info "Creating Podman secrets..."

    # Check if secrets already exist
    if podman secret ls | grep -q "postgres_user"; then
        warn "Podman secrets already exist. Skipping creation."
        return 0
    fi

    # Create secrets from files
    for secret_file in "$SECRETS_DIR"/*.txt "$SECRETS_DIR"/*.pem; do
        if [ -f "$secret_file" ]; then
            secret_name=$(basename "$secret_file" | sed 's/\.txt$//' | sed 's/\.pem$//')
            podman secret create "$secret_name" "$secret_file"
            log "Created Podman secret: $secret_name"
        fi
    done
}

# Create environment file
create_env_file() {
    info "Creating production environment file..."

    cat > "$ENV_FILE" << EOF
# Matchgorithm Production Environment Variables
# This file contains non-sensitive configuration
# Sensitive data is stored as Podman secrets

# Server Configuration
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
RUST_LOG=info

# Domain Configuration (update for your domain)
DOMAIN=matchgorithm.com
DIRECTUS_SUBDOMAIN=directus.matchgorithm.com

# Monitoring
PROMETHEUS_RETENTION=200h
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=secure_password_here

# Backup Configuration
BACKUP_SCHEDULE=daily
BACKUP_RETENTION=30

# Security Settings
SSL_CERT_PATH=/etc/nginx/certs/fullchain.pem
SSL_KEY_PATH=/etc/nginx/certs/privkey.pem

# Rate Limiting
RATE_LIMIT_GENERAL=30r/s
RATE_LIMIT_API=10r/s

# Cache Settings
STATIC_CACHE_DURATION=30d
API_CACHE_DURATION=5m
EOF

    log "Created $ENV_FILE"
    warn "Review and update $ENV_FILE with your domain and settings"
}

# Main setup function
main() {
    log "Starting Matchgorithm environment setup..."

    create_secrets_dir
    generate_db_secrets
    generate_hasura_secrets
    generate_directus_secrets
    generate_jwt_secrets
    generate_api_secrets
    create_podman_secrets
    create_env_file

    log "Environment setup completed!"
    echo ""
    info "Next steps:"
    echo "1. Review and update placeholder values in $SECRETS_DIR/"
    echo "2. Update $ENV_FILE with your domain configuration"
    echo "3. Run: ./scripts/generate_certs.sh (for development)"
    echo "4. Run: ./scripts/production_setup.sh"
    echo "5. Run: ./scripts/final_validation.sh"
    echo ""
    info "Security reminder:"
    echo "- Never commit secrets to version control"
    echo "- Rotate secrets regularly in production"
    echo "- Use strong, unique passwords for all services"
}

# Run main function
main "$@"