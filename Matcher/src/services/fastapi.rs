//! FastAPI XGBoost Optimizer client
//!
//! Integrates with the external FastAPI service for:
//! - ML-based scoring and ranking
//! - Genetic algorithm optimization
//! - Constraint programming with OR-Tools
//!
//! See: https://github.com/ryanallan/fastapi_xgboost_optimizer

use axum::{
    extract::{Path, State},
    http::StatusCode,
    response::Json,
};
use reqwest::Client;
use serde::{Deserialize, Serialize};
use std::sync::Arc;

/// FastAPI client for optimization requests
#[derive(Clone)]
pub struct FastApiClient {
    base_url: String,
    client: Arc<Client>,
}

impl FastApiClient {
    pub fn new(base_url: String) -> Self {
        Self {
            base_url,
            client: Arc::new(Client::new()),
        }
    }

    /// Submit optimization request
    pub async fn optimize(
        &self,
        request: OptimizeRequest,
    ) -> Result<OptimizeResponse, FastApiError> {
        let url = format!("{}/api/v1/optimize", self.base_url);

        let response = self
            .client
            .post(&url)
            .json(&request)
            .send()
            .await
            .map_err(FastApiError::Network)?;

        if !response.status().is_success() {
            return Err(FastApiError::ApiError(response.status().as_u16()));
        }

        response.json().await.map_err(FastApiError::Parse)
    }

    /// Get optimization status
    pub async fn get_status(&self, request_id: &str) -> Result<StatusResponse, FastApiError> {
        let url = format!("{}/api/v1/optimize/{}/status", self.base_url, request_id);

        let response = self
            .client
            .get(&url)
            .send()
            .await
            .map_err(FastApiError::Network)?;

        response.json().await.map_err(FastApiError::Parse)
    }

    /// Get optimization results
    pub async fn get_results(&self, request_id: &str) -> Result<OptimizeResponse, FastApiError> {
        let url = format!("{}/api/v1/optimize/{}/results", self.base_url, request_id);

        let response = self
            .client
            .get(&url)
            .send()
            .await
            .map_err(FastApiError::Network)?;

        response.json().await.map_err(FastApiError::Parse)
    }

    /// Health check
    pub async fn health(&self) -> Result<bool, FastApiError> {
        let url = format!("{}/health", self.base_url);
        let response = self
            .client
            .get(&url)
            .send()
            .await
            .map_err(FastApiError::Network)?;
        Ok(response.status().is_success())
    }
}

// Request/Response types matching FastAPI schema
#[derive(Debug, Serialize, Deserialize)]
pub struct OptimizeRequest {
    pub name: String,
    pub description: Option<String>,
    pub variables: serde_json::Value,
    pub objectives: Vec<Objective>,
    pub constraints: Vec<Constraint>,
    pub parameters: OptimizeParameters,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct Objective {
    pub name: String,
    #[serde(rename = "type")]
    pub obj_type: String, // "minimize" or "maximize"
    pub function: String,
    pub weight: f64,
    pub variables: Vec<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct Constraint {
    pub name: String,
    #[serde(rename = "type")]
    pub constraint_type: String, // "hard" or "soft"
    pub weight: Option<f64>,
    pub priority: Option<i32>,
    pub spatial_constraint: Option<SpatialConstraint>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct SpatialConstraint {
    #[serde(rename = "type")]
    pub spatial_type: String,
    pub geometry: serde_json::Value,
    pub srid: i32,
    pub operation: String,
    pub buffer: Option<f64>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct OptimizeParameters {
    pub max_iterations: i32,
    pub time_limit: i32,
    pub convergence_threshold: f64,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct OptimizeResponse {
    pub request_id: String,
    pub status: String,
    pub solutions: Option<Vec<Solution>>,
    pub best_solution: Option<Solution>,
    pub execution_time: Option<f64>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct Solution {
    pub solution_id: String,
    pub variables: serde_json::Value,
    pub objectives: serde_json::Value,
    pub fitness_score: f64,
    pub rank: i32,
    pub is_feasible: bool,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct StatusResponse {
    pub request_id: String,
    pub status: String,
    pub progress: Option<f64>,
    pub stage: Option<String>,
}

/// FastAPI client errors
#[derive(Debug)]
pub enum FastApiError {
    Network(reqwest::Error),
    Parse(reqwest::Error),
    ApiError(u16),
}

impl std::fmt::Display for FastApiError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            FastApiError::Network(e) => write!(f, "Network error: {}", e),
            FastApiError::Parse(e) => write!(f, "Parse error: {}", e),
            FastApiError::ApiError(code) => write!(f, "API error: {}", code),
        }
    }
}

impl std::error::Error for FastApiError {}

// Axum route handlers

/// POST /api/optimize - Submit optimization request
pub async fn optimize_proxy(
    State(state): State<crate::services::AppState>,
    Json(payload): Json<OptimizeRequest>,
) -> Result<Json<OptimizeResponse>, StatusCode> {
    match state.fastapi_client.optimize(payload).await {
        Ok(response) => Ok(Json(response)),
        Err(e) => {
            tracing::error!("FastAPI optimize error: {}", e);
            Err(StatusCode::BAD_GATEWAY)
        }
    }
}

/// GET /api/optimize/:id/status - Get optimization status
pub async fn status_proxy(
    State(state): State<crate::services::AppState>,
    Path(request_id): Path<String>,
) -> Result<Json<StatusResponse>, StatusCode> {
    match state.fastapi_client.get_status(&request_id).await {
        Ok(response) => Ok(Json(response)),
        Err(e) => {
            tracing::error!("FastAPI status error: {}", e);
            Err(StatusCode::BAD_GATEWAY)
        }
    }
}
