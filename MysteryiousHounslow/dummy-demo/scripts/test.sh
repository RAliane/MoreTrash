#!/bin/bash

echo "🧪 Testing Dummy Demo Functionality"
echo "=================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
PASSED=0
FAILED=0

# Test function
test_endpoint() {
    local url=$1
    local expected_status=${2:-200}
    local description=$3

    echo -n "Testing $description... "

    if curl -s -o /dev/null -w "%{http_code}" "$url" | grep -q "$expected_status"; then
        echo -e "${GREEN}✅ PASSED${NC}"
        ((PASSED++))
    else
        echo -e "${RED}❌ FAILED${NC}"
        ((FAILED++))
    fi
}

# Test database connection
test_database() {
    echo -n "Testing database connection... "

    if docker-compose exec -T db pg_isready -U postgres >/dev/null 2>&1; then
        echo -e "${GREEN}✅ PASSED${NC}"
        ((PASSED++))
    else
        echo -e "${RED}❌ FAILED${NC}"
        ((FAILED++))
    fi
}

# Test vector search
test_vector_search() {
    echo -n "Testing vector search... "

    response=$(curl -s -X POST http://localhost:3000/vector-search \
      -H "Content-Type: application/json" \
      -d '{"query_vector": [0.1, 0.2, 0.3], "max_results": 2}')

    if echo "$response" | grep -q "similarity"; then
        echo -e "${GREEN}✅ PASSED${NC}"
        ((PASSED++))
    else
        echo -e "${RED}❌ FAILED${NC}"
        ((FAILED++))
    fi
}

# Run tests
echo "🔍 Running service checks..."

# Test web app endpoints
test_endpoint "http://localhost:3000/" 200 "web app root"
test_endpoint "http://localhost:3000/health" 200 "web app health"
test_endpoint "http://localhost:3000/items" 200 "web app items"

# Test Directus
test_endpoint "http://localhost:8056/server/health" 200 "Directus health"

# Test database
test_database

# Test vector search
test_vector_search

echo ""
echo "📊 Test Results:"
echo "  ✅ Passed: $PASSED"
echo "  ❌ Failed: $FAILED"
echo "  📈 Success Rate: $(( (PASSED * 100) / (PASSED + FAILED) ))%"

if [ $FAILED -eq 0 ]; then
    echo -e "\n${GREEN}🎉 All tests passed! Dummy demo is working correctly.${NC}"
    echo ""
    echo "🌐 Access URLs:"
    echo "  📱 Web App: http://localhost:3000"
    echo "  🛠️ Directus: http://localhost:8056"
    echo "  🐘 Database: localhost:5433"
    echo ""
    echo "🔍 Test the vector search:"
    echo 'curl -X POST http://localhost:3000/vector-search -H "Content-Type: application/json" -d '\''{"query_vector": [0.1, 0.2, 0.3], "max_results": 3}'\'
else
    echo -e "\n${RED}❌ Some tests failed. Check the services and try again.${NC}"
    echo ""
    echo "🔧 Troubleshooting:"
    echo "  docker-compose logs"
    echo "  docker-compose restart"
    echo "  ./scripts/start.sh"
fi