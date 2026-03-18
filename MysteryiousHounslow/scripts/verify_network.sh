#!/bin/bash

# Network Security Verification Script
# Verifies triple network separation implementation

set -e

echo "🔍 Verifying Matchgorithm Network Security Setup"
echo "================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check result
check_result() {
    local result=$1
    local message=$2
    if [ $result -eq 0 ]; then
        echo -e "${GREEN}✅ PASS${NC}: $message"
        return 0
    else
        echo -e "${RED}❌ FAIL${NC}: $message"
        return 1
    fi
}

# Function to warn
warn() {
    echo -e "${YELLOW}⚠️  WARNING${NC}: $1"
}

# Check Podman networks exist
echo "🔍 Checking Podman networks..."
podman network exists edge-net 2>/dev/null
check_result $? "edge-net network exists"

podman network exists auth-net 2>/dev/null
check_result $? "auth-net network exists"

podman network exists db-net 2>/dev/null
check_result $? "db-net network exists"

# Verify network configurations
echo ""
echo "🔍 Verifying network configurations..."

# Check subnets
EDGE_SUBNET=$(podman network inspect edge-net | grep '"subnet"' | head -1 | grep -o '10\.0\.1\.0/24' || echo "")
[ -n "$EDGE_SUBNET" ]
check_result $? "edge-net has correct subnet (10.0.1.0/24)"

AUTH_SUBNET=$(podman network inspect auth-net | grep '"subnet"' | head -1 | grep -o '10\.0\.2\.0/24' || echo "")
[ -n "$AUTH_SUBNET" ]
check_result $? "auth-net has correct subnet (10.0.2.0/24)"

DB_SUBNET=$(podman network inspect db-net | grep '"subnet"' | head -1 | grep -o '10\.0\.3\.0/24' || echo "")
[ -n "$DB_SUBNET" ]
check_result $? "db-net has correct subnet (10.0.3.0/24)"

# Check internal flags
AUTH_INTERNAL=$(podman network inspect auth-net | grep '"internal"' | grep 'true' || echo "")
[ -n "$AUTH_INTERNAL" ]
check_result $? "auth-net is internal (no external access)"

DB_INTERNAL=$(podman network inspect db-net | grep '"internal"' | grep 'true' || echo "")
[ -n "$DB_INTERNAL" ]
check_result $? "db-net is internal (no external access)"

# Check service network assignments (if services are running)
echo ""
echo "🔍 Checking service network assignments..."

# Check if compose is running
if podman-compose ps 2>/dev/null | grep -q "Up"; then
    echo "📋 Services are running - checking network assignments..."

    # Get container network info
    NGINX_NETWORKS=$(podman inspect matchgorithm-nginx 2>/dev/null | grep -A5 '"Networks"' | grep -c "edge-net\|auth-net" || echo "0")
    [ "$NGINX_NETWORKS" -ge 2 ]
    check_result $? "nginx connected to edge-net and auth-net"

    AXUM_NETWORKS=$(podman inspect matchgorithm-app 2>/dev/null | grep -A5 '"Networks"' | grep -c "edge-net" || echo "0")
    [ "$AXUM_NETWORKS" -ge 1 ]
    check_result $? "axum connected to edge-net"

    HASURA_NETWORKS=$(podman inspect matchgorithm-hasura 2>/dev/null | grep -A5 '"Networks"' | grep -c "auth-net\|db-net" || echo "0")
    [ "$HASURA_NETWORKS" -ge 2 ]
    check_result $? "hasura connected to auth-net and db-net"

    DIRECTUS_NETWORKS=$(podman inspect matchgorithm-directus 2>/dev/null | grep -A5 '"Networks"' | grep -c "auth-net\|db-net" || echo "0")
    [ "$DIRECTUS_NETWORKS" -ge 2 ]
    check_result $? "directus connected to auth-net and db-net"

    POSTGRES_NETWORKS=$(podman inspect matchgorithm-postgres 2>/dev/null | grep -A5 '"Networks"' | grep -c "db-net" || echo "0")
    [ "$POSTGRES_NETWORKS" -ge 1 ]
    check_result $? "postgres connected to db-net only"

    N8N_NETWORKS=$(podman inspect matchgorithm-n8n 2>/dev/null | grep -A5 '"Networks"' | grep -c "auth-net" || echo "0")
    [ "$N8N_NETWORKS" -ge 1 ]
    check_result $? "n8n connected to auth-net"

else
    warn "Services not running - skipping network assignment checks"
    warn "Run 'podman-compose up -d' and re-run this script"
fi

# Check firewall rules
echo ""
echo "🔍 Checking firewall rules..."

# Check if iptables rules exist for our networks
IPTABLES_RULES=$(iptables -L -v 2>/dev/null | grep -c "edge-net\|auth-net\|db-net" || echo "0")
if [ "$IPTABLES_RULES" -gt 0 ]; then
    check_result 0 "iptables rules configured for networks"
else
    check_result 1 "iptables rules configured for networks"
fi

# Check specific security rules
DROP_RULES=$(iptables -L -v 2>/dev/null | grep -c "DROP" || echo "0")
if [ "$DROP_RULES" -gt 0 ]; then
    check_result 0 "DROP rules configured for traffic control"
else
    check_result 1 "DROP rules configured for traffic control"
fi

LOG_RULES=$(iptables -L -v 2>/dev/null | grep -c "LOG" || echo "0")
if [ "$LOG_RULES" -gt 0 ]; then
    check_result 0 "LOG rules configured for auditing"
else
    check_result 1 "LOG rules configured for auditing"
fi

echo ""
echo "🎯 Network Security Verification Complete"
echo ""
echo "📋 Next Steps:"
echo "1. Start services: podman-compose up -d"
echo "2. Re-run verification: ./scripts/verify_network.sh"
echo "3. Test connectivity: curl http://localhost/api/health"
echo "4. Monitor logs: podman-compose logs -f"
echo ""
echo "🔧 Troubleshooting:"
echo "- Network issues: podman network prune && recreate networks"
echo "- Service issues: podman-compose down && podman-compose up -d"
echo "- Firewall issues: ./scripts/network_security.sh"
echo ""
echo "📞 For help: Check docs/network_setup.md"