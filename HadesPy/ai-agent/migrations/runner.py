#!/usr/bin/env python3
"""PostgreSQL Migration Runner

This script executes SQL migration files in order, tracks applied migrations,
and handles rollback on failure.

Usage:
    python runner.py status          - Check migration status
    python runner.py migrate         - Run pending migrations
    python runner.py rollback <ver>  - Rollback to specific version
    python runner.py reset           - Reset all migrations (DANGER)
"""

import argparse
import asyncio
import hashlib
import logging
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from database.postgres_client import PostgresClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class Migration:
    """Represents a single migration."""
    version: str
    name: str
    filepath: Path
    checksum: str
    content: str


class MigrationManager:
    """Manages PostgreSQL database migrations."""
    
    def __init__(self, migrations_dir: Path, client: Optional[PostgresClient] = None):
        """Initialize the migration manager.
        
        Args:
            migrations_dir: Directory containing .sql migration files
            client: PostgreSQL client instance (created if not provided)
        """
        self.migrations_dir = migrations_dir
        self.client = client or PostgresClient()
        self._migrations_cache: Optional[List[Migration]] = None
    
    async def initialize(self) -> None:
        """Initialize the database client."""
        await self.client.initialize()
    
    async def close(self) -> None:
        """Close the database client."""
        await self.client.close()
    
    def _compute_checksum(self, content: str) -> str:
        """Compute SHA256 checksum of migration content.
        
        Args:
            content: Migration SQL content
            
        Returns:
            Hexadecimal checksum string
        """
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def _load_migrations(self) -> List[Migration]:
        """Load all migration files from the migrations directory.
        
        Returns:
            List of Migration objects sorted by version
        """
        if self._migrations_cache is not None:
            return self._migrations_cache
        
        migrations: List[Migration] = []
        
        # Find all .sql files in migrations directory
        sql_files = sorted(self.migrations_dir.glob("*.sql"))
        
        for filepath in sql_files:
            # Skip backup directory
            if "backup" in filepath.parts:
                continue
                
            # Parse filename: 001_migration_name.sql -> version="001", name="migration_name"
            parts = filepath.stem.split('_', 1)
            version = parts[0]
            name = parts[1] if len(parts) > 1 else filepath.stem
            
            content = filepath.read_text()
            checksum = self._compute_checksum(content)
            
            migrations.append(Migration(
                version=version,
                name=name,
                filepath=filepath,
                checksum=checksum,
                content=content
            ))
        
        # Sort by version
        migrations.sort(key=lambda m: m.version)
        self._migrations_cache = migrations
        
        return migrations
    
    async def _ensure_migrations_table(self) -> None:
        """Create the schema_migrations table if it doesn't exist."""
        await self.client.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                id SERIAL PRIMARY KEY,
                version VARCHAR(255) NOT NULL UNIQUE,
                applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                description TEXT,
                checksum VARCHAR(64),
                execution_time_ms INTEGER
            )
        """)
    
    async def get_applied_migrations(self) -> List[dict]:
        """Get list of already applied migrations from database.
        
        Returns:
            List of applied migration records
        """
        await self._ensure_migrations_table()
        
        try:
            rows = await self.client.fetch(
                """
                SELECT version, applied_at, description, checksum, execution_time_ms
                FROM schema_migrations
                ORDER BY version
                """
            )
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to fetch applied migrations: {e}")
            return []
    
    async def get_pending_migrations(self) -> List[Migration]:
        """Get list of migrations that haven't been applied yet.
        
        Returns:
            List of pending Migration objects
        """
        all_migrations = self._load_migrations()
        applied = {m['version'] for m in await self.get_applied_migrations()}
        
        return [m for m in all_migrations if m.version not in applied]
    
    async def apply_migration(self, migration: Migration) -> Tuple[bool, Optional[str]]:
        """Apply a single migration.
        
        Args:
            migration: Migration to apply
            
        Returns:
            Tuple of (success, error_message)
        """
        start_time = datetime.now()
        
        try:
            logger.info(f"Applying migration {migration.version}: {migration.name}")
            
            # Execute migration within a transaction
            async with self.client.transaction() as conn:
                # Execute the migration SQL
                await conn.execute(migration.content)
                
                # Record the migration
                execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
                
                await conn.execute(
                    """
                    INSERT INTO schema_migrations 
                    (version, description, checksum, execution_time_ms)
                    VALUES ($1, $2, $3, $4)
                    """,
                    migration.version,
                    migration.name,
                    migration.checksum,
                    execution_time
                )
            
            logger.info(f"Migration {migration.version} applied successfully in {execution_time}ms")
            return True, None
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Migration {migration.version} failed: {error_msg}")
            return False, error_msg
    
    async def run_migrations(self) -> Tuple[List[str], List[Tuple[str, str]]]:
        """Run all pending migrations.
        
        Returns:
            Tuple of (applied_versions, failed_migrations)
        """
        pending = await self.get_pending_migrations()
        
        if not pending:
            logger.info("No pending migrations")
            return [], []
        
        logger.info(f"Found {len(pending)} pending migration(s)")
        
        applied: List[str] = []
        failed: List[Tuple[str, str]] = []
        
        for migration in pending:
            success, error = await self.apply_migration(migration)
            
            if success:
                applied.append(migration.version)
            else:
                failed.append((migration.version, error or "Unknown error"))
                # Stop on first failure
                break
        
        if failed:
            logger.error(f"Migration failed at version {failed[0][0]}. Rolling back...")
            # Note: PostgreSQL transactions automatically rollback on error,
            # but we may need manual cleanup for partial migrations
        
        return applied, failed
    
    async def rollback_migration(self, version: str) -> bool:
        """Rollback a specific migration.
        
        Note: This requires down migration files (not yet implemented).
        
        Args:
            version: Version to rollback
            
        Returns:
            True if successful
        """
        logger.warning(f"Rollback requested for version {version}")
        logger.warning("Rollback requires down migration scripts (not yet implemented)")
        
        # Check if version exists
        applied = await self.get_applied_migrations()
        version_exists = any(m['version'] == version for m in applied)
        
        if not version_exists:
            logger.error(f"Migration version {version} not found in applied migrations")
            return False
        
        # TODO: Implement rollback with down migration files
        # Format: 001_migration_name.down.sql
        
        return False
    
    async def reset_migrations(self, force: bool = False) -> bool:
        """Reset all migrations by dropping and recreating tables.
        
        DANGER: This will delete all data!
        
        Args:
            force: Must be True to proceed
            
        Returns:
            True if successful
        """
        if not force:
            logger.error("Reset requires force=True - THIS WILL DELETE ALL DATA!")
            return False
        
        logger.warning("RESETTING ALL MIGRATIONS - DELETING ALL DATA!")
        
        try:
            # Get list of all tables in public schema
            tables = await self.client.fetch(
                """
                SELECT tablename FROM pg_tables 
                WHERE schemaname = 'public'
                AND tablename != 'schema_migrations'
                """
            )
            
            # Drop all tables
            import re
            valid_identifier = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')
            
            for table in tables:
                table_name = table['tablename']
                logger.info(f"Dropping table: {table_name}")
                # Validate table name is a valid PostgreSQL identifier
                # This prevents SQL injection while allowing legitimate table names
                if not isinstance(table_name, str) or not valid_identifier.match(table_name):
                    logger.error(f"Invalid table name, skipping: {table_name}")
                    continue
                # Use parameterized query with proper identifier escaping
                # Table name is validated, so safe to use in f-string
                await self.client.execute(f'DROP TABLE IF EXISTS "{table_name}" CASCADE')
            
            # Drop schema_migrations table last
            await self.client.execute("DROP TABLE IF EXISTS schema_migrations CASCADE")
            
            logger.info("All tables dropped. Migrations reset.")
            return True
            
        except Exception as e:
            logger.error(f"Reset failed: {e}")
            return False
    
    async def get_status(self) -> dict:
        """Get comprehensive migration status.
        
        Returns:
            Dictionary with migration status information
        """
        all_migrations = self._load_migrations()
        applied = await self.get_applied_migrations()
        applied_versions = {m['version'] for m in applied}
        
        pending = [m for m in all_migrations if m.version not in applied_versions]
        
        # Check for checksum mismatches
        mismatches = []
        for applied_migration in applied:
            version = applied_migration['version']
            expected_checksum = applied_migration.get('checksum')
            
            # Find the file for this version
            file_migration = next((m for m in all_migrations if m.version == version), None)
            
            if file_migration and expected_checksum:
                if file_migration.checksum != expected_checksum:
                    mismatches.append({
                        'version': version,
                        'expected': expected_checksum[:16] + '...',
                        'actual': file_migration.checksum[:16] + '...'
                    })
        
        # Get database health
        health = await self.client.health_check()
        
        return {
            'database_status': health.get('status', 'unknown'),
            'pg_version': health.get('pg_version', 'unknown'),
            'vector_extension': health.get('vector_extension', 'not installed'),
            'total_migrations': len(all_migrations),
            'applied_count': len(applied),
            'pending_count': len(pending),
            'applied_versions': [m['version'] for m in applied],
            'pending_versions': [m.version for m in pending],
            'checksum_mismatches': mismatches,
            'pool_stats': health.get('pool_stats', {}),
        }


async def cmd_status(manager: MigrationManager) -> int:
    """Handle status command.
    
    Args:
        manager: Migration manager instance
        
    Returns:
        Exit code
    """
    status = await manager.get_status()
    
    print("\n" + "=" * 60)
    print("MIGRATION STATUS")
    print("=" * 60)
    print(f"Database Status: {status['database_status']}")
    print(f"PostgreSQL Version: {status['pg_version'][:50]}..." if len(str(status['pg_version'])) > 50 else f"PostgreSQL Version: {status['pg_version']}")
    print(f"pgvector Extension: {status['vector_extension']}")
    print(f"\nTotal Migrations: {status['total_migrations']}")
    print(f"Applied: {status['applied_count']}")
    print(f"Pending: {status['pending_count']}")
    
    if status['applied_versions']:
        print(f"\nApplied Versions: {', '.join(status['applied_versions'])}")
    
    if status['pending_versions']:
        print(f"\nPending Versions: {', '.join(status['pending_versions'])}")
    
    if status['checksum_mismatches']:
        print("\n⚠️  CHECKSUM MISMATCHES DETECTED:")
        for m in status['checksum_mismatches']:
            print(f"   Version {m['version']}: Migration file has been modified!")
    
    if status['pool_stats']:
        print(f"\nConnection Pool: {status['pool_stats']}")
    
    print("=" * 60 + "\n")
    
    return 0 if status['database_status'] == 'healthy' else 1


async def cmd_migrate(manager: MigrationManager) -> int:
    """Handle migrate command.
    
    Args:
        manager: Migration manager instance
        
    Returns:
        Exit code
    """
    print("\n" + "=" * 60)
    print("RUNNING MIGRATIONS")
    print("=" * 60 + "\n")
    
    applied, failed = await manager.run_migrations()
    
    print("\n" + "=" * 60)
    
    if applied:
        print(f"✅ Successfully applied {len(applied)} migration(s):")
        for version in applied:
            print(f"   - {version}")
    
    if failed:
        print(f"\n❌ Failed to apply {len(failed)} migration(s):")
        for version, error in failed:
            print(f"   - {version}: {error}")
        print("=" * 60 + "\n")
        return 1
    
    if not applied and not failed:
        print("✅ No pending migrations - database is up to date")
    
    print("=" * 60 + "\n")
    return 0


async def cmd_rollback(manager: MigrationManager, version: str) -> int:
    """Handle rollback command.
    
    Args:
        manager: Migration manager instance
        version: Version to rollback to
        
    Returns:
        Exit code
    """
    print(f"\nRolling back to version {version}...")
    success = await manager.rollback_migration(version)
    return 0 if success else 1


async def cmd_reset(manager: MigrationManager, force: bool) -> int:
    """Handle reset command.
    
    Args:
        manager: Migration manager instance
        force: Force flag
        
    Returns:
        Exit code
    """
    if not force:
        print("\n❌ Reset requires --force flag")
        print("⚠️  WARNING: This will DELETE ALL DATA!")
        return 1
    
    print("\n" + "!" * 60)
    print("WARNING: ABOUT TO DELETE ALL DATA!")
    print("!" * 60 + "\n")
    
    success = await manager.reset_migrations(force=True)
    return 0 if success else 1


async def main() -> int:
    """Main entry point.
    
    Returns:
        Exit code
    """
    parser = argparse.ArgumentParser(
        description="PostgreSQL Migration Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python runner.py status              # Check migration status
    python runner.py migrate             # Run pending migrations
    python runner.py rollback 001        # Rollback to version 001
    python runner.py reset --force       # Reset all migrations (DANGER)
        """
    )
    
    parser.add_argument(
        'command',
        choices=['status', 'migrate', 'rollback', 'reset'],
        help='Command to execute'
    )
    
    parser.add_argument(
        'version',
        nargs='?',
        help='Version for rollback command'
    )
    
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force reset (required for reset command)'
    )
    
    parser.add_argument(
        '--migrations-dir',
        type=Path,
        default=Path(__file__).parent,
        help='Directory containing migration files'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.command == 'rollback' and not args.version:
        parser.error("Rollback command requires a version argument")
    
    # Initialize manager
    manager = MigrationManager(args.migrations_dir)
    
    try:
        await manager.initialize()
        
        # Execute command
        if args.command == 'status':
            return await cmd_status(manager)
        
        elif args.command == 'migrate':
            return await cmd_migrate(manager)
        
        elif args.command == 'rollback':
            return await cmd_rollback(manager, args.version)
        
        elif args.command == 'reset':
            return await cmd_reset(manager, args.force)
        
        else:
            parser.print_help()
            return 1
            
    except Exception as e:
        logger.error(f"Command failed: {e}")
        return 1
    finally:
        await manager.close()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
