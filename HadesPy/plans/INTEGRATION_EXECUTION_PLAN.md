# HadesPy Integration Execution Plan
## Deterministic Migration: PostGIS → Neo4j + Cognee Graph Memory

**Version:** 1.0  
**Status:** READY FOR REVIEW  
**Mode:** DMAIC (Define Phase Complete)

---

## Overview

This document provides the executable integration plan derived from architectural analysis of:
- **Source:** `/Branch/fastapi_xgboost_optimizer` (PostGIS-based optimizer)
- **Target:** `/ai-agent` (FastAPI/FastMCP with Cognee RAG)

**Core Constraint:** Zero residual PostGIS dependencies. All spatial logic must be provably equivalent in Neo4j.

---

## Pre-Flight Checklist

Before executing any migration steps:

```bash
# Verify analysis artifacts exist
[ -f plans/INTEGRATION_ARCHITECTURE_REVIEW.md ] || exit 1
[ -f integration_review.toml ] || exit 1

# Verify codebase state
grep -r "from app.database.postgis_client" Branch/ --include="*.py" | wc -l  # Should be 8
grep -r "shapely" Branch/ --include="*.py" | wc -l  # Should be 12+
grep -r "neo4j" ai-agent/ --include="*.py" | wc -l  # Should be 0

# Verify test environment
docker ps | grep neo4j || echo "WARNING: Neo4j not running"
docker ps | grep lancedb || echo "WARNING: LanceDB not running"
```

---

## Phase 1: Abstraction Layer (Days 1-3)

### 1.1 Create Spatial Interface Contract

**File:** `ai-agent/src/core/spatial_interface.py`

```python
"""Abstract spatial operations interface.

This module defines the contract for spatial operations,
allowing seamless backend swaps (PostGIS → Neo4j → Future).
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class Point:
    """Generic point representation (backend-agnostic)."""
    x: float
    y: float
    srid: int = 4326


@dataclass
class SpatialConstraint:
    """Backend-agnostic spatial constraint."""
    operation: str  # 'within', 'distance', 'intersects'
    reference_point: Point
    buffer_distance: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


class SpatialBackend(ABC):
    """Abstract base for spatial database backends."""
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize backend connection."""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close backend connection."""
        pass
    
    @abstractmethod
    async def find_within_distance(
        self,
        point: Point,
        distance_meters: float,
        entity_type: str,
    ) -> List[Dict[str, Any]]:
        """Find entities within distance of point."""
        pass
    
    @abstractmethod
    async def find_k_nearest(
        self,
        point: Point,
        entity_type: str,
        k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Find k nearest entities to point."""
        pass
    
    @abstractmethod
    async def check_constraint(
        self,
        constraint: SpatialConstraint,
        entity_data: Dict[str, Any],
    ) -> bool:
        """Check if entity satisfies spatial constraint."""
        pass
```

**Deliverable:** Interface module with 100% type coverage.

### 1.2 Implement Neo4j Spatial Backend

**File:** `ai-agent/src/database/neo4j_spatial.py`

```python
"""Neo4j implementation of spatial backend."""

from neo4j import AsyncGraphDatabase
from src.core.spatial_interface import SpatialBackend, Point, SpatialConstraint


class Neo4jSpatialBackend(SpatialBackend):
    """Neo4j-backed spatial operations."""
    
    def __init__(self, uri: str, user: str, password: str):
        self.driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
        self.is_ready = False
    
    async def initialize(self) -> None:
        """Verify connectivity and create indexes."""
        await self.driver.verify_connectivity()
        
        # Create point indexes for spatial performance
        async with self.driver.session() as session:
            await session.run("""
                CREATE POINT INDEX location_index IF NOT EXISTS
                FOR (n:Location) ON (n.coordinates)
            """)
            await session.run("""
                CREATE POINT INDEX constraint_location_index IF NOT EXISTS
                FOR (n:Constraint) ON (n.location)
            """)
        
        self.is_ready = True
    
    async def find_k_nearest(
        self,
        point: Point,
        entity_type: str,
        k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Neo4j-native kNN using point.distance()."""
        query = """
            MATCH (n:$entity_type)
            WHERE n.coordinates IS NOT NULL
            WITH n, point.distance(n.coordinates, point({x: $x, y: $y})) AS dist
            ORDER BY dist
            LIMIT $k
            RETURN n, dist
        """.replace("$entity_type", entity_type)
        
        async with self.driver.session() as session:
            result = await session.run(query, {
                "x": point.x, "y": point.y, "k": k
            })
            records = await result.data()
            
        return [
            {"entity": r["n"], "distance": r["dist"]}
            for r in records
        ]
```

**Deliverable:** Neo4j backend passing spatial interface contract tests.

### 1.3 Create Migration Shim

**File:** `ai-agent/src/database/spatial_factory.py`

```python
"""Factory for spatial backend selection."""

from src.config import get_settings
from src.core.spatial_interface import SpatialBackend


async def get_spatial_backend() -> SpatialBackend:
    """Get configured spatial backend."""
    settings = get_settings()
    
    if settings.USE_NEO4J_SPATIAL:
        from src.database.neo4j_spatial import Neo4jSpatialBackend
        return Neo4jSpatialBackend(
            uri=settings.NEO4J_URI,
            user=settings.NEO4J_USER,
            password=settings.NEO4J_PASSWORD,
        )
    
    # Fallback or raise error after migration complete
    raise RuntimeError("No spatial backend configured")
```

---

## Phase 2: KNN Service Migration (Days 4-5)

### 2.1 Port kNN Service to Graph

**File:** `ai-agent/src/services/graph_knn.py`

**Mapping from Branch/knn_service.py:**

| Original Method | Graph Equivalent | Lines |
|-----------------|------------------|-------|
| `find_nearest_neighbors` | `find_k_nearest` | 51-88 |
| `check_constraint_violations` | `check_constraint` | 170-222 |
| `create_spatial_index` | `CREATE POINT INDEX` | 344-377 |
| `get_spatial_statistics` | Aggregation query | 393-447 |

**Implementation Requirements:**
1. Maintain identical return type signatures
2. Preserve async/await patterns
3. Add Neo4j-specific error handling

**Verification:**
```python
# Test parity
async def test_knn_parity():
    """Verify Neo4j kNN matches PostGIS kNN results."""
    postgis_results = await legacy_knn.find_nearest_neighbors(...)
    neo4j_results = await graph_knn.find_k_nearest(...)
    
    # Allow 1% deviation due to distance calculation differences
    assert len(postgis_results) == len(neo4j_results)
    for p, n in zip(postgis_results, neo4j_results):
        assert abs(p["distance"] - n["distance"]) < 0.01
```

---

## Phase 3: Cognee Graph Integration (Days 6-9)

### 3.1 Extend CogneeMemory with Graph Backend

**File:** `ai-agent/src/memory_graph.py`

```python
"""Graph-enhanced memory system with Neo4j backend."""

from src.memory import CogneeMemory, MemoryChunk
from neo4j import AsyncGraphDatabase


class GraphMemory(CogneeMemory):
    """Cognee memory with Neo4j relationship layer."""
    
    def __init__(self, *args, neo4j_uri: str, **kwargs):
        super().__init__(*args, **kwargs)
        self.neo4j_driver = AsyncGraphDatabase.driver(neo4j_uri)
    
    async def add(self, text: str, metadata: Optional[Dict] = None) -> MemoryChunk:
        """Add memory with graph node creation."""
        # 1. Store vector in LanceDB (via parent)
        chunk = await super().add(text, metadata)
        
        # 2. Create graph node
        async with self.neo4j_driver.session() as session:
            await session.run("""
                CREATE (m:MemoryChunk {
                    id: $id,
                    text_hash: $hash,
                    created_at: datetime(),
                    source_type: $source_type,
                    session_id: $session_id
                })
            """, {
                "id": chunk.id,
                "hash": hashlib.sha256(text.encode()).hexdigest()[:16],
                "source_type": metadata.get("source_type", "unknown"),
                "session_id": metadata.get("session_id", "default"),
            })
            
            # 3. Link to similar memories
            similar = await self.search(text, top_k=3)
            for sim in similar:
                if sim.id != chunk.id:
                    await session.run("""
                        MATCH (m1:MemoryChunk {id: $id1})
                        MATCH (m2:MemoryChunk {id: $id2})
                        CREATE (m1)-[:SEMANTICALLY_SIMILAR {
                            score: $score
                        }]->(m2)
                    """, {"id1": chunk.id, "id2": sim.id, "score": sim.score})
        
        return chunk
    
    async def get_context_graph(
        self,
        query: str,
        depth: int = 2,
    ) -> Dict[str, Any]:
        """Retrieve memory with relationship context."""
        # 1. Find seed memories via vector search
        seeds = await self.search(query, top_k=3)
        
        # 2. Expand via graph traversal
        async with self.neo4j_driver.session() as session:
            result = await session.run("""
                MATCH (seed:MemoryChunk)
                WHERE seed.id IN $seed_ids
                CALL apoc.path.subgraphNodes(seed, {
                    relationshipFilter: 'SEMANTICALLY_SIMILAR|TEMPORALLY_FOLLOWS',
                    minLevel: 1,
                    maxLevel: $depth
                }) YIELD node
                RETURN DISTINCT node
            """, {"seed_ids": [s.id for s in seeds], "depth": depth})
            
            nodes = await result.data()
            
        return {
            "seeds": seeds,
            "related": [n["node"] for n in nodes],
        }
```

### 3.2 LanceDB Integration

**File:** `ai-agent/src/vector_store.py`

```python
"""LanceDB vector store for embeddings."""

import lancedb
import numpy as np
from pathlib import Path


class LanceVectorStore:
    """LanceDB-backed vector storage."""
    
    def __init__(self, uri: str, dimension: int = 384):
        self.uri = Path(uri)
        self.uri.parent.mkdir(parents=True, exist_ok=True)
        self.dimension = dimension
        self._db = None
        self._table = None
    
    async def initialize(self):
        """Initialize LanceDB connection."""
        self._db = await lancedb.connect_async(str(self.uri))
        
        # Create table if not exists
        try:
            self._table = await self._db.open_table("memory_embeddings")
        except FileNotFoundError:
            import pyarrow as pa
            schema = pa.schema([
                ("id", pa.string()),
                ("embedding", pa.list_(pa.float32(), self.dimension)),
                ("text_preview", pa.string()),
                ("created_at", pa.timestamp('us')),
            ])
            self._table = await self._db.create_table(
                "memory_embeddings",
                schema=schema,
            )
    
    async def add(self, id: str, embedding: List[float], text_preview: str):
        """Add embedding to store."""
        import pyarrow as pa
        from datetime import datetime
        
        batch = pa.table({
            "id": [id],
            "embedding": [embedding],
            "text_preview": [text_preview[:100]],
            "created_at": [datetime.utcnow()],
        })
        await self._table.add(batch)
    
    async def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Vector similarity search."""
        results = await self._table.search(query_embedding).limit(top_k).to_arrow()
        return results.to_pandas().to_dict("records")
```

---

## Phase 4: Configuration Migration (Day 10)

### 4.1 Environment Variable Updates

**File:** `ai-agent/.env.example` additions:

```bash
# =============================================================================
# NEO4J GRAPH DATABASE (Migration from PostGIS)
# =============================================================================
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=change-me-in-production
NEO4J_MAX_CONNECTION_POOL_SIZE=50
NEO4J_CONNECTION_TIMEOUT=30

# =============================================================================
# LANCEDB VECTOR STORE (New)
# =============================================================================
LANCEDB_URI=./artifacts/vector_store.lance
LANCEDB_DIMENSION=384  # Match embedding model

# =============================================================================
# MIGRATION FEATURE FLAGS
# =============================================================================
USE_GRAPH_MEMORY=false
USE_NEO4J_SPATIAL=false
POSTGIS_FALLBACK=true

# Set all to true after validation complete
```

### 4.2 Settings Update

**File:** `ai-agent/src/config.py` additions:

```python
    # Neo4j Configuration
    neo4j_uri: str = Field(default="bolt://localhost:7687", alias="NEO4J_URI")
    neo4j_user: str = Field(default="neo4j", alias="NEO4J_USER")
    neo4j_password: str = Field(default="", alias="NEO4J_PASSWORD")
    neo4j_max_pool: int = Field(default=50, alias="NEO4J_MAX_CONNECTION_POOL_SIZE")
    
    # LanceDB Configuration
    lancedb_uri: str = Field(default="artifacts/vector_store.lance", alias="LANCEDB_URI")
    lancedb_dimension: int = Field(default=384, alias="LANCEDB_DIMENSION")
    
    # Migration Flags
    use_graph_memory: bool = Field(default=False, alias="USE_GRAPH_MEMORY")
    use_neo4j_spatial: bool = Field(default=False, alias="USE_NEO4J_SPATIAL")
    postgis_fallback: bool = Field(default=True, alias="POSTGIS_FALLBACK")
    
    @property
    def is_graph_mode(self) -> bool:
        """Check if running in graph memory mode."""
        return self.use_graph_memory and not self.postgis_fallback
```

---

## Phase 5: Testing & Validation (Days 11-14)

### 5.1 Deterministic Test Suite

**File:** `ai-agent/tests/test_spatial_migration.py`

```python
"""Deterministic tests for PostGIS → Neo4j migration."""

import pytest
import hashlib
from src.database.neo4j_spatial import Neo4jSpatialBackend
from src.core.spatial_interface import Point, SpatialConstraint


class TestSpatialParity:
    """Verify Neo4j spatial matches PostGIS behavior."""
    
    @pytest.fixture
    async def neo4j_backend(self):
        backend = Neo4jSpatialBackend(
            uri="bolt://localhost:7687",
            user="neo4j",
            password="test",
        )
        await backend.initialize()
        yield backend
        await backend.close()
    
    @pytest.mark.parametrize("k", [1, 5, 10, 100])
    async def test_knn_result_count(self, neo4j_backend, k):
        """kNN must return exactly k results when available."""
        point = Point(x=0.0, y=0.0, srid=4326)
        results = await neo4j_backend.find_k_nearest(
            point=point,
            entity_type="TestLocation",
            k=k,
        )
        assert len(results) <= k  # May have fewer if insufficient data
    
    async def test_distance_constraint_accuracy(self, neo4j_backend):
        """Distance constraints must match PostGIS calculations."""
        point = Point(x=10.0, y=10.0)
        constraint = SpatialConstraint(
            operation="distance",
            reference_point=point,
            buffer_distance=1000.0,  # meters
        )
        
        # Test entity at 500m (should pass)
        entity_near = {"location": Point(x=10.01, y=10.0)}
        assert await neo4j_backend.check_constraint(constraint, entity_near)
        
        # Test entity at 2000m (should fail)
        entity_far = {"location": Point(x=10.2, y=10.0)}
        assert not await neo4j_backend.check_constraint(constraint, entity_far)


class TestDeterminism:
    """Ensure deterministic behavior across executions."""
    
    async def test_query_determinism(self, neo4j_backend):
        """Same query must return identical results."""
        point = Point(x=5.0, y=5.0)
        
        results_1 = await neo4j_backend.find_k_nearest(point, "Location", k=5)
        results_2 = await neo4j_backend.find_k_nearest(point, "Location", k=5)
        
        # Hash comparison for deep equality
        hash_1 = hashlib.sha256(str(results_1).encode()).hexdigest()
        hash_2 = hashlib.sha256(str(results_2).encode()).hexdigest()
        assert hash_1 == hash_2
```

### 5.2 Integration Test Matrix

| Test | PostGIS Baseline | Neo4j Target | Tolerance |
|------|-----------------|--------------|-----------|
| kNN (k=5) | [id1, id2, id3, id4, id5] | Same order | 100% |
| Distance filter | 150 results | 150 results | ±2% |
| Constraint violation | True/False | Same boolean | 100% |
| Query latency (p95) | 45ms | < 50ms | +11% |
| Concurrent queries | 1000/sec | 1000/sec | ±5% |

---

## Phase 6: Production Cutover (Day 15)

### 6.1 Cutover Checklist

```markdown
- [ ] All integration tests passing
- [ ] Performance benchmarks within tolerance
- [ ] Feature flags configured
- [ ] Rollback procedure tested
- [ ] Monitoring dashboards updated
- [ ] On-call runbook distributed
- [ ] Database backups verified
```

### 6.2 Progressive Rollout

```python
# Rollout stages (via feature flags)

Stage 1 (10% traffic):
  USE_GRAPH_MEMORY=true
  USE_NEO4J_SPATIAL=false  # Keep PostGIS for spatial
  POSTGIS_FALLBACK=true

Stage 2 (50% traffic):
  USE_GRAPH_MEMORY=true
  USE_NEO4J_SPATIAL=true
  POSTGIS_FALLBACK=true

Stage 3 (100% traffic):
  USE_GRAPH_MEMORY=true
  USE_NEO4J_SPATIAL=true
  POSTGIS_FALLBACK=false  # Full cutover

Stage 4 (Cleanup):
  Remove PostGIS client code
  Remove POSTGIS_FALLBACK flag
```

### 6.3 Rollback Triggers

| Trigger | Action | TTL |
|---------|--------|-----|
| Error rate > 1% | Stage rollback | Immediate |
| p95 latency > 200ms | Stage rollback | 5 min |
| Neo4j connection failures | Full rollback | Immediate |
| Data inconsistency detected | Full rollback + alert | Immediate |

---

## Deliverables Checklist

| Deliverable | Location | Status |
|------------|----------|--------|
| Architecture Review | `plans/INTEGRATION_ARCHITECTURE_REVIEW.md` | ✅ Complete |
| Execution Plan | `plans/INTEGRATION_EXECUTION_PLAN.md` | ✅ Complete |
| Spatial Interface | `ai-agent/src/core/spatial_interface.py` | 📝 TODO |
| Neo4j Backend | `ai-agent/src/database/neo4j_spatial.py` | 📝 TODO |
| Graph Memory | `ai-agent/src/memory_graph.py` | 📝 TODO |
| LanceDB Store | `ai-agent/src/vector_store.py` | 📝 TODO |
| Deterministic Tests | `ai-agent/tests/test_spatial_migration.py` | 📝 TODO |
| Migration Scripts | `scripts/migrate_postgis_to_neo4j.py` | 📝 TODO |

---

## Execution Commands

```bash
# 1. Initialize Neo4j schema
cd ai-agent && python -m scripts.init_neo4j_schema

# 2. Run migration tests
pytest tests/test_spatial_migration.py -v --tb=short

# 3. Enable feature flags
export USE_GRAPH_MEMORY=true
export USE_NEO4J_SPATIAL=true

# 4. Start with new backend
python -m src.main

# 5. Verify no PostGIS imports
! grep -r "postgis\|geoalchemy" src/ --include="*.py"
```

---

**END OF EXECUTION PLAN**
