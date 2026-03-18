// Authentication service - manages user login, logout, and session management
// Uses Directus for user storage and JWT for authentication

mod jwt;
mod directus;

use axum::{
    extract::State,
    http::StatusCode,
    response::Json,
};
use serde::{Deserialize, Serialize};
use crate::services::auth::directus::DirectusUser;
use crate::utils::validation::{LoginRequest, RegisterRequest, validate_request};
use crate::middleware::security::log_security_event;

#[derive(Deserialize)]
pub struct PasswordResetRequest {
    pub email: String,
}

#[derive(Deserialize)]
pub struct PasswordResetConfirm {
    pub token: String,
    pub password: String,
}

#[derive(Serialize)]
pub struct PasswordResetResponse {
    pub message: String,
}

// Login handler
pub async fn login(
    State(state): State<crate::services::AppState>,
    Json(payload): Json<LoginRequest>,
) -> Result<Json<LoginResponse>, StatusCode> {
    // Validate input
    if let Err(errors) = validate_request(&payload) {
        log_security_event("INVALID_LOGIN_REQUEST", &format!("Validation errors: {:?}", errors));
        return Err(StatusCode::BAD_REQUEST);
    }

    // Authenticate user with Directus
    let directus_user = match state.directus_auth_client.login(&payload.email, &payload.password).await {
        Ok(user) => {
            tracing::info!("User {} logged in successfully", user.email);
            user
        }
        Err(e) => {
            log_security_event("FAILED_LOGIN", &format!("Email: {}, Error: {:?}", payload.email, e));
            return Err(StatusCode::UNAUTHORIZED);
        }
    };

    // Generate JWT token
    let token = match state.jwt_service.create_token(&directus_user.id) {
        Ok(t) => t,
        Err(e) => {
            tracing::error!("Failed to generate JWT token: {:?}", e);
            return Err(StatusCode::INTERNAL_SERVER_ERROR);
        }
    };

    let user_data = UserData {
        id: directus_user.id,
        email: directus_user.email,
        name: format!(
            "{} {}",
            directus_user.first_name.unwrap_or_default(),
            directus_user.last_name.unwrap_or_default()
        ).trim().to_string(),
    };

    tracing::info!("Login successful for user: {}", user_data.email);
    Ok(Json(LoginResponse { token, user: user_data }))
}

// Register handler
pub async fn register(
    State(state): State<crate::services::AppState>,
    Json(payload): Json<RegisterRequest>,
) -> Result<Json<LoginResponse>, StatusCode> {
    // Validate input
    if let Err(errors) = validate_request(&payload) {
        log_security_event("INVALID_REGISTER_REQUEST", &format!("Validation errors: {:?}", errors));
        return Err(StatusCode::BAD_REQUEST);
    }

    // Register user with Directus
    let directus_user = match state.directus_auth_client.register(
        &payload.email,
        &payload.password,
        payload.first_name.as_deref(),
        payload.last_name.as_deref(),
    ).await {
        Ok(user) => {
            tracing::info!("User {} registered successfully", user.email);
            user
        }
        Err(e) => {
            log_security_event("FAILED_REGISTRATION", &format!("Email: {}, Error: {:?}", payload.email, e));
            return Err(StatusCode::BAD_REQUEST);
        }
    };

    // Generate JWT token
    let token = match state.jwt_service.create_token(&directus_user.id) {
        Ok(t) => t,
        Err(e) => {
            tracing::error!("Failed to generate JWT token: {:?}", e);
            return Err(StatusCode::INTERNAL_SERVER_ERROR);
        }
    };

    let user_data = UserData {
        id: directus_user.id,
        email: directus_user.email,
        name: format!(
            "{} {}",
            directus_user.first_name.unwrap_or_default(),
            directus_user.last_name.unwrap_or_default()
        ).trim().to_string(),
    };

    tracing::info!("Registration successful for user: {}", user_data.email);
    Ok(Json(LoginResponse { token, user: user_data }))
}

// Logout handler
pub async fn logout() -> Result<StatusCode, StatusCode> {
    // For stateless JWT, logout is handled client-side by removing the token
    // In a production system, you might want to implement token blacklisting
    tracing::info!("User logged out");
    Ok(StatusCode::OK)
}

// Password reset request handler
pub async fn request_password_reset(
    State(state): State<crate::services::AppState>,
    Json(payload): Json<PasswordResetRequest>,
) -> Result<Json<PasswordResetResponse>, StatusCode> {
    // Validate email format (basic check)
    if payload.email.is_empty() || !payload.email.contains('@') {
        log_security_event("INVALID_RESET_REQUEST", &format!("Invalid email: {}", payload.email));
        return Err(StatusCode::BAD_REQUEST);
    }

    // Request password reset from Directus
    match state.directus_auth_client.request_password_reset(&payload.email).await {
        Ok(()) => {
            tracing::info!("Password reset requested for: {}", payload.email);
            log_security_event("PASSWORD_RESET_REQUESTED", &payload.email);
            Ok(Json(PasswordResetResponse {
                message: "Password reset email sent".to_string(),
            }))
        }
        Err(e) => {
            tracing::error!("Password reset request failed for {}: {:?}", payload.email, e);
            log_security_event("FAILED_RESET_REQUEST", &format!("Email: {}, Error: {:?}", payload.email, e));
            // Don't reveal if email exists or not for security
            Ok(Json(PasswordResetResponse {
                message: "If the email exists, a reset link has been sent".to_string(),
            }))
        }
    }
}

// Password reset confirmation handler
pub async fn reset_password(
    State(state): State<crate::services::AppState>,
    Json(payload): Json<PasswordResetConfirm>,
) -> Result<Json<PasswordResetResponse>, StatusCode> {
    // Validate password strength (basic check)
    if payload.password.len() < 8 {
        log_security_event("INVALID_RESET_PASSWORD", "Password too short");
        return Err(StatusCode::BAD_REQUEST);
    }

    // Reset password with Directus
    match state.directus_auth_client.reset_password(&payload.token, &payload.password).await {
        Ok(()) => {
            tracing::info!("Password reset successful with token");
            log_security_event("PASSWORD_RESET_SUCCESS", "Token used successfully");
            Ok(Json(PasswordResetResponse {
                message: "Password reset successfully".to_string(),
            }))
        }
        Err(e) => {
            tracing::error!("Password reset failed: {:?}", e);
            log_security_event("FAILED_RESET_CONFIRM", &format!("Error: {:?}", e));
            Err(StatusCode::BAD_REQUEST)
        }
    }
}
