#!/bin/sh
# Directus Initialization Script for Render
# Sets up Directus with proper configuration

set -e

echo "=========================================="
echo "  Directus Initialization"
echo "=========================================="

# Wait for database to be ready
echo "Waiting for database..."
max_attempts=30
attempt=1

while [ $attempt -le $max_attempts ]; do
    if pg_isready -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" > /dev/null 2>&1; then
        echo "Database is ready!"
        break
    fi
    echo "Attempt $attempt/$max_attempts: Database not ready, waiting..."
    sleep 5
    attempt=$((attempt + 1))
done

if [ $attempt -gt $max_attempts ]; then
    echo "ERROR: Database connection timeout"
    exit 1
fi

# Apply database migrations
echo "Applying database migrations..."
npx directus database migrate:latest

# Check if schema needs to be applied
if [ -f /directus/snapshots/schema.yml ]; then
    echo "Applying schema snapshot..."
    npx directus schema apply --yes /directus/snapshots/schema.yml || {
        echo "Warning: Schema apply failed, may already exist"
    }
fi

# Seed initial data if tables are empty
echo "Checking if seeding is needed..."
SEED_CHECK=$(npx directus items read courses --limit 1 2>/dev/null || echo "")

if [ -z "$SEED_CHECK" ]; then
    echo "Seeding initial course data..."
    if [ -f /directus/seed-courses.js ]; then
        node /directus/seed-courses.js || {
            echo "Warning: Seeding failed, continuing anyway"
        }
    fi
else
    echo "Data already exists, skipping seed"
fi

echo "=========================================="
echo "  Directus Initialization Complete"
echo "=========================================="

# Start Directus
exec npx directus start
