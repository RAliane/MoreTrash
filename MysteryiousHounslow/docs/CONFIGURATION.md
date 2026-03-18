# Configuration Guide

Matchgorithm uses **Podman secrets** for all sensitive credentials in production and environment variables for local development.

## Required Podman Secrets

All secrets must be created before starting services.

### Database Secrets

```bash
podman secret create postgres_user <(echo "postgres")
podman secret create postgres_password <(echo "your-secure-password")
podman secret create postgres_db <(echo "matchgorithm")
```

**Used by:** postgres, directus, n8n, matchgorithm-app

### Directus Secrets

```bash
podman secret create directus_url <(echo "http://directus:8055")
podman secret create directus_token <(echo "your-directus-admin-token")
podman secret create directus_secret <(echo "your-directus-secret-key")
podman secret create directus_admin_email <(echo "admin@matchgorithm.co.uk")
podman secret create directus_admin_password <(echo "secure-admin-password")
```

**Used by:** directus, matchgorithm-app

### Hasura Secrets

```bash
podman secret create hasura_endpoint <(echo "http://hasura:8080/v1/graphql")
podman secret create hasura_admin_secret <(echo "your-hasura-admin-secret")
```

**Used by:** hasura, matchgorithm-app

### n8n Secrets

```bash
podman secret create n8n_webhook_url <(echo "http://n8n:5678/webhook")
podman secret create n8n_api_url <(echo "http://n8n:5678/api")
```

**Used by:** n8n, matchgorithm-app

### OAuth Secrets

```bash
podman secret create google_client_id <(echo "your-google-oauth-id")
podman secret create google_client_secret <(echo "your-google-oauth-secret")
podman secret create github_client_id <(echo "your-github-oauth-id")
podman secret create github_client_secret <(echo "your-github-oauth-secret")
podman secret create apple_client_id <(echo "your-apple-app-id")
podman secret create apple_team_id <(echo "your-apple-team-id")
podman secret create apple_key_id <(echo "your-apple-key-id")
podman secret create apple_private_key <(cat apple-private-key.p8)
```

**Used by:** matchgorithm-app

### AI Provider Secrets

```bash
# Choose ONE provider
podman secret create groq_api_key <(echo "your-groq-api-key")
# OR
podman secret create openrouter_api_key <(echo "your-openrouter-api-key")
```

**Used by:** matchgorithm-app

## Local Development (.env)

For local development, create a `.env` file in the project root:

```bash
# Database
POSTGRES_USER=postgres
POSTGRES_PASSWORD=localpassword
POSTGRES_DB=matchgorithm
DATABASE_URL=postgresql://postgres:localpassword@localhost:5432/matchgorithm

# Directus
DIRECTUS_URL=http://localhost:8055
DIRECTUS_TOKEN=local-dev-token
DIRECTUS_SECRET=local-dev-secret
DIRECTUS_ADMIN_EMAIL=admin@localhost
DIRECTUS_ADMIN_PASSWORD=admin

# Hasura
HASURA_GRAPHQL_ENDPOINT=http://localhost:8080/v1/graphql
HASURA_ADMIN_SECRET=local-hasura-secret

# n8n
N8N_WEBHOOK_URL=http://localhost:5678/webhook
N8N_API_URL=http://localhost:5678/api

# OAuth (optional for local dev)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=

# AI Provider
AI_PROVIDER=groq
GROQ_API_KEY=your-api-key
```

## Environment Variable Reference

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `POSTGRES_USER` | Yes | PostgreSQL username | `postgres` |
| `POSTGRES_PASSWORD` | Yes | PostgreSQL password | `secure-password` |
| `POSTGRES_DB` | Yes | Database name | `matchgorithm` |
| `DATABASE_URL` | Yes | Full Postgres connection string | `postgresql://user:pass@host:5432/db` |
| `DIRECTUS_URL` | Yes | Directus API URL | `http://directus:8055` |
| `DIRECTUS_TOKEN` | Yes | Directus admin access token | `admin-token-here` |
| `DIRECTUS_SECRET` | Yes | Directus secret key | `secret-key-here` |
| `HASURA_GRAPHQL_ENDPOINT` | Yes | Hasura GraphQL endpoint | `http://hasura:8080/v1/graphql` |
| `HASURA_ADMIN_SECRET` | Yes | Hasura admin secret | `hasura-admin-secret` |
| `N8N_WEBHOOK_URL` | Yes | n8n webhook base URL | `http://n8n:5678/webhook` |
| `N8N_API_URL` | Yes | n8n REST API URL | `http://n8n:5678/api` |
| `GOOGLE_CLIENT_ID` | No | Google OAuth client ID | From Google Console |
| `GOOGLE_CLIENT_SECRET` | No | Google OAuth secret | From Google Console |
| `GITHUB_CLIENT_ID` | No | GitHub OAuth app ID | From GitHub Settings |
| `GITHUB_CLIENT_SECRET` | No | GitHub OAuth secret | From GitHub Settings |
| `APPLE_CLIENT_ID` | No | Apple app identifier | From Apple Developer |
| `APPLE_TEAM_ID` | No | Apple team ID | From Apple Developer |
| `APPLE_KEY_ID` | No | Apple key ID | From Apple Developer |
| `APPLE_PRIVATE_KEY` | No | Apple private key (.p8) | From Apple Developer |
| `AI_PROVIDER` | Yes | AI provider (`groq` or `openrouter`) | `groq` |
| `GROQ_API_KEY` | Conditional | Groq API key if using Groq | From Groq Console |
| `OPENROUTER_API_KEY` | Conditional | OpenRouter key if using OpenRouter | From OpenRouter |

## Validation

To validate your configuration, run:

```bash
cargo run --bin validate-config
```

This will:
- Check all required secrets are present
- Verify database connectivity
- Test Directus authentication
- Validate Hasura endpoint
- Confirm n8n availability

## Security Notes

- **Never commit secrets to version control**
- Rotate secrets every 90 days in production
- Use different secrets for dev/staging/production
- Store Apple private key as a file secret, not inline
- Audit secret access logs regularly

## Troubleshooting

### Secret not found error

Ensure the secret exists:
```bash
podman secret ls
```

Create missing secrets as shown above.

### Database connection refused

Check Postgres container is running:
```bash
podman ps | grep postgres
```

Verify DATABASE_URL matches container configuration.

### Directus authentication failed

Regenerate Directus token through admin panel:
1. Log into Directus at http://localhost:8055
2. Navigate to Settings > Access Tokens
3. Create new admin token
4. Update `directus_token` secret
