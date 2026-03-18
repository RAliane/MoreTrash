# Matchgorithm

AI-Powered Matching Platform with Evolutionary Algorithms.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Nginx Reverse Proxy                       │
│                         (SSL Termination)                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Dioxus     │  │   Directus   │  │    Hasura    │          │
│  │  (Rust SSR)  │  │    (CMS)     │  │  (GraphQL)   │          │
│  │   :8000      │  │    :8055     │  │    :8080     │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                 │                 │                    │
│         └─────────────────┴─────────────────┘                    │
│                           │                                      │
│                  ┌────────┴────────┐                            │
│                  │   PostgreSQL    │                            │
│                  │      :5432      │                            │
│                  └─────────────────┘                            │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐                            │
│  │   FastAPI    │  │     n8n      │                            │
│  │ (ML Service) │  │ (Automation) │                            │
│  │    :8001     │  │    :5678     │                            │
│  └──────────────┘  └──────────────┘                            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Frontend | Dioxus (Rust) | SSR reactive UI |
| Backend | Axum (Rust) | HTTP server |
| CMS | Directus | Content & data management |
| GraphQL | Hasura | Real-time data API |
| Database | PostgreSQL 13 | Primary data store |
| ML Service | FastAPI + XGBoost | Optimization engine |
| Automation | n8n | Workflow automation |
| Containers | Podman | Container runtime |
| Deployment | DigitalOcean | Cloud infrastructure |

## Prerequisites

- Rust 1.75+ with cargo
- Podman 4.0+ (or Docker as alternative)
- PostgreSQL client tools (optional, for debugging)

## Quick Start

### 1. Clone and Configure

```bash
git clone https://github.com/matchgorithm/matchgorithm-app.git
cd matchgorithm-app

# Copy environment template
cp .env.example .env

# Edit .env with your configuration
# See CONFIGURATION section below
```

### 2. Start Services

```bash
# Start all services with Podman Compose
podman-compose up -d

# View logs
podman-compose logs -f

# Check service health
curl http://localhost:8000/health
```

### 3. Access Services

| Service | URL | Description |
|---------|-----|-------------|
| App | http://localhost:8000 | Main application |
| Directus | http://localhost:8055 | CMS admin panel |
| Hasura | http://localhost:8080 | GraphQL console |
| n8n | http://localhost:5678 | Workflow automation |

## Configuration

### Required Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@localhost:5432/db` |
| `DIRECTUS_URL` | Directus API URL | `http://localhost:8055` |
| `DIRECTUS_TOKEN` | Directus static access token | `your-token-here` |
| `HASURA_GRAPHQL_ENDPOINT` | Hasura GraphQL endpoint | `http://localhost:8080/v1/graphql` |
| `HASURA_ADMIN_SECRET` | Hasura admin secret | `your-secret-here` |

### Getting Your Directus Token

1. Start Directus: `podman-compose up -d directus`
2. Open http://localhost:8055
3. Log in with admin credentials
4. Go to Settings → Access Tokens
5. Create a new static token
6. Copy to your `.env` file

See `directus/README.md` for detailed setup instructions.

## Development

### Build and Run Locally

```bash
# Development mode (with hot reload)
cargo watch -x run

# Production build
cargo build --release

# Run tests
cargo test
```

### Project Structure

```
matchgorithm/
├── src/
│   ├── main.rs           # Application entry point
│   ├── config.rs         # Configuration management
│   ├── services/         # Backend services
│   │   ├── mod.rs
│   │   ├── auth.rs       # Authentication
│   │   ├── database.rs   # PostgreSQL connection
│   │   ├── directus.rs   # Directus CMS client
│   │   ├── fastapi.rs    # FastAPI ML client
│   │   └── hasura.rs     # Hasura GraphQL client
│   ├── pages/            # Dioxus page components
│   │   ├── mod.rs
│   │   ├── home.rs
│   │   ├── platform.rs
│   │   └── ...
│   └── components/       # Reusable UI components
│       ├── mod.rs
│       ├── header.rs
│       ├── footer.rs
│       └── ...
├── assets/               # Static CSS/JS
├── templates/            # HTML templates
├── directus/             # Directus configuration
│   ├── schema.json       # Collection schema
│   └── hooks/            # Custom hooks
├── Cargo.toml            # Rust dependencies
├── podman-compose.yml    # Container orchestration
├── nginx.conf            # Reverse proxy config
├── .env.example          # Environment template
└── README.md             # This file
```

## Deployment

### Production (DigitalOcean)

1. **Create Droplet**: Ubuntu 22.04, 4GB RAM minimum
2. **Install Podman**: `apt install podman podman-compose`
3. **Create Secrets**:
   ```bash
   echo "your_db_url" | podman secret create database_url -
   echo "your_token" | podman secret create directus_token -
   # ... repeat for all secrets
   ```
4. **Deploy**:
   ```bash
   git clone <repo>
   cd matchgorithm
   podman-compose -f podman-compose.yml up -d
   ```

See `docs/DEPLOYMENT.md` for detailed production setup.

## Integration with FastAPI XGBoost Optimizer

The Matchgorithm app integrates with the FastAPI XGBoost Optimizer service for ML-based matching optimization.

### Endpoints

- `POST /api/optimize` - Submit optimization request
- `GET /api/optimize/:id/status` - Check optimization status
- `GET /api/optimize/:id/results` - Get optimization results

### Example Request

```bash
curl -X POST http://localhost:8000/api/optimize \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Talent Matching",
    "variables": {...},
    "objectives": [...],
    "constraints": [...],
    "parameters": {"max_iterations": 1000}
  }'
```

See the FastAPI XGBoost Optimizer documentation for full API reference.

## License

Proprietary - All rights reserved.

## Support

- Email: support@matchgorithm.co.uk
- Documentation: https://docs.matchgorithm.co.uk
