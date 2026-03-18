"""
Directus REST API Client

Handles REST API operations with Directus CMS for content management
and administrative tasks.
"""

import aiohttp
import json
from typing import Dict, Any, List, Optional
import logging
import os

logger = logging.getLogger(__name__)


class DirectusClient:
    """REST API client for Directus"""

    def __init__(self):
        self.base_url = os.getenv("DIRECTUS_URL", "http://localhost:8055")
        self.api_key = os.getenv("DIRECTUS_API_KEY", "")
        self.session: aiohttp.ClientSession = None

    async def initialize(self):
        """Initialize the HTTP session"""
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        self.session = aiohttp.ClientSession(headers=headers)
        logger.info("Directus client initialized")

    async def get(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """GET request to Directus API"""
        url = f"{self.base_url}{endpoint}"
        async with self.session.get(url, params=params) as response:
            if response.status != 200:
                error_text = await response.text()
                logger.error(f"Directus GET failed: {response.status} - {error_text}")
                raise Exception(f"Directus GET failed: {response.status}")

            return await response.json()

    async def post(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """POST request to Directus API"""
        url = f"{self.base_url}{endpoint}"
        async with self.session.post(url, json=data) as response:
            if response.status not in [200, 201]:
                error_text = await response.text()
                logger.error(f"Directus POST failed: {response.status} - {error_text}")
                raise Exception(f"Directus POST failed: {response.status}")

            return await response.json()

    async def patch(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """PATCH request to Directus API"""
        url = f"{self.base_url}{endpoint}"
        async with self.session.patch(url, json=data) as response:
            if response.status != 200:
                error_text = await response.text()
                logger.error(f"Directus PATCH failed: {response.status} - {error_text}")
                raise Exception(f"Directus PATCH failed: {response.status}")

            return await response.json()

    async def delete(self, endpoint: str) -> Dict[str, Any]:
        """DELETE request to Directus API"""
        url = f"{self.base_url}{endpoint}"
        async with self.session.delete(url) as response:
            if response.status != 200:
                error_text = await response.text()
                logger.error(
                    f"Directus DELETE failed: {response.status} - {error_text}"
                )
                raise Exception(f"Directus DELETE failed: {response.status}")

            return await response.json()

    # Specific methods for common operations

    async def get_pending_items(self) -> List[Dict[str, Any]]:
        """Get items with pending status"""
        params = {"filter[status][_eq]": "pending"}
        result = await self.get("/items", params)
        return result.get("data", [])

    async def update_item_status(self, item_id: str, status: str) -> Dict[str, Any]:
        """Update item status"""
        data = {"status": status}
        return await self.patch(f"/items/{item_id}", data)

    async def create_content(
        self, collection: str, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create new content in a collection"""
        return await self.post(f"/items/{collection}", data)

    async def get_content(
        self, collection: str, item_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get content from a collection"""
        endpoint = f"/items/{collection}"
        if item_id:
            endpoint += f"/{item_id}"
        return await self.get(endpoint)

    async def update_content(
        self, collection: str, item_id: str, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update content in a collection"""
        return await self.patch(f"/items/{collection}/{item_id}", data)

    async def delete_content(self, collection: str, item_id: str) -> Dict[str, Any]:
        """Delete content from a collection"""
        return await self.delete(f"/items/{collection}/{item_id}")

    async def close(self):
        """Close the HTTP session"""
        if self.session:
            await self.session.close()
            logger.info("Directus client closed")

    async def health_check(self) -> bool:
        """Check Directus health"""
        try:
            # Try to access server info endpoint
            result = await self.get("/server/info")
            return bool(result)
        except:
            return False
