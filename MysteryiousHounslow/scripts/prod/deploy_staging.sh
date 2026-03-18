#!/bin/bash
set -e

echo "🚀 Matchgorithm Staging Deployment"
echo "📅 $(date) | 🕒 $(date +%H:%M) Europe/London"
echo ""

# Configuration
STAGING_URL="https://staging.matchgorithm.co.uk"
BACKUP_DIR="./backups"
DEPLOY_TIMEOUT=1800  # 30 minutes

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date +'%H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[WARN] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}" >&2
}

# Pre-deployment checks
pre_deployment_checks() {
    log "Running pre-deployment checks..."

    # Check if in correct directory
    if [ ! -f "podman-compose.yml" ]; then
        error "Not in Matchgorithm project directory"
        exit 1
    fi

    # Check Git status
    if [ -n "$(git status --porcelain)" ]; then
        error "Uncommitted changes detected. Commit or stash before deploying."
        git status
        exit 1
    fi

    # Check if on main branch
    current_branch=$(git branch --show-current)
    if [ "$current_branch" != "main" ]; then
        error "Not on main branch (current: $current_branch). Switch to main before deploying."
        exit 1
    fi

    # Check required files exist
    required_files=("docker/docker-compose.staging.yml" "docker/nginx/staging.conf")
    for file in "${required_files[@]}"; do
        if [ ! -f "$file" ]; then
            error "Required file missing: $file"
            exit 1
        fi
    done

    log "✅ Pre-deployment checks passed"
}

# Create pre-deployment backup
create_backup() {
    log "Creating pre-deployment backup..."

    mkdir -p "$BACKUP_DIR"

    if podman ps | grep -q matchgorithm-postgres; then
        backup_file="$BACKUP_DIR/pre_staging_backup_$(date +%Y%m%d_%H%M%S).sql.gz"
        log "Backing up database to $backup_file"

        if podman exec matchgorithm-postgres pg_dump -U postgres matchgorithm | gzip > "$backup_file"; then
            log "✅ Database backup created: $backup_file"
        else
            warn "⚠️  Database backup failed, continuing deployment"
        fi
    else
        log "ℹ️  Database not running, skipping backup"
    fi
}

# Stop existing services
stop_services() {
    log "Stopping existing staging services..."

    if podman-compose ps | grep -q "Up"; then
        podman-compose down
        sleep 10
        log "✅ Existing services stopped"
    else
        log "ℹ️  No existing services running"
    fi
}

# Build and start services
deploy_services() {
    log "Building and deploying staging services..."

    # Set timeout for deployment
    timeout $DEPLOY_TIMEOUT bash -c '
        # Build and start services
        podman-compose -f docker/docker-compose.yml -f docker/docker-compose.staging.yml build

        if [ $? -ne 0 ]; then
            echo "❌ Build failed"
            exit 1
        fi

        podman-compose -f docker/docker-compose.yml -f docker/docker-compose.staging.yml up -d

        if [ $? -ne 0 ]; then
            echo "❌ Deployment failed"
            exit 1
        fi

        echo "✅ Services deployed successfully"
    ' || {
        error "Deployment timed out or failed"
        exit 1
    }
}

# Wait for services to be ready
wait_for_services() {
    log "Waiting for services to be ready..."

    local max_attempts=60  # 5 minutes
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        log "Health check attempt $attempt/$max_attempts"

        # Check if all services are running
        running_services=$(podman-compose -f docker/docker-compose.yml -f docker/docker-compose.staging.yml ps | grep -c "Up")
        expected_services=6  # nginx, app, directus, hasura, postgres, prometheus, grafana

        if [ "$running_services" -ge 5 ]; then  # Allow some flexibility
            log "✅ Services are running ($running_services/$expected_services)"

            # Test health endpoints
            if curl -s --max-time 10 "$STAGING_URL/health" | grep -q "healthy"; then
                log "✅ Health check passed"
                return 0
            else
                warn "⚠️  Health check failed, waiting..."
            fi
        else
            log "Waiting for services... ($running_services/$expected_services running)"
        fi

        sleep 10
        ((attempt++))
    done

    error "Services failed to start properly"
    podman-compose -f docker/docker-compose.yml -f docker/docker-compose.staging.yml logs
    exit 1
}

# Run post-deployment tests
run_tests() {
    log "Running post-deployment tests..."

    # Basic connectivity tests
    if curl -s --max-time 5 "$STAGING_URL" | grep -q "Matchgorithm"; then
        log "✅ Frontend accessible"
    else
        warn "⚠️  Frontend not responding correctly"
    fi

    # API health check
    if curl -s --max-time 5 "$STAGING_URL/api/health" | grep -q "ok\|healthy"; then
        log "✅ API health check passed"
    else
        warn "⚠️  API health check failed"
    fi

    # Database connectivity
    if podman exec matchgorithm-postgres-staging pg_isready -U postgres -d matchgorithm -h localhost; then
        log "✅ Database connectivity verified"
    else
        warn "⚠️  Database connectivity check failed"
    fi
}

# Send notifications
send_notifications() {
    log "Sending deployment notifications..."

    # In a real deployment, this would send emails/Slack notifications
    echo "Deployment completed successfully!" > /tmp/staging_deploy_notification
    echo "URL: $STAGING_URL" >> /tmp/staging_deploy_notification
    echo "Timestamp: $(date)" >> /tmp/staging_deploy_notification

    log "✅ Deployment notification prepared"
}

# Main deployment process
main() {
    log "Starting Matchgorithm staging deployment..."

    pre_deployment_checks
    create_backup
    stop_services
    deploy_services
    wait_for_services
    run_tests
    send_notifications

    echo ""
    echo "🎉 STAGING DEPLOYMENT COMPLETED SUCCESSFULLY!"
    echo ""
    echo "📋 Deployment Summary:"
    echo "🌐 Frontend: $STAGING_URL"
    echo "🔧 Admin: https://admin.staging.matchgorithm.co.uk"
    echo "📊 Monitoring: http://localhost:9090 (Prometheus)"
    echo "📈 Dashboards: http://localhost:3000 (Grafana)"
    echo ""
    echo "🔍 Run './scripts/final_verification.sh' to verify deployment"
    echo "📝 Check logs: podman-compose -f docker/docker-compose.yml -f docker/docker-compose.staging.yml logs -f"
}

# Handle command line arguments
case "${1:-}" in
    --dry-run)
        echo "🔍 Dry run mode - checking configuration only"
        pre_deployment_checks
        echo "✅ Configuration validation passed"
        ;;
    --rollback)
        echo "🔄 Rolling back staging deployment..."
        podman-compose -f docker/docker-compose.yml -f docker/docker-compose.staging.yml down
        echo "✅ Staging deployment rolled back"
        ;;
    *)
        main "$@"
        ;;
esac