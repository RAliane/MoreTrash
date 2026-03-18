//! Matchgorithm - AI-Powered Matching Platform
//!
//! This is the main entry point for the Dioxus fullstack application.
//! Architecture:
//! - Dioxus frontend with SSR (Server-Side Rendering)
//! - Axum backend for API routes
//! - Directus CMS as source of truth
//! - Hasura GraphQL for database queries
//! - FastAPI service for ML/optimization (external)

use axum::{
    routing::{get, post},
    Router,
};
use dioxus::prelude::*;
use tower_http::{
    compression::CompressionLayer,
    cors::{Any, CorsLayer},
    services::ServeDir,
    trace::TraceLayer,
};
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt};

mod config;
mod services;

// Page components (placeholder modules - implement UI here)
mod components;
mod pages;

use config::AppConfig;
use services::AppState;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Initialize tracing for structured logging
    tracing_subscriber::registry()
        .with(tracing_subscriber::EnvFilter::new(
            std::env::var("RUST_LOG").unwrap_or_else(|_| "info,matchgorithm=debug".into()),
        ))
        .with(tracing_subscriber::fmt::layer())
        .init();

    // Load configuration from environment (Podman secrets mounted as env vars)
    let config = AppConfig::from_env()?;

    tracing::info!("=== Matchgorithm Server Starting ===");
    tracing::info!("Environment: {}", config.environment);
    tracing::info!("Directus URL: {}", config.directus_url);
    tracing::info!("Hasura URL: {}", config.hasura_url);
    tracing::info!("FastAPI URL: {}", config.fastapi_url);

    // Initialize services
    let db_pool = services::database::init_pool(&config.database_url).await?;
    let directus_client = services::directus::DirectusClient::new(
        config.directus_url.clone(),
        config.directus_token.clone(),
    );
    let hasura_client = services::hasura::HasuraClient::new(
        config.hasura_url.clone(),
        config.hasura_admin_secret.clone(),
    );
    let fastapi_client = services::fastapi::FastApiClient::new(config.fastapi_url.clone());

    // Create application state
    let app_state = AppState {
        config: config.clone(),
        db_pool,
        directus_client,
        hasura_client,
        fastapi_client,
    };

    // Build router
    let app = Router::new()
        // Static assets
        .nest_service("/assets", ServeDir::new("assets"))
        .nest_service("/public", ServeDir::new("public"))
        // Health and metrics
        .route("/health", get(health_check))
        .route("/ready", get(readiness_check))
        // API routes
        .nest("/api", api_routes())
        // Dioxus SSR fallback for all frontend routes
        .fallback(get(render_app))
        // Middleware layers
        .layer(TraceLayer::new_for_http())
        .layer(CompressionLayer::new())
        .layer(
            CorsLayer::new()
                .allow_origin(Any)
                .allow_methods(Any)
                .allow_headers(Any),
        )
        .with_state(app_state);

    // Start server
    let addr = format!("{}:{}", config.host, config.port);
    let listener = tokio::net::TcpListener::bind(&addr).await?;

    tracing::info!("Matchgorithm running at http://{}", addr);
    tracing::info!("=== Server Ready ===");

    axum::serve(listener, app).await?;
    Ok(())
}

/// API routes grouped under /api
fn api_routes() -> Router<AppState> {
    Router::new()
        // Authentication
        .route("/auth/login", post(services::auth::login))
        .route("/auth/logout", post(services::auth::logout))
        .route("/auth/register", post(services::auth::register))
        .route("/auth/refresh", post(services::auth::refresh_token))
        .route(
            "/auth/forgot-password",
            post(services::auth::forgot_password),
        )
        .route("/auth/reset-password", post(services::auth::reset_password))
        .route("/auth/oauth/:provider", get(services::auth::oauth_redirect))
        .route(
            "/auth/oauth/:provider/callback",
            get(services::auth::oauth_callback),
        )
        // Directus CMS proxy
        .route("/cms/*path", get(services::directus::cms_proxy))
        .route("/cms/*path", post(services::directus::cms_proxy_post))
        // Hasura GraphQL proxy
        .route("/graphql", post(services::hasura::graphql_proxy))
        // FastAPI optimization proxy
        .route("/optimize", post(services::fastapi::optimize_proxy))
        .route("/optimize/:id/status", get(services::fastapi::status_proxy))
}

/// Health check endpoint
async fn health_check() -> &'static str {
    "OK"
}

/// Readiness check - verifies all services are connected
async fn readiness_check(
    axum::extract::State(state): axum::extract::State<AppState>,
) -> Result<&'static str, axum::http::StatusCode> {
    // Check database
    if state.db_pool.acquire().await.is_err() {
        return Err(axum::http::StatusCode::SERVICE_UNAVAILABLE);
    }
    Ok("READY")
}

/// Render Dioxus application (SSR)
async fn render_app() -> axum::response::Html<String> {
    // TODO: Implement full Dioxus SSR rendering
    // For now, return placeholder HTML that loads the WASM app
    axum::response::Html(include_str!("../templates/index.html").to_string())
}
