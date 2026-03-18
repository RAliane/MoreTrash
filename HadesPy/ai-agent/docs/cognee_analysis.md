# Cognee Repository Analysis

**Version Analyzed:** v0.5.3  
**Analysis Date:** 2026-03-02  
**Repository:** https://github.com/topoteretes/cognee

---

## Executive Summary

Cognee is a Python library for enriching LLM context with a semantic layer for better understanding and reasoning. It provides a complete RAG (Retrieval-Augmented Generation) pipeline with knowledge graph construction, vector storage, and multi-modal data ingestion.

---

## 1. Project Structure Overview

### 1.1 Root Directory Organization

```
cognee/
├── cognee/                    # Main Python package
├── cognee-frontend/           # Next.js/React frontend
├── cognee-mcp/                # Model Context Protocol integration
├── cognee-starter-kit/        # Starter templates
├── distributed/               # Distributed processing (Modal)
├── evals/                     # Evaluation framework
├── examples/                  # Usage examples
├── notebooks/                 # Jupyter notebooks
├── tests/                     # Test suite
├── bin/                       # CLI scripts
├── deployment/                # Deployment configs
├── tools/                     # Development tools
├── alembic/                   # Database migrations
└── assets/                    # Documentation assets
```

### 1.2 Core Package Structure (`cognee/`)

```
cognee/
├── api/v1/                    # REST API endpoints
│   ├── add/                   # Data ingestion API
│   ├── cognify/               # Knowledge graph processing
│   ├── search/                # Search endpoints
│   ├── datasets/              # Dataset management
│   ├── users/                 # Authentication & users
│   └── ...
├── modules/
│   ├── pipelines/             # Pipeline orchestration
│   ├── data/                  # Data models & methods
│   ├── users/                 # User management
│   ├── search/                # Search functionality
│   ├── retrieval/             # Retrieval strategies
│   ├── cognify/               # Cognify configuration
│   ├── notebooks/             # Notebook operations
│   └── ...
├── tasks/                     # Processing tasks
│   ├── ingestion/             # Data ingestion
│   ├── chunks/                # Text chunking
│   ├── documents/             # Document processing
│   ├── graph/                 # Graph extraction
│   ├── storage/               # Storage operations
│   ├── summarization/         # Text summarization
│   └── ...
├── infrastructure/
│   ├── databases/
│   │   ├── graph/             # Graph DB adapters
│   │   ├── vector/            # Vector DB adapters
│   │   ├── relational/        # SQL DB adapters
│   │   └── cache/             # Cache adapters
│   ├── llm/                   # LLM configuration
│   ├── files/                 # File storage
│   ├── loaders/               # Data loaders
│   └── engine/                # DataPoint engine
├── shared/                    # Shared utilities
└── cli/                       # Command-line interface
```

---

## 2. Key Integration Points for HadesPy

### 2.1 Primary API Entry Points

| Component | Path | Purpose |
|-----------|------|---------|
| Add API | `cognee/api/v1/add/add.py` | Data ingestion |
| Cognify API | `cognee/api/v1/cognify/cognify.py` | Knowledge graph construction |
| Search API | `cognee/api/v1/search/search.py` | Semantic search |
| Client | `cognee/api/client.py` | Python client interface |

### 2.2 Storage Abstractions

| Storage Type | Interface | Implementations |
|--------------|-----------|-----------------|
| Graph DB | `GraphDBInterface` | Neo4j, Kùzu, Neptune |
| Vector DB | `VectorDBInterface` | LanceDB, PGVector, ChromaDB |
| Relational DB | `SQLAlchemyAdapter` | PostgreSQL, SQLite |
| Cache | `CacheDBInterface` | Redis, Filesystem |

### 2.3 Configuration Hooks

```python
# LLM Configuration (cognee/infrastructure/llm/config.py)
- llm_provider: openai, anthropic, groq, ollama, etc.
- llm_model: Model selection
- llm_api_key: API authentication
- llm_endpoint: Custom endpoints
- llm_temperature: Generation temperature
- llm_max_completion_tokens: Token limits

# Vector DB Configuration (cognee/infrastructure/databases/vector/config.py)
- vector_db_provider: lancedb, pgvector, chromadb
- vector_db_url: Connection URL
- vector_db_key: Authentication key

# Graph DB Configuration (cognee/infrastructure/databases/graph/config.py)
- graph_db_provider: neo4j, kuzu, neptune
- graph_database_url: Connection URL
- graph_database_username/password: Authentication
```

---

## 3. Memory Ingestion API Documentation

### 3.1 Data Flow Overview

```
Input Data
    ↓
[ingest_data] → File storage → Text extraction → Dataset storage
    ↓
[cognify] → Document classification → Chunking → Entity extraction
    ↓
Graph construction → Vector embedding → Storage indexing
```

### 3.2 Ingestion Pipeline (`cognee/tasks/ingestion/ingest_data.py`)

**Function Signature:**
```python
async def ingest_data(
    data: Any,
    dataset_name: str,
    user: User,
    node_set: Optional[List[str]] = None,
    dataset_id: UUID = None,
    preferred_loaders: dict[str, dict[str, Any]] = None,
)
```

**Supported Input Types:**
- Text strings
- File paths (local, S3, file://)
- Binary file objects (BinaryIO)
- URLs (HTTP/HTTPS)
- GitHub repository URLs
- Lists of mixed types

**Processing Steps:**
1. **Data Resolution**: Resolve file paths and validate accessibility
2. **Content Extraction**: Extract text from various formats
3. **Text Transformation**: Convert to standardized text files
4. **Dataset Storage**: Store processed content with metadata
5. **Permission Assignment**: Grant user permissions on dataset

### 3.3 Cognify Pipeline (`cognee/api/v1/cognify/cognify.py`)

**Function Signature:**
```python
async def cognify(
    datasets: Union[str, list[str], list[UUID]] = None,
    user: User = None,
    graph_model: BaseModel = KnowledgeGraph,
    chunker=TextChunker,
    chunk_size: int = None,
    chunks_per_batch: int = None,
    config: Config = None,
    vector_db_config: dict = None,
    graph_db_config: dict = None,
    run_in_background: bool = False,
    incremental_loading: bool = True,
    custom_prompt: Optional[str] = None,
    temporal_cognify: bool = False,
    data_per_batch: int = 20,
)
```

**Processing Pipeline:**
1. **Document Classification**: Identifies document types
2. **Text Chunking**: Paragraph-based semantic segmentation
3. **Entity Extraction**: LLM-based entity identification
4. **Relationship Detection**: Connection discovery
5. **Graph Construction**: Knowledge graph building
6. **Content Summarization**: Hierarchical summaries

### 3.4 Data Models

**Data Model (`cognee/modules/data/models/Data.py`):**
```python
class Data(Base):
    id: UUID                    # Primary key
    label: str                  # Optional label
    name: str                   # File name
    extension: str              # File extension
    mime_type: str              # MIME type
    loader_engine: str          # Loader used
    raw_data_location: str      # Storage location
    content_hash: str           # Content fingerprint
    external_metadata: JSON     # Custom metadata
    node_set: JSON              # Graph organization
    pipeline_status: JSON       # Processing status
    token_count: int            # Token count
    data_size: int              # File size in bytes
    owner_id: UUID              # Owner reference
    created_at: DateTime
    updated_at: DateTime
```

---

## 4. Storage Abstractions

### 4.1 Graph Storage Abstraction

**Interface:** `cognee/infrastructure/databases/graph/graph_db_interface.py`

```python
class GraphDBInterface(ABC):
    # Core operations
    async def query(self, query: str, params: dict) -> List[Any]
    async def add_node(self, node: Union[DataPoint, str], properties: Optional[Dict])
    async def add_nodes(self, nodes: Union[List[Node], List[DataPoint]])
    async def add_edge(self, source_id: str, target_id: str, relationship_name: str, properties: Dict)
    async def add_edges(self, edges: List[EdgeData])
    async def get_node(self, node_id: str)
    async def get_nodes(self, node_ids: List[str])
    async def delete_node(self, node_id: str)
    async def delete_graph(self)
    async def has_edge(self, source_id: str, target_id: str, relationship_name: str)
    async def get_neighbors(self, node_id: str, edge_type: Optional[str])
    async def get_graph_data(self, node_id: Optional[str])
    async def get_graph_metrics(self)
```

**Neo4j Implementation (`cognee/infrastructure/databases/graph/neo4j_driver/adapter.py`):**
- Uses `neo4j.AsyncGraphDatabase` driver
- Supports connection pooling with `max_connection_lifetime=120`
- Implements deadlock retry mechanism
- Provides graph metrics (clustering, density, paths)
- Uniqueness constraint on `__Node__.id`

**Key Features:**
- Cypher query support
- Transaction support
- Connection retry logic
- Distributed task queue integration
- Metrics collection

### 4.2 Vector Storage Abstraction

**Interface:** `cognee/infrastructure/databases/vector/vector_db_interface.py`

```python
class VectorDBInterface(Protocol):
    # Collection management
    async def has_collection(self, collection_name: str) -> bool
    async def create_collection(self, collection_name: str, payload_schema: Optional[Any])
    
    # Data operations
    async def create_data_points(self, collection_name: str, data_points: List[DataPoint])
    async def retrieve(self, collection_name: str, data_point_ids: list[str])
    
    # Search
    async def search(
        self,
        collection_name: str,
        query_text: Optional[str],
        query_vector: Optional[List[float]],
        limit: Optional[int],
        with_vector: bool = False,
        include_payload: bool = False,
        node_name: Optional[List[str]] = None,
    )
```

**PGVector Implementation (`cognee/infrastructure/databases/vector/pgvector/PGVectorAdapter.py`):**
- Uses SQLAlchemy with asyncpg
- Integrates with pgvector extension
- Supports HNSW indexing
- Handles embedding via configurable engines
- Batch operations with retry logic

**Supported Vector Databases:**
- **LanceDB**: Embedded, file-based
- **PGVector**: PostgreSQL extension
- **ChromaDB**: Standalone vector DB

### 4.3 Embedding Engines

**Location:** `cognee/infrastructure/databases/vector/embeddings/`

| Engine | Provider | Use Case |
|--------|----------|----------|
| FastembedEmbeddingEngine | Fastembed | Local embedding |
| LiteLLMEmbeddingEngine | LiteLLM | Multi-provider |
| OllamaEmbeddingEngine | Ollama | Self-hosted |

---

## 5. Security Assessment

### 5.1 HIGH Severity Findings

#### 5.1.1 Code Injection via `exec()` in Graph Model Generation

**Location:** `cognee/shared/graph_model_utils.py:46`

```python
# Vulnerable code:
exec(result, mod.__dict__)
```

**Risk:** Dynamic code execution from potentially untrusted JSON schema input. If an attacker can control the Pydantic JSON schema input, they can execute arbitrary Python code.

**Mitigation:** Input validation and sandboxing required before executing generated code.

#### 5.1.2 Shell Injection in UI/CLI Components

**Locations:**
- `cognee/api/v1/ui/npm_utils.py:17-25` - `shell=True` with npm commands
- `cognee/api/v1/ui/node_setup.py:45,57,163,174` - Node.js setup commands
- `cognee/eval_framework/modal_eval_dashboard.py:41` - Modal commands

**Risk:** Multiple uses of `shell=True` in subprocess calls could allow command injection if user-controlled input reaches these functions.

### 5.2 MEDIUM Severity Findings

#### 5.2.1 LLM API Key Exposure

**Location:** `cognee/infrastructure/llm/config.py`

**Risk:** API keys stored in environment variables without encryption. Keys logged in telemetry if not properly sanitized.

**Observation:** `strip_quotes_from_strings` validator removes quotes but doesn't mask sensitive values in logs.

#### 5.2.2 Unrestricted File Upload Paths

**Location:** `cognee/api/v1/add/routers/get_add_router.py`

**Risk:** File uploads accepted without strict validation of file types. Path traversal possible if filename sanitization fails.

#### 5.2.3 Cypher Query Injection Potential

**Location:** `cognee/infrastructure/databases/graph/neo4j_driver/adapter.py`

**Risk:** Dynamic Cypher query construction. While parameterized queries are used in most places, string formatting for relationship types could be vulnerable.

### 5.3 LOW Severity Findings

#### 5.3.1 Default User Credentials

**Risk:** Default user created automatically if no authentication configured (`get_default_user()`).

#### 5.3.2 Debug Mode Information Disclosure

**Risk:** Stack traces and debug information may leak in error responses if DEBUG mode enabled.

### 5.4 Security Strengths

| Feature | Implementation |
|---------|---------------|
| Authentication | FastAPI-Users with JWT |
| Authorization | Role-based permissions (RBAC) |
| Input Validation | Pydantic models throughout API |
| Database Security | Parameterized queries (mostly) |
| Rate Limiting | Built-in rate limit support |
| Telemetry | Optional, configurable |

### 5.5 Authentication Hooks

**Primary Authentication:** `cognee/modules/users/methods/get_authenticated_user.py`

- JWT-based authentication via FastAPI-Users
- API bearer token support
- Default user fallback for local development

**Permission System:** `cognee/modules/users/permissions/`

- Dataset-level permissions (read/write/delete/share)
- Tenant isolation
- Role-based access control

---

## 6. Dependency Compatibility Matrix

### 6.1 Cognee Dependencies (v0.5.3)

| Package | Cognee Version | HadesPy Version | Conflict |
|---------|---------------|-----------------|----------|
| fastapi | >=0.116.2,<1.0.0 | >=0.115.0 | ⚠️ Minor version diff |
| pydantic | >=2.10.5 | >=2.10.0 | ✅ Compatible |
| pydantic-settings | >=2.2.1,<3 | >=2.7.0 | ✅ Compatible |
| uvicorn | >=0.34.0,<1.0.0 | >=0.34.0 | ✅ Compatible |
| neo4j | >=5.28.0,<6 (optional) | >=5.15.0 | ✅ Compatible |
| asyncpg | >=0.30.0,<1.0.0 | >=0.29.0 | ⚠️ HadesPy needs upgrade |
| sqlalchemy | >=2.0.39,<3.0.0 | Not specified | ⚠️ Need verification |
| numpy | >=1.26.4,<=4.0.0 | >=1.26.0 | ✅ Compatible |
| openai | >=1.80.1 | Not specified | ⚠️ May conflict |
| tenacity | >=9.0.0 | >=9.0.0 | ✅ Compatible |
| python-dotenv | >=1.0.1,<2.0.0 | >=1.0.0 | ✅ Compatible |

### 6.2 Version Conflicts Identified

1. **asyncpg**: Cognee requires `>=0.30.0`, HadesPy uses `>=0.29.0` - **Upgrade recommended**

2. **fastapi**: Cognee requires `>=0.116.2`, HadesPy uses `>=0.115.0` - **Minor version difference, should be compatible**

3. **SQLAlchemy**: Cognee requires `>=2.0.39`, HadesPy doesn't specify - **Need to add constraint**

4. **cognee**: HadesPy references `cognee>=0.1.0` which is very outdated - **Update to v0.5.3**

### 6.3 Optional Dependencies for Integration

To use Cognee with HadesPy's existing infrastructure:

```toml
# Required for Neo4j integration (HadesPy uses Neo4j)
neo4j = ["neo4j>=5.28.0,<6"]

# Required for PostgreSQL/PGVector
postgres = ["psycopg2>=2.9.10,<3", "pgvector>=0.3.5,<0.4", "asyncpg>=0.30.0,<1.0.0"]

# Optional but recommended
langchain = ["langsmith>=0.2.3,<1.0.0", "langchain_text_splitters>=0.3.2,<1.0.0"]
dev = ["pytest>=7.4.0,<8", "pytest-asyncio>=0.21.1,<0.22"]
```

---

## 7. Integration Recommendations

### 7.1 Recommended Architecture

```
HadesPy API Layer
       ↓
Cognee Client (cognee/api/client.py)
       ↓
   +-------------------+  +-------------------+
   |   Vector Store    |  |    Graph Store    |
   |   (PGVector)      |  |    (Neo4j)        |
   +-------------------+  +-------------------+
```

### 7.2 Key Files for Integration

1. **Client Interface:** `cognee/api/client.py` - Main Python API
2. **Add Data:** `cognee/api/v1/add/add.py` - Data ingestion
3. **Search:** `cognee/api/v1/search/search.py` - Query interface
4. **Settings:** `cognee/modules/settings/get_settings.py` - Configuration

### 7.3 Configuration Requirements

Environment variables required:

```bash
# LLM Configuration
LLM_API_KEY=your_api_key
LLM_PROVIDER=openai
LLM_MODEL=openai/gpt-5-mini

# Vector Database
VECTOR_DB_PROVIDER=pgvector
VECTOR_DB_URL=postgresql+asyncpg://user:pass@localhost/db

# Graph Database
GRAPH_DB_PROVIDER=neo4j
GRAPH_DATABASE_URL=bolt://localhost:7687
GRAPH_DATABASE_USERNAME=neo4j
GRAPH_DATABASE_PASSWORD=password

# Relational Database (for metadata)
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/db
```

### 7.4 Risk Mitigation Priorities

1. **HIGH**: Sanitize inputs to `graph_model_utils.py` before `exec()` call
2. **HIGH**: Review all `shell=True` subprocess calls
3. **MEDIUM**: Upgrade asyncpg to >=0.30.0 in HadesPy
4. **MEDIUM**: Implement input validation for file uploads
5. **LOW**: Review Cypher query construction for injection risks

---

## 8. Appendix

### 8.1 File References

| Purpose | Path |
|---------|------|
| Main Config | `cognee/base_config.py` |
| LLM Config | `cognee/infrastructure/llm/config.py` |
| Graph Interface | `cognee/infrastructure/databases/graph/graph_db_interface.py` |
| Vector Interface | `cognee/infrastructure/databases/vector/vector_db_interface.py` |
| Neo4j Adapter | `cognee/infrastructure/databases/graph/neo4j_driver/adapter.py` |
| PGVector Adapter | `cognee/infrastructure/databases/vector/pgvector/PGVectorAdapter.py` |
| Add Router | `cognee/api/v1/add/routers/get_add_router.py` |
| Search Router | `cognee/api/v1/search/routers/get_search_router.py` |
| User Auth | `cognee/modules/users/methods/get_authenticated_user.py` |

### 8.2 Analysis Methodology

- Static code analysis of v0.5.3 tag
- Dependency comparison with HadesPy pyproject.toml
- Security pattern matching for common vulnerabilities
- Architecture review of storage abstractions

---

*Analysis completed by Kilo Code on 2026-03-02*
