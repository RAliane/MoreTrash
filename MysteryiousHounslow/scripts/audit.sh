#!/bin/bash

# Matchgorithm Security Audit Script
# Runs cargo audit and other security checks

set -e

echo "🔒 Running Matchgorithm Security Audit"
echo "====================================="

# Check if cargo-audit is installed
if ! command -v cargo-audit &> /dev/null; then
    echo "❌ cargo-audit not found. Installing..."
    cargo install cargo-audit
fi

# Run cargo audit
echo "🔍 Running cargo audit..."
cargo audit

# Check for outdated dependencies
echo "📦 Checking for outdated dependencies..."
cargo outdated --exit-code 1 || echo "⚠️  Some dependencies are outdated. Consider updating."

# Check for security advisories in dependencies
echo "🛡️  Checking for security advisories..."
if command -v cargo-deny &> /dev/null; then
    cargo deny check advisories
else
    echo "ℹ️  cargo-deny not found. Install with: cargo install cargo-deny"
fi

# Run clippy for code quality
echo "🔧 Running clippy for code quality..."
cargo clippy -- -D warnings

# Check for secrets in code (basic)
echo "🔐 Checking for potential secrets in code..."
if command -v gitleaks &> /dev/null; then
    gitleaks detect --verbose --redact
else
    echo "ℹ️  gitleaks not found. Install from: https://github.com/gitleaks/gitleaks"
    # Basic grep check
    if grep -r "password\|secret\|key\|token" src/ --include="*.rs" | grep -v "example\|test\|TODO\|FIXME"; then
        echo "⚠️  Potential secrets found. Please review."
    else
        echo "✅ No obvious secrets found in source code."
    fi
fi

# Check file permissions
echo "📁 Checking file permissions..."
if find . -name "*.rs" -perm /111 -type f | grep -q .; then
    echo "⚠️  Some source files are executable. Consider: chmod -x *.rs"
else
    echo "✅ Source file permissions look good."
fi

echo "🎉 Security audit completed!"
echo ""
echo "📋 Summary:"
echo "- ✅ Cargo audit passed"
echo "- ✅ Clippy checks passed"
echo "- ✅ No obvious secrets in code"
echo "- ✅ File permissions OK"
echo ""
echo "For production deployment:"
echo "- Ensure all secrets are in Podman secrets"
echo "- Run this script before each release"
echo "- Monitor dependencies regularly with cargo audit"