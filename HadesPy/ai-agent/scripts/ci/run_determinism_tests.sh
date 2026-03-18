#!/bin/bash
# Run Determinism Tests - 20 Iterations
# This script runs the RAG pipeline 20 times and verifies all outputs are identical
# Exit with error if hashes don't match (per TOML spec requirement)
#
# Usage:
#   ./run_determinism_tests.sh [iterations]
#
# Environment Variables:
#   DETERMINISM_ITERATIONS: Number of iterations (default: 20)
#   NEO4J_URI: Neo4j connection URI (default: bolt://neo4j:7687)
#   NEO4J_USER: Neo4j username (default: neo4j)
#   NEO4J_PASSWORD: Neo4j password (default: test)

set -euo pipefail

# Configuration
ITERATIONS="${DETERMINISM_ITERATIONS:-20}"
RESULTS_DIR="${CI_PROJECT_DIR:-$(pwd)}/determinism_results"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="${SCRIPT_DIR}/verify_determinism.py"

echo "========================================"
echo "DETERMINISM TEST SUITE"
echo "========================================"
echo "Iterations: ${ITERATIONS}"
echo "Results dir: ${RESULTS_DIR}"
echo "Start time: $(date -Iseconds)"
echo "========================================"

# Create results directory
mkdir -p "${RESULTS_DIR}"

# Override NUM_RUNS in verify_determinism.py via environment
export DETERMINISM_RUNS="${ITERATIONS}"

# Check if Python script exists
if [[ ! -f "${PYTHON_SCRIPT}" ]]; then
    echo "ERROR: Python verification script not found at ${PYTHON_SCRIPT}"
    exit 1
fi

echo ""
echo "Running determinism validation with ${ITERATIONS} iterations..."

# Run the Python determinism verification script
# It will exit with non-zero if determinism check fails
if python3 "${PYTHON_SCRIPT}"; then
    echo ""
    echo "========================================"
    echo "✓ DETERMINISM TEST PASSED"
    echo "All ${ITERATIONS} iterations produced identical outputs"
    echo "End time: $(date -Iseconds)"
    echo "========================================"
    exit 0
else
    EXIT_CODE=$?
    echo ""
    echo "========================================"
    echo "✗ DETERMINISM TEST FAILED"
    echo "Found non-deterministic behavior!"
    echo "Exit code: ${EXIT_CODE}"
    echo "End time: $(date -Iseconds)"
    echo "========================================"
    echo ""
    echo "BUILD WILL FAIL - Determinism is critical per TOML spec"
    exit 1
fi
