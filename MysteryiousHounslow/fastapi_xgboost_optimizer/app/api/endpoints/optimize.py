from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import List, Optional
import uuid
from datetime import datetime

from app.api.dependencies import get_current_user, validate_api_key
from app.core.schemas import (
    OptimizationRequest,
    OptimizationResponse,
    OptimizationStatus,
    BatchOptimizationRequest,
    BatchOptimizationResponse,
)
from app.orchestration.workflow import OptimizationWorkflow
from app.infrastructure.cache import RedisCache
from app.infrastructure.metrics import metrics

router = APIRouter()


@router.post(
    "/",
    response_model=OptimizationResponse,
    summary="Submit Optimization Request",
    description="Submit a single optimization request for processing",
)
async def optimize(
    request: OptimizationRequest,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(validate_api_key),
    current_user: Optional[dict] = Depends(get_current_user),
) -> OptimizationResponse:
    """
    Submit an optimization request for processing.

    The request will be processed asynchronously and the result can be retrieved
    using the returned request_id.
    """
    request_id = str(uuid.uuid4())

    # Initialize workflow
    workflow = OptimizationWorkflow(request_id=request_id)

    # Start background processing
    background_tasks.add_task(workflow.process_request, request)

    # Return initial response
    return OptimizationResponse(
        request_id=request_id,
        status="processing",
        created_at=datetime.utcnow(),
        message="Optimization request submitted successfully",
    )


@router.post(
    "/batch",
    response_model=BatchOptimizationResponse,
    summary="Submit Batch Optimization Requests",
    description="Submit multiple optimization requests for batch processing",
)
async def optimize_batch(
    requests: BatchOptimizationRequest,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(validate_api_key),
    current_user: Optional[dict] = Depends(get_current_user),
) -> BatchOptimizationResponse:
    """
    Submit multiple optimization requests for batch processing.
    """
    batch_id = str(uuid.uuid4())
    request_ids = []

    for req in requests.requests:
        request_id = str(uuid.uuid4())
        request_ids.append(request_id)

        # Initialize workflow for each request
        workflow = OptimizationWorkflow(request_id=request_id)
        background_tasks.add_task(workflow.process_request, req)

    return BatchOptimizationResponse(
        batch_id=batch_id,
        request_ids=request_ids,
        status="processing",
        created_at=datetime.utcnow(),
        total_requests=len(requests.requests),
    )


@router.get(
    "/{request_id}/status",
    response_model=OptimizationStatus,
    summary="Get Optimization Status",
    description="Get the current status of an optimization request",
)
async def get_optimization_status(
    request_id: str,
    api_key: str = Depends(validate_api_key),
    current_user: Optional[dict] = Depends(get_current_user),
) -> OptimizationStatus:
    """Get the status of an optimization request."""
    cache = RedisCache()

    # Try to get status from cache
    status_data = await cache.get(f"optimization:{request_id}:status")

    if not status_data:
        raise HTTPException(
            status_code=404, detail=f"Optimization request {request_id} not found"
        )

    return OptimizationStatus(**status_data)


@router.get(
    "/{request_id}/results",
    summary="Get Optimization Results",
    description="Get the results of a completed optimization request",
)
async def get_optimization_results(
    request_id: str,
    api_key: str = Depends(validate_api_key),
    current_user: Optional[dict] = Depends(get_current_user),
):
    """Get the results of an optimization request."""
    cache = RedisCache()

    # Get results from cache
    results_data = await cache.get(f"optimization:{request_id}:results")

    if not results_data:
        raise HTTPException(
            status_code=404,
            detail=f"Results for optimization request {request_id} not found",
        )

    return results_data


@router.delete(
    "/{request_id}",
    summary="Cancel Optimization Request",
    description="Cancel a running optimization request",
)
async def cancel_optimization(
    request_id: str,
    api_key: str = Depends(validate_api_key),
    current_user: Optional[dict] = Depends(get_current_user),
):
    """Cancel an optimization request."""
    cache = RedisCache()

    # Check if request exists
    status_data = await cache.get(f"optimization:{request_id}:status")
    if not status_data:
        raise HTTPException(
            status_code=404, detail=f"Optimization request {request_id} not found"
        )

    # Mark as cancelled
    await cache.set(
        f"optimization:{request_id}:status",
        {
            "request_id": request_id,
            "status": "cancelled",
            "updated_at": datetime.utcnow().isoformat(),
        },
    )

    return {"message": f"Optimization request {request_id} cancelled"}


@router.get(
    "/metrics",
    summary="Get API Metrics",
    description="Get performance metrics for the optimization API",
)
async def get_metrics():
    """Get API performance metrics."""
    return {
        "requests_total": metrics.requests_total._value.get(),
        "requests_duration": metrics.requests_duration._value.get(),
        "optimization_success_rate": metrics.optimization_success_rate._value.get(),
        "active_optimizations": metrics.active_optimizations._value.get(),
    }
