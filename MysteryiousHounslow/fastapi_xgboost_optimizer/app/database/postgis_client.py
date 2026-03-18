from typing import Dict, List, Any, Optional, Tuple
import asyncpg
import structlog
from contextlib import asynccontextmanager

from app.infrastructure.config import settings
from app.infrastructure.logging import get_database_logger

logger = get_database_logger()


class PostGISClient:
    """PostGIS database client for spatial operations."""

    def __init__(self):
        self.connection_string = settings.DATABASE_URL
        self.postgis_extensions = settings.POSTGIS_EXTENSIONS
        self.pool: Optional[asyncpg.Pool] = None

    async def initialize(self) -> bool:
        """Initialize database connection pool."""
        try:
            self.pool = await asyncpg.create_pool(
                self.connection_string, min_size=5, max_size=20, command_timeout=60
            )

            # Verify PostGIS extensions
            async with self.pool.acquire() as conn:
                for extension in self.postgis_extensions:
                    await conn.execute(f"CREATE EXTENSION IF NOT EXISTS {extension}")

            logger.info("PostGIS client initialized successfully")
            return True

        except Exception as e:
            logger.error("PostGIS client initialization failed", error=str(e))
            return False

    async def close(self):
        """Close database connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("PostGIS client connection pool closed")

    @asynccontextmanager
    async def get_connection(self):
        """Get database connection from pool."""
        if not self.pool:
            raise RuntimeError("Database pool not initialized")

        async with self.pool.acquire() as conn:
            yield conn

    async def execute_spatial_query(
        self, query: str, params: Tuple = None, geometry_format: str = "geojson"
    ) -> List[Dict[str, Any]]:
        """Execute spatial query and format results."""
        try:
            async with self.get_connection() as conn:
                if geometry_format == "geojson":
                    # Ensure geometries are returned as GeoJSON
                    formatted_query = query.replace(
                        "ST_AsGeoJSON(geometry)", "ST_AsGeoJSON(geometry)::json"
                    )
                else:
                    formatted_query = query

                rows = (
                    await conn.fetch(formatted_query, *params)
                    if params
                    else await conn.fetch(formatted_query)
                )

                # Convert to dict format
                results = []
                for row in rows:
                    result = dict(row)
                    results.append(result)

                logger.debug(
                    "Spatial query executed",
                    query_length=len(query),
                    results_count=len(results),
                )

                return results

        except Exception as e:
            logger.error("Spatial query execution failed", error=str(e))
            raise

    async def find_nearest_neighbors(
        self,
        table_name: str,
        target_point: Tuple[float, float],
        geometry_column: str = "geometry",
        k: int = 10,
        max_distance: Optional[float] = None,
        srid: int = 3857,
    ) -> List[Dict[str, Any]]:
        """Find k-nearest neighbors using PostGIS <-> operator."""
        distance_filter = ""
        if max_distance:
            distance_filter = f"AND ST_DWithin({geometry_column}, ST_SetSRID(ST_MakePoint($1, $2), $3), ${4})"
            params = (
                target_point[0],
                target_point[1],
                srid,
                max_distance,
                target_point[0],
                target_point[1],
                srid,
                target_point[0],
                target_point[1],
                srid,
                k,
            )
        else:
            params = (
                target_point[0],
                target_point[1],
                srid,
                target_point[0],
                target_point[1],
                srid,
                k,
            )

        query = f"""
        SELECT
            *,
            ST_AsGeoJSON({geometry_column})::json as geometry_json,
            ST_Distance({geometry_column}, ST_SetSRID(ST_MakePoint($1, $2), $3)) as distance
        FROM {table_name}
        WHERE {geometry_column} IS NOT NULL
        {distance_filter}
        ORDER BY {geometry_column} <-> ST_SetSRID(ST_MakePoint($4, $5), $6)
        LIMIT $7
        """

        try:
            results = await self.execute_spatial_query(query, params)

            # Clean up geometry field
            for result in results:
                if "geometry_json" in result:
                    result["geometry"] = result.pop("geometry_json")

            logger.info(
                "kNN query completed",
                table=table_name,
                target_point=target_point,
                results_count=len(results),
            )

            return results

        except Exception as e:
            logger.error("kNN query failed", error=str(e))
            raise

    async def check_spatial_relationship(
        self,
        table_name: str,
        geometry: Dict[str, Any],
        operation: str,
        geometry_column: str = "geometry",
        srid: int = 3857,
    ) -> List[Dict[str, Any]]:
        """Check spatial relationships (within, contains, intersects, etc.)."""
        geom_wkt = self._geojson_to_wkt(geometry)

        operation_map = {
            "within": f"ST_Within({geometry_column}, ST_GeomFromText($1, $2))",
            "contains": f"ST_Contains({geometry_column}, ST_GeomFromText($1, $2))",
            "intersects": f"ST_Intersects({geometry_column}, ST_GeomFromText($1, $2))",
            "distance": f"ST_Distance({geometry_column}, ST_GeomFromText($1, $2))",
        }

        if operation not in operation_map:
            raise ValueError(f"Unsupported spatial operation: {operation}")

        query = f"""
        SELECT
            *,
            ST_AsGeoJSON({geometry_column})::json as geometry_json,
            {operation_map[operation]} as spatial_result
        FROM {table_name}
        WHERE {geometry_column} IS NOT NULL
        """

        params = (geom_wkt, srid)

        try:
            results = await self.execute_spatial_query(query, params)

            # Clean up geometry field
            for result in results:
                if "geometry_json" in result:
                    result["geometry"] = result.pop("geometry_json")

            logger.debug(
                "Spatial relationship query completed",
                operation=operation,
                results_count=len(results),
            )

            return results

        except Exception as e:
            logger.error("Spatial relationship query failed", error=str(e))
            raise

    async def calculate_spatial_statistics(
        self, table_name: str, geometry_column: str = "geometry"
    ) -> Dict[str, Any]:
        """Calculate spatial statistics for a table."""
        query = f"""
        SELECT
            COUNT(*) as total_features,
            ST_GeometryType({geometry_column}) as geometry_type,
            ST_SRID({geometry_column}) as srid,
            ST_AsGeoJSON(ST_Envelope(ST_Collect({geometry_column})))::json as bounds,
            ST_AsGeoJSON(ST_Centroid(ST_Collect({geometry_column})))::json as centroid
        FROM {table_name}
        WHERE {geometry_column} IS NOT NULL
        """

        try:
            results = await self.execute_spatial_query(query)

            if results:
                stats = dict(results[0])
                # Convert bounds and centroid to proper format
                if "bounds" in stats:
                    stats["bounds"] = stats["bounds"]
                if "centroid" in stats:
                    stats["centroid"] = stats["centroid"]

                logger.info("Spatial statistics calculated", table=table_name)
                return stats
            else:
                return {"error": "No spatial data found"}

        except Exception as e:
            logger.error("Spatial statistics calculation failed", error=str(e))
            raise

    def _geojson_to_wkt(self, geojson: Dict[str, Any]) -> str:
        """Convert GeoJSON geometry to WKT format."""
        geom_type = geojson.get("type", "Point")
        coordinates = geojson.get("coordinates", [])

        if geom_type == "Point":
            return f"POINT({coordinates[0]} {coordinates[1]})"
        elif geom_type == "Polygon":
            # Convert polygon coordinates
            rings = []
            for ring in coordinates:
                points = " ".join([f"{x} {y}" for x, y in ring])
                rings.append(f"({points})")
            return f"POLYGON({','.join(rings)})"
        else:
            # For other types, return a simple point
            if isinstance(coordinates, list) and len(coordinates) >= 2:
                return f"POINT({coordinates[0]} {coordinates[1]})"
            else:
                return "POINT(0 0)"

    async def insert_spatial_feature(
        self,
        table_name: str,
        geometry: Dict[str, Any],
        properties: Dict[str, Any],
        geometry_column: str = "geometry",
        srid: int = 3857,
    ) -> int:
        """Insert a spatial feature into the database."""
        geom_wkt = self._geojson_to_wkt(geometry)

        # Build dynamic insert query
        columns = [geometry_column] + list(properties.keys())
        placeholders = [f"ST_GeomFromText(${i + 1}, ${i + 2})"] + [
            f"${i + 3}" for i in range(len(properties))
        ]
        values = [geom_wkt, srid] + list(properties.values())

        query = f"""
        INSERT INTO {table_name} ({", ".join(columns)})
        VALUES ({", ".join(placeholders)})
        RETURNING id
        """

        try:
            async with self.get_connection() as conn:
                result = await conn.fetchval(query, *values)

                logger.info(
                    "Spatial feature inserted", table=table_name, feature_id=result
                )

                return result

        except Exception as e:
            logger.error("Spatial feature insertion failed", error=str(e))
            raise
