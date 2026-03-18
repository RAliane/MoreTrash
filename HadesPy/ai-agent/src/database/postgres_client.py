"""Async PostgreSQL client with pgvector support.

This module provides an async PostgreSQL connection pool using asyncpg,
with support for vector operations via pgvector extension.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple, Union

import asyncpg
from asyncpg import Pool, Connection
from asyncpg.exceptions import PostgresError

from ..config import get_settings

logger = logging.getLogger(__name__)


class PostgresClient:
    """Async PostgreSQL client with connection pooling and pgvector support."""

    def __init__(self) -> None:
        """Initialize the PostgreSQL client."""
        self._pool: Optional[Pool] = None
        self._settings = get_settings()
        self._initialized: bool = False
        self._lock: asyncio.Lock = asyncio.Lock()
    
    @property
    def is_initialized(self) -> bool:
        """Check if the client is initialized."""
        return self._initialized and self._pool is not None
    
    async def initialize(self) -> None:
        """Initialize the connection pool.
        
        Creates an asyncpg connection pool with configured settings.
        Registers pgvector type codecs for automatic vector handling.
        """
        if self._initialized:
            logger.debug("PostgreSQL client already initialized")
            return
        
        async with self._lock:
            if self._initialized:
                return
            
            try:
                settings = self._settings
                
                # Build connection string from settings or use provided URL
                dsn = self._build_connection_string()
                
                logger.info("Initializing PostgreSQL connection pool")
                
                # Create connection pool
                self._pool = await asyncpg.create_pool(
                    dsn=dsn,
                    min_size=settings.pg_pool_size if hasattr(settings, 'pg_pool_size') else 5,
                    max_size=settings.pg_max_overflow if hasattr(settings, 'pg_max_overflow') else 20,
                    command_timeout=60,
                    server_settings={
                        'application_name': 'ai-agent',
                        'jit': 'off',  # Disable JIT for short queries
                    },
                    init=self._init_connection,
                )
                
                self._initialized = True
                logger.info("PostgreSQL connection pool initialized successfully")
                
            except Exception as e:
                logger.error(f"Failed to initialize PostgreSQL connection pool: {e}")
                raise
    
    def _build_connection_string(self) -> str:
        """Build PostgreSQL connection string from settings.
        
        Returns:
            PostgreSQL connection DSN string
        """
        settings = self._settings
        
        # Check for explicit PostgreSQL database URL first
        if hasattr(settings, 'pg_database_url') and settings.pg_database_url:
            return settings.pg_database_url
        
        # Check for generic database URL
        if settings.database_url:
            return settings.database_url
        
        # Build from individual components (with defaults)
        host = getattr(settings, 'pg_host', 'localhost')
        port = getattr(settings, 'pg_port', 5432)
        database = getattr(settings, 'pg_database', 'ai_agent')
        user = getattr(settings, 'pg_user', 'postgres')
        password = getattr(settings, 'pg_password', '')
        
        return f"postgresql://{user}:{password}@{host}:{port}/{database}"
    
    @staticmethod
    async def _init_connection(conn: Connection) -> None:
        """Initialize a new connection with pgvector support.
        
        Args:
            conn: The new connection to initialize
        """
        # Register pgvector type
        await conn.set_type_codec(
            'vector',
            encoder=lambda v: str(v) if v is not None else None,
            decoder=lambda v: v,
            schema='public',
            format='text'
        )
        
        # Set search path
        await conn.execute('SET search_path TO public')
    
    async def close(self) -> None:
        """Close the connection pool."""
        if self._pool:
            logger.info("Closing PostgreSQL connection pool")
            await self._pool.close()
            self._pool = None
            self._initialized = False
            logger.info("PostgreSQL connection pool closed")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform a health check on the database.
        
        Returns:
            Dictionary with health status and database information
        """
        if not self._pool:
            return {
                'status': 'unhealthy',
                'error': 'Connection pool not initialized',
                'pg_version': None,
                'vector_extension': None,
            }
        
        try:
            async with self._pool.acquire() as conn:
                # Check basic connectivity
                pg_version = await conn.fetchval('SELECT version()')
                
                # Check pgvector extension
                vector_ext = await conn.fetchval(
                    "SELECT extversion FROM pg_extension WHERE extname = 'vector'"
                )
                
                # Check if we can query tables
                table_count = await conn.fetchval(
                    "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'"
                )
                
                # Get connection pool stats
                pool_stats = {
                    'size': self._pool.get_size(),
                    'free': self._pool.get_free_size(),
                    'max_size': self._pool.get_max_size(),
                }
                
                return {
                    'status': 'healthy',
                    'pg_version': pg_version,
                    'vector_extension': vector_ext,
                    'table_count': table_count,
                    'pool_stats': pool_stats,
                }
                
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'pg_version': None,
                'vector_extension': None,
            }
    
    @asynccontextmanager
    async def connection(self) -> AsyncGenerator[Connection, None]:
        """Get a connection from the pool.
        
        Yields:
            Database connection
        """
        if not self._pool:
            raise RuntimeError("PostgreSQL client not initialized. Call initialize() first.")
        
        async with self._pool.acquire() as conn:
            yield conn
    
    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[Connection, None]:
        """Get a connection with transaction.
        
        Yields:
            Database connection with active transaction
        """
        if not self._pool:
            raise RuntimeError("PostgreSQL client not initialized. Call initialize() first.")
        
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                yield conn
    
    async def fetch(
        self, 
        query: str, 
        *args: Any
    ) -> List[asyncpg.Record]:
        """Execute a SELECT query and return all results.
        
        Args:
            query: SQL query string
            *args: Query parameters
            
        Returns:
            List of records
        """
        async with self.connection() as conn:
            return await conn.fetch(query, *args)
    
    async def fetchrow(
        self, 
        query: str, 
        *args: Any
    ) -> Optional[asyncpg.Record]:
        """Execute a SELECT query and return first result.
        
        Args:
            query: SQL query string
            *args: Query parameters
            
        Returns:
            First record or None
        """
        async with self.connection() as conn:
            return await conn.fetchrow(query, *args)
    
    async def fetchval(
        self, 
        query: str, 
        *args: Any
    ) -> Any:
        """Execute a SELECT query and return single value.
        
        Args:
            query: SQL query string
            *args: Query parameters
            
        Returns:
            Single value or None
        """
        async with self.connection() as conn:
            return await conn.fetchval(query, *args)
    
    async def execute(
        self, 
        query: str, 
        *args: Any
    ) -> str:
        """Execute a non-SELECT query.
        
        Args:
            query: SQL query string
            *args: Query parameters
            
        Returns:
            Query completion status
        """
        async with self.connection() as conn:
            return await conn.execute(query, *args)
    
    async def executemany(
        self, 
        query: str, 
        args: List[Tuple[Any, ...]]
    ) -> None:
        """Execute a query multiple times with different parameters.
        
        Args:
            query: SQL query string
            args: List of parameter tuples
        """
        async with self.connection() as conn:
            await conn.executemany(query, args)
    
    async def insert_vector(
        self,
        table: str,
        text: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Insert a record with vector embedding.
        
        Args:
            table: Table name (usually 'memory_chunks')
            text: Text content
            embedding: Vector embedding as list of floats
            metadata: Optional metadata dictionary
            
        Returns:
            ID of inserted record
        """
        # Validate table name against allowlist to prevent SQL injection
        allowed_tables = {'memory_chunks', 'courses', 'students', 'recommendations'}
        if table not in allowed_tables:
            raise ValueError(f"Invalid table name: {table}. Must be one of: {allowed_tables}")
        
        query = f"""
            INSERT INTO {table} (text, embedding, metadata)
            VALUES ($1, $2::vector, $3::jsonb)
            RETURNING id
        """
        
        async with self.connection() as conn:
            return await conn.fetchval(
                query,
                text,
                embedding,
                metadata or {}
            )
    
    async def search_similar(
        self,
        query_embedding: List[float],
        table: str = 'memory_chunks',
        threshold: float = 0.7,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Search for similar vectors using cosine similarity.
        
        Args:
            query_embedding: Query vector
            table: Table to search
            threshold: Minimum similarity threshold
            limit: Maximum number of results
            
        Returns:
            List of matching records with similarity scores
        """
        # Validate table name against allowlist to prevent SQL injection
        allowed_tables = {'memory_chunks', 'courses', 'students', 'recommendations'}
        if table not in allowed_tables:
            raise ValueError(f"Invalid table name: {table}. Must be one of: {allowed_tables}")
        
        query = f"""
            SELECT
                id,
                text,
                metadata,
                1 - (embedding <=> $1::vector) as similarity,
                created_at
            FROM {table}
            WHERE 1 - (embedding <=> $1::vector) >= $2
            ORDER BY embedding <=> $1::vector
            LIMIT $3
        """
        
        rows = await self.fetch(query, query_embedding, threshold, limit)
        
        return [
            {
                'id': row['id'],
                'text': row['text'],
                'metadata': row['metadata'],
                'similarity': row['similarity'],
                'created_at': row['created_at'],
            }
            for row in rows
        ]


class MigrationRunner:
    """Database migration runner for PostgreSQL."""
    
    def __init__(self, client: PostgresClient, migrations_dir: Path):
        """Initialize the migration runner.
        
        Args:
            client: PostgreSQL client instance
            migrations_dir: Directory containing migration files
        """
        self.client = client
        self.migrations_dir = migrations_dir
    
    async def get_applied_migrations(self) -> List[str]:
        """Get list of already applied migrations.
        
        Returns:
            List of applied migration versions
        """
        try:
            rows = await self.client.fetch(
                "SELECT version FROM schema_migrations ORDER BY version"
            )
            return [row['version'] for row in rows]
        except asyncpg.exceptions.UndefinedTableError:
            # schema_migrations table doesn't exist yet
            return []
    
    async def apply_migration(self, version: str, sql_content: str) -> None:
        """Apply a single migration.
        
        Args:
            version: Migration version identifier
            sql_content: SQL content to execute
        """
        async with self.client.transaction() as conn:
            # Execute migration SQL
            await conn.execute(sql_content)
            
            # Record migration
            await conn.execute(
                """
                INSERT INTO schema_migrations (version, applied_at)
                VALUES ($1, CURRENT_TIMESTAMP)
                ON CONFLICT (version) DO NOTHING
                """,
                version
            )
    
    async def run_migrations(self) -> List[str]:
        """Run all pending migrations.
        
        Returns:
            List of applied migration versions
        """
        applied = await self.get_applied_migrations()
        applied_new: List[str] = []
        
        # Get all migration files
        migration_files = sorted(self.migrations_dir.glob("*.sql"))
        
        for migration_file in migration_files:
            # Extract version from filename (e.g., "001_create_postgres_schema.sql" -> "001")
            version = migration_file.stem.split('_')[0]
            
            if version not in applied:
                logger.info(f"Applying migration {version}: {migration_file.name}")
                
                sql_content = migration_file.read_text()
                
                try:
                    await self.apply_migration(version, sql_content)
                    applied_new.append(version)
                    logger.info(f"Migration {version} applied successfully")
                    
                except Exception as e:
                    logger.error(f"Migration {version} failed: {e}")
                    raise
        
        if not applied_new:
            logger.info("No pending migrations")
        
        return applied_new
    
    async def rollback_migration(self, version: str) -> None:
        """Rollback a specific migration.
        
        Note: This is a placeholder. Actual rollback implementation
        would require down migration scripts.
        
        Args:
            version: Migration version to rollback
        """
        logger.warning(f"Rollback not implemented for migration {version}")
        raise NotImplementedError("Rollback requires down migration scripts")


# Module-level singleton
_postgres_client_instance: Optional[PostgresClient] = None

async def get_postgres_client() -> PostgresClient:
    """Get the singleton PostgresClient instance."""
    global _postgres_client_instance
    if _postgres_client_instance is None:
        _postgres_client_instance = PostgresClient()
    return _postgres_client_instance


async def init_postgres() -> PostgresClient:
    """Initialize PostgreSQL and run migrations.
    
    Returns:
        Initialized PostgreSQL client
    """
    client = PostgresClient()
    await client.initialize()
    
    # Run migrations
    migrations_dir = Path(__file__).parent.parent.parent / "migrations"
    runner = MigrationRunner(client, migrations_dir)
    await runner.run_migrations()
    
    return client


async def close_postgres() -> None:
    """Close PostgreSQL connections."""
    client = PostgresClient()
    await client.close()
