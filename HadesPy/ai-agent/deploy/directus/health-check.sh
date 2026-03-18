#!/bin/sh
# Directus Health Check Script for Render
# Returns 0 if healthy, 1 if unhealthy

# Check if Directus server health endpoint is responding
if wget -q --spider http://localhost:8055/server/health 2>/dev/null; then
    echo "Directus health check passed"
    exit 0
fi

# Fallback: check if port is listening
if nc -z localhost 8055 2>/dev/null; then
    echo "Directus port is listening"
    exit 0
fi

echo "Directus health check failed"
exit 1
