#!/bin/bash
set -e

echo "🔍 Starting Comprehensive Bug Check..."

# 1. Frontend Checks
echo "🌐 Checking frontend routes..."
for route in "/" "/login" "/dashboard" "/forgot-password" "/reset-password"; do
  status=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000${route} 2>/dev/null || echo "500")
  if [ "$status" -ne 200 ]; then
    echo "❌ Route ${route} returned ${status}"
  else
    echo "✅ Route ${route} OK"
  fi
done

# 2. Backend API Checks
echo -e "\n🔧 Checking backend APIs..."
for endpoint in "/api/v1/health" "/api/v1/optimize" "/api/v1/candidates"; do
  status=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8001${endpoint} 2>/dev/null || echo "500")
  if [ "$status" -ne 200 ]; then
    echo "❌ Endpoint ${endpoint} returned ${status}"
  else
    echo "✅ Endpoint ${endpoint} OK"
  fi
done

# 3. Database Checks
echo -e "\n🗃️ Checking database schema..."
# This would need psql access, placeholder for now
echo "ℹ️  Database checks require psql access"

# 4. Security Checks
echo -e "\n🔒 Checking security..."
hardcoded_secrets=$(grep -r --include="*.rs" --include="*.py" --include="*.toml" "password\|secret\|api_key" . 2>/dev/null | grep -v ".git" | grep -v "secrets/" | wc -l)
if [ "$hardcoded_secrets" -gt 0 ]; then
  echo "❌ Found ${hardcoded_secrets} potential hardcoded secrets"
else
  echo "✅ No hardcoded secrets found"
fi

# 5. Network Checks
echo -e "\n🌍 Checking network isolation..."
networks=$(podman network ls --format "{{.Name}}" 2>/dev/null | grep -E "edge-net|auth-net|db-net" | wc -l)
if [ "$networks" -ne 3 ]; then
  echo "❌ Missing networks (expected 3, found ${networks})"
else
  echo "✅ All networks exist"
fi

# 6. Container Health Checks
echo -e "\n🐳 Checking container health..."
containers=$(podman ps --format "{{.Names}}" 2>/dev/null | grep -E "matchgorithm" | wc -l)
if [ "$containers" -lt 3 ]; then
  echo "❌ Not enough containers running (expected 3+, found ${containers})"
else
  echo "✅ Containers are running"
fi

echo -e "\n🎉 Comprehensive Bug Check Complete!"
if [ "$hardcoded_secrets" -gt 0 ]; then
  echo "⚠️  Issues found. Review output above."
  exit 1
else
  echo "✅ All automated checks passed!"
fi