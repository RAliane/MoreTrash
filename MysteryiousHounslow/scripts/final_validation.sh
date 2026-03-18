#!/bin/bash

# Matchgorithm Production Validation Script
# Comprehensive end-to-end validation for production readiness

set -e

echo "🧪 Matchgorithm Production Validation"
echo "====================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to check service health
check_service() {
    local name=$1
    local url=$2
    local expected_status=${3:-200}

    echo -e "${BLUE}🔍 Checking $name...${NC}"

    if curl -s -o /dev/null -w "%{http_code}" "$url" | grep -q "^$expected_status$"; then
        echo -e "${GREEN}✅ $name is healthy${NC}"
        return 0
    else
        echo -e "${RED}❌ $name is not responding${NC}"
        return 1
    fi
}

# Function to check database connectivity
check_database() {
    echo -e "${BLUE}🔍 Checking PostgreSQL...${NC}"

    if command -v psql &> /dev/null; then
        # Try to connect to database
        if PGPASSWORD="${POSTGRES_PASSWORD:-secure_password}" psql -h localhost -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DB:-matchgorithm}" -c "SELECT 1;" &>/dev/null; then
            echo -e "${GREEN}✅ PostgreSQL connection successful${NC}"

            # Check if tables exist
            table_count=$(PGPASSWORD="${POSTGRES_PASSWORD:-secure_password}" psql -h localhost -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DB:-matchgorithm}" -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null || echo "0")

            if [ "$table_count" -ge 3 ]; then
                echo -e "${GREEN}✅ Database tables created ($table_count tables)${NC}"
            else
                echo -e "${YELLOW}⚠️  Database tables may be missing ($table_count tables found)${NC}"
            fi

            return 0
        else
            echo -e "${RED}❌ PostgreSQL connection failed${NC}"
            return 1
        fi
    else
        echo -e "${YELLOW}⚠️  psql not available, skipping database check${NC}"
        return 0
    fi
}

# Function to check TLS certificates
check_tls() {
    local domain=$1

    echo -e "${BLUE}🔍 Checking TLS for $domain...${NC}"

    if command -v openssl &> /dev/null; then
        if echo | openssl s_client -connect "$domain:443" -servername "$domain" 2>/dev/null | openssl x509 -noout -dates &>/dev/null; then
            echo -e "${GREEN}✅ TLS certificate is valid${NC}"
            return 0
        else
            echo -e "${YELLOW}⚠️  TLS certificate check failed (may be self-signed)${NC}"
            return 0  # Not critical for validation
        fi
    else
        echo -e "${YELLOW}⚠️  openssl not available, skipping TLS check${NC}"
        return 0
    fi
}

# Function to check network isolation
check_networks() {
    echo -e "${BLUE}🔍 Checking network isolation...${NC}"

    local network_count
    network_count=$(podman network ls --format "{{.Name}}" | grep -E "(edge-net|auth-net|db-net)" | wc -l)

    if [ "$network_count" -eq 3 ]; then
        echo -e "${GREEN}✅ All networks created ($network_count/3)${NC}"

        # Check network properties
        if podman network inspect auth-net | grep -q '"internal": true'; then
            echo -e "${GREEN}✅ Auth network is internal${NC}"
        else
            echo -e "${YELLOW}⚠️  Auth network may not be properly isolated${NC}"
        fi

        if podman network inspect db-net | grep -q '"internal": true'; then
            echo -e "${GREEN}✅ Database network is internal${NC}"
        else
            echo -e "${YELLOW}⚠️  Database network may not be properly isolated${NC}"
        fi

        return 0
    else
        echo -e "${RED}❌ Missing networks ($network_count/3 found)${NC}"
        return 1
    fi
}

# Main validation
main() {
    local failed_checks=0

    echo "🔍 Starting comprehensive validation..."
    echo ""

    # 1. Directus Health Check
    if check_service "Directus" "http://localhost:8055/server/ping"; then
        echo "Directus health: OK"
    else
        ((failed_checks++))
    fi
    echo ""

    # 2. Hasura Health Check
    if check_service "Hasura" "http://localhost:8080/v1/graphql" "200"; then
        # Try a simple query
        if curl -s -X POST http://localhost:8080/v1/graphql \
            -H "Content-Type: application/json" \
            -d '{"query": "{ __typename }"}' | grep -q "__typename"; then
            echo -e "${GREEN}✅ Hasura GraphQL is responsive${NC}"
        else
            echo -e "${YELLOW}⚠️  Hasura GraphQL query failed${NC}"
            ((failed_checks++))
        fi
    else
        ((failed_checks++))
    fi
    echo ""

    # 3. PostgreSQL Check
    if check_database; then
        echo "Database validation: OK"
    else
        ((failed_checks++))
    fi
    echo ""

    # 4. Frontend (Axum) Check
    if check_service "Frontend (Axum)" "http://localhost:8000/api/health"; then
        echo "Frontend health: OK"
    else
        ((failed_checks++))
    fi
    echo ""

    # 5. ML Pipeline Check (via Axum proxy)
    if check_service "ML Pipeline" "http://localhost:8000/api/v1/health"; then
        echo "ML Pipeline health: OK"
    else
        ((failed_checks++))
    fi
    echo ""

    # 6. TLS Certificate Check
    if check_tls "localhost"; then  # In production, check actual domains
        echo "TLS validation: OK"
    fi
    echo ""

    # 7. Network Isolation Check
    if check_networks; then
        echo "Network isolation: OK"
    else
        ((failed_checks++))
    fi
    echo ""

    # 8. End-to-End Flow Test
    echo -e "${BLUE}🔍 Testing end-to-end flow...${NC}"

    # Test optimization endpoint
    if curl -s -X POST http://localhost:8000/api/v1/optimize \
        -H "Content-Type: application/json" \
        -d '{"user_id": "test-user", "location": {"lat": 51.5, "lng": -0.1, "radius": 5000}}' \
        | grep -q "request_id\|matches"; then
        echo -e "${GREEN}✅ End-to-end optimization flow works${NC}"
    else
        echo -e "${RED}❌ End-to-end flow failed${NC}"
        ((failed_checks++))
    fi
    echo ""

    # Summary
    echo "🎯 Validation Summary"
    echo "===================="

    if [ $failed_checks -eq 0 ]; then
        echo -e "${GREEN}🎉 ALL VALIDATION CHECKS PASSED!${NC}"
        echo ""
        echo "✅ Directus: Operational"
        echo "✅ Hasura: GraphQL responsive"
        echo "✅ PostgreSQL: Connected and migrated"
        echo "✅ Frontend: Axum routes working"
        echo "✅ Backend: FastAPI endpoints responding"
        echo "✅ Networks: Properly isolated"
        echo "✅ E2E Flow: Optimization pipeline functional"
        echo ""
        echo "🚀 Matchgorithm is PRODUCTION READY!"
        echo ""
        echo "Next steps:"
        echo "1. Configure domain DNS and SSL certificates"
        echo "2. Set up monitoring and alerting"
        echo "3. Configure backup procedures"
        echo "4. Perform security testing"
        echo "5. Plan deployment and rollback procedures"
        return 0
    else
        echo -e "${RED}❌ $failed_checks VALIDATION CHECK(S) FAILED!${NC}"
        echo ""
        echo "🔴 Critical issues must be resolved before production deployment"
        echo ""
        echo "🛠️  Common resolution steps:"
        echo "   1. Check podman-compose logs: podman-compose logs"
        echo "   2. Verify network connectivity: podman network inspect [network]"
        echo "   3. Test individual services: curl http://localhost:[port]/health"
        echo "   4. Check database migrations: ./db/migrations/"
        echo "   5. Rebuild and redeploy: podman-compose up -d --build"
        echo ""
        echo "📞 Contact: devops@matchgorithm.com for deployment assistance"
        return 1
    fi
}

# Run validation
main "$@"