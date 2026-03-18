"""
Main API endpoints for the FastAPI XGBoost Optimizer.

This module implements the primary API endpoints for optimization requests,
including the main optimization endpoint, health checks, and metrics.
"""

import asyncio
import time
from typing import Any, Dict, List, Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Request,
    Response,
    status,
)
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.backend.api.dependencies import (
    RateLimiterDependency,
    authenticate_api_key,
    get_request_id,
)
from src.backend.api.validation import (
    BatchOptimizationRequest,
    ErrorResponse,
    HealthResponse,
    MetricsResponse,
    OptimizationRequest,
    OptimizationResponse,
    OptimizationStatusResponse,
)
from src.backend.core.config import settings
from src.backend.core.exceptions import ValidationException
from src.backend.core.models import OptimizationStatus
from src.backend.database.hasura_client import HasuraClient
from src.backend.orchestration.workflow import OptimizationWorkflow
from src.backend.infrastructure.monitoring import MetricsCollector
from src.backend.services.knn_service import HybridKNNService

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Create router
router = APIRouter()

# Initialize services
workflow = OptimizationWorkflow()
metrics_collector = MetricsCollector()
hasura_client = HasuraClient()


@router.post(
    "/optimize",
    response_model=OptimizationResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit optimization request",
    description="Submit a new optimization problem for processing",
    dependencies=[Depends(authenticate_api_key)],
)
@limiter.limit(settings.RATE_LIMIT)
async def submit_optimization(
    request: Request,
    response: Response,
    optimization_request: OptimizationRequest,
    background_tasks: BackgroundTasks,
    request_id: str = Depends(get_request_id),
) -> OptimizationResponse:
    """
    Submit a new optimization request.

    This endpoint accepts optimization problems and returns a response with
    the optimization results. Processing is done asynchronously with
    real-time progress tracking.

    Args:
        request: FastAPI request object
        response: FastAPI response object
        optimization_request: Optimization problem definition
        background_tasks: Background task manager
        request_id: Unique request identifier

    Returns:
        OptimizationResponse: Optimization results
    """
    start_time = time.time()

    try:
        # Set request ID in response headers
        response.headers["X-Request-ID"] = request_id

        # Track request metrics
        metrics_collector.record_request_start(request_id, "optimize")

        # TODO: Store request in database via Hasura GraphQL
        # await hasura_client.store_optimization_request(
        #     request_id=request_id,
        #     request_data=optimization_request.dict(),
        # )

        # Execute optimization workflow
        optimization_result = await workflow.execute(
            request=optimization_request, request_id=request_id
        )

        # Record metrics
        execution_time = time.time() - start_time
        metrics_collector.record_request_complete(
            request_id=request_id,
            status=optimization_result.status,
            execution_time=execution_time,
        )

        # TODO: Store results via Hasura GraphQL
        # await hasura_client.store_optimization_result(
        #     request_id=request_id, result=optimization_result.dict()
        # )

        return optimization_result

    except Exception as e:
        # Record error metrics
        metrics_collector.record_request_error(request_id, str(e))

        # TODO: Store error information via Hasura GraphQL
        # await hasura_client.store_optimization_error(
        #     request_id=request_id, error=str(e)
        # )

        raise


@router.post(
    "/optimize/batch",
    response_model=List[OptimizationResponse],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit batch optimization requests",
    description="Submit multiple optimization problems for batch processing",
    dependencies=[Depends(authenticate_api_key)],
)
@limiter.limit("50/minute")
async def submit_batch_optimization(
    request: Request,
    batch_request: BatchOptimizationRequest,
    request_id: str = Depends(get_request_id),
) -> List[OptimizationResponse]:
    """
    Submit multiple optimization requests for batch processing.

    Args:
        request: FastAPI request object
        batch_request: Batch of optimization requests
        request_id: Unique request identifier

    Returns:
        List[OptimizationResponse]: List of optimization results
    """
    # Process requests concurrently with semaphore to limit parallelism
    semaphore = asyncio.Semaphore(5)  # Max 5 concurrent optimizations

    async def process_single_request(
        opt_request: OptimizationRequest, idx: int
    ) -> OptimizationResponse:
        async with semaphore:
            sub_request_id = f"{request_id}-{idx}"
            return await workflow.execute(
                request=opt_request, request_id=sub_request_id
            )

    # Create tasks for all requests
    tasks = [
        process_single_request(opt_request, idx)
        for idx, opt_request in enumerate(batch_request.requests)
    ]

    # Execute all tasks concurrently
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Handle exceptions and convert to responses
    responses = []
    for idx, result in enumerate(results):
        if isinstance(result, Exception):
            # Create error response for failed requests
            error_response = OptimizationResponse(
                request_id=f"{request_id}-{idx}",
                status=OptimizationStatus.FAILED,
                execution_time=0.0,
                error={
                    "code": "BATCH_PROCESSING_ERROR",
                    "message": str(result),
                    "details": {"index": idx},
                },
            )
            responses.append(error_response)
        else:
            responses.append(result)

    return responses


@router.get(
    "/optimize/{request_id}/status",
    response_model=OptimizationStatusResponse,
    summary="Get optimization status",
    description="Check the status of an optimization request",
    dependencies=[Depends(authenticate_api_key)],
)
async def get_optimization_status(
    request_id: str,
) -> OptimizationStatusResponse:
    """
    Get the current status of an optimization request.

    Args:
        request_id: Optimization request ID

    Returns:
        OptimizationStatusResponse: Current status information
    """
    # TODO: Query optimization status from Hasura GraphQL
    # status_data = await hasura_client.get_optimization_status(
    #     request_id=request_id
    # )
    status_data = None  # Placeholder

    if not status_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Optimization request '{request_id}' not found",
        )

    return OptimizationStatusResponse(**status_data)


@router.get(
    "/optimize/{request_id}/results",
    response_model=OptimizationResponse,
    summary="Get optimization results",
    description="Retrieve the results of a completed optimization",
    dependencies=[Depends(authenticate_api_key)],
)
async def get_optimization_results(
    request_id: str,
) -> OptimizationResponse:
    """
    Get the results of a completed optimization request.

    Args:
        request_id: Optimization request ID

    Returns:
        OptimizationResponse: Optimization results
    """
    # TODO: Query optimization results from Hasura GraphQL
    # result_data = await hasura_client.get_optimization_result(
    #     request_id=request_id
    # )
    result_data = None  # Placeholder

    if not result_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Optimization request '{request_id}' not found or not completed",
        )

    return OptimizationResponse(**result_data)


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check endpoint",
    description="Check the health status of the service",
)
async def health_check(request: Request) -> HealthResponse:
    """
    Health check endpoint for service monitoring.

    Args:
        request: FastAPI request object

    Returns:
        HealthResponse: Service health status
    """
    # Check database connectivity
    db_healthy = await hasura_client.health_check()

    # Check ML model availability
    ml_healthy = (
        hasattr(request.app.state, "xgboost_engine")
        and request.app.state.xgboost_engine.is_ready()
    )

    # Calculate overall health
    overall_healthy = db_healthy and ml_healthy

    return HealthResponse(
        status="healthy" if overall_healthy else "unhealthy",
        timestamp=time.time(),
        version="1.0.0",
        services={
            "database": "healthy" if db_healthy else "unhealthy",
            "ml_engine": "healthy" if ml_healthy else "unhealthy",
            "api": "healthy",
        },
    )


@router.get(
    "/metrics",
    response_model=MetricsResponse,
    summary="Get service metrics",
    description="Retrieve performance and operational metrics",
    dependencies=[Depends(authenticate_api_key)],
)
async def get_metrics() -> MetricsResponse:
    """
    Get service performance and operational metrics.

    Returns:
        MetricsResponse: Service metrics
    """
    # Get current metrics from collector
    current_metrics = metrics_collector.get_current_metrics()

    return MetricsResponse(
        timestamp=time.time(),
        uptime=metrics_collector.get_uptime(),
        requests_total=current_metrics.get("requests_total", 0),
        requests_per_minute=current_metrics.get("requests_per_minute", 0),
        average_response_time=current_metrics.get("average_response_time", 0.0),
        error_rate=current_metrics.get("error_rate", 0.0),
        active_optimizations=current_metrics.get("active_optimizations", 0),
        completed_optimizations=current_metrics.get("completed_optimizations", 0),
        failed_optimizations=current_metrics.get("failed_optimizations", 0),
        constraint_satisfaction_rate=current_metrics.get(
            "constraint_satisfaction_rate", 0.0
        ),
        average_fitness_score=current_metrics.get("average_fitness_score", 0.0),
    )


@router.get(
    "/config",
    response_model=Dict[str, Any],
    summary="Get configuration",
    description="Retrieve current service configuration (excluding sensitive data)",
    dependencies=[Depends(authenticate_api_key)],
)
async def get_configuration() -> Dict[str, Any]:
    """
    Get current service configuration.

    Returns:
        Dict[str, Any]: Service configuration (sanitized)
    """
    from src.backend.core.config import settings

    # Return sanitized configuration
    return {
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "debug": settings.DEBUG,
        "rate_limit": settings.RATE_LIMIT,
        "xgboost_parameters": {
            "n_estimators": settings.XGBOOST_N_ESTIMATORS,
            "max_depth": settings.XGBOOST_MAX_DEPTH,
            "learning_rate": settings.XGBOOST_LEARNING_RATE,
        },
        "pygad_parameters": {
            "population_size": settings.PYGAD_POPULATION_SIZE,
            "num_generations": settings.PYGAD_NUM_GENERATIONS,
            "parent_selection_type": settings.PYGAD_PARENT_SELECTION_TYPE,
        },
        "ortools_parameters": {
            "max_time": settings.ORTOOLS_MAX_TIME,
            "num_search_workers": settings.ORTOOLS_NUM_SEARCH_WORKERS,
            "enable_lns": settings.ORTOOLS_ENABLE_LNS,
        },
        "workflow_parameters": {
            "timeout": settings.WORKFLOW_TIMEOUT,
            "retry_attempts": settings.MICROTASK_RETRY_ATTEMPTS,
        },
    }


# =============================================
# kNN Match Endpoints (Hybrid Implementation)
# =============================================


@router.post(
    "/matches",
    response_model=Dict[str, Any],  # Will be defined in models
    status_code=status.HTTP_200_OK,
    summary="Find similar matches using hybrid kNN",
    description="Find similar items using PostGIS kNN with Python preprocessing",
    dependencies=[Depends(authenticate_api_key)],
)
async def find_matches(
    request: Dict[str, Any],  # Will be typed with MatchRequest
    user_id: str = Depends(authenticate_api_key),
    db_session=Depends(get_database_session),  # Need to add this
) -> Dict[str, Any]:
    """
    Find similar matches using hybrid kNN approach.

    This endpoint implements CC-OAS compliant vector similarity search:
    - PostGIS handles core kNN operations (deterministic, DB-first)
    - Python handles preprocessing/postprocessing (flexible business logic)
    - Zero-trust: No direct vector access from application layer
    - UK GDPR compliant: All core operations in UK-hosted Postgres

    Args:
        request: Match request with vector, location, and preferences
        user_id: Authenticated user ID
        db_session: Database session

    Returns:
        Dict containing matches and metadata
    """
    try:
        # Create match request from dict
        match_request = {
            "vector": request.get("vector", []),
            "location": request.get("location"),
            "preferences": request.get("preferences", {}),
        }

        # Initialize hybrid kNN service
        knn_service = HybridKNNService(db_session)

        # Execute hybrid kNN search
        result = await knn_service.find_similar_matches(match_request, user_id)

        return {
            "user_id": result.user_id,
            "matches": [
                {
                    "id": str(match.id),
                    "similarity": match.similarity,
                    "distance_meters": match.distance_meters,
                    "match_quality": match.match_quality,
                    "priority_score": match.priority_score,
                    "location": match.location,
                    "metadata": match.metadata,
                    "final_score": getattr(match, "final_score", match.similarity),
                }
                for match in result.matches
            ],
            "metadata": result.metadata,
            "cc_oas_compliant": True,
            "uk_gdpr_compliant": True,
        }

    except Exception as e:
        logger.error(f"Match search failed for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Match search failed",
        )


# Add error response examples to OpenAPI
@router.api_route(
    "/error-examples",
    methods=["GET"],
    response_model=ErrorResponse,
    include_in_schema=False,
)
async def get_error_examples() -> Dict[str, Any]:
    """Endpoint to demonstrate error response formats (for documentation)."""
    return {
        "validation_error": {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Input validation failed",
                "details": {
                    "cause": "Invalid value for field 'objectives'",
                    "context": "OptimizationRequest validation",
                    "suggestion": "Check that objectives list is not empty",
                    "field": "objectives",
                    "value": [],
                },
            },
            "timestamp": "2026-01-12T10:30:00Z",
        },
        "constraint_error": {
            "error": {
                "code": "CONSTRAINT_VIOLATION",
                "message": "Hard constraint violated",
                "details": {
                    "cause": "Spatial constraint 'max_distance' exceeded",
                    "context": "Hard constraint enforcement",
                    "suggestion": "Reduce distance or adjust constraint parameters",
                    "constraint_type": "spatial",
                    "violation_value": 150.5,
                    "constraint_limit": 100.0,
                },
            },
            "timestamp": "2026-01-12T10:30:00Z",
        },
        "optimization_error": {
            "error": {
                "code": "OPTIMIZATION_ERROR",
                "message": "Optimization engine failed",
                "details": {
                    "cause": "XGBoost model failed to load",
                    "context": "ML scoring phase",
                    "suggestion": "Check model files and configuration",
                    "engine": "xgboost",
                    "engine_error": "Model file not found: models/xgboost/model.json",
                },
            },
            "timestamp": "2026-01-12T10:30:00Z",
        },
    }
