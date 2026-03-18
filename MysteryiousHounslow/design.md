# FastAPI XGBoost Optimizer - Architecture Design

## Project Philosophy
This project embodies **production-grade engineering** with a focus on:
- **Deterministic Optimization**: All microtasks are atomic and deterministic
- **Constraint-Driven Solutions**: Hard constraints enforced first, soft constraints optimized
- **Production Readiness**: Comprehensive error handling, logging, monitoring, and testing
- **Modular Architecture**: Clear separation of concerns with extensive modularity

## Architecture Overview

### Layered Architecture Pattern
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

## Core Components

### 1. API Layer (`api/`)
**Purpose**: HTTP interface and request/response handling
**Key Modules**:
- `endpoints.py`: Main optimization endpoint
- `validation.py`: Pydantic models and request validation
- `middleware.py`: Rate limiting, logging, error handling
- `dependencies.py`: Authentication and shared dependencies

**Design Patterns**:
- Dependency Injection for shared resources
- Pydantic for data validation
- FastAPI's async/await for performance

### 2. Orchestration Layer (`orchestration/`)
**Purpose**: Coordinate the optimization workflow
**Key Modules**:
- `workflow.py`: Main workflow orchestrator
- `microtasks.py`: Atomic task definitions and execution
- `pipeline.py`: Stage-by-stage processing logic

**Design Patterns**:
- Chain of Responsibility for workflow stages
- Strategy Pattern for different optimization approaches
- Command Pattern for microtask execution

### 3. Business Logic Layer (`core/`)
**Purpose**: Core business rules and constraint processing
**Key Modules**:
- `constraints.py`: Hard and soft constraint definitions
- `models.py`: Business domain models
- `processors.py`: Data processing and transformation

**Design Patterns**:
- Specification Pattern for constraint validation
- Factory Pattern for model creation
- Builder Pattern for complex object construction

### 4. ML/Optimization Layer (`optimization/`)
**Purpose**: Machine learning and optimization algorithms
**Key Modules**:
- `xgboost_engine.py`: ML scoring and ranking
- `genetic_optimizer.py`: PyGAD integration for multi-objective optimization
- `constraint_solver.py`: Google OR-Tools CP-SAT integration
- `knn_service.py`: PostGIS kNN queries for spatial constraints

**Design Patterns**:
- Adapter Pattern for external library integration
- Strategy Pattern for different optimization algorithms
- Observer Pattern for optimization progress tracking

### 5. Data Access Layer (`database/`)
**Purpose**: Database operations and data persistence
**Key Modules**:
- `postgis_client.py`: Spatial database operations
- `hasura_client.py`: PyHasura GraphQL client
- `models.py`: Database entity models
- `migrations.py`: Database schema management

**Design Patterns**:
- Repository Pattern for data access abstraction
- Unit of Work Pattern for transaction management
- Data Mapper Pattern for ORM integration

### 6. Infrastructure Layer (`infrastructure/`)
**Purpose**: Cross-cutting concerns and utilities
**Key Modules**:
- `logging_config.py`: Structured logging configuration
- `error_handler.py`: Global exception handling
- `config.py`: Configuration management
- `monitoring.py`: Metrics and health checks

**Design Patterns**:
- Singleton Pattern for configuration
- Decorator Pattern for cross-cutting concerns
- Chain of Responsibility for error handling

## Data Flow Architecture

### Request Processing Pipeline
```
1. HTTP Request → API Layer (Validation & Auth)
2. Validated Request → Orchestration Layer (Workflow Coordination)
3. Business Rules → Core Layer (Constraint Processing)
4. Optimization → ML Layer (XGBoost + PyGAD + OR-Tools)
5. Data Access → Database Layer (PostGIS + Hasura)
6. Response ← Orchestration (Aggregation & Formatting)
7. HTTP Response ← API Layer (Structured Response)
```

### Constraint Processing Flow
```
1. Input Constraints → Validation Engine
2. Hard Constraints → PostGIS kNN + CP-SAT Solver
3. Soft Constraints → XGBoost Scoring + PyGAD Optimization
4. Solution Validation → Multi-stage Verification
5. Final Solution → Persistence + Response
```

## Technology Integration Points

### FastAPI Integration
- **Async/Await**: Non-blocking I/O for database and ML operations
- **Dependency Injection**: Shared resources (database clients, ML models)
- **Pydantic Models**: Request/response validation and serialization
- **OpenAPI**: Automatic API documentation generation

### XGBoost Integration
- **Model Management**: Model loading, caching, and versioning
- **Feature Engineering**: Input transformation and feature extraction
- **Scoring Service**: Real-time prediction and ranking
- **Model Updates**: A/B testing and model deployment pipeline

### Google OR-Tools Integration
- **CP-SAT Solver**: Constraint satisfaction and optimization
- **Model Building**: Dynamic constraint construction
- **Solution Extraction**: Result parsing and validation
- **Parameter Tuning**: Solver configuration and optimization

### PostGIS Integration
- **Spatial Queries**: kNN, distance calculations, spatial relationships
- **Index Optimization**: Spatial indexing for performance
- **Data Validation**: Geographic data integrity checks
- **Query Optimization**: Efficient spatial data retrieval

### PyGAD Integration
- **Genetic Algorithm**: Multi-objective optimization engine
- **Fitness Functions**: Custom scoring for optimization objectives
- **Population Management**: Solution diversity and evolution
- **Convergence Tracking**: Optimization progress monitoring

### PyHasura Integration
- **GraphQL Client**: Type-safe database operations
- **Real-time Subscriptions**: Live data updates and notifications
- **Permission Management**: Row-level security and access control
- **Schema Introspection**: Dynamic query generation

## Configuration Management

### Environment-based Configuration
```python
# config.py structure
class Settings(BaseSettings):
    # API Configuration
    API_VERSION: str = "v1"
    RATE_LIMIT: int = 100
    
    # Database Configuration
    POSTGRES_URL: str
    POSTGIS_EXTENSIONS: List[str]
    
    # ML Configuration
    XGBOOST_MODEL_PATH: str
    XGBOOST_PARAMETERS: Dict[str, Any]
    
    # Optimization Configuration
    PYGAD_PARAMETERS: Dict[str, Any]
    ORTOOLS_PARAMETERS: Dict[str, Any]
    
    # Logging Configuration
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
```

### Dynamic Configuration
- **Hot Reloading**: Configuration changes without restart
- **Validation**: Type-safe configuration with runtime validation
- **Hierarchy**: Environment-specific configuration overrides
- **Secrets Management**: Secure handling of sensitive data

## Error Handling Architecture

### Exception Hierarchy
```python
class OptimizationException(Exception):
    """Base exception for all optimization errors"""
    
class ValidationException(OptimizationException):
    """Input validation errors"""
    
class ConstraintException(OptimizationException):
    """Constraint processing errors"""
    
class OptimizationEngineException(OptimizationException):
    """ML/Optimization engine errors"""
    
class DatabaseException(OptimizationException):
    """Database operation errors"""
```

### Error Response Format
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Input validation failed",
    "details": {
      "cause": "Missing required field: 'objectives'",
      "context": "OptimizationRequest validation",
      "suggestion": "Include 'objectives' array in request body",
      "field": "objectives",
      "value": null
    }
  },
  "timestamp": "2026-01-12T10:30:00Z",
  "request_id": "req-1234567890"
}
```

## Testing Architecture

### Test Pyramid
```
Unit Tests (70%)
├── API endpoint tests
├── Business logic tests
├── ML model tests
└── Database operation tests

Integration Tests (20%)
├── API integration tests
├── Database integration tests
├── ML pipeline tests
└── External service tests

E2E Tests (10%)
├── Complete optimization workflow
├── Error handling scenarios
└── Performance benchmarks
```

### Test Data Management
- **Fixtures**: Reusable test data and mock objects
- **Factories**: Dynamic test data generation
- **Database**: Test database with migrations
- **ML Models**: Mock models for testing

This architecture ensures a robust, scalable, and maintainable system that can handle complex optimization problems while maintaining production-grade reliability and performance.