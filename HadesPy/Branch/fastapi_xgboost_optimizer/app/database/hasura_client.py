"""
Hasura GraphQL client for database operations.

This module provides GraphQL API access to the database using PyHasura
for optimized queries, mutations, and subscriptions.
"""

import asyncio
import json
from typing import Any, Dict, List, Optional

import aiohttp
import httpx
from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport
from gql.transport.httpx import HTTPXAsyncTransport

from app.core.config import settings
from app.core.exceptions import DatabaseException
from app.core.models import (
    Constraint,
    Microtask,
    Objective,
    OptimizationRequest,
    OptimizationResponse,
    OptimizationStatus,
    Solution,
)
from app.infrastructure.logging_config import get_logger


class HasuraClient:
    """
    Hasura GraphQL client for database operations.
    
    Provides GraphQL API access for optimized database operations,
    real-time subscriptions, and permission management.
    """
    
    def __init__(self):
        """Initialize the Hasura client."""
        self.logger = get_logger(__name__)
        self.client = None
        self.transport = None
        self.session = None
        self.is_ready = False
        
        # Hasura configuration
        self.hasura_url = settings.HASURA_URL
        self.admin_secret = settings.HASURA_ADMIN_SECRET
        
        self.logger.info("Hasura client initialized")
    
    async def initialize(self) -> None:
        """
        Initialize the Hasura client connection.
        
        Raises:
            DatabaseException: If initialization fails
        """
        try:
            # Create transport with admin secret
            headers = {"x-hasura-admin-secret": self.admin_secret}
            
            # Use HTTPX transport for better performance
            self.transport = HTTPXAsyncTransport(
                url=self.hasura_url,
                headers=headers,
                timeout=30.0,
            )
            
            # Create GraphQL client
            self.client = Client(
                transport=self.transport,
                fetch_schema_from_transport=True,
            )
            
            # Test connection
            async with self.client as session:
                self.session = session
                
                # Simple health check query
                health_query = gql("""
                    query {
                        __schema {
                            queryType {
                                name
                            }
                        }
                    }
                """)
                
                result = await session.execute(health_query)
                
                if result:
                    self.is_ready = True
                    self.logger.info("Hasura client ready")
                else:
                    raise Exception("Failed to connect to Hasura")
                
        except Exception as exc:
            self.logger.error(
                "Failed to initialize Hasura client",
                extra={"error": str(exc)},
                exc_info=True
            )
            raise DatabaseException(
                message="Failed to initialize Hasura client",
                operation="initialize",
                database_error=str(exc),
            )
    
    async def close(self) -> None:
        """Close the Hasura client connection."""
        try:
            if self.transport:
                await self.transport.close()
            
            self.is_ready = False
            self.logger.info("Hasura client closed")
            
        except Exception as exc:
            self.logger.error(
                "Error closing Hasura client",
                extra={"error": str(exc)}
            )
    
    async def execute_query(
        self,
        query: str,
        variables: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute a GraphQL query.
        
        Args:
            query: GraphQL query string
            variables: Query variables
            
        Returns:
            Dict[str, Any]: Query result
            
        Raises:
            DatabaseException: If query execution fails
        """
        if not self.is_ready or not self.session:
            raise DatabaseException(
                message="Hasura client not initialized",
                operation="execute_query",
            )
        
        try:
            # Parse and execute query
            gql_query = gql(query)
            result = await self.session.execute(gql_query, variable_values=variables)
            
            self.logger.debug(
                "GraphQL query executed",
                extra={"query": query[:100] + "..." if len(query) > 100 else query}
            )
            
            return result
            
        except Exception as exc:
            self.logger.error(
                "GraphQL query failed",
                extra={"error": str(exc)}
            )
            raise DatabaseException(
                message="GraphQL query failed",
                operation="execute_query",
                database_error=str(exc),
            )
    
    async def execute_mutation(
        self,
        mutation: str,
        variables: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute a GraphQL mutation.
        
        Args:
            mutation: GraphQL mutation string
            variables: Mutation variables
            
        Returns:
            Dict[str, Any]: Mutation result
            
        Raises:
            DatabaseException: If mutation execution fails
        """
        if not self.is_ready or not self.session:
            raise DatabaseException(
                message="Hasura client not initialized",
                operation="execute_mutation",
            )
        
        try:
            # Parse and execute mutation
            gql_mutation = gql(mutation)
            result = await self.session.execute(gql_mutation, variable_values=variables)
            
            self.logger.debug(
                "GraphQL mutation executed",
                extra={"mutation": mutation[:100] + "..." if len(mutation) > 100 else mutation}
            )
            
            return result
            
        except Exception as exc:
            self.logger.error(
                "GraphQL mutation failed",
                extra={"error": str(exc)}
            )
            raise DatabaseException(
                message="GraphQL mutation failed",
                operation="execute_mutation",
                database_error=str(exc),
            )
    
    async def store_optimization_request(
        self,
        request_id: str,
        request_data: Dict[str, Any],
        session: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """
        Store optimization request in database.
        
        Args:
            request_id: Request identifier
            request_data: Request data
            session: Database session (optional)
            
        Returns:
            Dict[str, Any]: Insert result
        """
        mutation = """
            mutation InsertOptimizationRequest($request_id: String!, $request_data: jsonb!) {
                insert_optimization_requests_one(
                    object: {
                        request_id: $request_id,
                        request_data: $request_data,
                        status: "pending"
                    }
                ) {
                    request_id
                    created_at
                }
            }
        """
        
        variables = {
            "request_id": request_id,
            "request_data": request_data,
        }
        
        result = await self.execute_mutation(mutation, variables)
        return result
    
    async def store_optimization_result(
        self,
        request_id: str,
        result: Dict[str, Any],
        session: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """
        Store optimization result in database.
        
        Args:
            request_id: Request identifier
            result: Optimization result
            session: Database session (optional)
            
        Returns:
            Dict[str, Any]: Update result
        """
        mutation = """
            mutation UpdateOptimizationResult(
                $request_id: String!,
                $result: jsonb!,
                $status: String!
            ) {
                update_optimization_requests(
                    where: { request_id: { _eq: $request_id } },
                    _set: {
                        result_data: $result,
                        status: $status,
                        completed_at: now()
                    }
                ) {
                    affected_rows
                }
            }
        """
        
        variables = {
            "request_id": request_id,
            "result": result,
            "status": result.get("status", "completed"),
        }
        
        result = await self.execute_mutation(mutation, variables)
        return result
    
    async def store_optimization_error(
        self,
        request_id: str,
        error: str,
        session: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """
        Store optimization error in database.
        
        Args:
            request_id: Request identifier
            error: Error message
            session: Database session (optional)
            
        Returns:
            Dict[str, Any]: Update result
        """
        mutation = """
            mutation UpdateOptimizationError(
                $request_id: String!,
                $error: String!
            ) {
                update_optimization_requests(
                    where: { request_id: { _eq: $request_id } },
                    _set: {
                        error_message: $error,
                        status: "failed",
                        completed_at: now()
                    }
                ) {
                    affected_rows
                }
            }
        """
        
        variables = {
            "request_id": request_id,
            "error": error,
        }
        
        result = await self.execute_mutation(mutation, variables)
        return result
    
    async def get_optimization_status(
        self,
        request_id: str,
        session: Optional[AsyncSession] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Get optimization status from database.
        
        Args:
            request_id: Request identifier
            session: Database session (optional)
            
        Returns:
            Optional[Dict[str, Any]]: Status information
        """
        query = """
            query GetOptimizationStatus($request_id: String!) {
                optimization_requests(
                    where: { request_id: { _eq: $request_id } }
                ) {
                    request_id
                    status
                    created_at
                    started_at
                    completed_at
                    progress
                    current_stage
                }
            }
        """
        
        variables = {"request_id": request_id}
        
        result = await self.execute_query(query, variables)
        
        if result and result.get("optimization_requests"):
            return result["optimization_requests"][0]
        
        return None
    
    async def get_optimization_result(
        self,
        request_id: str,
        session: Optional[AsyncSession] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Get optimization result from database.
        
        Args:
            request_id: Request identifier
            session: Database session (optional)
            
        Returns:
            Optional[Dict[str, Any]]: Optimization result
        """
        query = """
            query GetOptimizationResult($request_id: String!) {
                optimization_requests(
                    where: { request_id: { _eq: $request_id } }
                ) {
                    request_id
                    request_data
                    result_data
                    status
                    created_at
                    completed_at
                    execution_time
                }
            }
        """
        
        variables = {"request_id": request_id}
        
        result = await self.execute_query(query, variables)
        
        if result and result.get("optimization_requests"):
            return result["optimization_requests"][0]
        
        return None
    
    async def update_optimization_status(
        self,
        request_id: str,
        status: OptimizationStatus,
        session: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """
        Update optimization status.
        
        Args:
            request_id: Request identifier
            status: New status
            session: Database session (optional)
            
        Returns:
            Dict[str, Any]: Update result
        """
        mutation = """
            mutation UpdateOptimizationStatus(
                $request_id: String!,
                $status: String!
            ) {
                update_optimization_requests(
                    where: { request_id: { _eq: $request_id } },
                    _set: {
                        status: $status,
                        started_at: case when $status = 'processing' then now() else started_at end
                    }
                ) {
                    affected_rows
                }
            }
        """
        
        variables = {
            "request_id": request_id,
            "status": status.value,
        }
        
        result = await self.execute_mutation(mutation, variables)
        return result
    
    async def store_microtask_result(
        self,
        microtask: Microtask,
        request_id: str,
    ) -> Dict[str, Any]:
        """
        Store microtask result in database.
        
        Args:
            microtask: Microtask instance
            request_id: Parent request ID
            
        Returns:
            Dict[str, Any]: Insert result
        """
        mutation = """
            mutation InsertMicrotask(
                $task_id: String!,
                $request_id: String!,
                $name: String!,
                $task_type: String!,
                $parameters: jsonb!,
                $status: String!,
                $result: jsonb,
                $error: String,
                $execution_time: numeric,
                $dependencies: jsonb!
            ) {
                insert_microtasks_one(
                    object: {
                        task_id: $task_id,
                        request_id: $request_id,
                        name: $name,
                        task_type: $task_type,
                        parameters: $parameters,
                        status: $status,
                        result_data: $result,
                        error_message: $error,
                        execution_time: $execution_time,
                        dependencies: $dependencies
                    }
                ) {
                    task_id
                    created_at
                }
            }
        """
        
        variables = {
            "task_id": microtask.id,
            "request_id": request_id,
            "name": microtask.name,
            "task_type": microtask.task_type,
            "parameters": microtask.parameters,
            "status": microtask.status.value,
            "result": microtask.result,
            "error": microtask.error,
            "execution_time": microtask.execution_time,
            "dependencies": microtask.dependencies,
        }
        
        result = await self.execute_mutation(mutation, variables)
        return result
    
    async def get_microtask_history(
        self,
        request_id: str,
    ) -> List[Dict[str, Any]]:
        """
        Get microtask execution history for a request.
        
        Args:
            request_id: Request identifier
            
        Returns:
            List[Dict[str, Any]]: Microtask history
        """
        query = """
            query GetMicrotaskHistory($request_id: String!) {
                microtasks(
                    where: { request_id: { _eq: $request_id } }
                    order_by: { created_at: asc }
                ) {
                    task_id
                    name
                    task_type
                    status
                    result_data
                    error_message
                    execution_time
                    created_at
                    completed_at
                }
            }
        """
        
        variables = {"request_id": request_id}
        
        result = await self.execute_query(query, variables)
        
        return result.get("microtasks", []) if result else []
    
    async def get_optimization_metrics(
        self,
        time_range: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Get optimization metrics from database.
        
        Args:
            time_range: Optional time range filter
            
        Returns:
            Dict[str, Any]: Metrics data
        """
        query = """
            query GetOptimizationMetrics {
                optimization_requests_aggregate {
                    aggregate {
                        count
                        avg {
                            execution_time
                        }
                    }
                }
                
                optimization_requests_aggregate(
                    where: { status: { _eq: "completed" } }
                ) {
                    aggregate {
                        count
                    }
                }
                
                optimization_requests_aggregate(
                    where: { status: { _eq: "failed" } }
                ) {
                    aggregate {
                        count
                    }
                }
            }
        """
        
        result = await self.execute_query(query)
        
        if result:
            total = result["optimization_requests_aggregate"]["aggregate"]["count"]
            completed = result["optimization_requests_aggregate_2"]["aggregate"]["count"]
            failed = result["optimization_requests_aggregate_3"]["aggregate"]["count"]
            avg_time = result["optimization_requests_aggregate"]["aggregate"]["avg"]["execution_time"]
            
            return {
                "total_requests": total,
                "completed_requests": completed,
                "failed_requests": failed,
                "success_rate": completed / total if total > 0 else 0,
                "average_execution_time": avg_time,
            }
        
        return {}
    
    async def health_check(self) -> bool:
        """Check Hasura client health."""
        try:
            if not self.is_ready:
                return False
            
            query = gql("""
                query {
                    __schema {
                        queryType {
                            name
                        }
                    }
                }
            """)
            
            result = await self.execute_query(query)
            return bool(result)
            
        except Exception:
            return False
    
    async def subscribe_to_updates(
        self,
        request_id: str,
        callback: Callable[[Dict[str, Any]], None],
    ) -> None:
        """
        Subscribe to real-time updates for an optimization request.
        
        Args:
            request_id: Request identifier
            callback: Callback function for updates
        """
        # This would implement GraphQL subscriptions
        # For now, it's a placeholder
        self.logger.info(
            "Subscription requested",
            extra={"request_id": request_id}
        )
    
    async def create_database_schema(self) -> bool:
        """Create database schema if it doesn't exist."""
        try:
            # Create optimization_requests table
            mutation = """
                mutation CreateOptimizationRequestsTable {
                    create_table(
                        name: "optimization_requests",
                        columns: [
                            {
                                name: "request_id",
                                type: "text",
                                nullable: false,
                                primary_key: true
                            },
                            {
                                name: "request_data",
                                type: "jsonb",
                                nullable: false
                            },
                            {
                                name: "result_data",
                                type: "jsonb"
                            },
                            {
                                name: "status",
                                type: "text",
                                nullable: false,
                                default: "'pending'"
                            },
                            {
                                name: "progress",
                                type: "numeric",
                                default: "0"
                            },
                            {
                                name: "current_stage",
                                type: "text"
                            },
                            {
                                name: "execution_time",
                                type: "numeric"
                            },
                            {
                                name: "error_message",
                                type: "text"
                            },
                            {
                                name: "created_at",
                                type: "timestamptz",
                                nullable: false,
                                default: "now()"
                            },
                            {
                                name: "started_at",
                                type: "timestamptz"
                            },
                            {
                                name: "completed_at",
                                type: "timestamptz"
                            }
                        ]
                    ) {
                        name
                    }
                }
            """
            
            # Note: This is a simplified example - in practice, you'd use
            # database migrations with tools like Alembic
            
            self.logger.info("Database schema creation requested")
            return True
            
        except Exception as exc:
            self.logger.error(
                "Failed to create database schema",
                extra={"error": str(exc)}
            )
            return False