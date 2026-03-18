# Matchgorithm: AI-Powered Matching Platform

[![CI](https://github.com/your-org/matchgorithm/workflows/CI/badge.svg)](https://github.com/your-org/matchgorithm/actions)
[![Security Audit](https://github.com/your-org/matchgorithm/workflows/Security%20Audit/badge.svg)](https://github.com/your-org/matchgorithm/actions)

**Matchgorithm** is an **AI-powered matching platform** built with modern technologies for production-grade deployment.

## 🚀 Late Git Initialization Notice

This repository was initialized **after extensive development** to formalize version control.
All prior work is documented in:
- [GIT_HISTORY.md](GIT_HISTORY.md) (detailed change log)
- [docs/architecture/](docs/architecture/) (technical decisions)
- [scripts/](scripts/) (automation and fixes)

## 📦 Project Structure

```
Matchgorithm/
├── .github/                  # GitHub workflows and issue templates
│   └── workflows/            # CI/CD pipelines
├── docs/                     # All documentation
│   ├── architecture/         # Architecture diagrams
│   ├── deployment/          # Deployment guides
│   └── api/                  # API references
├── scripts/                  # All utility scripts
│   ├── ci/                   # CI-specific scripts
│   ├── dev/                  # Dev utilities
│   └── prod/                 # Production scripts
├── src/                      # Source code
│   ├── frontend/             # Dioxus/Axum frontend
│   │   ├── components/       # Reusable components
│   │   ├── pages/            # Route components
│   │   ├── services/         # API services
│   │   ├── utils/            # Utilities
│   │   └── main.rs           # Frontend entry
│   ├── backend/              # FastAPI backend
│   │   ├── api/              # API routes
│   │   ├── core/             # Business logic
│   │   ├── models/           # Data models
│   │   ├── services/         # External services
│   │   └── main.py           # Backend entry
│   └── shared/               # Shared code
├── migrations/               # Database migrations
├── config/                   # Configuration files
├── tests/                    # All tests
│   ├── unit/                 # Unit tests
│   ├── integration/          # Integration tests
│   └── e2e/                  # End-to-end tests
├── docker/                   # Docker/Podman files
│   ├── nginx/                # Nginx config
│   └── Dockerfile            # Container definitions
├── .gitignore
├── .pre-commit-config.yaml
├── README.md
├── LICENSE
└── CHANGELOG.md
```

## 🏗️ Architecture

### Core Components
- **Frontend**: Rust/Dioxus/Axum web application
- **Backend**: Python/FastAPI with ML optimization pipeline
- **Database**: PostgreSQL with PostGIS and pgvector extensions
- **APIs**: Hasura GraphQL and Directus REST
- **Deployment**: Podman containers with production hardening

### ML Pipeline
- **XGBoost**: Gradient boosting for feature ranking
- **OR-Tools**: Constraint programming for optimization
- **PyGAD**: Genetic algorithms for complex matching
- **pgvector**: Vector similarity search for embeddings

### Security Features
- **Network Isolation**: Triple network separation (edge-net, auth-net, db-net)
- **Authentication**: JWT with Directus integration
- **Password Reset**: SMTP-based secure password recovery
- **Resource Limits**: Container CPU/memory constraints
- **Security Scanning**: Automated SAST/DAST in CI/CD

## 🚀 Quick Start

### Prerequisites
- Rust 1.70+ with cargo
- Python 3.11+ with UV package manager
- Podman 4.0+ or Docker 20.0+
- PostgreSQL client tools

### Development Setup

```bash
# Clone repository
git clone https://github.com/your-org/matchgorithm.git
cd matchgorithm

# Setup environment
./scripts/setup_environment.sh

# Generate SSL certificates (development)
./scripts/generate_certs.sh

# Start all services
podman-compose up -d

# Run migrations
./scripts/run_migrations.sh

# Verify setup
./scripts/final_validation.sh
```

### Production Deployment

```bash
# Configure production secrets
./scripts/setup_environment.sh

# Deploy with monitoring
./scripts/production_setup.sh

# Setup monitoring
./scripts/setup_monitoring.sh
```

## 📚 Documentation

- **[Architecture](docs/architecture/)** - System design and components
- **[Deployment](docs/deployment/)** - Production setup and operations
- **[API Reference](docs/api/)** - REST and GraphQL endpoints
- **[Development](docs/development/)** - Contributing and development setup

## 🔧 Development

### Building

```bash
# Frontend
cd src/frontend && cargo build

# Backend
cd src/backend && uv pip install -e .

# Full stack
podman-compose build
```

### Testing

```bash
# Unit tests
cargo test
pytest tests/unit/

# Integration tests
pytest tests/integration/

# End-to-end tests
./scripts/final_validation.sh
```

### Code Quality

```bash
# Formatting
cargo fmt
black src/backend/

# Linting
cargo clippy
flake8 src/backend/

# Security scanning
./scripts/security_scan.sh
```

## 🔒 Security

- **Secrets Management**: Podman secrets with secure storage
- **Network Security**: Firewall rules and container isolation
- **Authentication**: JWT-based secure API access
- **Monitoring**: Real-time security event logging
- **Compliance**: SOC2 and GDPR ready architecture

## 📊 Monitoring

- **Prometheus**: Metrics collection and alerting
- **Grafana**: Dashboards for system monitoring
- **Health Checks**: Automated service health monitoring
- **Logging**: Structured logging with correlation IDs

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Workflow

- **GitFlow**: Feature branches with PR reviews
- **CI/CD**: Automated testing and security scanning
- **Code Review**: Required for all changes
- **Documentation**: Update docs for all features

## 📄 License

Proprietary - All rights reserved

## 🙏 Acknowledgments

Built with extensive collaboration with **Grok Code Fast 1**, providing comprehensive code review, architecture guidance, and implementation assistance throughout the development process.
