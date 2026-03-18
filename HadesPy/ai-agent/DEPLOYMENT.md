# Render Deployment Guide

This guide covers deploying the AI Agent application to [Render](https://render.com) using Infrastructure as Code (IaC) with a Blueprint.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Architecture Overview](#architecture-overview)
- [One-Click Deploy](#one-click-deploy)
- [Manual Deployment](#manual-deployment)
- [Post-Deployment Configuration](#post-deployment-configuration)
- [Environment Variables](#environment-variables)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Tools

- [Render CLI](https://render.com/docs/cli) installed and authenticated
- Docker (for local image building)
- Git

### Render Account Setup

1. Create a Render account at [render.com](https://render.com)
2. Install the Render CLI:
   ```bash
   curl -fsSL https://raw.githubusercontent.com/render-oss/cli/main/install.sh | bash
   ```
3. Authenticate with Render:
   ```bash
   render login
   ```

## Architecture Overview

The AI Agent stack consists of the following services on Render:

```
┌─────────────────────────────────────────────────────────────────┐
│                        Render Stack                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │  ai-agent-   │    │ ai-agent-    │    │ ai-agent-    │       │
│  │     api      │◄──►│  directus    │    │   worker     │       │
│  │   (Web)      │    │   (Web)      │    │  (Worker)    │       │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘       │
│         │                   │                   │               │
│         └───────────────────┼───────────────────┘               │
│                             │                                   │
│         ┌───────────────────┴───────────────────┐               │
│         ▼                                       ▼               │
│  ┌──────────────┐                      ┌──────────────┐         │
│  │ai-agent-     │                      │ai-agent-neo4j│         │
│  │  postgres    │                      │  (Private)   │         │
│  │  (Database)  │                      │  (Graph DB)  │         │
│  └──────────────┘                      └──────────────┘         │
│         ▲                                                       │
│         │                                                       │
│  ┌──────────────┐                                               │
│  │ai-agent-     │                                               │
│  │directus-     │                                               │
│  │  postgres    │                                               │
│  │  (Database)  │                                               │
│  └──────────────┘                                               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Services

| Service | Type | Description |
|---------|------|-------------|
| `ai-agent-api` | Web | Main FastAPI application |
| `ai-agent-directus` | Web | Directus CMS for content management |
| `ai-agent-worker` | Worker | Background job processor |
| `ai-agent-neo4j` | Private Service | Neo4j graph database |
| `ai-agent-postgres` | Managed Database | Main PostgreSQL with pgvector |
| `ai-agent-directus-postgres` | Managed Database | Directus PostgreSQL |

## One-Click Deploy

The fastest way to deploy is using the provided deployment script:

```bash
# Navigate to the project directory
cd ai-agent

# Run the deployment script
./scripts/deploy.sh --environment prod
```

### Deployment Script Options

```bash
./scripts/deploy.sh [OPTIONS]

Options:
  --environment <env>     Deployment environment (prod|staging) [default: prod]
  --skip-migrations       Skip database migrations
  --skip-build           Skip container image builds
  -h, --help             Show help message

Examples:
  ./deploy.sh --environment prod
  ./deploy.sh --environment staging --skip-migrations
  ./deploy.sh --environment prod --skip-build
```

## Manual Deployment

If you prefer manual control over the deployment process:

### Step 1: Validate Blueprint

```bash
# Check the blueprint syntax
cd ai-agent
python3 -c "import yaml; yaml.safe_load(open('render.yaml'))"
```

### Step 2: Apply Blueprint

```bash
# Deploy all services defined in render.yaml
render blueprint apply render.yaml
```

### Step 3: Enable pgvector Extension

After the PostgreSQL database is provisioned, enable the pgvector extension:

1. Go to the Render dashboard
2. Navigate to your PostgreSQL database
3. Open the SQL panel
4. Run:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```

### Step 4: Run Database Migrations

```bash
# Set the DATABASE_URL environment variable from Render
export DATABASE_URL=$(render services env get ai-agent-api DATABASE_URL --format value)

# Run migrations
python3 -m migrations.runner --direction up
```

### Step 5: Verify Deployment

```bash
# Run health checks
./scripts/render-health-check.sh
```

## Post-Deployment Configuration

### 1. Configure Directus Admin

1. Access your Directus instance at `https://ai-agent-directus.onrender.com`
2. Log in with the admin credentials (check Render environment variables)
3. Create a static token for API access
4. Add the token to your API service environment variables as `DIRECTUS_TOKEN`

### 2. Seed Initial Data

If seeding didn't complete automatically:

```bash
# Access Directus and run seed script
render ssh ai-agent-directus
node /directus/seed-courses.js
```

### 3. Configure LLM Provider

Update the environment variables for your chosen LLM provider:

**For Ollama (default):**
```bash
render services env set ai-agent-api LLM_PROVIDER=ollama
render services env set ai-agent-api LLM_MODEL=llama2
```

**For OpenAI:**
```bash
render services env set ai-agent-api LLM_PROVIDER=openai
render services env set ai-agent-api OPENAI_API_KEY=sk-...
```

### 4. Set Up Custom Domain (Optional)

1. In the Render dashboard, go to your web service
2. Click "Settings" → "Custom Domain"
3. Follow Render's instructions to configure DNS

## Environment Variables

### Required Variables

| Variable | Service | Description |
|----------|---------|-------------|
| `DATABASE_URL` | ai-agent-api | PostgreSQL connection string |
| `NEO4J_URI` | ai-agent-api | Neo4j connection URI |
| `NEO4J_PASSWORD` | ai-agent-api | Neo4j password |
| `DIRECTUS_URL` | ai-agent-api | Directus instance URL |
| `DIRECTUS_TOKEN` | ai-agent-api | Directus API token |
| `SECRET_KEY` | ai-agent-api | Application secret key |

### Auto-Generated Variables

Render automatically generates these secure values:

- `NEO4J_AUTH` (Neo4j username:password)
- `KEY` and `SECRET` (Directus security keys)
- `ADMIN_PASSWORD` (Directus initial admin password)

### Copying Environment File

```bash
# Copy example file
cp .env.production.example .env.production

# Edit with your values
nano .env.production
```

## Troubleshooting

### Service Won't Start

Check logs in the Render dashboard or via CLI:

```bash
render services logs ai-agent-api --follow
```

### Database Connection Issues

1. Verify the database is fully provisioned
2. Check environment variables are correctly set
3. Ensure pgvector extension is enabled

### Neo4j Connection Issues

Neo4j is deployed as a private service and is only accessible from other services in the same Render account. Ensure:

1. The `ai-agent-neo4j` service is running
2. Environment variables reference the internal hostname

### Migration Failures

If migrations fail:

```bash
# Check migration status
render ssh ai-agent-api
python3 -m migrations.runner --status

# Run migrations manually
python3 -m migrations.runner --direction up
```

### Health Check Failures

Run the health check script with debug output:

```bash
# Set environment variables
export API_URL=https://ai-agent-api.onrender.com
export DIRECTUS_URL=https://ai-agent-directus.onrender.com

# Run health check with verbose output
bash -x ./scripts/render-health-check.sh
```

## Maintenance

### Scaling Services

Update the `numInstances` in `render.yaml` or use the Render dashboard:

```bash
# Scale API to 2 instances
render services scale ai-agent-api --num-instances 2
```

### Updating Services

After code changes:

```bash
# Deploy updates
./scripts/deploy.sh --skip-migrations
```

### Database Backups

Render automatically backs up managed databases. To create a manual backup:

```bash
# Via Render CLI
render databases backup ai-agent-postgres
```

## Security Considerations

1. **Never commit `.env.production`** - It contains sensitive credentials
2. **Use Render's secret management** - All sensitive values are encrypted
3. **Enable CORS properly** - Update `CORS_ORIGINS` with your actual domains
4. **Regularly rotate secrets** - Update `SECRET_KEY` and API tokens periodically

## Support

For issues specific to:

- **Render platform**: [Render Support](https://render.com/docs)
- **Neo4j**: [Neo4j Documentation](https://neo4j.com/docs/)
- **Directus**: [Directus Documentation](https://docs.directus.io/)
- **Application**: Check application logs and health endpoints

## Additional Resources

- [Render Blueprints Documentation](https://render.com/docs/blueprints)
- [Render CLI Documentation](https://render.com/docs/cli)
- [FastAPI Deployment Guide](https://fastapi.tiangolo.com/deployment/)
