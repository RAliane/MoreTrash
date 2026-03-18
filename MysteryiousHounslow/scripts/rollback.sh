#!/bin/bash

# Matchgorithm Rollback Script
# Safely rollback to previous deployment version

set -e

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

# Check if services are running
check_services() {
    info "Checking current service status..."

    if ! podman-compose ps | grep -q "Up"; then
        error "No services are currently running"
        exit 1
    fi

    log "Services are running"
}

# Create database backup before rollback
backup_database() {
    info "Creating pre-rollback database backup..."

    BACKUP_FILE="rollback_backup_$(date +%Y%m%d_%H%M%S).sql"

    podman exec matchgorithm-postgres pg_dump -U matchgorithm -d matchgorithm > "$BACKUP_FILE"

    if [ $? -eq 0 ]; then
        log "Database backup created: $BACKUP_FILE"
        echo "$BACKUP_FILE" > .rollback_backup
    else
        error "Failed to create database backup"
        exit 1
    fi
}

# Stop all services gracefully
stop_services() {
    info "Stopping all services..."

    podman-compose down

    # Wait for services to stop
    sleep 10

    log "All services stopped"
}

# Restore from backup if available
restore_backup() {
    local backup_file="$1"

    if [ -f "$backup_file" ]; then
        info "Restoring database from backup: $backup_file"

        # Start only postgres
        podman-compose up -d postgres

        # Wait for postgres to be ready
        sleep 30

        # Restore database
        podman exec -i matchgorithm-postgres psql -U matchgorithm -d matchgorithm < "$backup_file"

        if [ $? -eq 0 ]; then
            log "Database restored successfully"
        else
            error "Database restore failed"
            exit 1
        fi
    else
        warn "No backup file provided, skipping database restore"
    fi
}

# Clean up old images and containers
cleanup() {
    info "Cleaning up old containers and images..."

    # Remove stopped containers
    podman container prune -f

    # Remove dangling images
    podman image prune -f

    log "Cleanup completed"
}

# Restart services with previous configuration
restart_services() {
    info "Restarting services..."

    # Pull latest images (in case of rollback to previous tag)
    podman-compose pull

    # Start all services
    podman-compose up -d

    # Wait for services to be ready
    sleep 30

    log "Services restarted"
}

# Validate rollback
validate_rollback() {
    info "Validating rollback..."

    # Run health checks
    if ./scripts/final_validation.sh > /dev/null 2>&1; then
        log "Rollback validation successful"
        return 0
    else
        error "Rollback validation failed"
        return 1
    fi
}

# Main rollback function
main() {
    local restore_from_backup="${1:-false}"
    local backup_file="${2:-}"

    log "Starting Matchgorithm rollback procedure..."

    # Confirmation prompt
    echo ""
    warn "⚠️  ROLLBACK WARNING ⚠️"
    echo "This will stop all services and restore to previous state."
    echo "A database backup will be created automatically."
    echo ""
    read -p "Are you sure you want to proceed? (yes/no): " -r
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        info "Rollback cancelled by user"
        exit 0
    fi

    check_services
    backup_database
    stop_services

    if [ "$restore_from_backup" = "true" ] && [ -n "$backup_file" ]; then
        restore_backup "$backup_file"
    fi

    cleanup
    restart_services

    if validate_rollback; then
        log "✅ Rollback completed successfully!"
        echo ""
        info "Rollback Summary:"
        echo "- Services restarted and validated"
        echo "- Database backup saved: $(cat .rollback_backup 2>/dev/null || echo 'N/A')"
        echo "- All services should be operational"
        echo ""
        info "Monitor the services closely and run validation if needed:"
        echo "  ./scripts/final_validation.sh"
    else
        error "❌ Rollback completed but validation failed!"
        echo ""
        info "Manual intervention may be required. Check logs:"
        echo "  podman-compose logs -f"
        exit 1
    fi
}

# Show usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --restore-from-backup FILE    Restore database from specific backup file"
    echo "  --help                        Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                             # Standard rollback with automatic backup"
    echo "  $0 --restore-from-backup backup.sql    # Rollback and restore from file"
}

# Parse arguments
case "${1:-}" in
    --restore-from-backup)
        if [ -z "${2:-}" ]; then
            error "Backup file must be specified with --restore-from-backup"
            exit 1
        fi
        main "true" "$2"
        ;;
    --help|-h)
        usage
        exit 0
        ;;
    "")
        main
        ;;
    *)
        error "Unknown option: $1"
        usage
        exit 1
        ;;
esac