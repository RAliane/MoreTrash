"""Neo4j implementation of spatial backend interface.

This module provides Neo4j-backed spatial operations, replacing
PostGIS dependencies with graph-native Cypher queries.

Key mappings from PostGIS:
- ST_DWithin → point.distance() <= threshold
- kNN <-> operator → ORDER BY point.distance() LIMIT k
- ST_Intersects → point.distance() = 0 (for points) or polygon intersection
- GIST index → Neo4j POINT INDEX
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from src.core.spatial_interface import (
    Point,
    Polygon,
    SpatialBackend,
    SpatialBackendError,
    SpatialConstraint,
    SpatialEntity,
    SpatialOperation,
)
from src.logging_config import get_logger

logger = get_logger(__name__)


class Neo4jSpatialBackend(SpatialBackend):
    """Neo4j-backed spatial operations.
    
    Uses Neo4j's native point type and spatial indexes for
    efficient geographic queries. Requires Neo4j 5.x with
    point index support.
    
    Example:
        >>> backend = Neo4jSpatialBackend(
        ...     uri="bolt://localhost:7687",
        ...     user="neo4j",
        ...     password="password"
        ... )
        >>> async with backend:
        ...     results = await backend.find_k_nearest(
        ...         point=Point(x=0.0, y=0.0),
        ...         entity_type="Location",
        ...         k=5
        ...     )
    """
    
    # Valid Neo4j label pattern: must start with letter/underscore, alphanumeric only
    _ENTITY_TYPE_PATTERN = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')
    
    def __init__(
        self,
        uri: str,
        user: str,
        password: str,
        database: str = "neo4j",
        max_query_results: int = 10000,
    ) -> None:
        """Initialize Neo4j spatial backend.
        
        Args:
            uri: Neo4j connection URI (bolt:// or neo4j://)
            user: Neo4j username
            password: Neo4j password
            database: Database name (default: neo4j)
            max_query_results: Maximum results for unbounded queries (default: 10000)
        """
        super().__init__()
        self.uri = uri
        self.user = user
        self.password = password
        self.database = database
        self._driver: Optional[Any] = None
        self._max_query_results = max_query_results
    
    def _validate_entity_type(self, entity_type: str) -> str:
        """Validate and escape entity type for safe Cypher usage.
        
        Args:
            entity_type: Entity type/label to validate
            
        Returns:
            Backtick-escaped entity type for Cypher
            
        Raises:
            ValueError: If entity type contains invalid characters
        """
        if not entity_type:
            raise ValueError("Entity type cannot be empty")
        
        if not self._ENTITY_TYPE_PATTERN.match(entity_type):
            raise ValueError(
                f"Invalid entity type '{entity_type}'. "
                "Must start with letter or underscore, contain only alphanumeric and underscore."
            )
        
        # Escape backticks in the entity type itself
        escaped = entity_type.replace("`", "``")
        return f"`{escaped}`"
    
    async def initialize(self) -> None:
        """Initialize Neo4j driver and create spatial indexes.
        
        Creates point indexes for efficient spatial queries.
        Idempotent - safe to call multiple times.
        
        Raises:
            SpatialBackendError: If connection fails
        """
        try:
            # Import here to allow interface usage without neo4j installed
            from neo4j import AsyncGraphDatabase
            
            self._driver = AsyncGraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password),
            )
            
            # Verify connectivity
            await self._driver.verify_connectivity()
            
            # Create point indexes for spatial performance
            await self._create_indexes()
            
            self.is_ready = True
            logger.info(
                "Neo4j spatial backend initialized",
                uri=self.uri,
                database=self.database,
            )
            
        except Exception as exc:
            logger.error("Failed to initialize Neo4j backend", error=str(exc))
            raise SpatialBackendError(
                message="Failed to initialize Neo4j connection",
                operation="initialize",
                backend_error=str(exc),
            ) from exc
    
    async def _create_indexes(self) -> None:
        """Create point indexes for spatial queries."""
        if not self._driver:
            return
        
        index_queries = [
            """
            CREATE POINT INDEX location_coords_index IF NOT EXISTS
            FOR (n:Location) ON (n.coordinates)
            """,
            """
            CREATE POINT INDEX constraint_coords_index IF NOT EXISTS
            FOR (n:Constraint) ON (n.location)
            """,
            """
            CREATE POINT INDEX memory_coords_index IF NOT EXISTS
            FOR (n:MemoryChunk) ON (n.coordinates)
            """,
        ]
        
        async with self._driver.session(database=self.database) as session:
            for query in index_queries:
                try:
                    await session.run(query)
                except Exception as exc:
                    # Index may already exist or not be supported
                    logger.warning(
                        "Index creation skipped",
                        query=query[:50],
                        error=str(exc),
                    )
    
    async def close(self) -> None:
        """Close Neo4j driver connection."""
        if self._driver:
            await self._driver.close()
            self._driver = None
            self.is_ready = False
            logger.info("Neo4j spatial backend closed")
    
    async def health_check(self) -> bool:
        """Check Neo4j connectivity.
        
        Returns:
            True if connection is healthy
        """
        if not self._driver:
            return False
        
        try:
            await self._driver.verify_connectivity()
            return True
        except Exception:
            return False
    
    async def find_within_distance(
        self,
        point: Point,
        distance_meters: float,
        entity_type: str,
        limit: Optional[int] = None,
    ) -> List[SpatialEntity]:
        """Find entities within distance using Neo4j point.distance().
        
        Equivalent to PostGIS ST_DWithin(geom::geography, point, distance).
        
        Note: Neo4j's point.distance() returns meters for WGS84 points.
        """
        if not self._driver:
            raise SpatialBackendError(
                message="Backend not initialized",
                operation="find_within_distance",
            )
        
        # Validate entity type to prevent Cypher injection
        safe_entity_type = self._validate_entity_type(entity_type)
        
        query = f"""
            MATCH (n:{safe_entity_type})
            WHERE n.coordinates IS NOT NULL
              AND point.distance(n.coordinates, $point) <= $distance
            RETURN n.id AS id,
                   n.coordinates AS coords,
                   n AS properties,
                   point.distance(n.coordinates, $point) AS distance
            {'LIMIT $limit' if limit else ''}
        """
        
        params = {
            "point": point.to_neo4j_point(),
            "distance": distance_meters,
        }
        if limit:
            params["limit"] = limit
        
        try:
            async with self._driver.session(database=self.database) as session:
                result = await session.run(query, params)
                records = await result.data()
                
            return [
                SpatialEntity(
                    id=str(r["id"]),
                    entity_type=entity_type,
                    location=Point(
                        x=r["coords"].x,
                        y=r["coords"].y,
                        srid=point.srid,
                    ),
                    properties=dict(r["properties"]),
                    distance=r["distance"],
                )
                for r in records
            ]
            
        except Exception as exc:
            logger.error(
                "find_within_distance failed",
                point=point.to_dict(),
                distance=distance_meters,
                error=str(exc),
            )
            raise SpatialBackendError(
                message="Spatial query failed",
                operation="find_within_distance",
                backend_error=str(exc),
            ) from exc
    
    async def find_k_nearest(
        self,
        point: Point,
        entity_type: str,
        k: int = 5,
    ) -> List[SpatialEntity]:
        """Find k nearest neighbors using Neo4j distance ordering.
        
        Equivalent to PostGIS:
            ORDER BY geom <-> ST_SetSRID(ST_MakePoint($x, $y), 4326)
            LIMIT $k
        """
        if not self._driver:
            raise SpatialBackendError(
                message="Backend not initialized",
                operation="find_k_nearest",
            )
        
        # Validate entity type to prevent Cypher injection
        safe_entity_type = self._validate_entity_type(entity_type)
        
        query = f"""
            MATCH (n:{safe_entity_type})
            WHERE n.coordinates IS NOT NULL
            WITH n, point.distance(n.coordinates, $point) AS distance
            ORDER BY distance
            LIMIT $k
            RETURN n.id AS id,
                   n.coordinates AS coords,
                   n AS properties,
                   distance
        """
        
        params = {
            "point": point.to_neo4j_point(),
            "k": k,
        }
        
        try:
            async with self._driver.session(database=self.database) as session:
                result = await session.run(query, params)
                records = await result.data()
                
            return [
                SpatialEntity(
                    id=str(r["id"]),
                    entity_type=entity_type,
                    location=Point(
                        x=r["coords"].x,
                        y=r["coords"].y,
                        srid=point.srid,
                    ),
                    properties=dict(r["properties"]),
                    distance=r["distance"],
                )
                for r in records
            ]
            
        except Exception as exc:
            logger.error(
                "find_k_nearest failed",
                point=point.to_dict(),
                k=k,
                error=str(exc),
            )
            raise SpatialBackendError(
                message="kNN query failed",
                operation="find_k_nearest",
                backend_error=str(exc),
            ) from exc
    
    async def check_constraint(
        self,
        constraint: SpatialConstraint,
        entity_location: Point,
    ) -> bool:
        """Check if entity satisfies spatial constraint.
        
        Handles different constraint operations:
        - DISTANCE: point.distance() <= buffer_distance
        - WITHIN: polygon.contains(point)
        - INTERSECTS: distance = 0 (for point geometries)
        - CONTAINS: Not applicable for point entity_location
        """
        constraint.validate()
        
        if constraint.operation == SpatialOperation.DISTANCE:
            if constraint.buffer_distance is None:
                raise ValueError("DISTANCE constraint requires buffer_distance")
            
            if isinstance(constraint.geometry, Point):
                # Calculate distance between two points
                from math import radians, sin, cos, sqrt, atan2
                
                # Haversine formula for geographic distance
                R = 6371000  # Earth's radius in meters
                lat1, lon1 = radians(entity_location.y), radians(entity_location.x)
                lat2, lon2 = radians(constraint.geometry.y), radians(constraint.geometry.x)
                
                dlat = lat2 - lat1
                dlon = lon2 - lon1
                a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
                c = 2 * atan2(sqrt(a), sqrt(1-a))
                distance = R * c
                
                return distance <= constraint.buffer_distance
            
            elif isinstance(constraint.geometry, Polygon):
                # Check if point is within polygon's bounding distance
                return constraint.geometry.contains(entity_location)
        
        elif constraint.operation == SpatialOperation.WITHIN:
            if not isinstance(constraint.geometry, Polygon):
                raise ValueError("WITHIN constraint requires Polygon geometry")
            return constraint.geometry.contains(entity_location)
        
        elif constraint.operation == SpatialOperation.INTERSECTS:
            # For point entity_location, intersects means identical or distance = 0
            if isinstance(constraint.geometry, Point):
                return (
                    entity_location.x == constraint.geometry.x and
                    entity_location.y == constraint.geometry.y
                )
            elif isinstance(constraint.geometry, Polygon):
                return constraint.geometry.contains(entity_location)
        
        elif constraint.operation == SpatialOperation.CONTAINS:
            # Point cannot contain anything
            return False
        
        return False
    
    async def find_constrained(
        self,
        constraint: SpatialConstraint,
        entity_type: str,
        limit: Optional[int] = None,
    ) -> List[SpatialEntity]:
        """Find entities satisfying a spatial constraint.
        
        For distance constraints, uses Neo4j's efficient point.distance().
        For polygon constraints, uses application-side filtering.
        """
        constraint.validate()
        
        if constraint.operation == SpatialOperation.DISTANCE:
            # Use database-native distance filtering
            if isinstance(constraint.geometry, Point) and constraint.buffer_distance:
                return await self.find_within_distance(
                    point=constraint.geometry,
                    distance_meters=constraint.buffer_distance,
                    entity_type=entity_type,
                    limit=limit,
                )
        
        elif constraint.operation == SpatialOperation.WITHIN:
            if isinstance(constraint.geometry, Polygon):
                # Fetch candidates within bounding box, then filter precisely
                # This is a simplified implementation - optimize for production
                all_entities = await self._get_all_entities(entity_type)
                constrained = [
                    e for e in all_entities
                    if constraint.geometry.contains(e.location)
                ]
                return constrained[:limit] if limit else constrained
        
        # Default: get all and filter
        all_entities = await self._get_all_entities(entity_type)
        constrained = [
            e for e in all_entities
            if await self.check_constraint(constraint, e.location)
        ]
        return constrained[:limit] if limit else constrained
    
    async def _get_all_entities(self, entity_type: str) -> List[SpatialEntity]:
        """Get all entities of a type (for filtering)."""
        if not self._driver:
            return []
        
        # Validate entity type to prevent Cypher injection
        safe_entity_type = self._validate_entity_type(entity_type)
        
        query = f"""
            MATCH (n:{safe_entity_type})
            WHERE n.coordinates IS NOT NULL
            RETURN n.id AS id, n.coordinates AS coords, n AS properties
            LIMIT $max_results
        """
        
        async with self._driver.session(database=self.database) as session:
            result = await session.run(query, {"max_results": self._max_query_results})
            records = await result.data()
            
        return [
            SpatialEntity(
                id=str(r["id"]),
                entity_type=entity_type,
                location=Point(
                    x=r["coords"].x,
                    y=r["coords"].y,
                    srid=4326,
                ),
                properties=dict(r["properties"]),
            )
            for r in records
        ]
    
    async def get_spatial_statistics(
        self,
        entity_type: str,
    ) -> Dict[str, Any]:
        """Get statistics for spatial data.
        
        Returns:
            Dict with count, bounding_box (min/max coordinates)
        """
        if not self._driver:
            raise SpatialBackendError(
                message="Backend not initialized",
                operation="get_spatial_statistics",
            )
        
        # Validate entity type to prevent Cypher injection
        safe_entity_type = self._validate_entity_type(entity_type)
        
        query = f"""
            MATCH (n:{safe_entity_type})
            WHERE n.coordinates IS NOT NULL
            RETURN
                count(n) as total_count,
                min(n.coordinates.x) as min_x,
                max(n.coordinates.x) as max_x,
                min(n.coordinates.y) as min_y,
                max(n.coordinates.y) as max_y
        """
        
        try:
            async with self._driver.session(database=self.database) as session:
                result = await session.run(query)
                record = await result.single()
                
            if not record:
                return {
                    "count": 0,
                    "bounding_box": None,
                }
            
            return {
                "count": record["total_count"],
                "bounding_box": {
                    "min_x": record["min_x"],
                    "max_x": record["max_x"],
                    "min_y": record["min_y"],
                    "max_y": record["max_y"],
                } if record["min_x"] else None,
            }
            
        except Exception as exc:
            logger.error(
                "get_spatial_statistics failed",
                entity_type=entity_type,
                error=str(exc),
            )
            raise SpatialBackendError(
                message="Statistics query failed",
                operation="get_spatial_statistics",
                backend_error=str(exc),
            ) from exc
