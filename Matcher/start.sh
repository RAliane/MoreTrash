#!/bin/bash

set -e

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Matchgorithm DigitalOcean Deployment ===${NC}"

# Check environment variables
echo -e "${YELLOW}Checking environment variables...${NC}"
required_vars=("POSTGRES_USER" "POSTGRES_PASSWORD" "POSTGRES_DB" "DIRECTUS_TOKEN")
for var in "${required_vars[@]}"; do
  if [ -z "${!var}" ]; then
    echo -e "${RED}Error: $var is not set${NC}"
    exit 1
  fi
done
echo -e "${GREEN}✓ Environment variables verified${NC}"

# Wait for database
echo -e "${YELLOW}Waiting for PostgreSQL...${NC}"
max_attempts=30
attempt=0
while ! nc -z postgres 5432 2>/dev/null; do
  attempt=$((attempt + 1))
  if [ $attempt -gt $max_attempts ]; then
    echo -e "${RED}PostgreSQL failed to start${NC}"
    exit 1
  fi
  echo -e "${YELLOW}Attempt $attempt/$max_attempts...${NC}"
  sleep 1
done
echo -e "${GREEN}✓ PostgreSQL is ready${NC}"

# Wait for Directus
echo -e "${YELLOW}Waiting for Directus...${NC}"
attempt=0
while ! curl -s http://directus:8055/admin >/dev/null 2>&1; do
  attempt=$((attempt + 1))
  if [ $attempt -gt 30 ]; then
    echo -e "${YELLOW}Warning: Directus may still be initializing${NC}"
    break
  fi
  sleep 1
done
echo -e "${GREEN}✓ Directus is ready${NC}"

# Install dependencies
if [ ! -d "node_modules" ]; then
  echo -e "${YELLOW}Installing dependencies...${NC}"
  npm install -g pnpm
  pnpm install --frozen-lockfile
  echo -e "${GREEN}✓ Dependencies installed${NC}"
fi

# Build application
if [ "$NODE_ENV" = "production" ]; then
  echo -e "${YELLOW}Building for production...${NC}"
  pnpm run prod:build
  echo -e "${GREEN}✓ Production build complete${NC}"
else
  echo -e "${YELLOW}Starting development mode...${NC}"
fi

# Start application
echo -e "${GREEN}Starting Matchgorithm application...${NC}"
if [ "$NODE_ENV" = "production" ]; then
  exec pnpm start
else
  exec pnpm dev
fi
