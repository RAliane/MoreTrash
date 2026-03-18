// Hasura GraphQL service - manages dynamic data queries and mutations
// Hasura provides real-time GraphQL API over Postgres database

use reqwest::Client;
use serde::{Deserialize, Serialize};
use std::sync::Arc;

#[derive(Clone)]
pub struct HasuraClient {
    graphql_endpoint: String,
    admin_secret: String,
    client: Arc<Client>,
}

impl HasuraClient {
    // Create new Hasura client with admin secret from Podman secrets
    pub fn new(graphql_endpoint: String, admin_secret: String) -> Self {
        Self {
            graphql_endpoint,
            admin_secret,
            client: Arc::new(Client::new()),
        }
    }

    // Execute GraphQL query
    pub async fn query<T: for<'de> Deserialize<'de>>(
        &self,
        query: &str,
        variables: Option<serde_json::Value>,
    ) -> Result<T, Box<dyn std::error::Error>> {
        let payload = GraphQLRequest {
            query: query.to_string(),
            variables,
        };

        let response = self.client
            .post(&self.graphql_endpoint)
            .header("x-hasura-admin-secret", &self.admin_secret)
            .json(&payload)
            .send()
            .await?;

        let result: GraphQLResponse<T> = response.json().await?;
        Ok(result.data)
    }

    // Execute GraphQL mutation
    pub async fn mutate<T: for<'de> Deserialize<'de>>(
        &self,
        mutation: &str,
        variables: Option<serde_json::Value>,
    ) -> Result<T, Box<dyn std::error::Error>> {
        self.query(mutation, variables).await
    }
}

#[derive(Serialize)]
struct GraphQLRequest {
    query: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    variables: Option<serde_json::Value>,
}

#[derive(Deserialize)]
struct GraphQLResponse<T> {
    data: T,
}

// GraphQL proxy handler for Axum
use axum::{
    extract::State,
    http::StatusCode,
    response::Json,
};

pub async fn graphql_proxy(
    State(state): State<crate::services::AppState>,
    Json(payload): Json<GraphQLRequest>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    // Proxy GraphQL request to Hasura
    match state.hasura_client.query::<serde_json::Value>(&payload.query, payload.variables).await {
        Ok(data) => Ok(Json(serde_json::json!({ "data": data }))),
        Err(_) => Err(StatusCode::INTERNAL_SERVER_ERROR),
    }
}
