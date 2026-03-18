#!/bin/bash
# Neo4j Health Check Script for Render
# Returns 0 if healthy, 1 if unhealthy

set -e

# Check if Neo4j is running
if ! pgrep -f "neo4j" > /dev/null; then
    echo "Neo4j process not found"
    exit 1
fi

# Check HTTP endpoint
if curl -sSf http://localhost:7474/db/manage/server/jmx/domain/org.neo4j/instance%3Dkernel%230%2Cname%3DDiagnostics > /dev/null 2>&1; then
    echo "Neo4j HTTP health check passed"
    exit 0
fi

# Fallback: check if bolt port is listening
if nc -z localhost 7687 2>/dev/null; then
    echo "Neo4j Bolt port is listening"
    exit 0
fi

echo "Neo4j health check failed"
exit 1
