"""
Monitoring and observability for the FastAPI XGBoost Optimizer.

This module provides metrics collection, health checks, and performance
monitoring for production deployment.
"""

import asyncio
import time
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from src.backend.core.config import settings
from src.backend.infrastructure.logging_config import get_logger


@dataclass
class HealthStatus:
    """Health status information."""
    status: str
    timestamp: float
    version: str
    services: Dict[str, str]
    details: Dict[str, Any]


@dataclass
class PerformanceMetrics:
    """Performance metrics."""
    timestamp: float
    uptime: float
    requests_total: int
    requests_per_minute: float
    average_response_time: float
    p95_response_time: float
    error_rate: float
    active_connections: int
    cpu_usage: Optional[float]
    memory_usage: Optional[float]


class HealthChecker:
    """Health check coordinator."""
    
    def __init__(self):
        """Initialize health checker."""
        self.logger = get_logger(__name__)
        self.checks: Dict[str, callable] = {}
        self.start_time = time.time()
    
    def register_check(self, name: str, check_func: callable) -> None:
        """
        Register a health check.
        
        Args:
            name: Check name
            check_func: Async function that returns health status
        """
        self.checks[name] = check_func
        self.logger.info(f"Health check registered: {name}")
    
    async def check_health(self) -> HealthStatus:
        """
        Run all health checks.
        
        Returns:
            HealthStatus: Overall health status
        """
        services = {}
        details = {}
        overall_status = "healthy"
        
        # Run all checks concurrently
        check_tasks = [
            self._run_check(name, check_func)
            for name, check_func in self.checks.items()
        ]
        
        results = await asyncio.gather(*check_tasks, return_exceptions=True)
        
        # Process results
        for name, result in zip(self.checks.keys(), results):
            if isinstance(result, Exception):
                services[name] = "unhealthy"
                details[name] = {"error": str(result)}
                overall_status = "unhealthy"
                self.logger.error(f"Health check failed: {name}", extra={"error": str(result)})
            else:
                services[name] = result.get("status", "healthy")
                details[name] = result.get("details", {})
        
        return HealthStatus(
            status=overall_status,
            timestamp=time.time(),
            version=settings.APP_VERSION,
            services=services,
            details=details,
        )
    
    async def _run_check(self, name: str, check_func: callable) -> Dict[str, Any]:
        """Run a single health check."""
        try:
            # Add timeout to prevent hanging
            return await asyncio.wait_for(check_func(), timeout=5.0)
        except asyncio.TimeoutError:
            return {"status": "timeout", "details": {"timeout": 5.0}}
        except Exception as exc:
            return {"status": "error", "details": {"error": str(exc)}}


class MetricsCollector:
    """Metrics collection and aggregation."""
    
    def __init__(self):
        """Initialize metrics collector."""
        self.logger = get_logger(__name__)
        self.metrics: Dict[str, Any] = {
            "requests_total": 0,
            "requests_by_status": {},
            "requests_by_endpoint": {},
            "response_times": [],
            "optimizations_total": 0,
            "optimizations_completed": 0,
            "optimizations_failed": 0,
            "optimizations_by_status": {},
            "constraint_violations": 0,
            "ml_predictions": 0,
            "database_queries": 0,
            "database_errors": 0,
            "errors_total": 0,
            "errors_by_type": {},
            "start_time": time.time(),
        }
        self.start_time = time.time()
    
    def record_request(
        self,
        method: str,
        endpoint: str,
        status_code: int,
        duration: float,
        request_id: Optional[str] = None,
    ) -> None:
        """
        Record a request metric.
        
        Args:
            method: HTTP method
            endpoint: Request endpoint
            status_code: HTTP status code
            duration: Request duration
            request_id: Request identifier
        """
        self.metrics["requests_total"] += 1
        
        # Status code tracking
        status_key = str(status_code)
        self.metrics["requests_by_status"][status_key] = (
            self.metrics["requests_by_status"].get(status_key, 0) + 1
        )
        
        # Endpoint tracking
        endpoint_key = f"{method} {endpoint}"
        self.metrics["requests_by_endpoint"][endpoint_key] = (
            self.metrics["requests_by_endpoint"].get(endpoint_key, 0) + 1
        )
        
        # Response time tracking
        self.metrics["response_times"].append(duration)
        
        # Keep only last 1000 response times
        if len(self.metrics["response_times"]) > 1000:
            self.metrics["response_times"] = self.metrics["response_times"][-1000:]
        
        self.logger.debug(
            "Request recorded",
            extra={
                "method": method,
                "endpoint": endpoint,
                "status_code": status_code,
                "duration": duration,
                "request_id": request_id,
            }
        )
    
    def record_optimization(
        self,
        status: str,
        execution_time: Optional[float] = None,
        num_solutions: int = 0,
        request_id: Optional[str] = None,
    ) -> None:
        """
        Record an optimization metric.
        
        Args:
            status: Optimization status
            execution_time: Execution time
            num_solutions: Number of solutions found
            request_id: Request identifier
        """
        self.metrics["optimizations_total"] += 1
        
        if status == "completed":
            self.metrics["optimizations_completed"] += 1
        elif status == "failed":
            self.metrics["optimizations_failed"] += 1
        
        self.metrics["optimizations_by_status"][status] = (
            self.metrics["optimizations_by_status"].get(status, 0) + 1
        )
        
        self.logger.debug(
            "Optimization recorded",
            extra={
                "status": status,
                "execution_time": execution_time,
                "num_solutions": num_solutions,
                "request_id": request_id,
            }
        )
    
    def record_error(self, error_type: str, error_message: str) -> None:
        """
        Record an error metric.
        
        Args:
            error_type: Type of error
            error_message: Error message
        """
        self.metrics["errors_total"] += 1
        self.metrics["errors_by_type"][error_type] = (
            self.metrics["errors_by_type"].get(error_type, 0) + 1
        )
        
        self.logger.error(
            "Error recorded",
            extra={
                "error_type": error_type,
                "error_message": error_message,
            }
        )
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        uptime = time.time() - self.start_time
        
        # Calculate response time statistics
        if not self.metrics["response_times"]:
            avg_response_time = 0
            p95_response_time = 0
            min_response_time = 0
            max_response_time = 0
        else:
            response_times = sorted(self.metrics["response_times"])
            avg_response_time = sum(response_times) / len(response_times)
            p95_response_time = response_times[int(len(response_times) * 0.95)]
            min_response_time = min(response_times)
            max_response_time = max(response_times)
        
        return {
            "uptime": uptime,
            "requests_total": self.metrics["requests_total"],
            "requests_per_minute": self.metrics["requests_total"] / max(1, uptime / 60),
            "average_response_time": avg_response_time,
            "p95_response_time": p95_response_time,
            "min_response_time": min_response_time,
            "max_response_time": max_response_time,
            "error_rate": self.metrics["errors_total"] / max(1, self.metrics["requests_total"]),
            "optimizations_total": self.metrics["optimizations_total"],
            "optimizations_completed": self.metrics["optimizations_completed"],
            "optimizations_failed": self.metrics["optimizations_failed"],
            "success_rate": self.metrics["optimizations_completed"] / max(1, self.metrics["optimizations_total"]),
            "constraint_violations": self.metrics["constraint_violations"],
            "ml_predictions": self.metrics["ml_predictions"],
            "database_queries": self.metrics["database_queries"],
            "database_errors": self.metrics["database_errors"],
        }
    
    def get_performance_metrics(self) -> PerformanceMetrics:
        """Get performance metrics as dataclass."""
        current_metrics = self.get_current_metrics()
        
        # Get system metrics if available
        cpu_usage, memory_usage = self._get_system_metrics()
        
        return PerformanceMetrics(
            timestamp=time.time(),
            uptime=current_metrics["uptime"],
            requests_total=current_metrics["requests_total"],
            requests_per_minute=current_metrics["requests_per_minute"],
            average_response_time=current_metrics["average_response_time"],
            p95_response_time=current_metrics["p95_response_time"],
            error_rate=current_metrics["error_rate"],
            active_connections=0,  # Would need connection tracking
            cpu_usage=cpu_usage,
            memory_usage=memory_usage,
        )
    
    def _get_system_metrics(self) -> Tuple[Optional[float], Optional[float]]:
        """Get system CPU and memory usage."""
        try:
            import psutil
            
            cpu_usage = psutil.cpu_percent(interval=0.1)
            memory_usage = psutil.virtual_memory().percent
            
            return cpu_usage, memory_usage
            
        except ImportError:
            # psutil not available
            return None, None
        except Exception:
            # Other errors
            return None, None


class AlertManager:
    """Alert management for critical conditions."""
    
    def __init__(self):
        """Initialize alert manager."""
        self.logger = get_logger(__name__)
        self.alerts: Dict[str, Dict[str, Any]] = {}
        self.thresholds = {
            "error_rate": 0.05,  # 5%
            "response_time": 5.0,  # 5 seconds
            "memory_usage": 0.9,  # 90%
            "cpu_usage": 0.9,  # 90%
        }
    
    def check_alerts(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Check for alert conditions.
        
        Args:
            metrics: Current metrics
            
        Returns:
            List[Dict[str, Any]]: Active alerts
        """
        alerts = []
        
        # Check error rate
        if metrics.get("error_rate", 0) > self.thresholds["error_rate"]:
            alerts.append({
                "type": "high_error_rate",
                "severity": "warning",
                "value": metrics["error_rate"],
                "threshold": self.thresholds["error_rate"],
                "message": f"Error rate is {metrics['error_rate']:.2%}",
            })
        
        # Check response time
        if metrics.get("average_response_time", 0) > self.thresholds["response_time"]:
            alerts.append({
                "type": "high_response_time",
                "severity": "warning",
                "value": metrics["average_response_time"],
                "threshold": self.thresholds["response_time"],
                "message": f"Average response time is {metrics['average_response_time']:.2f}s",
            })
        
        # Log alerts
        for alert in alerts:
            self.logger.warning(
                f"Alert: {alert['type']}",
                extra=alert,
            )
        
        return alerts


class MonitoringService:
    """Main monitoring service."""
    
    def __init__(self):
        """Initialize monitoring service."""
        self.logger = get_logger(__name__)
        self.health_checker = HealthChecker()
        self.metrics_collector = MetricsCollector()
        self.alert_manager = AlertManager()
        self.is_running = False
    
    async def start(self) -> None:
        """Start monitoring service."""
        self.is_running = True
        self.logger.info("Monitoring service started")
        
        # Start background tasks
        asyncio.create_task(self._metrics_collection_loop())
        asyncio.create_task(self._alert_checking_loop())
    
    async def stop(self) -> None:
        """Stop monitoring service."""
        self.is_running = False
        self.logger.info("Monitoring service stopped")
    
    async def _metrics_collection_loop(self) -> None:
        """Background loop for metrics collection."""
        while self.is_running:
            try:
                # Collect metrics every 60 seconds
                await asyncio.sleep(60)
                
                metrics = self.metrics_collector.get_current_metrics()
                
                self.logger.info(
                    "Metrics snapshot",
                    extra={"metrics": metrics},
                )
                
            except Exception as exc:
                self.logger.error(
                    "Metrics collection failed",
                    extra={"error": str(exc)},
                )
    
    async def _alert_checking_loop(self) -> None:
        """Background loop for alert checking."""
        while self.is_running:
            try:
                # Check alerts every 30 seconds
                await asyncio.sleep(30)
                
                metrics = self.metrics_collector.get_current_metrics()
                alerts = self.alert_manager.check_alerts(metrics)
                
                if alerts:
                    self.logger.warning(
                        f"{len(alerts)} active alerts",
                        extra={"alerts": alerts},
                    )
                
            except Exception as exc:
                self.logger.error(
                    "Alert checking failed",
                    extra={"error": str(exc)},
                )
    
    async def get_health_status(self) -> HealthStatus:
        """Get current health status."""
        return await self.health_checker.check_health()
    
    async def get_performance_metrics(self) -> PerformanceMetrics:
        """Get current performance metrics."""
        return self.metrics_collector.get_performance_metrics()
    
    def record_request(self, *args, **kwargs) -> None:
        """Record request metrics."""
        self.metrics_collector.record_request(*args, **kwargs)
    
    def record_optimization(self, *args, **kwargs) -> None:
        """Record optimization metrics."""
        self.metrics_collector.record_optimization(*args, **kwargs)
    
    def record_error(self, *args, **kwargs) -> None:
        """Record error metrics."""
        self.metrics_collector.record_error(*args, **kwargs)


# Global monitoring service instance
monitoring_service = MonitoringService()


def setup_monitoring() -> None:
    """Set up monitoring for the application."""
    if settings.METRICS_ENABLED:
        asyncio.create_task(monitoring_service.start())


# Export key components
__all__ = [
    "HealthStatus",
    "PerformanceMetrics",
    "HealthChecker",
    "MetricsCollector",
    "AlertManager",
    "MonitoringService",
    "monitoring_service",
    "setup_monitoring",
]