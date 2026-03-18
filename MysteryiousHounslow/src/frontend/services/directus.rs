// Directus CMS service - manages content and data via REST API
// Directus is the source of truth for all content, user data, and application state

use reqwest::Client;
use serde::{Deserialize, Serialize};
use std::sync::Arc;

#[derive(Clone)]
pub struct DirectusClient {
    base_url: String,
    api_key: String,
    client: Arc<Client>,
}

impl DirectusClient {
    // Create new Directus client with API key from Podman secrets
    pub fn new(base_url: String, api_key: String) -> Self {
        Self {
            base_url,
            api_key,
            client: Arc::new(Client::new()),
        }
    }

    // Get items from Directus collection
    pub async fn get_items<T: for<'de> Deserialize<'de>>(
        &self,
        collection: &str,
    ) -> Result<Vec<T>, Box<dyn std::error::Error>> {
        let url = format!("{}/items/{}", self.base_url, collection);
        
        let response = self.client
            .get(&url)
            .header("Authorization", format!("Bearer {}", self.api_key))
            .send()
            .await?;

        let data: DirectusResponse<T> = response.json().await?;
        Ok(data.data)
    }

    // Create item in Directus collection
    pub async fn create_item<T: Serialize>(
        &self,
        collection: &str,
        item: T,
    ) -> Result<String, Box<dyn std::error::Error>> {
        let url = format!("{}/items/{}", self.base_url, collection);
        
        let response = self.client
            .post(&url)
            .header("Authorization", format!("Bearer {}", self.api_key))
            .json(&item)
            .send()
            .await?;

        Ok(response.text().await?)
    }

    // Update item in Directus collection
    pub async fn update_item<T: Serialize>(
        &self,
        collection: &str,
        id: &str,
        item: T,
    ) -> Result<String, Box<dyn std::error::Error>> {
        let url = format!("{}/items/{}/{}", self.base_url, collection, id);
        
        let response = self.client
            .patch(&url)
            .header("Authorization", format!("Bearer {}", self.api_key))
            .json(&item)
            .send()
            .await?;

        Ok(response.text().await?)
    }

    // Delete item from Directus collection
    pub async fn delete_item(
        &self,
        collection: &str,
        id: &str,
    ) -> Result<(), Box<dyn std::error::Error>> {
        let url = format!("{}/items/{}/{}", self.base_url, collection, id);
        
        self.client
            .delete(&url)
            .header("Authorization", format!("Bearer {}", self.api_key))
            .send()
            .await?;

        Ok(())
    }
}

#[derive(Deserialize)]
struct DirectusResponse<T> {
    data: Vec<T>,
}

// CMS proxy handler for Axum
use axum::{
    extract::{Path, State},
    http::StatusCode,
    response::Json,
};

pub async fn cms_proxy(
    Path(endpoint): Path<String>,
    State(state): State<crate::services::AppState>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    // Proxy request to Directus
    match state.directus_client.get_items::<serde_json::Value>(&endpoint).await {
        Ok(items) => Ok(Json(serde_json::json!({ "data": items }))),
        Err(_) => Err(StatusCode::INTERNAL_SERVER_ERROR),
    }
}
