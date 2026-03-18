//! Authentication service
//!
//! Handles user authentication via Directus.
//! Supports email/password and OAuth (Google, GitHub, Apple).

use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    response::{Json, Redirect},
};
use serde::{Deserialize, Serialize};

#[derive(Debug, Deserialize)]
pub struct LoginRequest {
    pub email: String,
    pub password: String,
}

#[derive(Debug, Deserialize)]
pub struct RegisterRequest {
    pub email: String,
    pub password: String,
    pub first_name: String,
    pub last_name: String,
}

#[derive(Debug, Deserialize)]
pub struct ForgotPasswordRequest {
    pub email: String,
}

#[derive(Debug, Deserialize)]
pub struct ResetPasswordRequest {
    pub token: String,
    pub password: String,
}

#[derive(Debug, Deserialize)]
pub struct RefreshRequest {
    pub refresh_token: String,
}

#[derive(Debug, Serialize)]
pub struct AuthResponse {
    pub access_token: String,
    pub refresh_token: String,
    pub expires_in: i64,
    pub user: UserInfo,
}

#[derive(Debug, Serialize)]
pub struct UserInfo {
    pub id: String,
    pub email: String,
    pub first_name: String,
    pub last_name: String,
}

#[derive(Debug, Serialize)]
pub struct MessageResponse {
    pub message: String,
}

/// POST /api/auth/login
pub async fn login(
    State(state): State<crate::services::AppState>,
    Json(payload): Json<LoginRequest>,
) -> Result<Json<AuthResponse>, StatusCode> {
    // Authenticate via Directus
    let auth = state
        .directus_client
        .login(&payload.email, &payload.password)
        .await
        .map_err(|e| {
            tracing::warn!("Login failed for {}: {}", payload.email, e);
            StatusCode::UNAUTHORIZED
        })?;

    // Fetch user info from Directus
    let user = state
        .directus_client
        .get_current_user(&auth.access_token)
        .await
        .unwrap_or_else(|_| crate::services::directus::DirectusUser {
            id: "unknown".to_string(),
            email: payload.email.clone(),
            first_name: None,
            last_name: None,
        });

    Ok(Json(AuthResponse {
        access_token: auth.access_token,
        refresh_token: auth.refresh_token,
        expires_in: auth.expires,
        user: UserInfo {
            id: user.id,
            email: user.email,
            first_name: user.first_name.unwrap_or_default(),
            last_name: user.last_name.unwrap_or_default(),
        },
    }))
}

/// POST /api/auth/logout
pub async fn logout() -> StatusCode {
    // Invalidate token on client side
    StatusCode::OK
}

/// POST /api/auth/register
pub async fn register(
    State(state): State<crate::services::AppState>,
    Json(payload): Json<RegisterRequest>,
) -> Result<Json<AuthResponse>, (StatusCode, Json<MessageResponse>)> {
    // Create user in Directus
    let user = state
        .directus_client
        .create_user(
            &payload.email,
            &payload.password,
            &payload.first_name,
            &payload.last_name,
        )
        .await
        .map_err(|e| {
            tracing::warn!("Registration failed for {}: {}", payload.email, e);
            (
                StatusCode::BAD_REQUEST,
                Json(MessageResponse {
                    message: "Registration failed. Email may already be in use.".to_string(),
                }),
            )
        })?;

    // Auto-login after registration
    let auth = state
        .directus_client
        .login(&payload.email, &payload.password)
        .await
        .map_err(|e| {
            tracing::error!("Auto-login failed after registration: {}", e);
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(MessageResponse {
                    message: "Account created but login failed. Please sign in.".to_string(),
                }),
            )
        })?;

    Ok(Json(AuthResponse {
        access_token: auth.access_token,
        refresh_token: auth.refresh_token,
        expires_in: auth.expires,
        user: UserInfo {
            id: user.id,
            email: user.email,
            first_name: user.first_name.unwrap_or_default(),
            last_name: user.last_name.unwrap_or_default(),
        },
    }))
}

/// POST /api/auth/refresh
pub async fn refresh_token(
    State(state): State<crate::services::AppState>,
    Json(payload): Json<RefreshRequest>,
) -> Result<Json<AuthResponse>, StatusCode> {
    let auth = state
        .directus_client
        .refresh_token(&payload.refresh_token)
        .await
        .map_err(|e| {
            tracing::warn!("Token refresh failed: {}", e);
            StatusCode::UNAUTHORIZED
        })?;

    Ok(Json(AuthResponse {
        access_token: auth.access_token,
        refresh_token: auth.refresh_token,
        expires_in: auth.expires,
        user: UserInfo {
            id: "".to_string(),
            email: "".to_string(),
            first_name: "".to_string(),
            last_name: "".to_string(),
        },
    }))
}

/// POST /api/auth/forgot-password
pub async fn forgot_password(
    State(state): State<crate::services::AppState>,
    Json(payload): Json<ForgotPasswordRequest>,
) -> Json<MessageResponse> {
    // Request password reset via Directus
    let _ = state
        .directus_client
        .request_password_reset(&payload.email)
        .await;

    // Always return success to prevent email enumeration
    Json(MessageResponse {
        message: "If an account exists, a reset link has been sent.".to_string(),
    })
}

/// POST /api/auth/reset-password
pub async fn reset_password(
    State(state): State<crate::services::AppState>,
    Json(payload): Json<ResetPasswordRequest>,
) -> Result<Json<MessageResponse>, (StatusCode, Json<MessageResponse>)> {
    state
        .directus_client
        .reset_password(&payload.token, &payload.password)
        .await
        .map_err(|e| {
            tracing::warn!("Password reset failed: {}", e);
            (
                StatusCode::BAD_REQUEST,
                Json(MessageResponse {
                    message: "Invalid or expired reset token.".to_string(),
                }),
            )
        })?;

    Ok(Json(MessageResponse {
        message: "Password has been reset successfully.".to_string(),
    }))
}

/// GET /api/auth/oauth/:provider
pub async fn oauth_redirect(
    State(state): State<crate::services::AppState>,
    Path(provider): Path<String>,
) -> Result<Redirect, StatusCode> {
    let config = &state.config;

    let (client_id, auth_url) = match provider.as_str() {
        "google" => {
            let client_id = config
                .google_client_id
                .as_ref()
                .ok_or(StatusCode::NOT_IMPLEMENTED)?;
            let url = format!(
                "https://accounts.google.com/o/oauth2/v2/auth?client_id={}&redirect_uri={}/api/auth/oauth/google/callback&response_type=code&scope=email%20profile",
                client_id,
                config.app_url.as_deref().unwrap_or("http://localhost:8000")
            );
            (client_id, url)
        }
        "github" => {
            let client_id = config
                .github_client_id
                .as_ref()
                .ok_or(StatusCode::NOT_IMPLEMENTED)?;
            let url = format!(
                "https://github.com/login/oauth/authorize?client_id={}&redirect_uri={}/api/auth/oauth/github/callback&scope=user:email",
                client_id,
                config.app_url.as_deref().unwrap_or("http://localhost:8000")
            );
            (client_id, url)
        }
        "apple" => {
            let client_id = config
                .apple_client_id
                .as_ref()
                .ok_or(StatusCode::NOT_IMPLEMENTED)?;
            let url = format!(
                "https://appleid.apple.com/auth/authorize?client_id={}&redirect_uri={}/api/auth/oauth/apple/callback&response_type=code&scope=email%20name&response_mode=form_post",
                client_id,
                config.app_url.as_deref().unwrap_or("http://localhost:8000")
            );
            (client_id, url)
        }
        _ => return Err(StatusCode::NOT_FOUND),
    };

    Ok(Redirect::temporary(&auth_url))
}

#[derive(Debug, Deserialize)]
pub struct OAuthCallback {
    pub code: String,
    pub state: Option<String>,
}

/// GET /api/auth/oauth/:provider/callback
pub async fn oauth_callback(
    State(state): State<crate::services::AppState>,
    Path(provider): Path<String>,
    Query(params): Query<OAuthCallback>,
) -> Result<Redirect, StatusCode> {
    // Exchange code for tokens with the provider
    // Then create/login user in Directus
    // This is a placeholder - full implementation depends on provider

    tracing::info!("OAuth callback for {} with code: {}", provider, params.code);

    // TODO: Implement full OAuth token exchange
    // For now, redirect to sign-in with error
    Ok(Redirect::temporary(
        "/auth/sign-in?error=oauth_not_implemented",
    ))
}
