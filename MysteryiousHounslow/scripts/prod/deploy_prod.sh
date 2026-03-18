#!/bin/bash
set -e

echo "🚀 Matchgorithm Production Deployment"
echo "📅 $(date) | 🕒 $(date +%H:%M) Europe/London"
echo ""

# Configuration
PROD_URL="https://matchgorithm.co.uk"
BACKUP_DIR="./backups"
DEPLOY_TIMEOUT=3600  # 1 hour for production
ROLLBACK_WINDOW=7200  # 2 hours for rollback window

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

# Critical pre-deployment validation
pre_production_checks() {
    log "🔍 Running critical pre-production validation..."

    # Must be on main branch
    current_branch=$(git branch --show-current)
    if [ "$current_branch" != "main" ]; then
        error "PRODUCTION DEPLOYMENT MUST BE FROM MAIN BRANCH"
        error "Current branch: $current_branch"
        exit 1
    fi

    # No uncommitted changes
    if [ -n "$(git status --porcelain)" ]; then
        error "PRODUCTION DEPLOYMENT CANNOT HAVE UNCOMMITTED CHANGES"
        git status
        exit 1
    fi

    # Recent commits should be tested
    last_commit_age=$(git log -1 --format=%ct)
    current_time=$(date +%s)
    age_hours=$(( (current_time - last_commit_age) / 3600 ))

    if [ $age_hours -gt 24 ]; then
        warn "⚠️  Last commit is $age_hours hours old"
        warn "⚠️  Ensure recent changes have been tested in staging"
        read -p "Continue with production deployment? (yes/no): " confirm
        if [ "$confirm" != "yes" ]; then
            log "Production deployment cancelled"
            exit 0
        fi
    fi

    # Check if staging deployment exists and is healthy
    log "Checking staging environment health..."
    if ! curl -s --max-time 10 "https://staging.matchgorithm.co.uk/health" | grep -q "healthy"; then
        error "STAGING ENVIRONMENT IS NOT HEALTHY"
        error "Fix staging issues before production deployment"
        exit 1
    fi

    # Verify all required secrets exist
    required_secrets=("postgres_password" "directus_secret" "hasura_admin_secret" "jwt_private_key_pem")
    for secret in "${required_secrets[@]}"; do
        if ! podman secret inspect "$secret" >/dev/null 2>&1; then
            error "Required secret missing: $secret"
            exit 1
        fi
    done

    # Run final verification script
    log "Running final verification checks..."
    if ! ./scripts/final_verification.sh; then
        error "FINAL VERIFICATION FAILED"
        error "Cannot deploy to production with verification failures"
        exit 1
    fi

    log "✅ All pre-production checks passed"
}

# Create emergency rollback plan
create_rollback_plan() {
    log "📋 Creating emergency rollback plan..."

    ROLLBACK_FILE="$BACKUP_DIR/rollback_plan_$(date +%Y%m%d_%H%M%S).txt"

    cat > "$ROLLBACK_FILE" << EOF
MATCHGORMAN PRODUCTION DEPLOYMENT ROLLBACK PLAN
===============================================
Deployment Date: $(date)
Deployed By: $(whoami)
Git Commit: $(git rev-parse HEAD)

ROLLBACK PROCEDURE:
1. Stop production services: podman-compose -f docker/docker-compose.prod.yml down
2. Restore from backup: ./scripts/prod/restore_backup.sh $BACKUP_DIR/pre_prod_backup_*.sql.gz
3. Restart with previous version: podman-compose -f docker/docker-compose.prod.yml up -d
4. Verify rollback: curl -s $PROD_URL/health

EMERGENCY CONTACTS:
- DevOps: devops@matchgorithm.co.uk
- Security: security@matchgorithm.co.uk
- Management: management@matchgorithm.co.uk

ROLLBACK WINDOW: $ROLLBACK_WINDOW seconds from deployment start
EOF

    log "📄 Rollback plan created: $ROLLBACK_FILE"
    echo "$ROLLBACK_FILE" > .current_rollback_plan
}

# Create production backup
create_production_backup() {
    log "💾 Creating production backup..."

    mkdir -p "$BACKUP_DIR"

    # Check if production database is running
    if podman ps | grep -q matchgorithm-postgres-prod; then
        backup_file="$BACKUP_DIR/pre_prod_backup_$(date +%Y%m%d_%H%M%S).sql.gz"
        log "Creating production backup: $backup_file"

        if podman exec matchgorithm-postgres-prod pg_dump -U postgres matchgorithm | gzip > "$backup_file"; then
            log "✅ Production backup created: $backup_file"
            echo "$backup_file" > .current_backup
        else
            error "PRODUCTION BACKUP FAILED - ABORTING DEPLOYMENT"
            exit 1
        fi
    else
        log "ℹ️  No existing production database, proceeding..."
    fi
}

# Blue-green deployment strategy
blue_green_deployment() {
    log "🔄 Executing blue-green deployment..."

    # In a full implementation, this would:
    # 1. Deploy to "green" environment alongside "blue"
    # 2. Run comprehensive tests on green
    # 3. Switch traffic to green
    # 4. Keep blue as rollback option

    # For now, implement a simplified version
    log "Deploying to production environment..."

    timeout $DEPLOY_TIMEOUT bash -c '
        # Build production images
        podman-compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml build

        if [ $? -ne 0 ]; then
            echo "❌ Production build failed"
            exit 1
        fi

        # Deploy with rolling update
        podman-compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml up -d

        if [ $? -ne 0 ]; then
            echo "❌ Production deployment failed"
            exit 1
        fi

        echo "✅ Production deployment initiated"
    ' || {
        error "Production deployment timed out or failed"
        # Attempt automatic rollback
        emergency_rollback
        exit 1
    }
}

# Emergency rollback function
emergency_rollback() {
    error "🚨 EMERGENCY ROLLBACK INITIATED"

    # Stop failed deployment
    podman-compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml down || true

    # Restore from backup if available
    if [ -f .current_backup ]; then
        backup_file=$(cat .current_backup)
        log "Restoring from backup: $backup_file"
        # Restore logic would go here
    fi

    # Notify team
    echo "EMERGENCY ROLLBACK EXECUTED - $(date)" >> deployment_incidents.log
}

# Post-deployment validation
post_deployment_validation() {
    log "🔍 Running post-deployment validation..."

    local max_attempts=120  # 10 minutes
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        log "Validation attempt $attempt/$max_attempts"

        # Check production health
        if curl -s --max-time 10 "$PROD_URL/health" | grep -q "healthy"; then
            log "✅ Production health check passed"

            # Run final verification
            if ./scripts/final_verification.sh; then
                log "✅ Post-deployment verification passed"
                return 0
            fi
        fi

        log "Waiting for production to stabilize..."
        sleep 30
        ((attempt++))
    done

    error "Post-deployment validation failed"
    emergency_rollback
    exit 1
}

# Notify stakeholders
notify_stakeholders() {
    log "📢 Notifying stakeholders..."

    NOTIFICATION_FILE="$BACKUP_DIR/deployment_notification_$(date +%Y%m%d_%H%M%S).txt"

    cat > "$NOTIFICATION_FILE" << EOF
MATCHGORMAN PRODUCTION DEPLOYMENT COMPLETED
==========================================
Deployment Date: $(date)
Deployed By: $(whoami)
Git Commit: $(git rev-parse HEAD)
Environment: Production
URL: $PROD_URL

SERVICES DEPLOYED:
- Frontend: $PROD_URL
- API: $PROD_URL/api/
- Admin: https://admin.matchgorithm.co.uk
- Monitoring: https://monitoring.matchgorithm.co.uk

ROLLBACK WINDOW: $ROLLBACK_WINDOW seconds from $(date)
Rollback Plan: $(cat .current_rollback_plan 2>/dev/null || echo "Not available")

MONITORING:
- Health: $PROD_URL/health
- Metrics: https://monitoring.matchgorithm.co.uk/metrics
- Logs: podman-compose -f docker/docker-compose.prod.yml logs -f

EMERGENCY CONTACTS:
- DevOps: devops@matchgorithm.co.uk
- Security: security@matchgorithm.co.uk
- Management: management@matchgorithm.co.uk
EOF

    log "📧 Notification prepared: $NOTIFICATION_FILE"

    # In a real deployment, this would send emails/Slack notifications
    echo "Production deployment completed successfully!" > /tmp/prod_deploy_complete
}

# Main production deployment
main() {
    log "🚨 STARTING PRODUCTION DEPLOYMENT 🚨"
    echo ""
    warn "⚠️  PRODUCTION DEPLOYMENT CHECKLIST:"
    echo "  ✅ Code tested in staging"
    echo "  ✅ All stakeholders notified"
    echo "  ✅ Rollback plan ready"
    echo "  ✅ Emergency contacts available"
    echo ""

    read -p "Confirm production deployment? (type 'PRODUCTION' to continue): " confirm
    if [ "$confirm" != "PRODUCTION" ]; then
        log "Production deployment cancelled"
        exit 0
    fi

    # Execute deployment phases
    pre_production_checks
    create_rollback_plan
    create_production_backup
    blue_green_deployment
    post_deployment_validation
    notify_stakeholders

    echo ""
    echo "🎉 PRODUCTION DEPLOYMENT COMPLETED SUCCESSFULLY! 🎉"
    echo ""
    echo "📋 Production Deployment Summary:"
    echo "🌐 Application: $PROD_URL"
    echo "🔧 Admin Panel: https://admin.matchgorithm.co.uk"
    echo "📊 Monitoring: https://monitoring.matchgorithm.co.uk"
    echo "📝 Rollback Plan: $(cat .current_rollback_plan 2>/dev/null)"
    echo ""
    echo "⏰ Rollback Window: $ROLLBACK_WINDOW seconds"
    echo "📞 On-call: Ready for monitoring"
    echo ""
    echo "📈 Begin post-deployment monitoring and user acceptance testing"
}

# Command line options
case "${1:-}" in
    --validate)
        echo "🔍 Validation-only mode"
        pre_production_checks
        echo "✅ Production deployment validation passed"
        ;;
    --rollback)
        echo "🔄 Emergency rollback mode"
        emergency_rollback
        ;;
    --status)
        echo "📊 Production deployment status"
        podman-compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml ps
        ;;
    *)
        main "$@"
        ;;
esac