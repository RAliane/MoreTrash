from typing import Dict, List, Any, Optional
import aiohttp
import json
import structlog

from app.infrastructure.config import settings
from app.infrastructure.logging import get_database_logger

logger = get_database_logger()


class HasuraClient:
    """PyHasura GraphQL client for database operations."""

    def __init__(self):
        self.url = settings.HASURA_URL
        self.admin_secret = settings.HASURA_ADMIN_SECRET
        self.session: Optional[aiohttp.ClientSession] = None

    async def initialize(self) -> bool:
        """Initialize HTTP client session."""
        try:
            headers = {}
            if self.admin_secret:
                headers["X-Hasura-Admin-Secret"] = self.admin_secret

            self.session = aiohttp.ClientSession(
                headers=headers, timeout=aiohttp.ClientTimeout(total=30)
            )

            logger.info("Hasura client initialized successfully")
            return True

        except Exception as e:
            logger.error("Hasura client initialization failed", error=str(e))
            return False

    async def close(self):
        """Close HTTP client session."""
        if self.session:
            await self.session.close()
            logger.info("Hasura client session closed")

    async def execute_query(
        self,
        query: str,
        variables: Optional[Dict[str, Any]] = None,
        operation_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute GraphQL query."""
        if not self.session:
            raise RuntimeError("Hasura client not initialized")

        payload = {"query": query}
        if variables:
            payload["variables"] = variables
        if operation_name:
            payload["operationName"] = operation_name

        try:
            async with self.session.post(self.url, json=payload) as response:
                result = await response.json()

                if response.status != 200:
                    logger.error(
                        "Hasura query failed", status=response.status, response=result
                    )
                    raise RuntimeError(f"Hasura query failed: {response.status}")

                if "errors" in result:
                    logger.warning(
                        "Hasura query returned errors", errors=result["errors"]
                    )
                    # Don't raise here, let caller handle

                logger.debug(
                    "Hasura query executed successfully",
                    has_data="data" in result,
                    has_errors="errors" in result,
                )

                return result

        except Exception as e:
            logger.error("Hasura query execution failed", error=str(e))
            raise

    async def insert_optimization_request(
        self, request_data: Dict[str, Any]
    ) -> Optional[str]:
        """Insert optimization request into database."""
        mutation = """
        mutation InsertOptimizationRequest($request: optimization_requests_insert_input!) {
            insert_optimization_requests_one(object: $request) {
                id
                created_at
            }
        }
        """

        variables = {"request": request_data}

        try:
            result = await self.execute_query(mutation, variables)

            if "data" in result and result["data"]["insert_optimization_requests_one"]:
                request_id = result["data"]["insert_optimization_requests_one"]["id"]
                logger.info("Optimization request inserted", request_id=request_id)
                return request_id
            else:
                logger.error("Failed to insert optimization request", result=result)
                return None

        except Exception as e:
            logger.error("Optimization request insertion failed", error=str(e))
            return None

    async def insert_optimization_result(
        self, request_id: str, result_data: Dict[str, Any]
    ) -> bool:
        """Insert optimization result into database."""
        mutation = """
        mutation InsertOptimizationResult($result: optimization_results_insert_input!) {
            insert_optimization_results_one(object: $result) {
                id
            }
        }
        """

        variables = {"result": {"request_id": request_id, **result_data}}

        try:
            result = await self.execute_query(mutation, variables)

            if "data" in result and result["data"]["insert_optimization_results_one"]:
                logger.info("Optimization result inserted", request_id=request_id)
                return True
            else:
                logger.error("Failed to insert optimization result", result=result)
                return False

        except Exception as e:
            logger.error("Optimization result insertion failed", error=str(e))
            return False

    async def get_optimization_history(
        self, limit: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get optimization request history."""
        query = """
        query GetOptimizationHistory($limit: Int, $offset: Int) {
            optimization_requests(
                limit: $limit
                offset: $offset
                order_by: {created_at: desc}
            ) {
                id
                name
                status
                created_at
                completed_at
                execution_time
                results_aggregate {
                    aggregate {
                        count
                    }
                }
            }
        }
        """

        variables = {"limit": limit, "offset": offset}

        try:
            result = await self.execute_query(query, variables)

            if "data" in result and "optimization_requests" in result["data"]:
                history = result["data"]["optimization_requests"]
                logger.debug("Optimization history retrieved", count=len(history))
                return history
            else:
                logger.warning("No optimization history found")
                return []

        except Exception as e:
            logger.error("Optimization history retrieval failed", error=str(e))
            return []

    async def get_request_details(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about an optimization request."""
        query = """
        query GetRequestDetails($request_id: uuid!) {
            optimization_requests_by_pk(id: $request_id) {
                id
                name
                description
                variables
                objectives
                constraints
                parameters
                status
                created_at
                completed_at
                execution_time
                results {
                    id
                    solution_data
                    fitness_score
                    rank
                    created_at
                }
            }
        }
        """

        variables = {"request_id": request_id}

        try:
            result = await self.execute_query(query, variables)

            if "data" in result and result["data"]["optimization_requests_by_pk"]:
                details = result["data"]["optimization_requests_by_pk"]
                logger.debug("Request details retrieved", request_id=request_id)
                return details
            else:
                logger.warning("Request not found", request_id=request_id)
                return None

        except Exception as e:
            logger.error(
                "Request details retrieval failed", request_id=request_id, error=str(e)
            )
            return None

    async def update_request_status(
        self, request_id: str, status: str, execution_time: Optional[float] = None
    ) -> bool:
        """Update optimization request status."""
        mutation = """
        mutation UpdateRequestStatus(
            $request_id: uuid!,
            $status: String!,
            $execution_time: numeric
        ) {
            update_optimization_requests_by_pk(
                pk_columns: {id: $request_id},
                _set: {
                    status: $status,
                    execution_time: $execution_time,
                    completed_at: now()
                }
            ) {
                id
                status
            }
        }
        """

        variables = {
            "request_id": request_id,
            "status": status,
            "execution_time": execution_time,
        }

        try:
            result = await self.execute_query(mutation, variables)

            if (
                "data" in result
                and result["data"]["update_optimization_requests_by_pk"]
            ):
                logger.info(
                    "Request status updated", request_id=request_id, status=status
                )
                return True
            else:
                logger.error("Failed to update request status", request_id=request_id)
                return False

        except Exception as e:
            logger.error(
                "Request status update failed", request_id=request_id, error=str(e)
            )
            return False
