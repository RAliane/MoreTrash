// Database service - manages Postgres connection pool
// Connects to Postgres 13 using connection string from Podman secrets

use sqlx::{postgres::PgPoolOptions, PgPool};

// Initialize Postgres connection pool
// The database URL is injected via Podman secrets
pub async fn init_pool(database_url: &str) -> Result<PgPool, sqlx::Error> {
    tracing::info!("Connecting to Postgres database...");

    let pool = PgPoolOptions::new()
        .max_connections(10)
        .connect(database_url)
        .await?;

    tracing::info!("Successfully connected to Postgres database");

    Ok(pool)
}
