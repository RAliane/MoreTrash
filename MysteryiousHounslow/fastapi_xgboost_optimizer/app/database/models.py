from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass


@dataclass
class OptimizationRequest:
    """Database model for optimization requests."""

    id: Optional[str] = None
    name: str = ""
    description: Optional[str] = None
    variables: Dict[str, Any] = None
    objectives: List[Dict[str, Any]] = None
    constraints: List[Dict[str, Any]] = None
    parameters: Dict[str, Any] = None
    status: str = "pending"
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    execution_time: Optional[float] = None


@dataclass
class OptimizationResult:
    """Database model for optimization results."""

    id: Optional[str] = None
    request_id: str = ""
    solution_data: Dict[str, Any] = None
    fitness_score: float = 0.0
    rank: int = 0
    is_feasible: bool = True
    metadata: Dict[str, Any] = None
    created_at: Optional[datetime] = None


@dataclass
class SpatialFeature:
    """Database model for spatial features."""

    id: Optional[int] = None
    geometry: Dict[str, Any] = None
    properties: Dict[str, Any] = None
    feature_type: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class MLModel:
    """Database model for ML models."""

    id: Optional[str] = None
    name: str = ""
    version: str = ""
    model_type: str = ""
    parameters: Dict[str, Any] = None
    metrics: Dict[str, Any] = None
    model_data: bytes = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class PerformanceMetric:
    """Database model for performance metrics."""

    id: Optional[str] = None
    request_id: Optional[str] = None
    metric_name: str = ""
    metric_value: float = 0.0
    timestamp: datetime = None
    metadata: Dict[str, Any] = None


class DatabaseMigrations:
    """Database migration definitions."""

    @staticmethod
    def get_initial_migrations() -> List[str]:
        """Get initial database schema migrations."""
        return [
            """
            -- Create PostGIS extension
            CREATE EXTENSION IF NOT EXISTS postgis;

            -- Create optimization_requests table
            CREATE TABLE optimization_requests (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name VARCHAR(255) NOT NULL,
                description TEXT,
                variables JSONB,
                objectives JSONB,
                constraints JSONB,
                parameters JSONB,
                status VARCHAR(50) DEFAULT 'pending',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                completed_at TIMESTAMP WITH TIME ZONE,
                execution_time NUMERIC
            );

            -- Create optimization_results table
            CREATE TABLE optimization_results (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                request_id UUID REFERENCES optimization_requests(id) ON DELETE CASCADE,
                solution_data JSONB,
                fitness_score NUMERIC,
                rank INTEGER,
                is_feasible BOOLEAN DEFAULT TRUE,
                metadata JSONB,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );

            -- Create spatial_features table
            CREATE TABLE spatial_features (
                id SERIAL PRIMARY KEY,
                geometry GEOMETRY(GEOMETRY, 3857),
                properties JSONB,
                feature_type VARCHAR(100),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );

            -- Create ml_models table
            CREATE TABLE ml_models (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name VARCHAR(255) NOT NULL,
                version VARCHAR(50) NOT NULL,
                model_type VARCHAR(100) NOT NULL,
                parameters JSONB,
                metrics JSONB,
                model_data BYTEA,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );

            -- Create performance_metrics table
            CREATE TABLE performance_metrics (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                request_id UUID REFERENCES optimization_requests(id) ON DELETE SET NULL,
                metric_name VARCHAR(255) NOT NULL,
                metric_value NUMERIC NOT NULL,
                timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                metadata JSONB
            );

            -- Create indexes
            CREATE INDEX idx_optimization_requests_status ON optimization_requests(status);
            CREATE INDEX idx_optimization_requests_created_at ON optimization_requests(created_at);
            CREATE INDEX idx_optimization_results_request_id ON optimization_results(request_id);
            CREATE INDEX idx_spatial_features_geometry ON spatial_features USING GIST(geometry);
            CREATE INDEX idx_spatial_features_type ON spatial_features(feature_type);
            CREATE INDEX idx_performance_metrics_name ON performance_metrics(metric_name);
            CREATE INDEX idx_performance_metrics_timestamp ON performance_metrics(timestamp);
            """,
            """
            -- Create optimization analytics view
            CREATE VIEW optimization_analytics AS
            SELECT
                DATE_TRUNC('day', created_at) as date,
                status,
                COUNT(*) as request_count,
                AVG(execution_time) as avg_execution_time,
                MIN(execution_time) as min_execution_time,
                MAX(execution_time) as max_execution_time
            FROM optimization_requests
            WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
            GROUP BY DATE_TRUNC('day', created_at), status
            ORDER BY date DESC, status;

            -- Create spatial analytics view
            CREATE VIEW spatial_analytics AS
            SELECT
                feature_type,
                COUNT(*) as feature_count,
                ST_AsGeoJSON(ST_Envelope(ST_Collect(geometry))) as bounds,
                ST_AsGeoJSON(ST_Centroid(ST_Collect(geometry))) as centroid
            FROM spatial_features
            GROUP BY feature_type;
            """,
        ]
