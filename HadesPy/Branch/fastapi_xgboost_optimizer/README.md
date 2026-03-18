# FastAPI XGBoost Optimizer

A production-ready optimization service combining FastAPI, XGBoost machine learning, genetic algorithms, and constraint programming to solve complex optimization problems with both hard and soft constraints.

## 🚀 Features

- **High-Performance API**: Built with FastAPI for async/await support and automatic OpenAPI documentation
- **Machine Learning Integration**: XGBoost for predictive scoring and ranking
- **Genetic Algorithm Optimization**: Multi-objective optimization using PyGAD
- **Constraint Programming**: Google OR-Tools CP-SAT for mathematical constraint satisfaction
- **Spatial Constraints**: PostGIS integration for geographic constraint enforcement
- **GraphQL Database**: PyHasura for efficient database operations
- **Production Ready**: Comprehensive error handling, logging, monitoring, and security
- **Containerized**: Podman-ready with secrets management and health checks

## 🏗️ Architecture

```
┌─────────────────────────────────────────────┐
│           API Layer (FastAPI)              │
│         - Endpoints & Validation           │
│         - Rate Limiting & Auth             │
├─────────────────────────────────────────────┤
│         Orchestration Layer                │
│         - Workflow Management              │
│         - Microtask Coordination           │
├─────────────────────────────────────────────┤
│      Business Logic Layer                  │
│         - Constraint Processing            │
│         - Optimization Engine              │
├─────────────────────────────────────────────┤
│         ML/Optimization Layer              │
│         - XGBoost Scoring                  │
│         - PyGAD Genetic Algorithm          │
│         - Google OR-Tools CP-SAT           │
├─────────────────────────────────────────────┤
│         Data Access Layer                  │
│         - PostGIS Integration              │
│         - PyHasura Client                  │
│         - Postgres Operations              │
├─────────────────────────────────────────────┤
│         Infrastructure Layer               │
│         - Logging & Monitoring             │
│         - Error Handling                   │
│         - Configuration Management         │
└─────────────────────────────────────────────┘
```

## 🛠️ Technology Stack

- **Backend**: FastAPI, Python 3.11+
- **Machine Learning**: XGBoost, scikit-learn
- **Optimization**: PyGAD (Genetic Algorithm), Google OR-Tools (CP-SAT)
- **Database**: PostgreSQL with PostGIS extension
- **GraphQL**: Hasura GraphQL Engine
- **Caching**: Redis
- **Container**: Podman/Docker with multi-stage builds
- **Monitoring**: Prometheus, Grafana
- **Testing**: pytest, pytest-asyncio

## 📋 Requirements

- Python 3.11+
- PostgreSQL 16+ with PostGIS
- Redis 7+
- Hasura GraphQL Engine v2.37+
- Podman/Docker (for containerized deployment)

## 🚀 Quick Start

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/ryanallan/fastapi_xgboost_optimizer.git
   cd fastapi_xgboost_optimizer
   ```

2. **Set up environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements/dev.txt
   ```

4. **Set up database**
   ```bash
   # Start PostgreSQL with PostGIS
   docker-compose up -d postgres hasura
   
   # Run migrations
   alembic upgrade head
   ```

5. **Run the application**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

### Containerized Deployment

1. **Build and run with Docker Compose**
   ```bash
   docker-compose up -d
   ```

2. **Or use Podman**
   ```bash
   podman-compose up -d
   ```

3. **Access the application**
   - API: http://localhost:8000
   - Documentation: http://localhost:8000/docs
   - Hasura Console: http://localhost:8080
   - Grafana: http://localhost:3000

## 📖 API Documentation

### Main Endpoints

- `POST /api/v1/optimize` - Submit optimization request
- `POST /api/v1/optimize/batch` - Submit batch optimization requests
- `GET /api/v1/optimize/{request_id}/status` - Get optimization status
- `GET /api/v1/optimize/{request_id}/results` - Get optimization results
- `DELETE /api/v1/optimize/{request_id}` - Cancel optimization request
- `GET /health` - Health check endpoint
- `GET /metrics` - Performance metrics

### Example Request

```json
POST /api/v1/optimize
{
  "name": "Facility Location Optimization",
  "description": "Find optimal facility locations with distance constraints",
  "variables": {
    "facility_x": {"type": "continuous", "bounds": [0, 1000]},
    "facility_y": {"type": "continuous", "bounds": [0, 1000]}
  },
  "objectives": [
    {
      "name": "minimize_distance",
      "type": "minimize",
      "function": "sqrt((facility_x - 500)^2 + (facility_y - 500)^2)",
      "weight": 1.0,
      "variables": ["facility_x", "facility_y"]
    }
  ],
  "constraints": [
    {
      "name": "distance_to_customers",
      "type": "soft",
      "weight": 0.8,
      "priority": 2,
      "spatial_constraint": {
        "type": "distance",
        "geometry": {"type": "Point", "coordinates": [500, 500]},
        "srid": 3857,
        "operation": "within",
        "buffer": 200.0
      }
    }
  ],
  "parameters": {
    "max_iterations": 1000,
    "time_limit": 300,
    "convergence_threshold": 0.001
  }
}
```

### Example Response

```json
{
  "request_id": "req-1234567890",
  "status": "completed",
  "solutions": [
    {
      "solution_id": "sol-1",
      "variables": {"facility_x": 520, "facility_y": 480},
      "objectives": {"minimize_distance": 28.28},
      "fitness_score": 0.95,
      "rank": 1,
      "is_feasible": true,
      "metadata": {"generation": 45}
    }
  ],
  "best_solution": {
    "solution_id": "sol-1",
    "variables": {"facility_x": 520, "facility_y": 480},
    "objectives": {"minimize_distance": 28.28},
    "fitness_score": 0.95,
    "rank": 1,
    "is_feasible": true,
    "metadata": {"generation": 45}
  },
  "execution_time": 15.2,
  "stage_completion": {
    "input_validation": 100.0,
    "constraint_validation": 100.0,
    "hard_constraint_enforcement": 100.0,
    "soft_constraint_scoring": 100.0,
    "ml_scoring": 100.0,
    "optimization": 100.0,
    "solution_validation": 100.0,
    "result_aggregation": 100.0
  },
  "convergence_history": [
    {"generation": 1, "fitness": 0.1},
    {"generation": 10, "fitness": 0.6},
    {"generation": 45, "fitness": 0.95}
  ],
  "constraint_satisfaction": {
    "distance_to_customers": 0.92
  },
  "created_at": "2026-01-12T10:30:00Z",
  "metadata": {
    "num_solutions": 1,
    "validation_rate": 1.0,
    "ml_score": 0.88
  }
}
```

## 🔧 Configuration

The application is configured through environment variables and YAML configuration files:

- `.env` - Environment variables
- `config/settings.yaml` - Application settings
- `config/optimization.yaml` - ML and optimization parameters
- `config/logging.yaml` - Logging configuration

### Key Configuration Options

- `DATABASE_URL` - PostgreSQL connection string
- `HASURA_URL` - Hasura GraphQL endpoint
- `XGBOOST_MODEL_PATH` - Path to XGBoost models
- `PYGAD_POPULATION_SIZE` - Genetic algorithm population size
- `ORTOOLS_MAX_TIME` - Maximum solver time
- `RATE_LIMIT` - API rate limiting

## 🧪 Testing

Run the test suite:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_api.py

# Run with verbose output
pytest -v
```

## 📊 Monitoring

The application includes comprehensive monitoring:

- **Health Checks**: `/health` endpoint
- **Metrics**: `/metrics` endpoint with Prometheus format
- **Logging**: Structured JSON logging with request correlation
- **Alerts**: Configurable thresholds for error rates and performance
- **Dashboards**: Grafana dashboards for visualization

### Key Metrics

- Request rate and response times
- Optimization success/failure rates
- Constraint satisfaction rates
- ML model prediction accuracy
- Database query performance
- System resource usage

## 🔒 Security

- API key authentication
- Rate limiting
- Input validation and sanitization
- SQL injection prevention
- XSS protection
- CORS configuration
- TLS/SSL support

## 🚀 Deployment

### Production Deployment Checklist

1. **Environment Setup**
   - Set `DEBUG=false`
   - Use strong secrets
   - Configure SSL/TLS certificates
   - Set up monitoring

2. **Database**
   - Use PostgreSQL with PostGIS
   - Configure connection pooling
   - Set up backups
   - Enable query logging

3. **Scaling**
   - Use multiple workers
   - Configure load balancing
   - Set up auto-scaling
   - Monitor resource usage

4. **Security**
   - Enable authentication
   - Configure rate limiting
   - Use HTTPS
   - Set up firewall rules

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run the test suite
6. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: [Full documentation](docs/)
- **Issues**: [GitHub Issues](https://github.com/ryanallan/fastapi_xgboost_optimizer/issues)
- **Discussions**: [GitHub Discussions](https://github.com/ryanallan/fastapi_xgboost_optimizer/discussions)

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) - Modern, fast web framework
- [XGBoost](https://xgboost.readthedocs.io/) - Scalable gradient boosting
- [PyGAD](https://pygad.readthedocs.io/) - Genetic algorithm library
- [Google OR-Tools](https://developers.google.com/optimization) - Optimization tools
- [PostGIS](https://postgis.net/) - Spatial database extender
- [Hasura](https://hasura.io/) - GraphQL engine

---

Built with ❤️ by Ryan Allan