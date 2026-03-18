# MysteryiousHounslow

**AI-Powered Matching Platform** built with:
- 🦀 Rust/Dioxus for frontend
- 🐍 Python/FastAPI for backend
- 🐘 Postgres/PostGIS for data
- 🧊 Hasura/Directus for control plane

## 🚀 Quick Start

```bash
# Clone repository
git clone https://github.com/RAliane/MysteryiousHounslow.git
cd MysteryiousHounslow

# Set up environment
./scripts/dev/setup.sh

# Start services
docker-compose up -d
```

## 📦 Project Structure

```text
MysteryiousHounslow/
├── src/
│   ├── backend/          # FastAPI/Python
│   ├── frontend/         # Dioxus/Rust
│   └── shared/          # Common utilities
├── scripts/
│   ├── verify_hybrid_knn.sh    # kNN verification
│   ├── test_sql_injection.sh   # Security testing
│   └── generate_api_docs.sh   # Documentation generation
├── migrations/
│   ├── 001_init.sql           # Database schema
│   └── 002_knn_function.sql   # kNN functions
├── docker/
│   ├── docker-compose.yml      # Development
│   ├── docker-compose.staging.yml  # Staging
│   └── docker-compose.prod.yml     # Production
├── docs/
│   ├── architecture/          # System design
│   ├── development/           # Developer guides
│   ├── deployment/            # Deployment guides
│   ├── api/                   # API documentation
│   ├── legal/                 # UK compliance
│   ├── operations/            # Operations guides
│   ├── tutorials/             # Step-by-step tutorials
│   ├── reference/             # Technical reference
│   ├── uk_specific/           # UK-specific guides
│   └── changelog.md           # Change history
├── pyproject.toml             # UV configuration
└── uv.lock                   # Dependency lock
```

## 🧩 Key Features

- **Hybrid kNN search**: PostGIS + Python vector similarity
- **UK GDPR compliant**: Data residency and processing
- **Zero-trust architecture**: Network isolation and authentication
- **Deterministic execution**: Reproducible matching results
- **DevSecOps pipeline**: Automated security scanning and compliance checks

## 📄 Documentation

| Area               | Path                          | Description                     |
|--------------------|-------------------------------|---------------------------------|
| Architecture      | [docs/architecture/](docs/architecture/) | System design and components    |
| API Reference     | [docs/api/](docs/api/)        | REST and GraphQL APIs          |
| Development       | [docs/development/](docs/development/) | Setup and coding guidelines    |
| UK Compliance     | [docs/uk_specific/](docs/uk_specific/) | GDPR and data residency        |
| Deployment        | [docs/deployment/](docs/deployment/) | Environment deployment guides  |
| Operations        | [docs/operations/](docs/operations/) | Monitoring and incident response |
| CLI Reference     | [docs/reference/cli.md](docs/reference/cli.md) | Command-line interface         |

## 🛠️ Development

### Prerequisites

- Python 3.11+
- Rust 1.70+
- Docker & Docker Compose
- UV package manager

### Setup

```bash
# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and setup
git clone https://github.com/RAliane/MysteryiousHounslow.git
cd MysteryiousHounslow

# Install dependencies
uv pip install -e .

# Setup development environment
mystery dev setup

# Run tests
mystery dev test

# Start services
docker-compose up -d
```

### CLI Usage

```bash
# Health check
mystery health

# Security scan
mystery security scan

# Deploy to staging
mystery deploy staging

# Monitor logs
mystery monitor logs
```

## 🔒 Security & Compliance

MysteryiousHounslow implements enterprise-grade security:

- **UK GDPR Compliant**: Full data residency and processing controls
- **SQL Injection Protection**: Parameterized queries and input validation
- **Network Isolation**: Zero-trust architecture with service segmentation
- **Automated Security Scanning**: Bandit, SQL injection detection, secrets scanning
- **Rate Limiting**: DDoS protection and API abuse prevention

## 📈 Performance

- **Sub-200ms kNN queries** with PostGIS vector indexing
- **Horizontal scalability** across multiple instances
- **Real-time monitoring** with Prometheus/Grafana
- **Automated testing** with 95%+ code coverage

## 🤝 Contributing

See [CONTRIBUTING.md](docs/contributors.md) for development guidelines.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: [docs/](docs/) directory
- **Issues**: [GitHub Issues](https://github.com/RAliane/MysteryiousHounslow/issues)
- **Discussions**: [GitHub Discussions](https://github.com/RAliane/MysteryiousHounslow/discussions)
- **Security**: security@mysteryioushounslow.co.uk

---

**Built with ❤️ in the United Kingdom** 🇬🇧