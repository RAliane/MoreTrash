# AI Agent Architecture Audit Report

**Date:** 2026-03-02  
**Auditor:** Phase 2 Architecture Review  
**Scope:** HadesPy ai-agent memory, graph, vector, ranking, and RAG pipeline layers  
**Reference:** ai_agent_full_stack.toml specification compliance

---

## Executive Summary

This audit identifies **7 critical architectural issues** across the AI agent system that violate the TOML specification's requirements for deterministic behavior, unified storage, and minimal security surface. The current architecture exhibits significant redundancy, unstable ordering, excessive graph traversal patterns, and hidden side effects that threaten production stability.

### Risk Distribution
| Severity | Count | Categories |
|----------|-------|------------|
| HIGH | 4 | Redundant storage, Multiple ranking, Security, Hidden side effects |
| MEDIUM | 9 | Graph traversal, Determinism, Overlapping sources |
| LOW | 3 | Documentation, Minor inconsistencies |

---

## 1. API Layer Issues

### Issue 1.1: Conditional Documentation Exposure
**Severity:** LOW  
**Location:** [`src/main.py`](../../src/main.py:117-119)

**Finding:** API documentation (`docs_url`, `redoc_url`) is conditionally exposed based on `is_development` flag, but the health check endpoint exposes internal configuration details regardless of environment.

```python
app = FastAPI(
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
)
```

**Risk:** Information leakage about graph mode and service architecture in production health responses.

**Recommendation:** Consistently apply environment-based exposure to all diagnostic endpoints.

---

## 2. Memory Layer Issues

### Issue 2.1: Redundant Embedding Storage - SQLite + Neo4j
**Severity:** HIGH  
**Location:** [`src/memory.py`](../../src/memory.py:1), [`src/memory_graph.py`](../../src/memory_graph.py:1)

**Finding:** The memory system stores embeddings in **three locations simultaneously**:
1. **SQLite** (BLOB storage) via `CogneeMemory` base class
2. **Neo4j** via `GraphMemory` node properties (embedding_id references)
3. Direct embedding storage in MemoryChunk nodes

```python
# In memory.py - SQLite storage
conn.execute("""
    INSERT INTO memory_chunks (text, embedding, metadata)
    VALUES (?, ?, ?)
""")

# In memory_graph.py - Neo4j also tracks embedding references
query = """
    CREATE (m:MemoryChunk {
        id: $id,
        embedding_model: $model
        -- embedding stored separately in SQLite
    })
"""
```

**Risk:** Data inconsistency, storage bloat, write amplification, synchronization complexity.

**Recommendation:** Consolidate to single storage backend (LanceDB) with Neo4j holding only relationship metadata.

### Issue 2.2: Hidden Side Effect - Auto-Created Graph Relationships
**Severity:** HIGH  
**Location:** [`src/memory_graph.py`](../../src/memory_graph.py:156-194)

**Finding:** The `add()` method silently creates `SEMANTICALLY_SIMILAR` relationships via `_link_similar_memories()`, executing vector searches and graph mutations as side effects.

```python
async def add(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> MemoryChunk:
    chunk = await super().add(text, metadata)  # Store in SQLite
    if self._is_graph_ready:
        await self._create_memory_node(chunk, text, metadata)
        await self._link_similar_memories(chunk, text)  # HIDDEN SIDE EFFECT
```

**Risk:** Unexpected performance degradation, graph bloat, non-deterministic relationship creation.

**Recommendation:** Extract relationship creation to explicit `link_similar()` method called by orchestrator, not base operation.

### Issue 2.3: Overlapping Memory Sources
**Severity:** MEDIUM  
**Location:** [`src/memory.py`](../../src/memory.py:312-321), [`src/memory_graph.py`](../../src/memory_graph.py:33)

**Finding:** Both `CogneeMemory` and `GraphMemory` maintain singleton instances, allowing direct access to base class bypassing graph layer.

```python
# Two different entry points to overlapping data
_memory_instance: Optional[CogneeMemory] = None  # memory.py
def get_memory() -> CogneeMemory:
    if _memory_instance is None:
        _memory_instance = CogneeMemory()
```

**Risk:** Data inconsistency when components use different memory instances.

**Recommendation:** Enforce unified memory interface; remove direct CogneeMemory singleton access.

### Issue 2.4: Unstable Ordering - No Deterministic Tie-Breaking
**Severity:** MEDIUM  
**Location:** [`src/memory.py`](../../src/memory.py:230-231)

**Finding:** Search results sorted only by similarity score without deterministic tie-breaker.

```python
results.sort(key=lambda x: x.score or 0, reverse=True)
# No secondary sort key for equal scores
```

**Risk:** Non-deterministic ordering of results with identical scores violates TOML determinism requirements.

**Recommendation:** Add secondary sort by `id` or `created_at` for deterministic ordering.

---

## 3. Graph Layer Issues

### Issue 3.1: Excessive Graph Traversal Patterns
**Severity:** MEDIUM  
**Location:** [`src/memory_graph.py`](../../src/memory_graph.py:342-384), [`src/graph/course_graph.py`](../../src/graph/course_graph.py:876-987)

**Finding:** Multiple variable-length path traversals without depth limits enforcement:

```python
# Variable-length pattern with user-controlled depth
query = """
    MATCH path = (seed)-[:SEMANTICALLY_SIMILAR|TEMPORALLY_FOLLOWS*1..$depth]-(related)
    WHERE related.id NOT IN $seed_ids
    WITH related, min(length(path)) as distance
    ORDER BY distance ASC
"""
```

**Risk:** Performance degradation on large graphs, potential query timeout, resource exhaustion.

**Recommendation:** 
- Cap maximum depth to 3
- Implement query timeouts
- Use apoc.path.expandConfig for controlled expansion

### Issue 3.2: Security Surface Expansion - Cypher Injection Risk
**Severity:** HIGH  
**Location:** [`src/database/neo4j_spatial.py`](../../src/database/neo4j_spatial.py:52-104), [`src/graph/course_graph.py`](../../src/graph/course_graph.py:908-926)

**Finding:** String concatenation used for relationship types in Cypher queries:

```python
# In course_graph.py - relationship type concatenation
relationship_types = "PREREQUISITE|PREREQUISITE_OF"
if include_similar:
    relationship_types += "|SIMILAR_TO"

result = await session.run("""
    MATCH path = (root:Course {id: $course_id})
        -[:""" + relationship_types + """*1..""" + str(depth) + """]-
        (connected:Course)
""")
```

**Risk:** While currently using hardcoded strings, pattern enables injection if extended to user input.

**Recommendation:** Use parameterized relationship type lists with APOC or validate against allowlist.

### Issue 3.3: Duplicate Graph Distance Calculations
**Severity:** MEDIUM  
**Location:** [`src/rag/course_recommender.py`](../../src/rag/course_recommender.py:731-760), [`src/graph/course_graph.py`](../../src/graph/course_graph.py:876-987)

**Finding:** Graph distance computed separately for each candidate course in RAG stage 3, causing N+1 query pattern:

```python
async def _calculate_graph_distance(self, course_id: str, completed_courses: List[str]) -> float:
    for completed_id in completed_courses:
        subgraph = await self.graph.get_course_subgraph(completed_id, depth=3)
        # Each iteration executes full graph traversal
```

**Risk:** O(N×M) query complexity, database overload with many candidates.

**Recommendation:** Batch distance calculations or use Neo4j's `apoc.algo.dijkstra` for multi-source shortest paths.

---

## 4. Vector Layer Issues

### Issue 4.1: Redundant Embedding Storage - Multiple Vector Stores
**Severity:** HIGH  
**Location:** [`src/vector_store.py`](../../src/vector_store.py:1), [`src/vector/course_store.py`](../../src/vector/course_store.py:1)

**Finding:** **Three separate vector storage systems** maintain overlapping embeddings:

| Store | Backend | Purpose | Embedding Duplication |
|-------|---------|---------|----------------------|
| `LanceVectorStore` | LanceDB | Generic vectors | All memory embeddings |
| `CourseVectorStore` | LanceDB | Course-specific | Course embeddings only |
| `CogneeMemory` | SQLite | Memory chunks | All memory embeddings |
| `CourseGraph` | Neo4j | Course nodes | Course embeddings |

```python
# LanceVectorStore stores embeddings
course_vectors.lance: vector + metadata

# CourseVectorStore separately stores
course_embeddings.lance: vector + course fields

# Neo4j Course nodes ALSO store
(c:Course {embedding: [...]})  # Same embeddings!
```

**Risk:** 4x storage overhead for course embeddings, consistency issues, update complexity.

**Recommendation:** Consolidate to single LanceDB instance with separate tables; Neo4j holds only IDs.

### Issue 4.2: SQL Injection Risk in Vector Filters
**Severity:** MEDIUM  
**Location:** [`src/vector/course_store.py`](../../src/vector/course_store.py:535-547)

**Finding:** User input directly interpolated into LanceDB filter strings:

```python
# Direct string interpolation of user input
if department_filter:
    query = query.where(f"department = '{department_filter}'")
if min_math_intensity is not None:
    query = query.where(f"math_intensity >= {min_math_intensity}")
```

**Risk:** While LanceDB uses Arrow not SQL, string interpolation bypasses proper parameter binding.

**Recommendation:** Use parameterized queries or validate/escape all filter inputs.

### Issue 4.3: Non-Deterministic Fallback Behavior
**Severity:** MEDIUM  
**Location:** [`src/vector/course_store.py`](../../src/vector/course_store.py:197-199), [`src/vector_store.py`](../../src/vector_store.py:82-84)

**Finding:** Fallback to in-memory dictionaries when LanceDB unavailable uses unordered storage:

```python
self._fallback_vectors: Dict[str, np.ndarray] = {}
self._fallback_metadata: Dict[str, Dict] = {}
```

**Risk:** Dictionary iteration order affects result ordering when fallback activated.

**Recommendation:** Use `dict(sorted(...))` or maintain sorted index for deterministic iteration.

---

## 5. Ranking Layer Issues

### Issue 5.1: Multiple Competing Ranking Authorities
**Severity:** HIGH  
**Location:** [`src/rag/course_recommender.py`](../../src/rag/course_recommender.py:519-644), [`src/ranking/xgboost_ranker.py`](../../src/ranking/xgboost_ranker.py:297-362)

**Finding:** **Four different ranking mechanisms** compete for final ordering:

1. **Stage 3 Weighted Scoring** (course_recommender.py):
```python
total_score = (
    self.vector_weight * vector_score +
    self.career_weight * career_score +
    self.intensity_weight * (math_match + humanities_match) / 2 +
    self.graph_weight * (1.0 / (1.0 + graph_dist))
)
```

2. **Stage 4 XGBoost Ranking** (xgboost_ranker.py):
```python
score = float(self.model.predict(features)[0])
rec.total_score = xgboost_score  # OVERWRITES stage 3 score
```

3. **Vector Search Ordering** (course_store.py):
```python
results.sort(key=lambda x: x.similarity_score, reverse=True)
```

4. **Graph Distance Boost** (course_recommender.py):
```python
if result.course_id in graph_ids:
    result.similarity_score = min(1.0, result.similarity_score * 1.1)
```

**Risk:** Unpredictable final ordering, training-serving skew, impossible to debug ranking decisions.

**Recommendation:** Implement single ranking authority with pluggable strategies; remove cross-stage score mutation.

### Issue 5.2: Unstable Random Split in Training
**Severity:** MEDIUM  
**Location:** [`src/ranking/xgboost_ranker.py`](../../src/ranking/xgboost_ranker.py:243-245)

**Finding:** Random split for validation uses global numpy state:

```python
np.random.seed(self.config.random_state)
val_groups = np.random.choice(unique_groups, size=n_val, replace=False)
```

**Risk:** Non-reproducible train/validation splits if random state not properly isolated.

**Recommendation:** Use `np.random.default_rng(self.config.random_state)` for isolated RNG.

### Issue 5.3: Score Mutation Side Effects
**Severity:** MEDIUM  
**Location:** [`src/ranking/xgboost_ranker.py`](../../src/ranking/xgboost_ranker.py:342-350)

**Finding:** `rank()` method mutates recommendation objects in-place:

```python
for rec, xgboost_score in predictions:
    rec.features["xgboost_score"] = xgboost_score
    rec.features["original_score"] = rec.total_score
    rec.total_score = xgboost_score  # MUTATES input object
```

**Risk:** Caller cannot access original scores after ranking; violates functional principles.

**Recommendation:** Return new recommendation objects instead of mutating inputs.

---

## 6. RAG Pipeline Issues

### Issue 6.1: Hidden Fallback Embedding Generation
**Severity:** MEDIUM  
**Location:** [`src/rag/course_recommender.py`](../../src/rag/course_recommender.py:646-707), [`src/llm/adapter.py`](../../src/llm/adapter.py:255-297)

**Finding:** Multiple hidden fallback paths for embedding generation with different algorithms:

```python
async def _get_student_embedding(self, prefs: StudentPreferences) -> List[float]:
    # Try 1: LLM Adapter (may fail silently)
    if self.llm and await self.llm.health_check():
        result = await self.llm.embed(text)
    
    # Try 2: Fallback deterministic embedding
    return self._fallback_student_embedding(prefs)
```

```python
# LLM Adapter has ITS OWN fallback
def _fallback_embed(self, text: str) -> EmbeddingResult:
    # Hash-based embedding with different algorithm
```

**Risk:** Same input produces different embeddings depending on service availability; violates determinism.

**Recommendation:** Make fallback behavior explicit in configuration; enforce consistent fallback algorithm.

### Issue 6.2: Duplicate Score Calculation
**Severity:** LOW  
**Location:** [`src/rag/course_recommender.py`](../../src/rag/course_recommender.py:709-730)

**Finding:** Career match score calculated in both Stage 2 (vector store) and Stage 3 (feature engineering):

```python
# Stage 2: In CourseVectorStore.search_by_career()
career_score = 1.0 if career_goal in career_paths else ...

# Stage 3: Recalculated
async def _calculate_career_match(self, career_goal: str, course_careers: List[str]) -> float:
    if career_goal in course_careers:
        return 1.0  # Same logic!
```

**Risk:** Inconsistent scoring if algorithms diverge; wasted computation.

**Recommendation:** Compute once in Stage 2, pass through to Stage 3.

---

## 7. Integration Layer Issues

### Issue 7.1: Bridge Creates Connections on Init
**Severity:** LOW  
**Location:** [`src/integrations/directus_neo4j_bridge.py`](../../src/integrations/directus_neo4j_bridge.py:76-166)

**Finding:** Bridge creates database connections during initialization rather than on first use:

```python
def __init__(...):
    self._pg_pool: Optional[asyncpg.Pool] = None
    self._neo4j_driver: Optional[AsyncDriver] = None
    # Connections created lazily but...see _get_pg_pool()
```

Actually lazy, but `_get_pg_pool()` creates pool on first access without explicit initialization call.

**Recommendation:** Implement explicit `initialize()` method called by orchestrator.

### Issue 7.2: Environment Variable Duplication
**Severity:** LOW  
**Location:** [`src/integrations/directus_neo4j_bridge.py`](../../src/integrations/directus_neo4j_bridge.py:101-122)

**Finding:** Multiple environment variable names for same configuration:

```python
self.neo4j_uri = neo4j_uri or os.getenv(
    "NEO4J_URI", 
    os.getenv("PG_NEO4J_URI", "bolt://localhost:7687")
)
```

**Risk:** Configuration confusion, maintenance overhead.

**Recommendation:** Use centralized config; single source of truth in `src/config.py`.

---

## 8. Cross-Cutting Issues

### Issue 8.1: Feature Name Inconsistency
**Severity:** MEDIUM  
**Location:** [`src/ranking/config.py`](../../src/ranking/config.py:58-68), [`src/rag/course_recommender.py`](../../src/rag/course_recommender.py:599-611)

**Finding:** Feature names differ between RAG pipeline output and XGBoost input:

```python
# ranking/config.py expects:
feature_names = [
    "vector_similarity_score",      # "_score" suffix
    "career_match_score",
    ...
]

# course_recommender.py produces:
features = {
    "vector_similarity": vector_score,  # No "_score" suffix!
    "career_match": career_score,
    ...
}
```

**Risk:** Feature mismatch causes XGBoost to use wrong features or zeros.

**Recommendation:** Define feature names in shared constants module.

### Issue 8.2: Singleton Pattern Abuse
**Severity:** LOW  
**Location:** Multiple files

**Finding:** Multiple singletons create tight coupling:
- `get_memory()` in memory.py
- `get_settings()` in config.py
- `get_ranking_config()` in ranking/config.py
- `get_directus_client()` in directus_client.py

**Risk:** Testing difficulty, hidden dependencies, initialization order issues.

**Recommendation:** Use dependency injection via FastAPI's `Depends()` system.

---

## Risk Matrix Summary

| Issue | Severity | Layer | Category | Effort to Fix |
|-------|----------|-------|----------|---------------|
| 2.1 | HIGH | Memory | Redundant Storage | Large |
| 2.2 | HIGH | Memory | Hidden Side Effects | Medium |
| 3.2 | HIGH | Graph | Security | Small |
| 4.1 | HIGH | Vector | Redundant Storage | Large |
| 5.1 | HIGH | Ranking | Multiple Authorities | Large |
| 2.3 | MEDIUM | Memory | Overlapping Sources | Small |
| 2.4 | MEDIUM | Memory | Determinism | Small |
| 3.1 | MEDIUM | Graph | Excessive Traversal | Medium |
| 3.3 | MEDIUM | Graph | Performance | Medium |
| 4.2 | MEDIUM | Vector | Security | Small |
| 4.3 | MEDIUM | Vector | Determinism | Small |
| 5.2 | MEDIUM | Ranking | Determinism | Small |
| 5.3 | MEDIUM | Ranking | Side Effects | Small |
| 6.1 | MEDIUM | RAG | Determinism | Medium |
| 8.1 | MEDIUM | Cross | Consistency | Small |

---

## Recommendations by Priority

### Immediate (High Severity)
1. **Consolidate embedding storage**: Choose single backend (recommend LanceDB) for all vectors
2. **Remove auto-relationship creation**: Make graph linking explicit
3. **Unify ranking authority**: Remove competing scoring mechanisms
4. **Fix Cypher injection patterns**: Parameterize all query components

### Short-term (Medium Severity)
1. Add deterministic tie-breaking to all sort operations
2. Implement explicit initialization patterns (remove hidden side effects)
3. Batch graph distance calculations
4. Standardize feature names across pipeline

### Long-term (Low Severity)
1. Migrate from singletons to dependency injection
2. Consolidate environment variable handling
3. Add comprehensive integration tests for fallback paths

---

## TOML Specification Compliance

| Requirement | Status | Notes |
|-------------|--------|-------|
| Deterministic behavior | ❌ FAIL | Multiple non-deterministic paths identified |
| Single embedding storage | ❌ FAIL | 4+ storage locations for embeddings |
| Minimal security surface | ⚠️ PARTIAL | Cypher/SQL injection risks present |
| Explicit initialization | ❌ FAIL | Hidden side effects in constructors |
| Unified ranking | ❌ FAIL | 4 competing ranking mechanisms |

---

*End of Architecture Audit Report*
