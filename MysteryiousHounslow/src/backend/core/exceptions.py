"""
Custom exception hierarchy for the FastAPI XGBoost Optimizer.

This module defines a comprehensive exception hierarchy that provides
detailed error context and supports structured error responses.
"""

from typing import Any, Dict, Optional
from datetime import datetime
import uuid


class BaseOptimizerException(Exception):
    """
    Base exception for all optimizer exceptions.
    
    Provides common attributes and methods for all custom exceptions.
    """
    
    def __init__(
        self,
        message: str,
        code: str,
        cause: Optional[str] = None,
        context: Optional[str] = None,
        suggestion: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        status_code: int = 500
    ):
        """
        Initialize the base exception.
        
        Args:
            message: Human-readable error message
            code: Unique error code for identification
            cause: Root cause of the error
            context: Context where the error occurred
            suggestion: Suggested corrective action
            details: Additional error details
            status_code: HTTP status code for API responses
        """
        super().__init__(message)
        self.message = message
        self.code = code
        self.cause = cause
        self.context = context
        self.suggestion = suggestion
        self.details = details or {}
        self.status_code = status_code
        self.timestamp = datetime.utcnow()
        self.error_id = str(uuid.uuid4())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary format."""
        return {
            "error": {
                "id": self.error_id,
                "code": self.code,
                "message": self.message,
                "details": {
                    "cause": self.cause,
                    "context": self.context,
                    "suggestion": self.suggestion,
                    **self.details
                }
            },
            "timestamp": self.timestamp.isoformat()
        }
    
    def __str__(self) -> str:
        """String representation of the exception."""
        return f"[{self.code}] {self.message}"


class ValidationException(BaseOptimizerException):
    """Exception raised for input validation errors."""
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        cause: Optional[str] = None,
        context: Optional[str] = None,
        suggestion: Optional[str] = None
    ):
        """
        Initialize validation exception.
        
        Args:
            message: Validation error message
            field: Field that failed validation
            value: Invalid value provided
            cause: Root cause of validation failure
            context: Context where validation failed
            suggestion: Suggested correction
        """
        details = {}
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = value
            
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            cause=cause or f"Invalid value for field '{field}'",
            context=context or "Input validation",
            suggestion=suggestion or "Check the input format and requirements",
            details=details,
            status_code=400
        )


class ConstraintException(BaseOptimizerException):
    """Exception raised for constraint violations."""
    
    def __init__(
        self,
        message: str,
        constraint_type: Optional[str] = None,
        constraint_details: Optional[Dict[str, Any]] = None,
        cause: Optional[str] = None,
        context: Optional[str] = None,
        suggestion: Optional[str] = None
    ):
        """
        Initialize constraint exception.
        
        Args:
            message: Constraint violation message
            constraint_type: Type of constraint violated
            constraint_details: Details about the constraint
            cause: Root cause of constraint violation
            context: Context where constraint was violated
            suggestion: Suggested correction
        """
        details = {}
        if constraint_type:
            details["constraint_type"] = constraint_type
        if constraint_details:
            details["constraint_details"] = constraint_details
            
        super().__init__(
            message=message,
            code="CONSTRAINT_VIOLATION",
            cause=cause or f"Constraint '{constraint_type}' violated",
            context=context or "Constraint enforcement",
            suggestion=suggestion or "Adjust input to satisfy constraints",
            details=details,
            status_code=422
        )


class OptimizationException(BaseOptimizerException):
    """Exception raised for optimization engine errors."""
    
    def __init__(
        self,
        message: str,
        engine: Optional[str] = None,
        engine_error: Optional[str] = None,
        cause: Optional[str] = None,
        context: Optional[str] = None,
        suggestion: Optional[str] = None
    ):
        """
        Initialize optimization exception.
        
        Args:
            message: Optimization error message
            engine: Optimization engine that failed
            engine_error: Original engine error
            cause: Root cause of optimization failure
            context: Context where optimization failed
            suggestion: Suggested correction
        """
        details = {}
        if engine:
            details["engine"] = engine
        if engine_error:
            details["engine_error"] = engine_error
            
        super().__init__(
            message=message,
            code="OPTIMIZATION_ERROR",
            cause=cause or f"Optimization engine '{engine}' failed",
            context=context or "Optimization process",
            suggestion=suggestion or "Check optimization parameters and constraints",
            details=details,
            status_code=500
        )


class DatabaseException(BaseOptimizerException):
    """Exception raised for database operation errors."""
    
    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        database_error: Optional[str] = None,
        cause: Optional[str] = None,
        context: Optional[str] = None,
        suggestion: Optional[str] = None
    ):
        """
        Initialize database exception.
        
        Args:
            message: Database error message
            operation: Database operation that failed
            database_error: Original database error
            cause: Root cause of database error
            context: Context where database error occurred
            suggestion: Suggested correction
        """
        details = {}
        if operation:
            details["operation"] = operation
        if database_error:
            details["database_error"] = database_error
            
        super().__init__(
            message=message,
            code="DATABASE_ERROR",
            cause=cause or f"Database operation '{operation}' failed",
            context=context or "Database access",
            suggestion=suggestion or "Check database connection and query syntax",
            details=details,
            status_code=500
        )


class WorkflowException(BaseOptimizerException):
    """Exception raised for workflow execution errors."""
    
    def __init__(
        self,
        message: str,
        stage: Optional[str] = None,
        workflow_id: Optional[str] = None,
        cause: Optional[str] = None,
        context: Optional[str] = None,
        suggestion: Optional[str] = None
    ):
        """
        Initialize workflow exception.
        
        Args:
            message: Workflow error message
            stage: Workflow stage that failed
            workflow_id: Workflow execution ID
            cause: Root cause of workflow failure
            context: Context where workflow failed
            suggestion: Suggested correction
        """
        details = {}
        if stage:
            details["stage"] = stage
        if workflow_id:
            details["workflow_id"] = workflow_id
            
        super().__init__(
            message=message,
            code="WORKFLOW_ERROR",
            cause=cause or f"Workflow stage '{stage}' failed",
            context=context or "Workflow execution",
            suggestion=suggestion or "Check workflow configuration and inputs",
            details=details,
            status_code=500
        )


class AuthenticationException(BaseOptimizerException):
    """Exception raised for authentication failures."""
    
    def __init__(
        self,
        message: str = "Authentication failed",
        auth_method: Optional[str] = None,
        cause: Optional[str] = None,
        context: Optional[str] = None,
        suggestion: Optional[str] = None
    ):
        """
        Initialize authentication exception.
        
        Args:
            message: Authentication error message
            auth_method: Authentication method that failed
            cause: Root cause of authentication failure
            context: Context where authentication failed
            suggestion: Suggested correction
        """
        details = {}
        if auth_method:
            details["auth_method"] = auth_method
            
        super().__init__(
            message=message,
            code="AUTHENTICATION_ERROR",
            cause=cause or "Invalid or missing authentication credentials",
            context=context or "Authentication",
            suggestion=suggestion or "Provide valid authentication credentials",
            details=details,
            status_code=401
        )


class RateLimitException(BaseOptimizerException):
    """Exception raised for rate limit violations."""
    
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        limit: Optional[int] = None,
        window: Optional[str] = None,
        retry_after: Optional[int] = None,
        cause: Optional[str] = None,
        context: Optional[str] = None
    ):
        """
        Initialize rate limit exception.
        
        Args:
            message: Rate limit error message
            limit: Request limit
            window: Time window for the limit
            retry_after: Seconds until retry
            cause: Root cause of rate limit violation
            context: Context where rate limit was exceeded
        """
        details = {}
        if limit:
            details["limit"] = limit
        if window:
            details["window"] = window
        if retry_after:
            details["retry_after"] = retry_after
            
        super().__init__(
            message=message,
            code="RATE_LIMIT_EXCEEDED",
            cause=cause or "Too many requests",
            context=context or "Rate limiting",
            suggestion=f"Retry after {retry_after} seconds" if retry_after else "Reduce request frequency",
            details=details,
            status_code=429
        )


# Exception mapping for common errors
EXCEPTION_MAPPING = {
    "validation": ValidationException,
    "constraint": ConstraintException,
    "optimization": OptimizationException,
    "database": DatabaseException,
    "workflow": WorkflowException,
    "authentication": AuthenticationException,
    "rate_limit": RateLimitException,
}