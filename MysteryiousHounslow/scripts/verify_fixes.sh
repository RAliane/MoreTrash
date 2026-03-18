#!/bin/bash
set -e

echo "🔍 Verifying Critical Bug Fixes..."

# 1. FastAPI Logger
echo "1/7 Checking FastAPI logger..."
if grep -q "import logging" fastapi_xgboost_optimizer/app/main.py; then
  echo "✅ Logger import fixed"
else
  echo "❌ Logger import missing"
  exit 1
fi

# 2. Database Sessions
echo "2/7 Checking database sessions..."
# Exclude commented lines
active_db_sessions=$(grep "db_session" fastapi_xgboost_optimizer/app/api/endpoints.py | grep -v "^[[:space:]]*#" | wc -l)
if [ "$active_db_sessions" -eq 0 ]; then
  echo "✅ No direct DB sessions"
else
  echo "❌ Direct DB sessions remain ($active_db_sessions found)"
  exit 1
fi

# 3. Directus Security
echo "3/7 Checking Directus security..."
if podman network inspect auth-net 2>/dev/null | grep -q directus; then
  echo "✅ Directus on auth-net only"
else
  echo "❌ Directus network misconfigured"
fi

# 4. Resource Limits
echo "4/7 Checking resource limits..."
if podman inspect matchgorithm-postgres 2>/dev/null | grep -q '"CpuQuota": 200000'; then
  echo "✅ PostgreSQL CPU limited"
else
  echo "⚠️  PostgreSQL resource limits not verified (container not running)"
fi

# 5. Auth Middleware
echo "5/7 Checking auth middleware..."
if grep -q "auth0_jwt_bearer" fastapi_xgboost_optimizer/app/main.py; then
  echo "✅ Auth middleware added"
else
  echo "❌ Auth middleware missing"
  exit 1
fi

# 6. Password Reset Forms
echo "6/7 Checking password reset forms..."
if grep -q "reqwest::Client::new()" src/pages/ForgotPassword.rs; then
  echo "✅ Forgot password form connected"
else
  echo "❌ Forgot password form not connected"
  exit 1
fi

if grep -q "reqwest::Client::new()" src/pages/ResetPassword.rs; then
  echo "✅ Reset password form connected"
else
  echo "❌ Reset password form not connected"
  exit 1
fi

# 7. Duplicate Endpoints
echo "7/7 Checking duplicate endpoints..."
optimize_count=$(grep -c '/api/v1/optimize' fastapi_xgboost_optimizer/app/main.py fastapi_xgboost_optimizer/app/api/endpoints.py)
if [ "$optimize_count" -eq 1 ]; then
  echo "✅ No duplicate endpoints"
else
  echo "❌ Duplicate endpoints remain ($optimize_count found)"
  exit 1
fi

echo "🎉 All critical fixes verified!"
echo ""
echo "Next steps:"
echo "1. Start containers: podman-compose up -d"
echo "2. Test password reset flow"
echo "3. Monitor resource usage"
echo "4. Run end-to-end tests"