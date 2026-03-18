#!/bin/bash
set -e

echo "🔍 MysteryiousHounslow Hybrid kNN Verification"
echo "📅 $(date) | 🕒 $(date +%H:%M) Europe/London"
echo ""

# Configuration
TEST_VECTOR=(0.1 0.2 0.3 0.4 0.5)
TEST_TOKEN="test_token_$(date +%s)"
SCORE=0
TOTAL=100

# 1. Environment Check (5%)
echo "1/10 🏗️ Environment Check (5%)"
if [ -d "/home/leo/Desktop/MysteryiousHounslow/" ] && \
   [ -f "/home/leo/Desktop/MysteryiousHounslow/pyproject.toml" ] && \
   ! ls /home/leo/Desktop/MysteryiousHounslow/ | grep -q "requirements.txt"; then
  echo "✅ Environment correct (5/5)"
  SCORE=$((SCORE + 5))
else
  echo "❌ Environment issues"
  exit 1
fi

# 2. PostGIS Setup (10%)
echo "2/10 🗃️ PostGIS Setup (10%)"
if psql -U postgres -d matchgorithm -c "\\dx" | grep -q pgvector && \
   psql -U postgres -d matchgorithm -c "\\di" | grep -q ivfflat && \
   psql -U postgres -d matchgorithm -c "\\df" | grep -q find_similar_items; then
  echo "✅ PostGIS setup complete (10/10)"
  SCORE=$((SCORE + 10))
else
  echo "❌ PostGIS setup incomplete"
  exit 1
fi

# 3. SQL Injection Protection (15%)
echo "3/10 🛡️ SQL Injection Protection (15%)"
if ! grep -r --include="*.py" --include="*.sql" \
     -E "EXECUTE.*'|\\|;|--|f\"" \
     /home/leo/Desktop/MysteryiousHounslow/; then
  echo "✅ No SQL injection patterns (15/15)"
  SCORE=$((SCORE + 15))
else
  echo "❌ SQL injection vulnerabilities found"
  exit 1
fi

# 4. Hybrid Endpoint (15%)
echo "4/10 🔗 Hybrid Endpoint (15%)"
if curl -s -X POST http://localhost:8001/api/v1/hybrid_knn \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer $TEST_TOKEN" \
     -d "{\"query_vector\": [0.1, 0.2, 0.3, 0.4, 0.5], \"max_results\": 3}" | \
   grep -q "matches"; then
  echo "✅ Hybrid endpoint functional (15/15)"
  SCORE=$((SCORE + 15))
else
  echo "❌ Hybrid endpoint failed"
  exit 1
fi

# 5. Feature Flag (5%)
echo "5/10 🚩 Feature Flag (5%)"
if curl -s -X POST http://localhost:8001/api/v1/hybrid_knn \
     -H "X-Feature-Flags: HYBRID_KNN=false" \
     -H "Content-Type: application/json" \
     -d '{"query_vector": [0.1, 0.2, 0.3, 0.4, 0.5]}' | \
   grep -q "400\|fallback"; then
  echo "✅ Feature flag working (5/5)"
  SCORE=$((SCORE + 5))
else
  echo "❌ Feature flag not working"
  exit 1
fi

# 6. Rate Limiting (10%)
echo "6/10 ⏱️ Rate Limiting (10%)"
if curl -s -o /dev/null -w "%{http_code}" \
     -X POST http://localhost:8001/api/v1/hybrid_knn \
     -H "Content-Type: application/json" \
     -d '{"query_vector": [0.1, 0.2, 0.3, 0.4, 0.5]}' | \
   grep -q "200" && \
   (for i in {1..101}; do
      curl -s -o /dev/null -w "%{http_code}" \
        -X POST http://localhost:8001/api/v1/hybrid_knn \
        -H "Content-Type: application/json" \
        -d '{"query_vector": [0.1, 0.2, 0.3, 0.4, 0.5]}' | \
        grep -q "429"
    done); then
  echo "✅ Rate limiting enforced (10/10)"
  SCORE=$((SCORE + 10))
else
  echo "❌ Rate limiting not working"
  exit 1
fi

# 7. Input Validation (10%)
echo "7/10 📋 Input Validation (10%)"
if curl -s -o /dev/null -w "%{http_code}" \
     -X POST http://localhost:8001/api/v1/hybrid_knn \
     -H "Content-Type: application/json" \
     -d '{"query_vector": [1000, 2000], "max_results": 101}' | \
   grep -q "422"; then
  echo "✅ Input validation working (10/10)"
  SCORE=$((SCORE + 10))
else
  echo "❌ Input validation failed"
  exit 1
fi

# 8. UK Compliance (10%)
echo "8/10 🇬🇧 UK Compliance (10%)"
if psql -U postgres -d matchgorithm -c "SHOW timezone" | grep -q "Europe/London" && \
   podman inspect matchgorithm_db | grep -q "MysteryiousHounslow" && \
   [ -f "/home/leo/Desktop/MysteryiousHounslow/docs/legal/privacy_policy.md" ]; then
  echo "✅ UK compliance verified (10/10)"
  SCORE=$((SCORE + 10))
else
  echo "❌ UK compliance issues"
  exit 1
fi

# 9. UV Compliance (10%)
echo "9/10 🐍 UV Compliance (10%)"
if [ -f "/home/leo/Desktop/MysteryiousHounslow/uv.lock" ] && \
   ! ls /home/leo/Desktop/MysteryiousHounslow/ | grep -q "requirements.txt"; then
  echo "✅ UV compliance verified (10/10)"
  SCORE=$((SCORE + 10))
else
  echo "❌ UV compliance issues"
  exit 1
fi

# 10. Performance (10%)
echo "10/10 ⚡ Performance (10%)"
START=$(date +%s%N)
curl -s -X POST http://localhost:8001/api/v1/hybrid_knn \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TEST_TOKEN" \
  -d '{"query_vector": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0], "max_results": 5}' >/dev/null
END=$(date +%s%N)
LATENCY=$(( (END - START) / 1000000 ))

if [ $LATENCY -lt 200 ]; then
  echo "✅ Performance acceptable: ${LATENCY}ms (10/10)"
  SCORE=$((SCORE + 10))
else
  echo "❌ Performance too slow: ${LATENCY}ms"
  exit 1
fi

# Final Score
echo ""
echo "🎯 Final Verification Score: ${SCORE}/100"

if [ $SCORE -eq 100 ]; then
  echo "🎉 ALL CHECKS PASSED! Hybrid kNN implementation is secure and compliant."
  echo ""
  echo "📋 Next Steps:"
  echo "1. Merge to main branch"
  echo "2. Deploy to staging for final testing"
  echo "3. Monitor performance metrics"
  echo "4. Prepare for production rollout"
else
  echo "❌ Some checks failed. Score: ${SCORE}/100"
  echo "Review failed checks above and fix issues."
  exit 1
fi