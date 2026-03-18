#!/bin/bash

# Matchgorithm DevSecOps Security Scan Suite
# Runs comprehensive security scans locally

set -e

echo "🔒 Matchgorithm DevSecOps Security Scan Suite"
echo "============================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to check if tool is installed
check_tool() {
    local tool=$1
    local install_cmd=$2

    if ! command -v "$tool" &> /dev/null; then
        echo -e "${YELLOW}⚠️  $tool not found${NC}"
        echo -e "${BLUE}Install with: $install_cmd${NC}"
        return 1
    else
        echo -e "${GREEN}✅ $tool found${NC}"
        return 0
    fi
}

# Function to run scan with error handling
run_scan() {
    local scan_name=$1
    local command=$2

    echo -e "\n${BLUE}🔍 Running $scan_name...${NC}"

    if eval "$command"; then
        echo -e "${GREEN}✅ $scan_name passed${NC}"
        return 0
    else
        echo -e "${RED}❌ $scan_name failed${NC}"
        return 1
    fi
}

# Check for hardcoded secrets
check_secrets() {
    echo -e "\n${BLUE}🔍 Checking for hardcoded secrets...${NC}"

    local secret_files
    secret_files=$(find . -name "*.env*" -type f -exec grep -l "password\|secret\|key\|token" {} \; 2>/dev/null | grep -v .git || true)

    if [ -n "$secret_files" ]; then
        echo -e "${RED}❌ Hardcoded secrets found in:${NC}"
        echo "$secret_files"
        return 1
    else
        echo -e "${GREEN}✅ No hardcoded secrets found${NC}"
        return 0
    fi
}

# Main scanning function
main() {
    local failed_scans=0

    echo "🛠️  Checking required tools..."
    echo "------------------------------"

    # Check Rust tools
    check_tool "cargo" "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh"
    check_tool "cargo-audit" "cargo install cargo-audit"

    # Check Python tools
    check_tool "python3" "apt install python3"
    check_tool "pip" "apt install python3-pip"

    # Check container tools
    check_tool "podman" "apt install podman"
    # Trivy check is optional

    echo -e "\n📊 Running Security Scans..."
    echo "============================"

    # 1. Secret scanning
    if run_scan "Secret Detection" "gitleaks detect --source=./ --report-format=json --report-path=docs/gitleaks_report.json"; then
        echo "✅ Secret scan passed"
    else
        ((failed_scans++))
    fi

    # 2. Rust security scans
    if run_scan "Cargo Audit" "cargo audit --json > docs/cargo_audit_report.json"; then
        echo "✅ Cargo audit passed"
    else
        ((failed_scans++))
    fi

    if run_scan "Clippy" "cargo clippy -- -D warnings"; then
        echo "✅ Clippy passed"
    else
        ((failed_scans++))
    fi

    # 3. Python security scans
    if run_scan "Bandit (Python SAST)" "pip install bandit && bandit -r fastapi_xgboost_optimizer/app/ -f json -o docs/bandit_report.json"; then
        echo "✅ Bandit passed"
    else
        ((failed_scans++))
    fi

    if run_scan "Safety (Python deps)" "pip install safety && cd fastapi_xgboost_optimizer && safety check --full-report --json > ../docs/safety_report.json"; then
        echo "✅ Safety passed"
    else
        ((failed_scans++))
    fi

    # 4. Container security (if image exists)
    if podman images | grep -q matchgorithm; then
        if run_scan "Container Scanning" "trivy image --exit-code 1 --severity CRITICAL --format json -o docs/trivy_report.json matchgorithm:latest"; then
            echo "✅ Container scan passed"
        else
            ((failed_scans++))
        fi
    else
        echo -e "\n${YELLOW}⚠️  No container image found - skipping container scan${NC}"
        echo -e "${BLUE}Build image first: podman build -t matchgorithm:latest .${NC}"
    fi

    # Summary
    echo -e "\n🎯 Scan Summary"
    echo "=============="

    if [ $failed_scans -eq 0 ]; then
        echo -e "${GREEN}🎉 All security scans passed!${NC}"
        echo ""
        echo "✅ Code is ready for production deployment"
        echo "✅ No security vulnerabilities detected"
        echo "✅ No hardcoded secrets found"
        return 0
    else
        echo -e "${RED}❌ $failed_scans security scan(s) failed${NC}"
        echo ""
        echo "🔴 Security issues must be resolved before deployment"
        echo "🔴 Check the output above for specific failures"
        echo ""
        echo "🛠️  Common fixes:"
        echo "   - Remove hardcoded secrets from .env files"
        echo "   - Update vulnerable dependencies"
        echo "   - Fix code security issues flagged by Bandit/Clippy"
        echo "   - Rebuild container image after fixes"
        return 1
    fi
}

# Run main function
main "$@"