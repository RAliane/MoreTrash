"""
K-Nearest Neighbors service for spatial constraint enforcement.

This module implements kNN queries using PostGIS for spatial constraint
validation and optimization.
"""

import asyncio
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from shapely.geometry import Point, Polygon
from shapely.wkt import loads as wkt_loads

from app.core.config import settings
from app.core.exceptions import OptimizationException
from app.core.models import SpatialConstraint
from app.database.postgis_client import PostGISClient
from app.infrastructure.logging_config import get_logger


class KNNService:
    """
    K-Nearest Neighbors service for spatial operations.
    
    Provides spatial constraint checking, distance calculations,
    and spatial query capabilities using PostGIS.
    """
    
    def __init__(self):
        """Initialize the KNN service."""
        self.logger = get_logger(__name__)
        self.postgis_client = PostGISClient()
        self.is_ready = False
        
        self.logger.info("KNN service initialized")
    
    async def initialize(self) -> None:
        """Initialize the service and check database connectivity."""
        try:
            await self.postgis_client.initialize()
            self.is_ready = True
            self.logger.info("KNN service ready")
        except Exception as exc:
            self.logger.error(
                "Failed to initialize KNN service",
                extra={"error": str(exc)}
            )
            raise
    
    async def find_nearest_neighbors(
        self,
        point: Tuple[float, float],
        table_name: str,
        k: int = 5,
        srid: int = 4326,
        attributes: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Find k nearest neighbors to a point.
        
        Args:
            point: Query point coordinates (x, y)
            table_name: Database table name
            k: Number of nearest neighbors
            srid: Spatial reference system ID
            attributes: Additional attributes to return
            
        Returns:
            List[Dict[str, Any]]: Nearest neighbors with distances
        """
        try:
            # Build query using PostGIS kNN operator
            query = f"""
                SELECT 
                    id,
                    ST_Distance(geom, ST_SetSRID(ST_MakePoint(%s, %s), %s)) as distance,
                    {', '.join(attributes) if attributes else 'geom'}
                FROM {table_name}
                WHERE geom IS NOT NULL
                ORDER BY geom <-> ST_SetSRID(ST_MakePoint(%s, %s), %s)
                LIMIT %s
            """
            
            params = [point[0], point[1], srid, point[0], point[1], srid, k]
            
            results = await self.postgis_client.execute_query(query, params)
            
            return results
            
        except Exception as exc:
            self.logger.error(
                "kNN query failed",
                extra={
                    "point": point,
                    "table": table_name,
                    "k": k,
                    "error": str(exc),
                }
            )
            raise OptimizationException(
                message="kNN query failed",
                code="KNN_QUERY_FAILED",
                engine_error=str(exc),
            )
    
    async def find_within_distance(
        self,
        point: Tuple[float, float],
        table_name: str,
        distance: float,
        srid: int = 4326,
        attributes: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Find all points within a certain distance.
        
        Args:
            point: Query point coordinates (x, y)
            table_name: Database table name
            distance: Search distance in meters
            srid: Spatial reference system ID
            attributes: Additional attributes to return
            
        Returns:
            List[Dict[str, Any]]: Points within distance
        """
        try:
            # Use ST_DWithin for efficient distance queries
            query = f"""
                SELECT 
                    id,
                    ST_Distance(geom, ST_SetSRID(ST_MakePoint(%s, %s), %s)) as distance,
                    {', '.join(attributes) if attributes else 'geom'}
                FROM {table_name}
                WHERE ST_DWithin(
                    geom::geography,
                    ST_SetSRID(ST_MakePoint(%s, %s), %s)::geography,
                    %s
                )
                ORDER BY distance
            """
            
            params = [
                point[0], point[1], srid,
                point[0], point[1], srid, distance
            ]
            
            results = await self.postgis_client.execute_query(query, params)
            
            return results
            
        except Exception as exc:
            self.logger.error(
                "Distance query failed",
                extra={
                    "point": point,
                    "distance": distance,
                    "table": table_name,
                    "error": str(exc),
                }
            )
            raise OptimizationException(
                message="Distance query failed",
                code="DISTANCE_QUERY_FAILED",
                engine_error=str(exc),
            )
    
    async def check_constraint_violations(
        self,
        spatial_constraint: SpatialConstraint,
        variable_values: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Check violations of a spatial constraint.
        
        Args:
            spatial_constraint: Spatial constraint definition
            variable_values: Current variable values
            
        Returns:
            List[Dict[str, Any]]: Constraint violations
        """
        try:
            violations = []
            
            # Extract point from variable values or constraint
            if hasattr(spatial_constraint.geometry, "x") and hasattr(spatial_constraint.geometry, "y"):
                query_point = (spatial_constraint.geometry.x, spatial_constraint.geometry.y)
            else:
                # Try to extract from variable values
                point_var = variable_values.get("point", variable_values.get("location"))
                if point_var and isinstance(point_var, (list, tuple)) and len(point_var) >= 2:
                    query_point = (point_var[0], point_var[1])
                else:
                    # Default to origin if no point found
                    query_point = (0.0, 0.0)
            
            # Check based on operation type
            if spatial_constraint.operation == "within":
                violations = await self._check_within_constraint(
                    query_point, spatial_constraint, variable_values
                )
            
            elif spatial_constraint.operation == "distance":
                violations = await self._check_distance_constraint(
                    query_point, spatial_constraint, variable_values
                )
            
            elif spatial_constraint.operation == "intersects":
                violations = await self._check_intersection_constraint(
                    query_point, spatial_constraint, variable_values
                )
            
            return violations
            
        except Exception as exc:
            self.logger.error(
                "Constraint violation check failed",
                extra={
                    "constraint_type": spatial_constraint.operation,
                    "error": str(exc),
                }
            )
            raise OptimizationException(
                message="Constraint violation check failed",
                code="CONSTRAINT_CHECK_FAILED",
                engine_error=str(exc),
            )
    
    async def _check_within_constraint(
        self,
        query_point: Tuple[float, float],
        constraint: SpatialConstraint,
        variable_values: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Check within constraint violations."""
        violations = []
        
        # Check if point is within buffer distance
        if constraint.buffer:
            # For within constraints, we need a reference geometry
            # This is a simplified implementation
            distance = await self._calculate_distance_to_reference(
                query_point, constraint
            )
            
            if distance > constraint.buffer:
                violations.append({
                    "type": "outside_buffer",
                    "distance": distance,
                    "buffer": constraint.buffer,
                    "violation": distance - constraint.buffer,
                })
        
        return violations
    
    async def _check_distance_constraint(
        self,
        query_point: Tuple[float, float],
        constraint: SpatialConstraint,
        variable_values: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Check distance constraint violations."""
        violations = []
        
        # Calculate distance to reference points/locations
        if constraint.buffer:
            distance = await self._calculate_distance_to_reference(
                query_point, constraint
            )
            
            if distance > constraint.buffer:
                violations.append({
                    "type": "exceeds_max_distance",
                    "distance": distance,
                    "max_distance": constraint.buffer,
                    "violation": distance - constraint.buffer,
                })
        
        return violations
    
    async def _check_intersection_constraint(
        self,
        query_point: Tuple[float, float],
        constraint: SpatialConstraint,
        variable_values: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Check intersection constraint violations."""
        violations = []
        
        # Check if point intersects with forbidden areas
        # This would query a spatial database for intersecting geometries
        
        return violations
    
    async def _calculate_distance_to_reference(
        self,
        query_point: Tuple[float, float],
        constraint: SpatialConstraint,
    ) -> float:
        """Calculate distance to reference geometry."""
        try:
            # Use PostGIS for accurate distance calculation
            query = """
                SELECT ST_Distance(
                    ST_SetSRID(ST_MakePoint(%s, %s), %s),
                    ST_SetSRID(ST_GeomFromText(%s), %s)
                ) as distance
            """
            
            # Convert geometry to WKT
            geom_wkt = constraint.geometry.wkt if hasattr(constraint.geometry, 'wkt') else "POINT(0 0)"
            
            params = [
                query_point[0], query_point[1], constraint.srid,
                geom_wkt, constraint.srid
            ]
            
            result = await self.postgis_client.execute_query(query, params)
            
            if result:
                return float(result[0]["distance"])
            else:
                return 0.0
                
        except Exception as exc:
            # Fallback to simple Euclidean distance
            self.logger.warning(
                "PostGIS distance calculation failed, using Euclidean",
                extra={"error": str(exc)}
            )
            
            # Simple Euclidean distance
            if hasattr(constraint.geometry, 'x') and hasattr(constraint.geometry, 'y'):
                ref_point = (constraint.geometry.x, constraint.geometry.y)
                return np.sqrt(
                    (query_point[0] - ref_point[0]) ** 2 +
                    (query_point[1] - ref_point[1]) ** 2
                )
            
            return 0.0
    
    async def create_spatial_index(
        self,
        table_name: str,
        geometry_column: str = "geom",
        index_type: str = "GIST",
    ) -> bool:
        """
        Create spatial index on a table.
        
        Args:
            table_name: Database table name
            geometry_column: Geometry column name
            index_type: Index type (GIST, SP-GiST, etc.)
            
        Returns:
            bool: True if index created successfully
        """
        try:
            index_name = f"idx_{table_name}_{geometry_column}_spatial"
            
            query = f"""
                CREATE INDEX IF NOT EXISTS {index_name}
                ON {table_name}
                USING {index_type} ({geometry_column})
            """
            
            await self.postgis_client.execute_query(query)
            
            self.logger.info(
                "Spatial index created",
                extra={
                    "table": table_name,
                    "column": geometry_column,
                    "index_type": index_type,
                }
            )
            
            return True
            
        except Exception as exc:
            self.logger.error(
                "Failed to create spatial index",
                extra={
                    "table": table_name,
                    "error": str(exc),
                }
            )
            return False
    
    async def get_spatial_statistics(
        self,
        table_name: str,
        geometry_column: str = "geom",
    ) -> Dict[str, Any]:
        """
        Get spatial statistics for a table.
        
        Args:
            table_name: Database table name
            geometry_column: Geometry column name
            
        Returns:
            Dict[str, Any]: Spatial statistics
        """
        try:
            # Get basic statistics
            query = f"""
                SELECT 
                    COUNT(*) as total_features,
                    ST_Extent({geometry_column}) as bounding_box,
                    ST_MemSize({geometry_column}) as total_size
                FROM {table_name}
                WHERE {geometry_column} IS NOT NULL
            """
            
            result = await self.postgis_client.execute_query(query)
            
            if result:
                stats = result[0]
                
                # Parse bounding box
                bbox_wkt = stats["bounding_box"]
                if bbox_wkt:
                    bbox_geom = wkt_loads(bbox_wkt)
                    bounds = bbox_geom.bounds
                else:
                    bounds = None
                
                return {
                    "total_features": int(stats["total_features"]),
                    "bounding_box": bounds,
                    "total_size_bytes": int(stats["total_size"]) if stats["total_size"] else 0,
                    "has_spatial_index": await self._check_spatial_index(table_name, geometry_column),
                }
            
            return {}
            
        except Exception as exc:
            self.logger.error(
                "Failed to get spatial statistics",
                extra={
                    "table": table_name,
                    "error": str(exc),
                }
            )
            raise OptimizationException(
                message="Failed to get spatial statistics",
                code="SPATIAL_STATS_FAILED",
                engine_error=str(exc),
            )
    
    async def _check_spatial_index(
        self,
        table_name: str,
        geometry_column: str,
    ) -> bool:
        """Check if table has spatial index."""
        try:
            query = """
                SELECT EXISTS(
                    SELECT 1
                    FROM pg_indexes
                    WHERE tablename = %s
                    AND indexdef LIKE %s
                ) as has_index
            """
            
            params = [table_name, f'%GIST%{geometry_column}%']
            result = await self.postgis_client.execute_query(query, params)
            
            return bool(result[0]["has_index"]) if result else False
            
        except Exception:
            return False
    
    async def bulk_spatial_operations(
        self,
        points: List[Tuple[float, float]],
        operation: str,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        """
        Perform bulk spatial operations on multiple points.
        
        Args:
            points: List of points to process
            operation: Operation type ('nearest', 'within_distance', etc.)
            **kwargs: Operation-specific parameters
            
        Returns:
            List[Dict[str, Any]]: Results for each point
        """
        try:
            # Process points in batches for efficiency
            batch_size = kwargs.get("batch_size", 100)
            results = []
            
            for i in range(0, len(points), batch_size):
                batch = points[i:i + batch_size]
                batch_results = await self._process_point_batch(batch, operation, **kwargs)
                results.extend(batch_results)
            
            return results
            
        except Exception as exc:
            self.logger.error(
                "Bulk spatial operation failed",
                extra={
                    "operation": operation,
                    "num_points": len(points),
                    "error": str(exc),
                }
            )
            raise OptimizationException(
                message="Bulk spatial operation failed",
                code="BULK_SPATIAL_FAILED",
                engine_error=str(exc),
            )
    
    async def _process_point_batch(
        self,
        points: List[Tuple[float, float]],
        operation: str,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        """Process a batch of points."""
        results = []
        
        for point in points:
            if operation == "nearest":
                result = await self.find_nearest_neighbors(
                    point,
                    kwargs["table_name"],
                    k=kwargs.get("k", 5),
                    srid=kwargs.get("srid", 4326),
                )
            elif operation == "within_distance":
                result = await self.find_within_distance(
                    point,
                    kwargs["table_name"],
                    kwargs["distance"],
                    srid=kwargs.get("srid", 4326),
                )
            else:
                result = []
            
            results.append({"point": point, "result": result})
        
        return results
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        if self.postgis_client:
            await self.postgis_client.close()
        
        self.is_ready = False
        self.logger.info("KNN service cleaned up")