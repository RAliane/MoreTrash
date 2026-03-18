#!/bin/bash
set -e

echo "🛡️ Automated SQL Injection Tests"

FAILURES=0

# Test 1: String concatenation
echo "1/4 Testing string concatenation..."
RESPONSE=$(curl -s -w "%{http_code}" -o /dev/null \
  -X POST http://localhost:8001/api/v1/hybrid_knn \
  -H "Content-Type: application/json" \
  -d '{"query_vector": [0.1, 0.2], "geo_filter": {"$nefarious": "1; DROP TABLE items; --"}}')

if [ "$RESPONSE" -ne "422" ]; then
  echo "❌ String concatenation test failed (HTTP $RESPONSE)"
  FAILURES=$((FAILURES + 1))
else
  echo "✅ String concatenation test passed"
fi

# Test 2: SQL comment injection
echo "2/4 Testing SQL comment injection..."
RESPONSE=$(curl -s -w "%{http_code}" -o /dev/null \
  -X POST http://localhost:8001/api/v1/hybrid_knn \
  -H "Content-Type: application/json" \
  -d '{"query_vector": [0.1, 0.2], "business_rules": {"category": "test'"'"' OR '"'"'1'"'"'='"'"'1"}}')

if [ "$RESPONSE" -ne "200" ]; then
  echo "❌ SQL comment test failed (HTTP $RESPONSE)"
  FAILURES=$((FAILURES + 1))
else
  echo "✅ SQL comment test passed"
fi

# Test 3: Union-based injection
echo "3/4 Testing union-based injection..."
RESPONSE=$(curl -s -w "%{http_code}" -o /dev/null \
  -X POST http://localhost:8001/api/v1/hybrid_knn \
  -H "Content-Type: application/json" \
  -d '{"query_vector": [0.1, 0.2], "max_results": "3 UNION SELECT 1,2,3,4,5"}')

if [ "$RESPONSE" -ne "422" ]; then
  echo "❌ Union-based injection test failed (HTTP $RESPONSE)"
  FAILURES=$((FAILURES + 1))
else
  echo "✅ Union-based injection test passed"
fi

# Test 4: Boolean-based blind
echo "4/4 Testing boolean-based blind injection..."
RESPONSE=$(curl -s -w "%{http_code}" -o /dev/null \
  -X POST http://localhost:8001/api/v1/hybrid_knn \
  -H "Content-Type: application/json" \
  -d '{"query_vector": [0.1, 0.2], "geo_filter": {"latitude": "1 AND 1=1"}}')

if [ "$RESPONSE" -ne "200" ]; then
  echo "❌ Boolean-based injection test failed (HTTP $RESPONSE)"
  FAILURES=$((FAILURES + 1))
else
  echo "✅ Boolean-based injection test passed"
fi

if [ $FAILURES -gt 0 ]; then
  echo "❌ $FAILURES SQL injection vulnerabilities detected"
  exit 1
else
  echo "✅ All SQL injection tests passed"
fi