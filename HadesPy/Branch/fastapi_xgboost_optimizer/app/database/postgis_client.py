"""
PostGIS client for spatial database operations.

This module provides async database connectivity and spatial query
capabilities using PostgreSQL with PostGIS extension.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, List, Optional, Union
from urllib.parse import urlparse

import asyncpg
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.exceptions import DatabaseException
from app.infrastructure.logging_config import get_logger


class PostGISClient:
    """
    Async PostGIS client for spatial database operations.
    
    Provides connection pooling, spatial queries, and transaction management
    for PostgreSQL with PostGIS extension.
    """
    
    def __init__(self):
        """Initialize the PostGIS client."""
        self.logger = get_logger(__name__)
        self.engine = None
        self.session_factory = None
        self.pool = None
        self.is_ready = False
        
        # Connection settings
        self.pool_size = settings.DATABASE_POOL_SIZE
        self.max_overflow = settings.DATABASE_MAX_OVERFLOW
        self.pool_timeout = settings.DATABASE_POOL_TIMEOUT
        
        self.logger.info("PostGIS client initialized")
    
    async def initialize(self) -> None:
        """
        Initialize database connection pool and engine.
        
        Raises:
            DatabaseException: If initialization fails
        """
        try:
            # Parse database URL
            db_url = settings.DATABASE_URL
            parsed_url = urlparse(db_url)
            
            # Create async engine
            self.engine = create_async_engine(
                db_url,
                pool_size=self.pool_size,
                max_overflow=self.max_overflow,
                pool_timeout=self.pool_timeout,
                pool_pre_ping=True,
                echo=settings.DEBUG,
            )
            
            # Create session factory
            self.session_factory = sessionmaker(
                bind=self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )
            
            # Test connection
            async with self.engine.begin() as conn:
                await conn.execute("SELECT 1")
            
            # Create connection pool for direct queries
            self.pool = await asyncpg.create_pool(
                db_url,
                min_size=5,
                max_size=self.pool_size,
                command_timeout=self.pool_timeout,
            )
            
            # Enable PostGIS extension
            await self._enable_postgis()
            
            self.is_ready = True
            
            self.logger.info(
                "PostGIS client initialized successfully",
                extra={
                    "pool_size": self.pool_size,
                    "database": parsed_url.path.lstrip("/"),
                }
            )
            
        except Exception as exc:
            self.logger.error(
                "Failed to initialize PostGIS client",
                extra={"error": str(exc)},
                exc_info=True
            )
            raise DatabaseException(
                message="Failed to initialize PostGIS client",
                operation="initialize",
                database_error=str(exc),
            )
    
    async def close(self) -> None:
        """Close database connections."""
        try:
            if self.pool:
                await self.pool.close()
            
            if self.engine:
                await self.engine.dispose()
            
            self.is_ready = False
            self.logger.info("PostGIS client closed")
            
        except Exception as exc:
            self.logger.error(
                "Error closing PostGIS client",
                extra={"error": str(exc)}
            )
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get database session from pool.
        
        Yields:
            AsyncSession: Database session
        """
        if not self.session_factory:
            raise DatabaseException(
                message="Database not initialized",
                operation="get_session",
            )
        
        session = self.session_factory()
        try:
            yield session
        finally:
            await session.close()
    
    async def execute_query(
        self,
        query: str,
        params: Optional[List[Any]] = None,
        fetch: str = "all",
    ) -> Union[List[Dict[str, Any]], Dict[str, Any], None]:
        """
        Execute a database query.
        
        Args:
            query: SQL query string
            params: Query parameters
            fetch: Fetch mode ('all', 'one', 'none')
            
        Returns:
            Query results
            
        Raises:
            DatabaseException: If query execution fails
        """
        if not self.pool:
            raise DatabaseException(
                message="Database pool not initialized",
                operation="execute_query",
            )
        
        try:
            async with self.pool.acquire() as conn:
                # Execute query
                if params:
                    stmt = await conn.prepare(query)
                    result = await stmt.fetch(*params) if fetch != "none" else await stmt.execute(*params)
                else:
                    result = await conn.fetch(query) if fetch != "none" else await conn.execute(query)
                
                # Process results
                if fetch == "all":
                    return [dict(row) for row in result] if result else []
                elif fetch == "one":
                    return dict(result[0]) if result else None
                else:
                    return None
                
        except Exception as exc:
            self.logger.error(
                "Query execution failed",
                extra={
                    "query": query[:100] + "..." if len(query) > 100 else query,
                    "error": str(exc),
                }
            )
            raise DatabaseException(
                message="Query execution failed",
                operation="execute_query",
                database_error=str(exc),
            )
    
    async def execute_transaction(
        self,
        queries: List[Tuple[str, Optional[List[Any]]]],
    ) -> List[List[Dict[str, Any]]]:
        """
        Execute multiple queries in a transaction.
        
        Args:
            queries: List of (query, params) tuples
            
        Returns:
            List of query results
            
        Raises:
            DatabaseException: If transaction fails
        """
        if not self.pool:
            raise DatabaseException(
                message="Database pool not initialized",
                operation="execute_transaction",
            )
        
        try:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    results = []
                    
                    for query, params in queries:
                        if params:
                            stmt = await conn.prepare(query)
                            result = await stmt.fetch(*params)
                        else:
                            result = await conn.fetch(query)
                        
                        results.append([dict(row) for row in result] if result else [])
                    
                    return results
                    
        except Exception as exc:
            self.logger.error(
                "Transaction execution failed",
                extra={"error": str(exc)}
            )
            raise DatabaseException(
                message="Transaction execution failed",
                operation="execute_transaction",
                database_error=str(exc),
            )
    
    async def spatial_query(
        self,
        query_type: str,
        geometry: str,
        table_name: str,
        srid: int = 4326,
        limit: Optional[int] = None,
        attributes: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Execute a spatial query.
        
        Args:
            query_type: Type of spatial query ('intersects', 'within', 'contains', etc.)
            geometry: WKT geometry string
            table_name: Database table name
            srid: Spatial reference system ID
            limit: Maximum number of results
            attributes: Additional attributes to return
            
        Returns:
            List[Dict[str, Any]]: Query results
        """
        try:
            # Build spatial query
            attribute_list = ", ".join(attributes) if attributes else "*"
            
            if query_type == "intersects":
                spatial_condition = f"ST_Intersects(geom, ST_GeomFromText(%s, %s))"
            elif query_type == "within":
                spatial_condition = f"ST_Within(geom, ST_GeomFromText(%s, %s))"
            elif query_type == "contains":
                spatial_condition = f"ST_Contains(geom, ST_GeomFromText(%s, %s))"
            elif query_type == "distance":
                distance = attributes.pop(0) if attributes else 1000  # Default 1km
                spatial_condition = f"ST_DWithin(geom::geography, ST_GeomFromText(%s, %s)::geography, %s)"
                params = [geometry, srid, distance]
            else:
                raise ValueError(f"Unsupported query type: {query_type}")
            
            if query_type != "distance":
                params = [geometry, srid]
            
            query = f"""
                SELECT {attribute_list}
                FROM {table_name}
                WHERE {spatial_condition}
            """
            
            if limit:
                query += f" LIMIT {limit}"
            
            results = await self.execute_query(query, params)
            
            self.logger.debug(
                "Spatial query executed",
                extra={
                    "query_type": query_type,
                    "table": table_name,
                    "num_results": len(results),
                }
            )
            
            return results
            
        except Exception as exc:
            self.logger.error(
                "Spatial query failed",
                extra={
                    "query_type": query_type,
                    "table": table_name,
                    "error": str(exc),
                }
            )
            raise DatabaseException(
                message="Spatial query failed",
                operation="spatial_query",
                database_error=str(exc),
            )
    
    async def k_nearest_neighbors(
        self,
        point: Tuple[float, float],
        table_name: str,
        k: int = 5,
        srid: int = 4326,
        attributes: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Find k nearest neighbors using PostGIS kNN.
        
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
            # Build kNN query using <-> operator
            attribute_list = ", ".join(attributes) if attributes else "*"
            
            query = f"""
                SELECT 
                    {attribute_list},
                    ST_Distance(geom, ST_SetSRID(ST_MakePoint(%s, %s), %s)) as distance
                FROM {table_name}
                WHERE geom IS NOT NULL
                ORDER BY geom <-> ST_SetSRID(ST_MakePoint(%s, %s), %s)
                LIMIT %s
            """
            
            params = [
                point[0], point[1], srid,
                point[0], point[1], srid, k
            ]
            
            results = await self.execute_query(query, params)
            
            self.logger.debug(
                "kNN query executed",
                extra={
                    "point": point,
                    "table": table_name,
                    "k": k,
                    "num_results": len(results),
                }
            )
            
            return results
            
        except Exception as exc:
            self.logger.error(
                "kNN query failed",
                extra={
                    "point": point,
                    "table": table_name,
                    "error": str(exc),
                }
            )
            raise DatabaseException(
                message="kNN query failed",
                operation="k_nearest_neighbors",
                database_error=str(exc),
            )
    
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
            index_type: Index type (GIST, SP-GiST)
            
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
            
            await self.execute_query(query)
            
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
        self, table_name: str, geometry_column: str = "geom") -> Dict[str, Any]:
        """
        Get spatial statistics for a table.
        
        Args:
            table_name: Database table name
            geometry_column: Geometry column name
            
        Returns:
            Dict[str, Any]: Spatial statistics
        """
        try:
            query = f"""
                SELECT 
                    COUNT(*) as total_features,
                    ST_Extent({geometry_column}) as bounding_box,
                    ST_MemSize({geometry_column}) as total_size
                FROM {table_name}
                WHERE {geometry_column} IS NOT NULL
            """
            
            result = await self.execute_query(query)
            
            if result:
                stats = result[0]
                
                return {
                    "total_features": int(stats["total_features"]),
                    "bounding_box": stats["bounding_box"],
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
            raise DatabaseException(
                message="Failed to get spatial statistics",
                operation="get_spatial_statistics",
                database_error=str(exc),
            )
    
    async def _check_spatial_index(
        self, table_name: str, geometry_column: str
    ) -> bool:
        """Check if table has spatial index."""
        try:
            query = """
                SELECT EXISTS(
                    SELECT 1
                    FROM pg_indexes
                    WHERE tablename = $1
                    AND indexdef LIKE $2
                ) as has_index
            """
            
            result = await self.execute_query(
                query, [table_name, f'%GIST%{geometry_column}%']
            )
            
            return bool(result[0]["has_index"]) if result else False
            
        except Exception:
            return False
    
    async def _enable_postgis(self) -> None:
        """Enable PostGIS extension in the database."""
        try:
            # Check if PostGIS is already enabled
            result = await self.execute_query(
                "SELECT PostGIS_Version()",
                fetch="one",
            )
            
            if result:
                self.logger.info(
                    "PostGIS is enabled",
                    extra={"version": result.get("postgis_version")}
                )
            else:
                # Try to enable PostGIS
                await self.execute_query("CREATE EXTENSION IF NOT EXISTS postgis")
                self.logger.info("PostGIS extension enabled")
                
        except Exception as exc:
            self.logger.error(
                "Failed to enable PostGIS",
                extra={"error": str(exc)}
            )
            raise DatabaseException(
                message="PostGIS extension not available",
                operation="enable_postgis",
                database_error=str(exc),
            )
    
    async def health_check(self) -> bool:
        """Check database connectivity."""
        try:
            if not self.pool:
                return False
            
            async with self.pool.acquire() as conn:
                result = await conn.fetch("SELECT 1")
                return bool(result)
            
        except Exception:
            return False