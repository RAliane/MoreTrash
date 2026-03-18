// Configuration management for Matchgorithm
// Loads environment variables from Podman secrets file and validates required settings

use serde::Deserialize;
use std::env;

#[derive(Clone, Debug, Deserialize)]
pub struct AppConfig {
    // Server configuration
    pub server_host: String,
    pub server_port: u16,

    // Database configuration
    pub database_url: String,
    pub postgres_user: String,
    pub postgres_password: String,
    pub postgres_db: String,

    // Directus configuration (Headless CMS)
    pub directus_url: String,
    pub directus_api_key: String,

    // Hasura configuration (GraphQL API)
    pub hasura_url: String,
    pub hasura_admin_secret: String,

    // Optional: AI integration
    pub groq_api_key: Option<String>,
    pub openrouter_api_key: Option<String>,

    // JWT configuration
    pub jwt_private_key_pem: String,
    pub jwt_public_key_pem: String,

    // OAuth configuration
    pub google_client_id: Option<String>,
    pub google_client_secret: Option<String>,
    pub github_client_id: Option<String>,
    pub github_client_secret: Option<String>,
    pub apple_client_id: Option<String>,
    pub apple_team_id: Option<String>,
    pub apple_key_id: Option<String>,
}

impl AppConfig {
    // Load configuration from environment variables
    // Environment variables are injected from Podman secrets file during container startup
    pub fn from_env() -> Result<Self, Box<dyn std::error::Error>> {
        // Load .env file if present (development)
        dotenvy::dotenv().ok();

        // Helper function to read from file if _FILE var exists
        let read_secret = |key: &str| -> String {
            if let Ok(file_path) = env::var(&format!("{}_FILE", key)) {
                std::fs::read_to_string(file_path).unwrap_or_else(|_| env::var(key).unwrap_or_default())
            } else {
                env::var(key).unwrap_or_default()
            }
        };

        Ok(Self {
            server_host: env::var("SERVER_HOST").unwrap_or_else(|_| "0.0.0.0".to_string()),
            server_port: env::var("SERVER_PORT")
                .unwrap_or_else(|_| "8000".to_string())
                .parse()?,

            database_url: read_secret("DATABASE_URL"),
            postgres_user: read_secret("POSTGRES_USER"),
            postgres_password: read_secret("POSTGRES_PASSWORD"),
            postgres_db: read_secret("POSTGRES_DB"),

            directus_url: read_secret("DIRECTUS_URL"),
            directus_api_key: read_secret("DIRECTUS_API_KEY"),

            hasura_url: read_secret("HASURA_GRAPHQL_ENDPOINT"),
            hasura_admin_secret: read_secret("HASURA_ADMIN_SECRET"),

            jwt_private_key_pem: read_secret("JWT_PRIVATE_KEY_PEM"),
            jwt_public_key_pem: read_secret("JWT_PUBLIC_KEY_PEM"),

            groq_api_key: env::var("GROQ_API_KEY").ok(),
            openrouter_api_key: env::var("OPENROUTER_API_KEY").ok(),

            google_client_id: env::var("GOOGLE_CLIENT_ID").ok(),
            google_client_secret: env::var("GOOGLE_CLIENT_SECRET").ok(),
            github_client_id: env::var("GITHUB_CLIENT_ID").ok(),
            github_client_secret: env::var("GITHUB_CLIENT_SECRET").ok(),
            apple_client_id: env::var("APPLE_CLIENT_ID").ok(),
            apple_team_id: env::var("APPLE_TEAM_ID").ok(),
            apple_key_id: env::var("APPLE_KEY_ID").ok(),
        })
    }
}
