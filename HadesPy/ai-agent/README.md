# AI Agent Full Stack

End-to-end AI agent system with Directus, FastAPI, FastMCP, Cognee RAG, Gradio UI, Podman networking, GitLab CI/CD, and hardened Linux deployment.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              EDGE NETWORK (edge_net)                        │
│  ┌─────────────┐                                                            │
│  │    Nginx    │  Reverse Proxy + TLS (Let's Encrypt)                       │
│  │   :80/443   │                                                            │
│  └──────┬──────┘                                                            │
└─────────┼───────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              APP NETWORK (app_net)                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐    │
│  │   FastAPI   │  │  Directus   │  │   Gradio    │  │   Prometheus    │    │
│  │   :8000     │  │   :8055     │  │   :7860     │  │     :9090       │    │
│  │  + FastMCP  │  │   (SQLite)  │  │     UI      │  │                 │    │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘    │
│         │                │                                              │    │
│         └────────────────┴──────────────────────────────────────────────┘    │
│                                    │                                         │
│                           ┌────────┴────────┐                               │
│                           │     Grafana     │                               │
│                           │     :3000       │                               │
│                           └─────────────────┘                               │
└─────────────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                               DB NETWORK (db_net)                           │
│  ┌─────────────┐  ┌─────────────┐                                           │
│  │  SQLite DB  │  │  Cognee     │                                           │
│  │  data.db    │  │ embeddings  │                                           │
│  └─────────────┘  └─────────────┘                                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.12+
- [UV](https://docs.astral.sh/uv/) package manager
- [Podman](https://podman.io/) & podman-compose
- (Optional) Linux server for deployment

### Bootstrap

```bash
# Clone and enter directory
cd ai-agent

# Run bootstrap script
chmod +x scripts/bootstrap.sh
./scripts/bootstrap.sh

# Edit environment configuration
vim .env
```

### Local Development

```bash
# Install dependencies
uv sync

# Run FastAPI server
uv run uvicorn src.main:app --reload

# In another terminal, run Gradio UI
uv run python -m src.ui_gradio

# Or run Streamlit UI
uv run streamlit run src/ui_streamlit.py
```

### Podman Deployment

```bash
# Start all services
podman-compose up -d

# View logs
podman-compose logs -f api

# Scale API workers
podman-compose up -d --scale api=3
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API info |
| `/health` | GET | Health check |
| `/metrics` | GET | Prometheus metrics |
| `/docs` | GET | OpenAPI documentation |
| `/agent` | SSE | FastMCP agent endpoint |
| `/api/collections/{name}` | GET/POST | Directus collections |
| `/api/memory` | POST | Add memory |
| `/api/memory/search` | GET | Search memories |
| `/api/chat` | POST | Chat with agent |

## FastMCP Tools

| Tool | Description |
|------|-------------|
| `directus_query` | Query Directus collections |
| `directus_create` | Create Directus records |
| `directus_update` | Update Directus records |
| `directus_delete` | Delete Directus records |
| `memory_add` | Add memory chunk |
| `memory_search` | Search memories |
| `memory_get_context` | Get relevant context |
| `memory_clear` | Clear all memories |
| `agent_chat` | Chat with AI agent |

## Project Structure

```
ai-agent/
├── src/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Pydantic settings
│   ├── logging_config.py    # Structured logging
│   ├── directus_client.py   # Directus integration
│   ├── memory.py            # Cognee RAG memory
│   ├── mcp_tools.py         # FastMCP tools
│   ├── ui_gradio.py         # Gradio interface
│   └── ui_streamlit.py      # Streamlit interface
├── tests/                   # Pytest test suite
├── artifacts/
│   ├── models.json          # Directus bootstrap schema
│   ├── data.db              # SQLite database
│   └── embeddings.db        # Vector store
├── deploy/
│   ├── nginx/               # Nginx configurations
│   ├── prometheus/          # Prometheus config
│   └── grafana/             # Grafana dashboards
├── scripts/
│   ├── bootstrap.sh         # Setup script
│   └── hardening.sh         # Security hardening
├── Containerfile            # Multi-stage build
├── podman-compose.yml       # Podman orchestration
├── pyproject.toml           # UV/Python config
└── .gitlab-ci.yml           # CI/CD pipeline
```

## Security

### UFW Firewall

```bash
# Run hardening script
sudo ./scripts/hardening.sh
```

Configures:
- Default deny incoming
- Allow 22 (SSH), 80 (HTTP), 443 (HTTPS)
- Rate limiting on SSH
- Internal network access for containers

### Fail2Ban

Protects:
- SSH brute force
- Nginx limit requests
- API abuse detection

### Podman Security

- Rootless containers (optional)
- User namespaces
- Network isolation (triple-layer)
- Secrets management

## Monitoring

### Prometheus Metrics

- `http_requests_total` - Request counter
- `http_request_duration_seconds` - Latency histogram
- `active_connections` - Connection gauge

### Grafana Dashboards

Access at `https://grafana.example.com`

Pre-configured dashboards:
- AI Agent Overview
- API Performance
- System Resources

## CI/CD Pipeline

GitLab CI stages:

1. **Lint** - Ruff, mypy
2. **Test** - Pytest (unit + integration)
3. **Security** - Bandit, pip-audit, Trivy
4. **Build** - Podman image
5. **Deploy** - Staging/Production

```yaml
# Trigger deployment
git tag v1.0.0
git push origin v1.0.0
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_ENV` | `development` | Environment mode |
| `FASTAPI_PORT` | `8000` | API server port |
| `DIRECTUS_URL` | `http://localhost:8055` | Directus endpoint |
| `COGNEE_EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Embedding model |
| `OPENAI_API_KEY` | - | OpenAI API key |

See `.env.example` for full list.

## Development

```bash
# Run tests
uv run pytest

# Run with coverage
uv run pytest --cov=src

# Format code
uv run ruff format src/

# Lint
uv run ruff check src/
```

## License

MIT License - See LICENSE file
