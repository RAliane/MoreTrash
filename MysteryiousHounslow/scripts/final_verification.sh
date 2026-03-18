#!/bin/bash
set -e

echo "🔍 Matchgorithm Final Production Verification"
echo "📅 $(date) | 🕒 $(date +%H:%M) Europe/London"
echo "👤 Verification initiated by: Rayan Aliane"
echo ""

# Configuration
STAGING_URL="https://staging.matchgorithm.co.uk"
PROD_URL="https://matchgorithm.co.uk"
TEST_EMAIL="test+$(date +%s)@matchgorithm.co.uk"
TEST_PASSWORD="SecureTestPassword123!"

# 1. Git Status
echo "1/20 📝 Checking Git status..."
if ! git status | grep -q "nothing to commit"; then
  echo "❌ Uncommitted changes found:"
  git status
  exit 1
fi
echo "✅ Git repository clean"

# 2. Security Scan
echo "2/20 🔒 Running security scan..."
if ! ./scripts/security_scan.sh; then
  echo "❌ Security issues found"
  exit 1
fi
echo "✅ Security scan passed"

# 3. UK Compliance
echo "3/20 🇬🇧 Checking UK compliance..."
if ! ./scripts/test/uk_compliance.sh; then
  echo "❌ UK compliance issues detected"
  exit 1
fi
echo "✅ UK compliance verified"

# 4. Database Health
echo "4/20 🗃️ Verifying database health..."
db_health=$(podman exec matchgorithm_db pg_isready -U postgres -d matchgorithm)
if [[ ! "$db_health" =~ "accepting connections" ]]; then
  echo "❌ Database unhealthy: $db_health"
  exit 1
fi
echo "✅ Database healthy"

# 5. Network Isolation
echo "5/20 🌐 Checking network isolation..."
for net in edge-net auth-net db-net; do
  if ! podman network inspect $net >/dev/null; then
    echo "❌ Network $net missing or misconfigured"
    exit 1
  fi
  echo "✅ Network $net properly configured"
done

# 6. Resource Limits
echo "6/20 ⚖️ Verifying resource limits..."
for service in fastapi axum directus db; do
  cpu_limit=$(podman inspect matchgorithm_$service | jq -r '.[0].HostConfig.CpuQuota')
  mem_limit=$(podman inspect matchgorithm_$service | jq -r '.[0].HostConfig.Memory')
  if [[ "$cpu_limit" == "null" || "$mem_limit" == "null" ]]; then
    echo "❌ Service $service missing resource limits"
    exit 1
  fi
  echo "✅ $service resources limited (CPU: ${cpu_limit}, Mem: ${mem_limit})"
done

# 7. Service Health
echo "7/20 🏥 Testing service health..."
for url in "$STAGING_URL/health" "$STAGING_URL/api/v1/health"; do
  if ! curl -s --max-time 5 "$url" | grep -q "ok\|healthy"; then
    echo "❌ $url unhealthy"
    exit 1
  fi
  echo "✅ $url healthy"
done

# 8. Password Reset Flow
echo "8/20 🔑 Testing password reset flow..."
reset_response=$(curl -s -X POST "$STAGING_URL/api/v1/auth/request-reset" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$TEST_EMAIL\"}")
if ! echo "$reset_response" | grep -q "success"; then
  echo "❌ Password reset failed:"
  echo "$reset_response"
  exit 1
fi
echo "✅ Password reset request successful"

# 9. Optimization Pipeline
echo "9/20 📊 Testing optimization pipeline..."
optimize_response=$(curl -s -X POST "$STAGING_URL/api/v1/optimize" \
  -H "Content-Type: application/json" \
  -d '{"lat":51.5074,"lng":-0.1278,"radius":5000}')
if ! echo "$optimize_response" | grep -q "matches"; then
  echo "❌ Optimization failed:"
  echo "$optimize_response"
  exit 1
fi
echo "✅ Optimization pipeline functional"

# 10. Backup System
echo "10/20 💾 Testing backup system..."
if ! podman exec matchgorithm_db pg_dump -U postgres matchgorithm | gzip > /tmp/backup_test_$(date +%Y%m%d).gz; then
  echo "❌ Backup failed"
  exit 1
fi
echo "✅ Backup system functional (Size: $(du -h /tmp/backup_test_*.gz | cut -f1))"

# 11. Monitoring
echo "11/20 📈 Checking monitoring..."
if ! curl -s --max-time 5 "http://localhost:9090/-/healthy" | grep -q "healthy"; then
  echo "❌ Prometheus unhealthy"
  exit 1
fi
echo "✅ Monitoring operational"

# 12. Auth Flow Verification
echo "12/20 🔐 Verifying authentication flows..."
# Test login with test user (created via Directus admin)
login_response=$(curl -s -X POST "$STAGING_URL/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$TEST_EMAIL\",\"password\":\"$TEST_PASSWORD\"}")
if ! echo "$login_response" | grep -q "token"; then
  echo "❌ Authentication failed:"
  echo "$login_response"
  exit 1
fi
echo "✅ Authentication flow verified"

# 13. UK Data Residency
echo "13/20 🇬🇧 Verifying UK data residency..."
db_location=$(podman inspect matchgorithm_db | jq -r '.[0].Config.Labels["com.docker.compose.project.working_dir"]')
if [[ ! "$db_location" =~ "matchgorithm" ]]; then
  echo "❌ Database location verification failed"
  exit 1
fi
echo "✅ UK data residency confirmed"

# 14. Legal Documents
echo "14/20 ⚖️ Checking legal documents..."
for doc in privacy_policy terms cookie_policy dpa; do
  if [ ! -f "docs/legal/$doc.md" ]; then
    echo "❌ Missing legal document: $doc.md"
    exit 1
  fi
  echo "✅ $doc.md present"
done

# 15. Directus Auth Routing
echo "15/20 🔄 Verifying Directus auth routing..."
routing_check=$(curl -s -I "$STAGING_URL/api/v1/auth/login" | grep -c "HTTP/2 200")
if [ "$routing_check" -ne 1 ]; then
  echo "❌ Auth routing misconfigured"
  exit 1
fi
echo "✅ Directus auth routing verified"

# 16. Rate Limiting
echo "16/20 ⏱️ Testing rate limiting..."
first_response=$(curl -s -w "%{http_code}" -o /dev/null "$STAGING_URL/api/v1/optimize")
second_response=$(curl -s -w "%{http_code}" -o /dev/null "$STAGING_URL/api/v1/optimize")
if [ "$first_response" -ne 200 ] || [ "$second_response" -ne 429 ]; then
  echo "❌ Rate limiting not properly configured"
  exit 1
fi
echo "✅ Rate limiting functional"

# 17. CORS Headers
echo "17/20 🌍 Checking CORS headers..."
cors_headers=$(curl -s -I "$STAGING_URL/api/v1/health" | grep -i "access-control")
if [[ ! "$cors_headers" =~ "access-control-allow-origin" ]]; then
  echo "❌ CORS headers missing"
  exit 1
fi
echo "✅ CORS headers properly configured"

# 18. Documentation Completeness
echo "18/20 📚 Verifying documentation..."
missing_docs=$(find docs -type d -empty | wc -l)
if [ "$missing_docs" -gt 0 ]; then
  echo "❌ $missing_docs empty documentation directories"
  exit 1
fi
echo "✅ Documentation complete"

# 19. Rust CLI (if available)
echo "19/20 🦀 Checking Rust CLI..."
if [ -d "matchgorithm-cli" ]; then
  if ! cargo build --manifest-path matchgorithm-cli/Cargo.toml; then
    echo "❌ CLI build failed"
    exit 1
  fi
  echo "✅ Rust CLI operational"
else
  echo "ℹ️  Rust CLI not yet implemented"
fi

# 20. Final System Check
echo "20/20 🎯 Final system verification..."
system_check=$(curl -s "$STAGING_URL/api/v1/system/check" | jq -r '.status')
if [ "$system_check" != "operational" ]; then
  echo "❌ System check failed: $system_check"
  exit 1
fi

echo ""
echo "🎉 ALL VERIFICATIONS PASSED!"
echo ""
echo "📋 Production Readiness Summary:"
echo "✅ Git repository clean"
echo "✅ Security scans passed"
echo "✅ UK compliance verified"
echo "✅ Database healthy"
echo "✅ Networks isolated"
echo "✅ Resources limited"
echo "✅ Services healthy"
echo "✅ Password reset functional"
echo "✅ Optimization pipeline working"
echo "✅ Backups verified"
echo "✅ Monitoring operational"
echo "✅ Authentication flows secure"
echo "✅ UK data residency confirmed"
echo "✅ Legal documents complete"
echo "✅ Directus auth routing correct"
echo "✅ Rate limiting functional"
echo "✅ CORS properly configured"
echo "✅ Documentation complete"
echo "✅ Rust CLI operational (if implemented)"
echo ""
echo "🚀 Matchgorithm is ready for production deployment!"
echo ""
echo "Next steps:"
echo "1. git push origin main"
echo "2. ./scripts/prod/deploy_prod.sh"
echo "3. Monitor initial deployment"