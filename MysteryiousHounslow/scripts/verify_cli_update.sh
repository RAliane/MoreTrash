#!/bin/bash
set -e

echo "🔍 Matchgorithm CLI Update Verification"
echo "📅 $(date) | 🕒 $(date +%H:%M) Europe/London"
echo ""

SCORE=0
TOTAL=100

# 1. Check only one CLI exists (10%)
echo "1/10 🧹 Checking CLI cleanup..."
if [ -d "/home/leo/Desktop/MysteryiousHounslow/matchgorithm-cli" ] && \
   [ $(find /home/leo/Desktop/MysteryiousHounslow/ -type d -name "*cli*" | wc -l) -eq 1 ]; then
  echo "✅ Only one CLI directory exists (10/10)"
  SCORE=$((SCORE + 10))
else
  echo "❌ Multiple CLI directories found"
  find /home/leo/Desktop/MysteryiousHounslow/ -type d -name "*cli*"
  exit 1
fi

# 2. Check CLI structure (10%)
echo "2/10 🏗️ Checking CLI structure..."
if [ -f "/home/leo/Desktop/MysteryiousHounslow/matchgorithm-cli/src/main.rs" ] && \
   [ -d "/home/leo/Desktop/MysteryiousHounslow/matchgorithm-cli/src/commands" ] && \
   [ -f "/home/leo/Desktop/MysteryiousHounslow/matchgorithm-cli/Cargo.toml" ]; then
  echo "✅ CLI structure correct (10/10)"
  SCORE=$((SCORE + 10))
else
  echo "❌ CLI structure incomplete"
  ls -la /home/leo/Desktop/MysteryiousHounslow/matchgorithm-cli/
  exit 1
fi

# 3. Check FastAPI integration (10%)
echo "3/10 🔗 Checking FastAPI integration..."
if grep -q "fastapi" /home/leo/Desktop/MysteryiousHounslow/matchgorithm-cli/src/commands/mod.rs && \
   [ -f "/home/leo/Desktop/MysteryiousHounslow/matchgorithm-cli/src/commands/fastapi.rs" ]; then
  echo "✅ FastAPI integration present (10/10)"
  SCORE=$((SCORE + 10))
else
  echo "❌ FastAPI integration missing"
  exit 1
fi

# 4. Check hybrid kNN commands (15%)
echo "4/10 🧮 Checking hybrid kNN commands..."
if [ -f "/home/leo/Desktop/MysteryiousHounslow/matchgorithm-cli/src/commands/knn.rs" ] && \
   grep -q "hybrid_knn" /home/leo/Desktop/MysteryiousHounslow/matchgorithm-cli/src/commands/knn.rs; then
  echo "✅ Hybrid kNN commands present (15/15)"
  SCORE=$((SCORE + 15))
else
  echo "❌ Hybrid kNN commands missing"
  exit 1
fi

# 5. Check documentation updates (15%)
echo "5/10 📚 Checking documentation updates..."
if [ -f "/home/leo/Desktop/MysteryiousHounslow/docs/cli/commands.md" ] && \
   [ -f "/home/leo/Desktop/MysteryiousHounslow/docs/cli/examples.md" ] && \
   [ -f "/home/leo/Desktop/MysteryiousHounslow/docs/architecture/cli.md" ]; then
  echo "✅ Documentation updated (15/15)"
  SCORE=$((SCORE + 15))
else
  echo "❌ Documentation missing"
  ls -la /home/leo/Desktop/MysteryiousHounslow/docs/cli/
  exit 1
fi

# 6. Check UK compliance docs (10%)
echo "6/10 🇬🇧 Checking UK compliance documentation..."
if [ -f "/home/leo/Desktop/MysteryiousHounslow/docs/compliance/uk_cli_compliance.md" ] && \
   [ -f "/home/leo/Desktop/MysteryiousHounslow/docs/compliance/cli_security.md" ]; then
  echo "✅ UK compliance docs present (10/10)"
  SCORE=$((SCORE + 10))
else
  echo "❌ UK compliance docs missing"
  exit 1
fi

# 7. Check UV compliance (10%)
echo "7/10 🐍 Checking UV package management..."
if [ -f "/home/leo/Desktop/MysteryiousHounslow/matchgorithm-cli/Cargo.toml" ] && \
   ! grep -q "requirements.txt\|poetry\|pip" /home/leo/Desktop/MysteryiousHounslow/matchgorithm-cli/Cargo.toml && \
   grep -q "uv" /home/leo/Desktop/MysteryiousHounslow/README.md; then
  echo "✅ UV compliance verified (10/10)"
  SCORE=$((SCORE + 10))
else
  echo "❌ UV compliance issues"
  exit 1
fi

# 8. Check CLI build (10%)
echo "8/10 🏗️ Checking CLI build..."
cd /home/leo/Desktop/MysteryiousHounslow/matchgorithm-cli && \
uv toolchain install stable && \
cargo build --release
if [ $? -eq 0 ]; then
  echo "✅ CLI builds successfully (10/10)"
  SCORE=$((SCORE + 10))
else
  echo "❌ CLI build failed"
  exit 1
fi

# 9. Test FastAPI integration (10%)
echo "9/10 🔗 Testing FastAPI integration..."
cd /home/leo/Desktop/MysteryiousHounslow/matchgorithm-cli && \
cargo test -- --nocapture | grep -E "test_fastapi_.*ok"
if [ $? -eq 0 ]; then
  echo "✅ FastAPI integration tests pass (10/10)"
  SCORE=$((SCORE + 10))
else
  echo "❌ FastAPI tests failed"
  exit 1
fi

# Final Score
echo ""
echo "🎯 Final Verification Score: ${SCORE}/100"

if [ $SCORE -eq 100 ]; then
  echo "🎉 ALL CHECKS PASSED! Documentation and CLI update complete."
  echo ""
  echo "📋 Next Steps:"
  echo "1. Test CLI with: cargo run -- --help"
  echo "2. Verify FastAPI integration: matchgorithm fastapi status"
  echo "3. Test hybrid kNN: matchgorithm knn test --vector 0.1,0.2,0.3,0.4,0.5"
  echo "4. Check UK compliance: matchgorithm security uk"
else
  echo "❌ Some checks failed. Score: ${SCORE}/100"
  echo "Review failed checks above and fix issues."
  exit 1
fi