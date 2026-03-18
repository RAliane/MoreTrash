"""Abstract spatial operations interface.

This module defines the contract for spatial operations,
allowing seamless backend swaps (PostGIS → Neo4j → Future).

This abstraction ensures:
1. No direct PostGIS/Neo4j dependencies in business logic
2. Deterministic testability via mock implementations
3. Type safety through Pydantic models
4. Async-native design matching existing patterns
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union


class SpatialOperation(str, Enum):
    """Supported spatial constraint operations."""
    WITHIN = "within"
    DISTANCE = "distance"
    INTERSECTS = "intersects"
    CONTAINS = "contains"


@dataclass(frozen=True)
class Point:
    """Generic point representation (backend-agnostic).
    
    Replaces shapely.geometry.Point to remove external dependency.
    
    Attributes:
        x: X coordinate (typically longitude in geographic CRS)
        y: Y coordinate (typically latitude in geographic CRS)
        srid: Spatial Reference System Identifier (default: 4326/WGS84)
    """
    x: float
    y: float
    srid: int = 4326
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {"x": self.x, "y": self.y, "srid": self.srid}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Point:
        """Deserialize from dictionary."""
        return cls(
            x=float(data["x"]),
            y=float(data["y"]),
            srid=int(data.get("srid", 4326)),
        )
    
    def to_wkt(self) -> str:
        """Convert to Well-Known Text format."""
        return f"POINT({self.x} {self.y})"
    
    def to_neo4j_point(self) -> Dict[str, Any]:
        """Convert to Neo4j point format."""
        return {"x": self.x, "y": self.y, "crs": f"epsg:{self.srid}"}


@dataclass(frozen=True)
class Polygon:
    """Generic polygon representation (backend-agnostic).
    
    Simple polygon defined by exterior ring coordinates.
    Does not support holes (interior rings) - add if needed.
    
    Attributes:
        coordinates: List of (x, y) tuples defining the exterior ring
        srid: Spatial Reference System Identifier
    """
    coordinates: List[Tuple[float, float]]
    srid: int = 4326
    
    def __post_init__(self) -> None:
        """Validate polygon has minimum required points."""
        if len(self.coordinates) < 3:
            raise ValueError("Polygon must have at least 3 coordinates")
    
    def to_wkt(self) -> str:
        """Convert to Well-Known Text format."""
        coord_str = ", ".join(f"{x} {y}" for x, y in self.coordinates)
        return f"POLYGON(({coord_str}))"
    
    def contains(self, point: Point) -> bool:
        """Check if point is within polygon using ray casting algorithm.
        
        This is a simple implementation. For production, consider:
        - Using backend-native contains (PostGIS ST_Contains, Neo4j point.within())
        - More robust geometric libraries for complex polygons
        """
        x, y = point.x, point.y
        n = len(self.coordinates)
        inside = False
        
        j = n - 1
        for i in range(n):
            xi, yi = self.coordinates[i]
            xj, yj = self.coordinates[j]
            
            if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
                inside = not inside
            j = i
        
        return inside


@dataclass
class SpatialConstraint:
    """Backend-agnostic spatial constraint definition.
    
    Mirrors the structure from Branch/models.py but removes
    shapely dependency and adds backend-agnostic geometry handling.
    
    Attributes:
        operation: Type of spatial operation to perform
        geometry: Point or Polygon to test against
        buffer_distance: Distance buffer in meters (for distance operations)
        srid: Spatial reference system (inherited from geometry if not set)
        metadata: Additional constraint metadata
    """
    operation: SpatialOperation
    geometry: Union[Point, Polygon]
    buffer_distance: Optional[float] = None
    srid: int = field(init=False)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self) -> None:
        """Set SRID from geometry."""
        object.__setattr__(self, "srid", self.geometry.srid)
    
    def validate(self) -> None:
        """Validate constraint configuration.
        
        Raises:
            ValueError: If constraint configuration is invalid
        """
        if self.operation == SpatialOperation.DISTANCE:
            if self.buffer_distance is None or self.buffer_distance <= 0:
                raise ValueError(
                    f"DISTANCE operation requires positive buffer_distance, "
                    f"got {self.buffer_distance}"
                )
        
        if self.operation in (SpatialOperation.WITHIN, SpatialOperation.CONTAINS):
            if isinstance(self.geometry, Point):
                raise ValueError(
                    f"{self.operation.value} operation requires Polygon geometry"
                )


@dataclass
class SpatialEntity:
    """Represents an entity with spatial properties.
    
    Used for returning spatial query results in a standardized format.
    
    Attributes:
        id: Unique entity identifier
        entity_type: Type/category of entity (e.g., "Location", "Constraint")
        location: Geographic position
        properties: Additional entity attributes
        distance: Distance from query point (for kNN results)
    """
    id: str
    entity_type: str
    location: Point
    properties: Dict[str, Any] = field(default_factory=dict)
    distance: Optional[float] = None


class SpatialBackend(ABC):
    """Abstract base for spatial database backends.
    
    Implementations:
    - Neo4jSpatialBackend: Neo4j with point indexes
    - PostGISSpatialBackend: Original PostGIS (for fallback)
    - MockSpatialBackend: Deterministic testing
    
    All methods are async to match FastAPI patterns.
    """
    
    def __init__(self) -> None:
        """Initialize backend state."""
        self.is_ready = False
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize backend connection and verify connectivity.
        
        Raises:
            ConnectionError: If backend is unreachable
            RuntimeError: If initialization fails
        """
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close backend connection and release resources."""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if backend is healthy and responsive.
        
        Returns:
            True if backend is operational
        """
        pass
    
    @abstractmethod
    async def find_within_distance(
        self,
        point: Point,
        distance_meters: float,
        entity_type: str,
        limit: Optional[int] = None,
    ) -> List[SpatialEntity]:
        """Find entities within distance of point.
        
        Equivalent to PostGIS ST_DWithin.
        
        Args:
            point: Center point for search
            distance_meters: Search radius in meters
            entity_type: Type of entities to search
            limit: Maximum results (None for unlimited)
        
        Returns:
            List of entities within distance
        """
        pass
    
    @abstractmethod
    async def find_k_nearest(
        self,
        point: Point,
        entity_type: str,
        k: int = 5,
    ) -> List[SpatialEntity]:
        """Find k nearest entities to point.
        
        Equivalent to PostGIS kNN with <-> operator.
        
        Args:
            point: Query point
            entity_type: Type of entities to search
            k: Number of nearest neighbors
        
        Returns:
            List of k nearest entities with distances
        """
        pass
    
    @abstractmethod
    async def check_constraint(
        self,
        constraint: SpatialConstraint,
        entity_location: Point,
    ) -> bool:
        """Check if entity location satisfies spatial constraint.
        
        Args:
            constraint: Spatial constraint to test
            entity_location: Location of entity to check
        
        Returns:
            True if constraint is satisfied
        """
        pass
    
    @abstractmethod
    async def find_constrained(
        self,
        constraint: SpatialConstraint,
        entity_type: str,
        limit: Optional[int] = None,
    ) -> List[SpatialEntity]:
        """Find entities satisfying a spatial constraint.
        
        Args:
            constraint: Spatial constraint to apply
            entity_type: Type of entities to search
            limit: Maximum results
        
        Returns:
            List of entities satisfying constraint
        """
        pass
    
    @abstractmethod
    async def get_spatial_statistics(
        self,
        entity_type: str,
    ) -> Dict[str, Any]:
        """Get statistics for spatial data.
        
        Equivalent to PostGIS ST_Extent, ST_MemSize aggregations.
        
        Args:
            entity_type: Type of entities to analyze
        
        Returns:
            Dictionary with count, bounding_box, etc.
        """
        pass
    
    async def __aenter__(self) -> SpatialBackend:
        """Async context manager entry."""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()


class SpatialBackendError(Exception):
    """Base exception for spatial backend errors."""
    
    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        backend_error: Optional[str] = None,
    ):
        super().__init__(message)
        self.operation = operation
        self.backend_error = backend_error


class ConstraintViolationError(SpatialBackendError):
    """Raised when a spatial constraint is violated."""
    pass


class BackendNotInitializedError(SpatialBackendError):
    """Raised when backend is used before initialization."""
    pass
