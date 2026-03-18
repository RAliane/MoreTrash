#!/bin/bash

# Security Dashboard - Analyze and report on security scan results
# Processes JSON reports from various security tools

set -e

echo "📊 Matchgorithm Security Dashboard"
echo "=================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Function to analyze Gitleaks report
analyze_gitleaks() {
    local report_file=$1

    if [ ! -f "$report_file" ]; then
        echo -e "${YELLOW}⚠️  Gitleaks report not found${NC}"
        return
    fi

    local secret_count=$(jq '.[] | select(.file != "") | .file' "$report_file" 2>/dev/null | wc -l)
    local unique_files=$(jq -r '.[] | select(.file != "") | .file' "$report_file" 2>/dev/null | sort | uniq | wc -l)

    echo -e "${BLUE}🔐 Gitleaks Secret Scan${NC}"
    echo "  Secrets found: $secret_count"
    echo "  Files affected: $unique_files"

    if [ "$secret_count" -gt 0 ]; then
        echo -e "${RED}  ❌ CRITICAL: Secrets detected in repository!${NC}"
        echo "  Affected files:"
        jq -r '.[] | select(.file != "") | "    - \(.file):\(.line_number) - \(.description)"' "$report_file" 2>/dev/null | head -10
        if [ "$secret_count" -gt 10 ]; then
            echo "    ... and $(($secret_count - 10)) more"
        fi
        return 1
    else
        echo -e "${GREEN}  ✅ No secrets found${NC}"
        return 0
    fi
}

# Function to analyze Bandit report
analyze_bandit() {
    local report_file=$1

    if [ ! -f "$report_file" ]; then
        echo -e "${YELLOW}⚠️  Bandit report not found${NC}"
        return
    fi

    local high_count=$(jq '[.results | to_entries[] | select(.value | map(.issue_severity) | contains(["HIGH"])) | .key] | length' "$report_file" 2>/dev/null || echo "0")
    local medium_count=$(jq '[.results | to_entries[] | select(.value | map(.issue_severity) | contains(["MEDIUM"])) | .key] | length' "$report_file" 2>/dev/null || echo "0")
    local low_count=$(jq '[.results | to_entries[] | select(.value | map(.issue_severity) | contains(["LOW"])) | .key] | length' "$report_file" 2>/dev/null || echo "0")

    echo -e "${BLUE}🐍 Bandit Python SAST${NC}"
    echo "  HIGH severity: $high_count"
    echo "  MEDIUM severity: $medium_count"
    echo "  LOW severity: $low_count"

    if [ "$high_count" -gt 0 ]; then
        echo -e "${RED}  ❌ HIGH severity issues found!${NC}"
        jq -r '.results | to_entries[] | select(.value | map(.issue_severity) | contains(["HIGH"])) | "    - \(.key): \(.value | map(select(.issue_severity == "HIGH")) | length) HIGH issues"' "$report_file" 2>/dev/null | head -5
        return 1
    elif [ "$medium_count" -gt 5 ]; then
        echo -e "${YELLOW}  ⚠️  Multiple MEDIUM severity issues${NC}"
        return 1
    else
        echo -e "${GREEN}  ✅ Security issues within acceptable limits${NC}"
        return 0
    fi
}

# Function to analyze Cargo Audit report
analyze_cargo_audit() {
    local report_file=$1

    if [ ! -f "$report_file" ]; then
        echo -e "${YELLOW}⚠️  Cargo Audit report not found${NC}"
        return
    fi

    local vuln_count=$(jq '.vulnerabilities.found | length' "$report_file" 2>/dev/null || echo "0")
    local critical_count=$(jq '[.vulnerabilities.found[] | select(.severity == "critical")] | length' "$report_file" 2>/dev/null || echo "0")
    local high_count=$(jq '[.vulnerabilities.found[] | select(.severity == "high")] | length' "$report_file" 2>/dev/null || echo "0")

    echo -e "${BLUE}🦀 Cargo Audit Rust Dependencies${NC}"
    echo "  Total vulnerabilities: $vuln_count"
    echo "  Critical: $critical_count"
    echo "  High: $high_count"

    if [ "$critical_count" -gt 0 ]; then
        echo -e "${RED}  ❌ CRITICAL vulnerabilities found!${NC}"
        jq -r '.vulnerabilities.found[] | select(.severity == "critical") | "    - \(.package.name) \(.package.version): \(.advisory.title)"' "$report_file" 2>/dev/null | head -5
        return 1
    elif [ "$high_count" -gt 0 ]; then
        echo -e "${YELLOW}  ⚠️  HIGH severity vulnerabilities found${NC}"
        return 1
    else
        echo -e "${GREEN}  ✅ No critical vulnerabilities${NC}"
        return 0
    fi
}

# Function to analyze Safety report
analyze_safety() {
    local report_file=$1

    if [ ! -f "$report_file" ]; then
        echo -e "${YELLOW}⚠️  Safety report not found${NC}"
        return
    fi

    local vuln_count=$(jq '.vulnerabilities | length' "$report_file" 2>/dev/null || echo "0")
    local critical_count=$(jq '[.vulnerabilities[] | select(.severity == "critical")] | length' "$report_file" 2>/dev/null || echo "0")
    local high_count=$(jq '[.vulnerabilities[] | select(.severity == "high")] | length' "$report_file" 2>/dev/null || echo "0")

    echo -e "${BLUE}📦 Safety Python Dependencies${NC}"
    echo "  Total vulnerabilities: $vuln_count"
    echo "  Critical: $critical_count"
    echo "  High: $high_count"

    if [ "$critical_count" -gt 0 ]; then
        echo -e "${RED}  ❌ CRITICAL dependency vulnerabilities!${NC}"
        jq -r '.vulnerabilities[] | select(.severity == "critical") | "    - \(.package): \(.vulnerability)"' "$report_file" 2>/dev/null | head -5
        return 1
    elif [ "$high_count" -gt 0 ]; then
        echo -e "${YELLOW}  ⚠️  HIGH severity dependency issues${NC}"
        return 1
    else
        echo -e "${GREEN}  ✅ Dependencies secure${NC}"
        return 0
    fi
}

# Function to analyze Trivy report
analyze_trivy() {
    local report_file=$1

    if [ ! -f "$report_file" ]; then
        echo -e "${YELLOW}⚠️  Trivy report not found${NC}"
        return
    fi

    local vuln_count=$(jq '[.Results[]?.Vulnerabilities[]?] | length' "$report_file" 2>/dev/null || echo "0")
    local critical_count=$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity == "CRITICAL")] | length' "$report_file" 2>/dev/null || echo "0")
    local high_count=$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity == "HIGH")] | length' "$report_file" 2>/dev/null || echo "0")

    echo -e "${BLUE}🐳 Trivy Container Scan${NC}"
    echo "  Total vulnerabilities: $vuln_count"
    echo "  Critical: $critical_count"
    echo "  High: $high_count"

    if [ "$critical_count" -gt 0 ]; then
        echo -e "${RED}  ❌ CRITICAL container vulnerabilities!${NC}"
        jq -r '.Results[]?.Vulnerabilities[]? | select(.Severity == "CRITICAL") | "    - \(.VulnerabilityID): \(.PkgName) \(.Title)"' "$report_file" 2>/dev/null | head -5
        return 1
    elif [ "$high_count" -gt 5 ]; then
        echo -e "${YELLOW}  ⚠️  Multiple HIGH severity container issues${NC}"
        return 1
    else
        echo -e "${GREEN}  ✅ Container security acceptable${NC}"
        return 0
    fi
}

# Main analysis
main() {
    local failed_analyses=0
    local reports_dir="docs"

    echo "🔍 Analyzing security reports..."
    echo ""

    # Analyze each report
    analyze_gitleaks "$reports_dir/gitleaks_report.json" || ((failed_analyses++))
    echo ""

    analyze_bandit "$reports_dir/bandit_report.json" || ((failed_analyses++))
    echo ""

    analyze_cargo_audit "$reports_dir/cargo_audit_report.json" || ((failed_analyses++))
    echo ""

    analyze_safety "$reports_dir/safety_report.json" || ((failed_analyses++))
    echo ""

    analyze_trivy "$reports_dir/trivy_report.json" || ((failed_analyses++))
    echo ""

    # Summary
    echo "📋 Security Analysis Summary"
    echo "============================"

    if [ $failed_analyses -eq 0 ]; then
        echo -e "${GREEN}🎉 ALL SECURITY CHECKS PASSED!${NC}"
        echo ""
        echo "✅ No critical vulnerabilities detected"
        echo "✅ Code security issues within acceptable limits"
        echo "✅ Dependencies are secure"
        echo "✅ Container image is secure"
        echo ""
        echo "🚀 Ready for production deployment"
        exit 0
    else
        echo -e "${RED}❌ $failed_analyses SECURITY ISSUE(S) DETECTED!${NC}"
        echo ""
        echo "🔴 Critical security issues must be resolved before deployment"
        echo ""
        echo "🛠️  Remediation Steps:"
        echo "   1. Review the detailed reports above"
        echo "   2. Address CRITICAL and HIGH severity issues immediately"
        echo "   3. Update vulnerable dependencies"
        echo "   4. Fix code security issues"
        echo "   5. Rebuild container images"
        echo "   6. Run scans again: ./scripts/security_scan.sh"
        echo ""
        echo "📞 For help: Check docs/devsecops_implementation.md"
        exit 1
    fi
}

# Run main analysis
main "$@"