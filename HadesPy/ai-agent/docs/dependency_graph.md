# AI Agent Dependency Graph

**Generated**: 2026-03-01  
**Branch**: feature/cognee-architecture-rewrite  
**Commit**: Pre-cognee-rewrite checkpoint

## Overview

This document maps the dependencies and import relationships within the AI Agent codebase to understand module coupling before the Cognee architecture rewrite.

## External Dependencies (from pyproject.toml)

### Core API Framework
| Package | Version | Purpose |
|---------|---------|---------|
| fastapi | >=0.115.0 | Web framework |
| pydantic | >=2.10.0 | Data validation |
| uvicorn | >=0.34.0 | ASGI server |
| httpx | >=0.28.0 | HTTP client |
| anyio | >=4.7.0 | Async compatibility |

### MCP (Model Context Protocol)
| Package | Version | Purpose |
|---------|---------|---------|
| fastmcp | >=0.4.0 | MCP server implementation |

### Directus Integration
| Package | Version | Purpose |
|---------|---------|---------|
| directus-sdk-py | >=1.0.0 | Directus CMS client |

### Memory / RAG
| Package | Version | Purpose |
|---------|---------|---------|
| cognee | >=0.1.0 | Core RAG framework (to be integrated) |
| sentence-transformers | >=3.3.0 | Text embeddings |

### Ranking / ML
| Package | Version | Purpose |
|---------|---------|---------|
| xgboost | >=2.0.0 | Learning-to-rank |
| numpy | >=1.26.0 | Numerical operations |
| pandas | >=2.2.0 | Data manipulation |
| scipy | >=1.12.0 | Scientific computing |

### UI
| Package | Version | Purpose |
|---------|---------|---------|
| gradio | >=5.12.0 | Web UI |
| streamlit | >=1.41.0 | Alternative UI |

### Database
| Package | Version | Purpose |
|---------|---------|---------|
| asyncpg | >=0.29.0 | PostgreSQL async driver |
| neo4j | >=5.15.0 | Neo4j graph database |

### Observability & Utilities
| Package | Version | Purpose |
|---------|---------|---------|
| prometheus-client | >=0.21.0 | Metrics |
| structlog | >=24.4.0 | Structured logging |
| pydantic-settings | >=2.7.0 | Configuration |
| python-dotenv | >=1.0.0 | Environment variables |
| tenacity | >=9.0.0 | Retry logic |
| orjson | >=3.10.0 | JSON serialization |

---

## Internal Module Dependency Graph

### Layer Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         PRESENTATION LAYER                       │
│  ┌──────────────┐  ┌──────────────┐                             │
│  │ ui_gradio.py │  │ui_streamlit.py│                            │
│  └──────┬───────┘  └──────┬───────┘                             │
├─────────┼─────────────────┼──────────────────────────────────────┤
│         │                 │           API LAYER                  │
│         │                 │          ┌──────────┐                │
│         │                 └─────────▶│ main.py  │                │
│         │                            └────┬─────┘                │
│         │                                 │                       │
├─────────┼─────────────────────────────────┼──────────────────────┤
│         │           SERVICE LAYER         │                       │
│         │    ┌──────────┐  ┌──────────┐  │  ┌──────────┐         │
│         └───▶│mcp_tools.py│  │directus_ │◀─┘  │ memory.py│         │
│              └──────────┘  │client.py │     └────┬─────┘         │
│                            └──────────┘          │               │
│                                                  ▼               │
│              ┌────────────────────────────────────────────────┐  │
│              │              RAG PIPELINE                       │  │
│              │  ┌──────────────┐    ┌──────────────────────┐  │  │
│              │  │rag/course_   │───▶│ranking/xgboost_ranker│  │  │
│              │  │recommender.py│    └──────────────────────┘  │  │
│              │  └──────┬───────┘                               │  │
│              │         │                                       │  │
│              │         ▼                                       │  │
│              │  ┌──────────────┐    ┌──────────────┐           │  │
│              │  │graph/course_ │◀──▶│vector/course_│           │  │
│              │  │graph.py      │    │store.py      │           │  │
│              │  └──────────────┘    └──────────────┘           │  │
│              └────────────────────────────────────────────────┘  │
├──────────────────────────────────────────────────────────────────┤
│                         DATA LAYER                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │database/neo4j│  │database/pg_  │  │ memory_graph │           │
│  │_spatial.py   │  │client.py     │  │vector_store  │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
│  ┌──────────────┐  ┌──────────────┐                              │
│  │database/spat │  │core/spatial_ │                              │
│  │ial_factory.py│  │interface.py  │                              │
│  └──────────────┘  └──────────────┘                              │
├──────────────────────────────────────────────────────────────────┤
│                      INFRASTRUCTURE LAYER                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │ config.py    │  │logging_config│  │ integrations/│           │
│  │              │  │.py           │  │directus_neo4j│           │
│  └──────────────┘  └──────────────┘  │_bridge.py    │           │
│                                       └──────────────┘           │
└──────────────────────────────────────────────────────────────────┘
```

### Detailed Import Dependencies

#### Core Infrastructure (Foundation Layer)
```
config.py
    └── (no internal dependencies - base layer)

logging_config.py
    └── config.py
```

#### Memory Layer
```
memory.py
    ├── config.py
    └── logging_config.py

memory_graph.py
    ├── config.py
    ├── logging_config.py
    └── memory.py (CogneeMemory, MemoryChunk)

vector_store.py
    ├── config.py
    └── logging_config.py
```

#### Database Layer
```
core/spatial_interface.py
    └── (no internal dependencies - interface definitions)

database/neo4j_spatial.py
    ├── core/spatial_interface.py (Point, Polygon, SpatialBackend, etc.)
    └── logging_config.py

database/spatial_factory.py
    ├── config.py
    ├── core/spatial_interface.py (SpatialBackend)
    └── logging_config.py

database/postgres_client.py
    └── (assumed: config.py, logging_config.py)
```

#### Vector & Graph Layer
```
vector/course_store.py
    ├── config.py
    └── logging_config.py

graph/course_graph.py
    ├── config.py
    └── logging_config.py
```

#### RAG Pipeline Layer
```
rag/course_recommender.py
    ├── config.py
    ├── graph/course_graph.py (CourseGraph, CourseNode)
    ├── llm/adapter.py (LLMAdapter)
    ├── logging_config.py
    └── vector/course_store.py (CourseSearchResult, CourseVectorStore)
    └── [optional] ranking/xgboost_ranker.py (CourseRanker)
```

#### Ranking Layer
```
ranking/config.py
    └── (no internal dependencies)

ranking/training_data.py
    └── ranking/config.py

ranking/xgboost_ranker.py
    ├── logging_config.py
    ├── ranking/config.py (get_ranking_config, RankingConfig)
    ├── ranking/training_data.py (TrainingExample, TrainingDataGenerator)
    └── rag/course_recommender.py (CourseRecommendation)
```

#### LLM Layer
```
llm/adapter.py
    ├── config.py
    └── logging_config.py
```

#### Integration Layer
```
integrations/directus_neo4j_bridge.py
    ├── config.py
    └── logging_config.py
```

#### Directus Client
```
directus_client.py
    ├── config.py
    └── logging_config.py
```

#### MCP Tools Layer
```
mcp_tools.py
    ├── config.py
    ├── directus_client.py (get_directus_client)
    ├── logging_config.py
    └── memory.py (get_memory)
```

#### UI Layer
```
ui_gradio.py
    ├── config.py
    └── logging_config.py

ui_streamlit.py
    ├── config.py
    └── logging_config.py
```

#### Application Entry Point
```
main.py
    ├── config.py (get_settings)
    ├── database/spatial_factory.py (close_spatial_backend)
    ├── directus_client.py (get_directus_client, init_directus)
    ├── logging_config.py (configure_logging, get_logger)
    ├── memory.py (get_memory, init_memory)
    ├── memory_graph.py (close_graph_memory, init_graph_memory)
    └── mcp_tools.py (get_mcp)
```

---

## Dependency Statistics

### By Layer

| Layer | Module Count | External Dependencies |
|-------|-------------|----------------------|
| Infrastructure | 2 | pydantic, pydantic-settings, structlog |
| Memory | 3 | numpy, sentence-transformers, sqlite3 |
| Database | 4 | neo4j, asyncpg |
| Vector/Graph | 2 | lancedb (optional), pyarrow (optional) |
| RAG | 1 | (depends on vector, graph, ranking) |
| Ranking | 3 | xgboost, numpy, pandas |
| LLM | 1 | (external API calls) |
| Integration | 1 | directus-sdk-py |
| MCP | 1 | fastmcp |
| UI | 2 | gradio, streamlit |
| API | 1 | fastapi, uvicorn |

### Circular Dependencies

**Current Status**: No circular dependencies detected between internal modules.

**Potential Risk Areas**:
- `ranking/xgboost_ranker.py` imports from `rag/course_recommender.py` (CourseRecommendation)
- This creates a one-way dependency from ranking → rag

---

## Cognee Integration Points

### Modules to be Replaced/Enhanced

1. **memory.py** - Will be replaced with cognee.Memory
2. **memory_graph.py** - Will be replaced with cognee.GraphMemory
3. **vector_store.py** - Will be replaced with cognee.VectorStore
4. **vector/course_store.py** - Will use cognee abstractions

### Modules Requiring Adaptation

1. **rag/course_recommender.py** - Needs cognee adapter
2. **graph/course_graph.py** - May integrate with cognee graph layer
3. **mcp_tools.py** - Memory operations need cognee interface
4. **main.py** - Initialization sequence changes

### Unchanged Modules

1. **ranking/xgboost_ranker.py** - Pure ML, no direct cognee dependency
2. **llm/adapter.py** - LLM interface stays
3. **database/neo4j_spatial.py** - Spatial operations remain
4. **config.py** - Add cognee configuration options

---

## Migration Risk Assessment

| Module | Risk Level | Reason |
|--------|-----------|--------|
| memory.py | **HIGH** | Core functionality replacement |
| memory_graph.py | **HIGH** | Graph memory rewrite |
| vector_store.py | **MEDIUM** | Storage backend change |
| rag/course_recommender.py | **MEDIUM** | Pipeline integration |
| mcp_tools.py | **MEDIUM** | Memory interface changes |
| main.py | **LOW** | Initialization changes only |
| ranking/* | **LOW** | Unchanged interface |
| config.py | **LOW** | Add settings only |

---

## Notes

- All modules follow a consistent pattern: import from `config.py` and `logging_config.py`
- The architecture is relatively well-layered with no circular dependencies
- The RAG pipeline has clear separation between retrieval (vector/graph) and ranking
- Cognee integration will primarily affect the memory and storage layers
