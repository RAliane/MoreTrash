//! Configuration management for Matchgorithm
//!
//! Loads environment variables from Podman secrets or .env file.
//! All required variables are documented below.

use std::env;

/// Application configuration loaded from environment
#[derive(Clone, Debug)]
pub struct AppConfig {
    // Server
    pub host: String,
    pub port: u16,
    pub environment: String,

    // Database (PostgreSQL)
    pub database_url: String,

    // Directus CMS (Source of Truth)
    pub directus_url: String,
    pub directus_token: String,

    // Hasura GraphQL
    pub hasura_url: String,
    pub hasura_admin_secret: String,

    // FastAPI XGBoost Optimizer (External Service)
    pub fastapi_url: String,

    // OAuth Providers (Optional)
    pub google_client_id: Option<String>,
    pub google_client_secret: Option<String>,
    pub github_client_id: Option<String>,
    pub github_client_secret: Option<String>,
    pub apple_client_id: Option<String>,
    pub apple_team_id: Option<String>,
    pub apple_key_id: Option<String>,

    // AI Providers (Optional)
    pub groq_api_key: Option<String>,
    pub openrouter_api_key: Option<String>,

    // JWT Secret for auth tokens
    pub jwt_secret: String,

    // App URL for OAuth callbacks
    pub app_url: Option<String>,
}

impl AppConfig {
    /// Load configuration from environment variables.
    /// In production, these are injected via Podman secrets.
    /// In development, use a .env file.
    pub fn from_env() -> Result<Self, ConfigError> {
        // Load .env file if present (development only)
        dotenvy::dotenv().ok();

        Ok(Self {
            // Server configuration
            host: env::var("HOST").unwrap_or_else(|_| "0.0.0.0".to_string()),
            port: env::var("PORT")
                .unwrap_or_else(|_| "8000".to_string())
                .parse()
                .map_err(|_| ConfigError::InvalidPort)?,
            environment: env::var("ENVIRONMENT").unwrap_or_else(|_| "development".to_string()),

            // Required: Database
            database_url: env::var("DATABASE_URL")
                .map_err(|_| ConfigError::Missing("DATABASE_URL"))?,

            // Required: Directus CMS
            directus_url: env::var("DIRECTUS_URL")
                .map_err(|_| ConfigError::Missing("DIRECTUS_URL"))?,
            directus_token: env::var("DIRECTUS_TOKEN")
                .map_err(|_| ConfigError::Missing("DIRECTUS_TOKEN"))?,

            // Required: Hasura GraphQL
            hasura_url: env::var("HASURA_GRAPHQL_ENDPOINT")
                .map_err(|_| ConfigError::Missing("HASURA_GRAPHQL_ENDPOINT"))?,
            hasura_admin_secret: env::var("HASURA_ADMIN_SECRET")
                .map_err(|_| ConfigError::Missing("HASURA_ADMIN_SECRET"))?,

            // Required: FastAPI Optimizer
            fastapi_url: env::var("FASTAPI_URL")
                .unwrap_or_else(|_| "http://localhost:8001".to_string()),

            // Optional: OAuth
            google_client_id: env::var("GOOGLE_CLIENT_ID").ok(),
            google_client_secret: env::var("GOOGLE_CLIENT_SECRET").ok(),
            github_client_id: env::var("GITHUB_CLIENT_ID").ok(),
            github_client_secret: env::var("GITHUB_CLIENT_SECRET").ok(),
            apple_client_id: env::var("APPLE_CLIENT_ID").ok(),
            apple_team_id: env::var("APPLE_TEAM_ID").ok(),
            apple_key_id: env::var("APPLE_KEY_ID").ok(),

            // Optional: AI
            groq_api_key: env::var("GROQ_API_KEY").ok(),
            openrouter_api_key: env::var("OPENROUTER_API_KEY").ok(),

            // JWT Secret (generate if not provided)
            jwt_secret: env::var("JWT_SECRET")
                .unwrap_or_else(|_| "CHANGE_ME_IN_PRODUCTION_32_CHARS".to_string()),

            // App URL for OAuth callbacks
            app_url: env::var("APP_URL").ok(),
        })
    }
}

/// Configuration errors
#[derive(Debug)]
pub enum ConfigError {
    Missing(&'static str),
    InvalidPort,
}

impl std::fmt::Display for ConfigError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            ConfigError::Missing(var) => {
                write!(f, "Missing required environment variable: {}", var)
            }
            ConfigError::InvalidPort => write!(f, "Invalid PORT value"),
        }
    }
}

impl std::error::Error for ConfigError {}
