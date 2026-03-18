# Current AI Agent Architecture

**Generated**: 2026-03-01  
**Branch**: feature/cognee-architecture-rewrite  
**Purpose**: Document the current memory and retrieval pipeline before Cognee integration

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Memory Layer](#memory-layer)
   - [CogneeMemory (memory.py)](#cogneememory-memorypy)
   - [GraphMemory (memory_graph.py)](#graphmemory-memory_graphpy)
3. [Vector Storage](#vector-storage)
   - [LanceVectorStore (vector_store.py)](#lancevectorstore-vector_storepy)
   - [CourseVectorStore (vector/course_store.py)](#coursevectorstore-vectorcourse_storepy)
4. [Graph Layer](#graph-layer)
   - [CourseGraph (graph/course_graph.py)](#coursegraph-graphcourse_graphpy)
   - [Neo4jSpatialBackend (database/neo4j_spatial.py)](#neo4jspatialbackend-databaseneo4j_spatialpy)
5. [Ranking Layer](#ranking-layer)
   - [CourseRanker (ranking/xgboost_ranker.py)](#courseranker-rankingxgboost_rankerpy)
6. [RAG Pipeline](#rag-pipeline)
   - [CourseRecommender (rag/course_recommender.py)](#courserecommender-ragcourse_recommenderpy)
7. [Data Flow](#data-flow)
8. [Configuration](#configuration)

---

## Architecture Overview

The AI Agent uses a **4-Stage Retrieval-Augmented Generation (RAG) Pipeline** for course recommendations:

```
┌─────────────────────────────────────────────────────────────────────┐
│                     RAG PIPELINE ARCHITECTURE                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   Stage 1: Graph Filter                                              │
│   ┌──────────────┐     ┌──────────────┐                             │
│   │ Student Prefs│────▶│ CourseGraph  │──┐                         │
│   └──────────────┘     └──────────────┘  │                          │
│                                          ▼                          │
│   Stage 2: Vector Retrieval         ┌──────────┐                    │
│   ┌──────────────┐                  │ Filtered │                    │
│   │ Query Embed  │───────────────▶  │ Courses  │                    │
│   └──────────────┘                  └────┬─────┘                    │
│                                          │                          │
│   Stage 3: Feature Engineering           ▼                          │
│   ┌──────────────┐     ┌──────────────┐ ┌──────────┐               │
│   │CourseFeatures│◀────│CourseVector  │◀│Vector DB │               │
│   └──────┬───────┘     │   Store      │ └──────────┘               │
│          │             └──────────────┘                              │
│          ▼                                                          │
│   Stage 4: XGBoost Ranking                                          │
│   ┌──────────────┐     ┌──────────────┐                             │
│   │CourseRanker  │────▶│Final Recommend│                            │
│   └──────────────┘     └──────────────┘                             │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Memory Layer

### CogneeMemory (memory.py)

**File**: [`src/memory.py`](../src/memory.py)

**Purpose**: Base memory system using sentence-transformers for embeddings and SQLite for storage.

**Key Components**:

```python
@dataclass
class MemoryChunk:
    id: Optional[str]
    text: str
    embedding: Optional[List[float]] = None
    metadata: Optional[Dict[str, Any]] = None
    score: Optional[float] = None

class CogneeMemory:
    # Uses sentence-transformers for embeddings
    # Stores vectors in SQLite with BLOB encoding
    # Supports similarity search via numpy operations
```

**Storage Schema** (SQLite):
```sql
CREATE TABLE memory_chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT NOT NULL,
    embedding BLOB NOT NULL,
    metadata TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Key Methods**:
- `add(text, metadata)` - Add memory with automatic embedding
- `search(query, top_k)` - Semantic similarity search
- `get_context(query, n_chunks)` - Get contextual memory

**Dependencies**:
- `sentence-transformers` - Embedding model
- `numpy` - Vector operations
- `sqlite3` - Vector storage

---

### GraphMemory (memory_graph.py)

**File**: [`src/memory_graph.py`](../src/memory_graph.py)

**Purpose**: Extends CogneeMemory with Neo4j graph relationships for contextual memory traversal.

**Architecture**:
```
┌─────────────────────────────────────────────────────────┐
│                    GraphMemory                           │
├─────────────────────────────────────────────────────────┤
│                                                          │
│   Vector Layer (inherited from CogneeMemory)            │
│   ┌─────────────────────────────────────────────────┐   │
│   │  SQLite + sentence-transformers                 │   │
│   │  - Text embeddings                              │   │
│   │  - Vector similarity search                     │   │
│   └─────────────────────────────────────────────────┘   │
│                          ▲                              │
│                          │ extends                      │
│   Graph Layer           │                              │
│   ┌─────────────────────────────────────────────────┐   │
│   │  Neo4j Graph Database                           │   │
│   │  - MemoryNode (content, embedding_id)           │   │
│   │  - RELATED_TO relationships                     │   │
│   │  - TEMPORALLY_FOLLOWS relationships             │   │
│   │  - SEMANTICALLY_SIMILAR relationships           │   │
│   └─────────────────────────────────────────────────┘   │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**Graph Schema** (Neo4j):
```cypher
// Memory nodes
(M:MemoryNode {id, content_hash, created_at, embedding_id})

// Relationships
(M1)-[:RELATED_TO {strength, type}]->(M2)
(M1)-[:TEMPORALLY_FOLLOWS]->(M2)
(M1)-[:SEMANTICALLY_SIMILAR {score}]->(M2)
```

**Key Methods**:
- `add(text, metadata, relationships)` - Add with graph relationships
- `get_context_graph(query, depth)` - Graph-based context retrieval
- `find_related(memory_id, relationship_type)` - Traverse relationships
- `create_relationship(from_id, to_id, rel_type, properties)` - Add edges

**Dependencies**:
- `neo4j` - Async Neo4j driver
- Inherits from `CogneeMemory`

---

## Vector Storage

### LanceVectorStore (vector_store.py)

**File**: [`src/vector_store.py`](../src/vector_store.py)

**Purpose**: High-performance vector storage using LanceDB with native vector indexing.

**Features**:
- Native vector indexing (IVF-PQ, HNSW)
- Columnar storage format (Arrow/Parquet compatible)
- Efficient similarity search
- Fallback to numpy brute-force if LanceDB unavailable

**Schema**:
```python
@dataclass
class VectorRecord:
    id: str
    vector: List[float]  # 384-dimensional by default
    text_preview: str
    metadata: Dict[str, Any]
    created_at: datetime
    score: Optional[float] = None
```

**Index Types**:
- `IVF_PQ` - Inverted File Index with Product Quantization (default)
- `HNSW` - Hierarchical Navigable Small World
- `NONE` - No index (full scan)

**Key Methods**:
- `add(id, vector, text, metadata)` - Add vector record
- `search(vector, top_k, filters)` - Similarity search with filters
- `delete(id)` - Remove record
- `update(id, vector, metadata)` - Update existing record

**Dependencies**:
- `lancedb` - Vector database (optional, with fallback)
- `pyarrow` - Columnar data format
- `numpy` - Vector operations

---

### CourseVectorStore (vector/course_store.py)

**File**: [`src/vector/course_store.py`](../src/vector/course_store.py)

**Purpose**: Course-specific vector storage with hybrid search capabilities.

**Schema**:
```python
@dataclass
class CourseVectorRecord:
    course_id: str
    name: str
    department: str
    embedding: List[float]  # 384 dims
    math_intensity: float
    humanities_intensity: float
    career_paths: List[str]
    credits: int = 0
    description: str = ""
    additional_metadata: Dict[str, Any]
```

**Search Methods**:
1. **Vector Search**: `search_similar(embedding, top_k)`
2. **Career Search**: `search_by_career(career_goal, top_k)`
3. **Hybrid Search**: Combines vector + metadata filters

**Hybrid Search Example**:
```python
results = await store.search_hybrid(
    embedding=query_embedding,
    career_goal="software_engineer",
    department_filter=["cs", "math"],
    min_math_intensity=0.5,
    top_k=10
)
```

**Dependencies**:
- `numpy` - Vector operations
- `lancedb` - Storage backend

---

## Graph Layer

### CourseGraph (graph/course_graph.py)

**File**: [`src/graph/course_graph.py`](../src/graph/course_graph.py)

**Purpose**: Neo4j graph operations for course management and discovery.

**Node Types**:
```cypher
(Course {
    id: string,
    name: string,
    description: string,
    department: string,
    credits: integer,
    math_intensity: float,
    humanities_intensity: float,
    career_paths: list,
    embedding: list  // 384-dim vector
})

(Department {
    code: string,
    name: string
})
```

**Relationship Types**:
```cypher
(c:Course)-[:PREREQUISITE {required: boolean}]->(c2:Course)
(c:Course)-[:SIMILAR_TO {score: float}]->(c2:Course)
(c:Course)-[:BELONGS_TO]->(d:Department)
(d:Department)-[:OFFERS]->(c:Course)
```

**Key Methods**:
- `create_course(properties)` - Create course node
- `create_prerequisite(course_id, prereq_id)` - Link prerequisites
- `find_similar_courses(course_id, threshold)` - Find similar courses
- `get_prerequisite_chain(course_id)` - Get full prerequisite tree
- `search_by_career(career_goal)` - Find courses for career path
- `create_similarity_edges(batch_size)` - Auto-create SIMILAR_TO edges

**Indexes**:
```cypher
CREATE INDEX course_id_idx FOR (c:Course) ON (c.id);
CREATE INDEX course_dept_idx FOR (c:Course) ON (c.department);
CREATE INDEX course_careers_idx FOR (c:Course) ON (c.career_paths);
```

**Dependencies**:
- `neo4j` - Async Neo4j driver

---

### Neo4jSpatialBackend (database/neo4j_spatial.py)

**File**: [`src/database/neo4j_spatial.py`](../src/database/neo4j_spatial.py)

**Purpose**: Spatial operations backend using Neo4j's native point types.

**Implements**: [`SpatialBackend`](src/core/spatial_interface.py) interface

**Features**:
- Point geometry storage and queries
- k-Nearest Neighbor search
- Distance-based filtering
- Polygon intersection queries

**Schema**:
```cypher
(e:EntityType {
    id: string,
    location: point({latitude: y, longitude: x}),
    metadata: map
})
```

**Key Methods**:
- `insert(entity)` - Store spatial entity
- `find_k_nearest(point, entity_type, k)` - kNN search
- `find_within_distance(point, entity_type, distance)` - Distance filter
- `find_intersecting(polygon, entity_type)` - Polygon intersection

**PostGIS Equivalents**:
| PostGIS | Neo4j Cypher |
|---------|--------------|
| `ST_DWithin` | `point.distance() <= threshold` |
| `kNN <->` | `ORDER BY point.distance() LIMIT k` |
| `ST_Intersects` | `point.distance() = 0` (for points) |
| `GIST INDEX` | `CREATE POINT INDEX` |

**Dependencies**:
- `neo4j` - Async Neo4j driver
- `core/spatial_interface.py` - Interface definitions

---

## Ranking Layer

### CourseRanker (ranking/xgboost_ranker.py)

**File**: [`src/ranking/xgboost_ranker.py`](../src/ranking/xgboost_ranker.py)

**Purpose**: XGBoost learning-to-rank for optimizing course recommendation ordering.

**Features**:
- Pairwise ranking (LambdaRank)
- Feature extraction from recommendations
- Model persistence
- Fallback to rule-based ranking if XGBoost unavailable

**Feature Schema**:
```python
feature_names = [
    "vector_similarity_score",      # Semantic similarity (0-1)
    "career_match_score",           # Career alignment (0-1)
    "math_intensity_match",         # Math interest alignment (0-1)
    "humanities_intensity_match",   # Humanities interest alignment (0-1)
    "graph_distance",               # Distance in course graph
    "prerequisite_score",           # Prerequisite satisfaction (0-1)
    "credits",                      # Course credits
    "department_match",             # Department preference match (0-1)
]
```

**Model Configuration**:
```python
objective = "rank:pairwise"  # LambdaRank
n_estimators = 100
max_depth = 6
learning_rate = 0.1
subsample = 0.8
colsample_bytree = 0.8
```

**Key Methods**:
- `train(training_data)` - Train ranker on labeled examples
- `rank(recommendations)` - Rerank recommendations
- `extract_features(rec)` - Convert recommendation to feature vector
- `save_model()` / `load_model()` - Model persistence

**Dependencies**:
- `xgboost` - Learning-to-rank model
- `numpy` - Feature vectors
- `pandas` - Data manipulation

---

## RAG Pipeline

### CourseRecommender (rag/course_recommender.py)

**File**: [`src/rag/course_recommender.py`](../src/rag/course_recommender.py)

**Purpose**: 4-stage RAG pipeline for course recommendations.

**Pipeline Stages**:

```
┌─────────────────────────────────────────────────────────────────┐
│  STAGE 1: GRAPH FILTER                                          │
│  ─────────────────────────────────────────────────────────────  │
│  Input: StudentPreferences {career_goal, completed_courses...}  │
│  ┌──────────────┐                                               │
│  │ CourseGraph  │── Query by career path, prerequisites        │
│  └──────────────┘                                               │
│  Output: candidate_course_ids[]                                 │
├─────────────────────────────────────────────────────────────────┤
│  STAGE 2: VECTOR RETRIEVAL                                      │
│  ─────────────────────────────────────────────────────────────  │
│  Input: query_embedding (from student prefs text)               │
│  ┌──────────────────┐                                           │
│  │ CourseVectorStore│── Semantic similarity search             │
│  └──────────────────┘                                           │
│  Output: vector_results[] with similarity scores                │
├─────────────────────────────────────────────────────────────────┤
│  STAGE 3: FEATURE ENGINEERING                                   │
│  ─────────────────────────────────────────────────────────────  │
│  Input: candidate courses + vector results                      │
│  ┌──────────────────┐                                           │
│  │ FeatureExtractor │── Combine scores into feature vectors    │
│  └──────────────────┘                                           │
│  Output: CourseRecommendation[] with features                   │
├─────────────────────────────────────────────────────────────────┤
│  STAGE 4: XGBOOST RANKING (optional)                            │
│  ─────────────────────────────────────────────────────────────  │
│  Input: CourseRecommendation[] with features                    │
│  ┌──────────────┐                                               │
│  │ CourseRanker │── Learning-to-rank reranking                 │
│  └──────────────┘                                               │
│  Output: Final sorted recommendations                           │
└─────────────────────────────────────────────────────────────────┘
```

**Data Structures**:

```python
@dataclass
class StudentPreferences:
    math_interest: float = 0.5
    humanities_interest: float = 0.5
    career_goal: str = ""
    constraints: List[str] = []  # e.g., ["high_math_required"]
    completed_courses: List[str] = []
    preferred_departments: List[str] = []
    max_credits: int = 18

@dataclass
class CourseRecommendation:
    course_id: str
    course_name: str
    department: str
    description: str
    career_paths: List[str]
    credits: int
    math_intensity: float
    humanities_intensity: float
    
    # Scores
    total_score: float
    vector_similarity_score: float
    career_match_score: float
    math_intensity_match: float
    humanities_intensity_match: float
    graph_distance: float
    prerequisite_score: float
    
    # XGBoost features
    features: Dict[str, float]
    
    # Context
    matched_careers: List[str]
    reason: str
```

**Key Methods**:
- `recommend(student_prefs, top_k)` - Main recommendation entry point
- `_stage1_graph_filter(prefs)` - Filter by career/prerequisites
- `_stage2_vector_retrieval(prefs, candidates)` - Semantic search
- `_stage3_feature_engineering(results, prefs)` - Build feature vectors
- `_stage4_ranking(recommendations)` - XGBoost reranking

**Configuration**:
```bash
USE_XGBOOST_RANKING=true  # Enable Stage 4
XGBOOST_MODEL_PATH=/path/to/model.json
```

**Dependencies**:
- `graph/course_graph.py` - Graph filtering
- `vector/course_store.py` - Vector retrieval
- `ranking/xgboost_ranker.py` - Ranking (optional)
- `llm/adapter.py` - Query embedding

---

## Data Flow

### Recommendation Request Flow

```
┌──────────┐     ┌──────────────┐     ┌──────────────────┐
│  Client  │────▶│  main.py     │────▶│ CourseRecommender│
└──────────┘     └──────────────┘     └────────┬─────────┘
                                               │
          ┌────────────────────────────────────┼────────────────────┐
          │                                    │                    │
          ▼                                    ▼                    ▼
   ┌──────────────┐                    ┌──────────────┐     ┌──────────────┐
   │ CourseGraph  │◀──────────────────▶│ VectorStore  │     │   XGBoost    │
   │   (Neo4j)    │                    │  (LanceDB)   │     │   Ranker     │
   └──────────────┘                    └──────────────┘     └──────────────┘
          │                                    │                    │
          │         ┌──────────────────────────┘                    │
          │         │                                               │
          ▼         ▼                                               ▼
   ┌─────────────────────────────────────────────────────────────────────┐
   │                    CourseRecommendation[]                           │
   │                    (sorted by total_score)                          │
   └─────────────────────────────────────────────────────────────────────┘
```

### Memory Storage Flow

```
┌──────────┐     ┌──────────────┐     ┌─────────────────────┐
│  Input   │────▶│ GraphMemory  │────▶│ CogneeMemory (base) │
│  Text    │     │add()         │     │ embedding + storage │
└──────────┘     └──────┬───────┘     └─────────────────────┘
                        │
                        ▼
               ┌─────────────────┐
               │ Neo4j Graph     │
               │ - MemoryNode    │
               │ - Relationships │
               └─────────────────┘
```

---

## Configuration

### Environment Variables

```bash
# Memory
COGNEE_EMBEDDING_MODEL=all-MiniLM-L6-v2
COGNEE_VECTOR_STORE=./data/vectors.db

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
NEO4J_DATABASE=neo4j

# Vector Store
LANCEDB_URI=./data/lancedb
VECTOR_DIMENSION=384

# Ranking
USE_XGBOOST_RANKING=true
XGBOOST_MODEL_PATH=./models/ranker.json

# LLM
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o
LLM_API_KEY=sk-...
```

### Settings Class (config.py)

```python
class Settings(BaseSettings):
    # Memory
    cognee_embedding_model: str = "all-MiniLM-L6-v2"
    cognee_vector_store: Path = Path("./data/vectors.db")
    
    # Neo4j
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"
    neo4j_database: str = "neo4j"
    
    # Vector store
    lancedb_uri: Path = Path("./data/lancedb")
    vector_dimension: int = 384
    
    # Ranking
    use_xgboost_ranking: bool = False
    xgboost_model_path: Path = Path("./models/ranker.json")
```

---

## Migration Notes for Cognee Integration

### Current Limitations

1. **Memory Layer**: Manual SQLite + sentence-transformers integration
2. **Graph Layer**: Direct Neo4j driver usage
3. **Vector Layer**: LanceDB with custom fallback logic
4. **Orchestration**: Custom 4-stage pipeline

### Cognee Replacement Strategy

| Component | Current | With Cognee |
|-----------|---------|-------------|
| Memory | `CogneeMemory` | `cognee.Memory` |
| Graph | `GraphMemory` | `cognee.GraphMemory` |
| Vector | `LanceVectorStore` | `cognee.VectorStore` |
| RAG | `CourseRecommender` | `cognee.RAGPipeline` + adapters |
| Embeddings | Manual ST loading | `cognee.Embedder` |

### Files Requiring Changes

1. **High Impact**:
   - `memory.py` - Replace with cognee.Memory
   - `memory_graph.py` - Replace with cognee.GraphMemory
   - `vector_store.py` - Replace with cognee.VectorStore

2. **Medium Impact**:
   - `rag/course_recommender.py` - Use cognee pipeline
   - `mcp_tools.py` - Update memory interface
   - `main.py` - Update initialization

3. **Low Impact**:
   - `ranking/xgboost_ranker.py` - No changes (post-processing)
   - `config.py` - Add cognee settings

---

## Appendix: File Locations

| Component | File Path | Lines |
|-----------|-----------|-------|
| CogneeMemory | [`src/memory.py`](../src/memory.py) | ~350 |
| GraphMemory | [`src/memory_graph.py`](../src/memory_graph.py) | ~450 |
| LanceVectorStore | [`src/vector_store.py`](../src/vector_store.py) | ~500 |
| CourseVectorStore | [`src/vector/course_store.py`](../src/vector/course_store.py) | ~900 |
| CourseGraph | [`src/graph/course_graph.py`](../src/graph/course_graph.py) | ~1000 |
| Neo4jSpatialBackend | [`src/database/neo4j_spatial.py`](../src/database/neo4j_spatial.py) | ~500 |
| CourseRanker | [`src/ranking/xgboost_ranker.py`](../src/ranking/xgboost_ranker.py) | ~450 |
| CourseRecommender | [`src/rag/course_recommender.py`](../src/rag/course_recommender.py) | ~900 |
