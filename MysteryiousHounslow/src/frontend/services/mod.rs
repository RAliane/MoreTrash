// Services module - manages backend integrations
// Includes database connection, Directus CMS client, Hasura GraphQL client, and auth services

pub mod auth;
pub mod database;
pub mod directus;
pub mod hasura;

use crate::config::AppConfig;
use sqlx::PgPool;

// Application state shared across all handlers
#[derive(Clone)]
pub struct AppState {
    pub config: AppConfig,
    pub db_pool: PgPool,
    pub directus_client: directus::DirectusClient,
    pub hasura_client: hasura::HasuraClient,
    pub jwt_service: auth::jwt::JwtService,
    pub directus_auth_client: auth::directus::DirectusAuthClient,
}
