//! Services module - backend integrations
//!
//! Architecture:
//! - Directus: Source of truth for content and user data
//! - Hasura: GraphQL API for real-time data queries
//! - FastAPI: ML/optimization service (external)
//! - Database: Direct Postgres access for performance-critical queries

pub mod auth;
pub mod database;
pub mod directus;
pub mod fastapi;
pub mod hasura;

use crate::config::AppConfig;
use sqlx::PgPool;

/// Shared application state passed to all route handlers
#[derive(Clone)]
pub struct AppState {
    pub config: AppConfig,
    pub db_pool: PgPool,
    pub directus_client: directus::DirectusClient,
    pub hasura_client: hasura::HasuraClient,
    pub fastapi_client: fastapi::FastApiClient,
}
