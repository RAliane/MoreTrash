"""Directus client integration with SQLite backend."""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import get_settings
from src.logging_config import get_logger

logger = get_logger(__name__)


class DirectusError(Exception):
    """Base exception for Directus errors."""
    pass


class DirectusClient:
    """Client for interacting with Directus CMS."""

    def __init__(
        self,
        url: Optional[str] = None,
        token: Optional[str] = None,
        database_path: Optional[str] = None,
    ):
        self.settings = get_settings()
        self.url = url or self.settings.directus_url
        self.token = token or self.settings.directus_token
        self.database_path = database_path or self.settings.directus_database_path
        self._local_mode = self.settings.directus_database == "sqlite"
        self._http_client: Optional[httpx.AsyncClient] = None

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None:
            headers = {}
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"
            self._http_client = httpx.AsyncClient(
                base_url=self.url,
                headers=headers,
                timeout=30.0,
            )
        return self._http_client

    @contextmanager
    def _get_db_connection(self):
        """Get SQLite database connection."""
        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _ensure_table(self, collection: str) -> None:
        """Ensure collection table exists in SQLite."""
        with self._get_db_connection() as conn:
            conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {collection} (
                    id TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def query(
        self,
        collection: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0,
        sort: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Query records from a collection."""
        if self._local_mode:
            return await self._query_local(collection, filters, limit, offset, sort)
        return await self._query_http(collection, filters, limit, offset, sort)

    async def _query_local(
        self,
        collection: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0,
        sort: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Query records from local SQLite."""
        self._ensure_table(collection)

        with self._get_db_connection() as conn:
            query = f"SELECT * FROM {collection}"
            params = []

            if filters:
                conditions = []
                for key, value in filters.items():
                    conditions.append(f"json_extract(data, '$.{key}') = ?")
                    params.append(value)
                if conditions:
                    query += " WHERE " + " AND ".join(conditions)

            if sort:
                order_clauses = []
                for field in sort:
                    if field.startswith("-"):
                        order_clauses.append(f"json_extract(data, '$.{field[1:]}') DESC")
                    else:
                        order_clauses.append(f"json_extract(data, '$.{field}') ASC")
                query += " ORDER BY " + ", ".join(order_clauses)
            else:
                query += " ORDER BY created_at DESC"

            query += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor = conn.execute(query, params)
            rows = cursor.fetchall()

            results = []
            for row in rows:
                data = json.loads(row["data"])
                data["id"] = row["id"]
                data["created_at"] = row["created_at"]
                data["updated_at"] = row["updated_at"]
                results.append(data)

            logger.info(
                "Directus local query executed",
                collection=collection,
                results_count=len(results),
            )
            return results

    async def _query_http(
        self,
        collection: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0,
        sort: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Query records via HTTP API."""
        client = await self._get_http_client()

        params: Dict[str, Any] = {
            "limit": limit,
            "offset": offset,
        }
        if sort:
            params["sort"] = ",".join(sort)
        if filters:
            for key, value in filters.items():
                params[f"filter[{key}]"] = value

        response = await client.get(f"/items/{collection}", params=params)
        response.raise_for_status()

        data = response.json()
        results = data.get("data", [])

        logger.info(
            "Directus HTTP query executed",
            collection=collection,
            results_count=len(results),
        )
        return results

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def create(
        self,
        collection: str,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create a new record in a collection."""
        if self._local_mode:
            return await self._create_local(collection, data)
        return await self._create_http(collection, data)

    async def _create_local(
        self,
        collection: str,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create record in local SQLite."""
        self._ensure_table(collection)

        record_id = str(uuid4())
        now = datetime.utcnow().isoformat()

        # Remove id if provided in data, we'll generate our own
        data_copy = {k: v for k, v in data.items() if k != "id"}

        with self._get_db_connection() as conn:
            conn.execute(
                f"INSERT INTO {collection} (id, data, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (record_id, json.dumps(data_copy), now, now),
            )
            conn.commit()

        result = {
            "id": record_id,
            **data_copy,
            "created_at": now,
            "updated_at": now,
        }

        logger.info(
            "Directus local record created",
            collection=collection,
            record_id=record_id,
        )
        return result

    async def _create_http(
        self,
        collection: str,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create record via HTTP API."""
        client = await self._get_http_client()

        response = await client.post(f"/items/{collection}", json=data)
        response.raise_for_status()

        result = response.json().get("data", {})

        logger.info(
            "Directus HTTP record created",
            collection=collection,
            record_id=result.get("id"),
        )
        return result

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def update(
        self,
        collection: str,
        record_id: str,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update a record in a collection."""
        if self._local_mode:
            return await self._update_local(collection, record_id, data)
        return await self._update_http(collection, record_id, data)

    async def _update_local(
        self,
        collection: str,
        record_id: str,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update record in local SQLite."""
        self._ensure_table(collection)

        now = datetime.utcnow().isoformat()

        with self._get_db_connection() as conn:
            # Get existing data
            cursor = conn.execute(
                f"SELECT data FROM {collection} WHERE id = ?",
                (record_id,),
            )
            row = cursor.fetchone()
            if not row:
                raise DirectusError(f"Record {record_id} not found in {collection}")

            existing_data = json.loads(row["data"])
            existing_data.update(data)

            conn.execute(
                f"UPDATE {collection} SET data = ?, updated_at = ? WHERE id = ?",
                (json.dumps(existing_data), now, record_id),
            )
            conn.commit()

        result = {
            "id": record_id,
            **existing_data,
            "updated_at": now,
        }

        logger.info(
            "Directus local record updated",
            collection=collection,
            record_id=record_id,
        )
        return result

    async def _update_http(
        self,
        collection: str,
        record_id: str,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update record via HTTP API."""
        client = await self._get_http_client()

        response = await client.patch(f"/items/{collection}/{record_id}", json=data)
        response.raise_for_status()

        result = response.json().get("data", {})

        logger.info(
            "Directus HTTP record updated",
            collection=collection,
            record_id=record_id,
        )
        return result

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def delete(
        self,
        collection: str,
        record_id: str,
    ) -> bool:
        """Delete a record from a collection."""
        if self._local_mode:
            return await self._delete_local(collection, record_id)
        return await self._delete_http(collection, record_id)

    async def _delete_local(
        self,
        collection: str,
        record_id: str,
    ) -> bool:
        """Delete record from local SQLite."""
        self._ensure_table(collection)

        with self._get_db_connection() as conn:
            cursor = conn.execute(
                f"DELETE FROM {collection} WHERE id = ?",
                (record_id,),
            )
            conn.commit()
            deleted = cursor.rowcount > 0

        if deleted:
            logger.info(
                "Directus local record deleted",
                collection=collection,
                record_id=record_id,
            )
        return deleted

    async def _delete_http(
        self,
        collection: str,
        record_id: str,
    ) -> bool:
        """Delete record via HTTP API."""
        client = await self._get_http_client()

        response = await client.delete(f"/items/{collection}/{record_id}")
        response.raise_for_status()

        logger.info(
            "Directus HTTP record deleted",
            collection=collection,
            record_id=record_id,
        )
        return True

    async def get_by_id(
        self,
        collection: str,
        record_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get a single record by ID."""
        results = await self.query(collection, filters={"id": record_id}, limit=1)
        return results[0] if results else None

    async def bootstrap_collections(self) -> None:
        """Bootstrap collections from models.json."""
        models_path = Path(self.settings.directus_bootstrap_models)

        if not models_path.exists():
            logger.warning(
                "Bootstrap models file not found",
                path=str(models_path),
            )
            return

        with open(models_path) as f:
            models = json.load(f)

        collections = models.get("collections", [])

        for collection_def in collections:
            collection_name = collection_def.get("collection")
            if not collection_name:
                continue

            if self._local_mode:
                self._ensure_table(collection_name)
                logger.info(
                    "Collection bootstrapped",
                    collection=collection_name,
                )

        logger.info(
            "Directus bootstrap completed",
            collections_count=len(collections),
        )

    async def close(self) -> None:
        """Close client connections."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None


# Singleton instance
_directus_client: Optional[DirectusClient] = None


def get_directus_client() -> DirectusClient:
    """Get singleton Directus client instance."""
    global _directus_client
    if _directus_client is None:
        _directus_client = DirectusClient()
    return _directus_client


async def init_directus() -> DirectusClient:
    """Initialize Directus and bootstrap collections."""
    client = get_directus_client()
    await client.bootstrap_collections()
    return client
