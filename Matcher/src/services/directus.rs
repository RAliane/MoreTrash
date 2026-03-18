//! Directus CMS client - Source of Truth
//!
//! Directus manages all content and serves as the canonical data store.
//! Configuration: Set DIRECTUS_URL and DIRECTUS_TOKEN in environment.
//!
//! To get your Directus token:
//! 1. Log into Directus admin panel
//! 2. Go to Settings > Access Tokens
//! 3. Create a new static token with appropriate permissions
//! 4. Copy the token to your .env file or Podman secret

use axum::{
    body::Bytes,
    extract::{Path, State},
    http::{Method, StatusCode},
    response::Json,
};
use reqwest::Client;
use serde::{de::DeserializeOwned, Deserialize, Serialize};
use std::sync::Arc;

/// Directus REST API client
#[derive(Clone)]
pub struct DirectusClient {
    base_url: String,
    token: String,
    client: Arc<Client>,
}

impl DirectusClient {
    /// Create new Directus client
    ///
    /// # Arguments
    /// * `base_url` - Directus API URL (e.g., "http://localhost:8055")
    /// * `token` - Static access token from Directus admin panel
    pub fn new(base_url: String, token: String) -> Self {
        Self {
            base_url: base_url.trim_end_matches('/').to_string(),
            token,
            client: Arc::new(Client::new()),
        }
    }

    /// Get items from a collection
    pub async fn get_items<T: DeserializeOwned>(
        &self,
        collection: &str,
    ) -> Result<Vec<T>, DirectusError> {
        let url = format!("{}/items/{}", self.base_url, collection);

        let response = self
            .client
            .get(&url)
            .header("Authorization", format!("Bearer {}", self.token))
            .send()
            .await
            .map_err(DirectusError::Network)?;

        if !response.status().is_success() {
            return Err(DirectusError::ApiError(response.status().as_u16()));
        }

        let data: DirectusResponse<Vec<T>> = response.json().await.map_err(DirectusError::Parse)?;
        Ok(data.data)
    }

    /// Get single item by ID
    pub async fn get_item<T: DeserializeOwned>(
        &self,
        collection: &str,
        id: &str,
    ) -> Result<T, DirectusError> {
        let url = format!("{}/items/{}/{}", self.base_url, collection, id);

        let response = self
            .client
            .get(&url)
            .header("Authorization", format!("Bearer {}", self.token))
            .send()
            .await
            .map_err(DirectusError::Network)?;

        if !response.status().is_success() {
            return Err(DirectusError::ApiError(response.status().as_u16()));
        }

        let data: DirectusResponse<T> = response.json().await.map_err(DirectusError::Parse)?;
        Ok(data.data)
    }

    /// Create new item
    pub async fn create_item<T: Serialize, R: DeserializeOwned>(
        &self,
        collection: &str,
        item: &T,
    ) -> Result<R, DirectusError> {
        let url = format!("{}/items/{}", self.base_url, collection);

        let response = self
            .client
            .post(&url)
            .header("Authorization", format!("Bearer {}", self.token))
            .json(item)
            .send()
            .await
            .map_err(DirectusError::Network)?;

        if !response.status().is_success() {
            return Err(DirectusError::ApiError(response.status().as_u16()));
        }

        let data: DirectusResponse<R> = response.json().await.map_err(DirectusError::Parse)?;
        Ok(data.data)
    }

    /// Update existing item
    pub async fn update_item<T: Serialize, R: DeserializeOwned>(
        &self,
        collection: &str,
        id: &str,
        item: &T,
    ) -> Result<R, DirectusError> {
        let url = format!("{}/items/{}/{}", self.base_url, collection, id);

        let response = self
            .client
            .patch(&url)
            .header("Authorization", format!("Bearer {}", self.token))
            .json(item)
            .send()
            .await
            .map_err(DirectusError::Network)?;

        if !response.status().is_success() {
            return Err(DirectusError::ApiError(response.status().as_u16()));
        }

        let data: DirectusResponse<R> = response.json().await.map_err(DirectusError::Parse)?;
        Ok(data.data)
    }

    /// Delete item
    pub async fn delete_item(&self, collection: &str, id: &str) -> Result<(), DirectusError> {
        let url = format!("{}/items/{}/{}", self.base_url, collection, id);

        let response = self
            .client
            .delete(&url)
            .header("Authorization", format!("Bearer {}", self.token))
            .send()
            .await
            .map_err(DirectusError::Network)?;

        if !response.status().is_success() {
            return Err(DirectusError::ApiError(response.status().as_u16()));
        }

        Ok(())
    }

    /// Authenticate user and get tokens
    pub async fn login(&self, email: &str, password: &str) -> Result<AuthResponse, DirectusError> {
        let url = format!("{}/auth/login", self.base_url);

        let response = self
            .client
            .post(&url)
            .json(&serde_json::json!({
                "email": email,
                "password": password
            }))
            .send()
            .await
            .map_err(DirectusError::Network)?;

        if !response.status().is_success() {
            return Err(DirectusError::AuthFailed);
        }

        let data: DirectusResponse<AuthResponse> =
            response.json().await.map_err(DirectusError::Parse)?;
        Ok(data.data)
    }

    /// Get current authenticated user
    pub async fn get_current_user(&self, token: &str) -> Result<DirectusUser, DirectusError> {
        let url = format!("{}/users/me", self.base_url);

        let response = self
            .client
            .get(&url)
            .header("Authorization", format!("Bearer {}", token))
            .send()
            .await
            .map_err(DirectusError::Network)?;

        if !response.status().is_success() {
            return Err(DirectusError::ApiError(response.status().as_u16()));
        }

        let data: DirectusResponse<DirectusUser> =
            response.json().await.map_err(DirectusError::Parse)?;
        Ok(data.data)
    }

    /// Create new user
    pub async fn create_user(
        &self,
        email: &str,
        password: &str,
        first_name: &str,
        last_name: &str,
    ) -> Result<DirectusUser, DirectusError> {
        let url = format!("{}/users", self.base_url);

        let response = self
            .client
            .post(&url)
            .header("Authorization", format!("Bearer {}", self.token))
            .json(&serde_json::json!({
                "email": email,
                "password": password,
                "first_name": first_name,
                "last_name": last_name,
                "role": "user",
                "status": "active"
            }))
            .send()
            .await
            .map_err(DirectusError::Network)?;

        if !response.status().is_success() {
            return Err(DirectusError::ApiError(response.status().as_u16()));
        }

        let data: DirectusResponse<DirectusUser> =
            response.json().await.map_err(DirectusError::Parse)?;
        Ok(data.data)
    }

    /// Refresh authentication token
    pub async fn refresh_token(&self, refresh_token: &str) -> Result<AuthResponse, DirectusError> {
        let url = format!("{}/auth/refresh", self.base_url);

        let response = self
            .client
            .post(&url)
            .json(&serde_json::json!({
                "refresh_token": refresh_token,
                "mode": "json"
            }))
            .send()
            .await
            .map_err(DirectusError::Network)?;

        if !response.status().is_success() {
            return Err(DirectusError::AuthFailed);
        }

        let data: DirectusResponse<AuthResponse> =
            response.json().await.map_err(DirectusError::Parse)?;
        Ok(data.data)
    }

    /// Request password reset email
    pub async fn request_password_reset(&self, email: &str) -> Result<(), DirectusError> {
        let url = format!("{}/auth/password/request", self.base_url);

        let response = self
            .client
            .post(&url)
            .json(&serde_json::json!({
                "email": email,
                "reset_url": format!("{}/auth/reset-password", 
                    std::env::var("APP_URL").unwrap_or_else(|_| "http://localhost:8000".to_string()))
            }))
            .send()
            .await
            .map_err(DirectusError::Network)?;

        if !response.status().is_success() {
            return Err(DirectusError::ApiError(response.status().as_u16()));
        }

        Ok(())
    }

    /// Reset password with token
    pub async fn reset_password(&self, token: &str, password: &str) -> Result<(), DirectusError> {
        let url = format!("{}/auth/password/reset", self.base_url);

        let response = self
            .client
            .post(&url)
            .json(&serde_json::json!({
                "token": token,
                "password": password
            }))
            .send()
            .await
            .map_err(DirectusError::Network)?;

        if !response.status().is_success() {
            return Err(DirectusError::ApiError(response.status().as_u16()));
        }

        Ok(())
    }
}

#[derive(Debug, Deserialize, Serialize)]
pub struct DirectusUser {
    pub id: String,
    pub email: String,
    pub first_name: Option<String>,
    pub last_name: Option<String>,
}

#[derive(Deserialize)]
struct DirectusResponse<T> {
    data: T,
}

#[derive(Debug, Deserialize)]
pub struct AuthResponse {
    pub access_token: String,
    pub refresh_token: String,
    pub expires: i64,
}

/// Directus errors
#[derive(Debug)]
pub enum DirectusError {
    Network(reqwest::Error),
    Parse(reqwest::Error),
    ApiError(u16),
    AuthFailed,
}

impl std::fmt::Display for DirectusError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            DirectusError::Network(e) => write!(f, "Network error: {}", e),
            DirectusError::Parse(e) => write!(f, "Parse error: {}", e),
            DirectusError::ApiError(code) => write!(f, "API error: {}", code),
            DirectusError::AuthFailed => write!(f, "Authentication failed"),
        }
    }
}

impl std::error::Error for DirectusError {}

// Axum route handlers

/// GET /api/cms/*path - Proxy GET requests to Directus
pub async fn cms_proxy(
    State(state): State<crate::services::AppState>,
    Path(path): Path<String>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    let items: Vec<serde_json::Value> =
        state.directus_client.get_items(&path).await.map_err(|e| {
            tracing::error!("Directus GET error: {}", e);
            StatusCode::BAD_GATEWAY
        })?;

    Ok(Json(serde_json::json!({ "data": items })))
}

/// POST /api/cms/*path - Proxy POST requests to Directus
pub async fn cms_proxy_post(
    State(state): State<crate::services::AppState>,
    Path(path): Path<String>,
    Json(payload): Json<serde_json::Value>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    let result: serde_json::Value = state
        .directus_client
        .create_item(&path, &payload)
        .await
        .map_err(|e| {
            tracing::error!("Directus POST error: {}", e);
            StatusCode::BAD_GATEWAY
        })?;

    Ok(Json(serde_json::json!({ "data": result })))
}
