use reqwest::Client;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Serialize, Deserialize, Debug)]
pub struct LoginRequest {
    pub email: String,
    pub password: String,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct RegisterRequest {
    pub email: String,
    pub password: String,
    pub first_name: Option<String>,
    pub last_name: Option<String>,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct PasswordResetRequest {
    pub email: String,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct PasswordResetConfirm {
    pub token: String,
    pub password: String,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct DirectusAuthResponse {
    pub data: Option<DirectusUser>,
    pub errors: Option<Vec<DirectusError>>,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct DirectusUser {
    pub id: String,
    pub email: String,
    pub first_name: Option<String>,
    pub last_name: Option<String>,
    pub role: Option<String>,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct DirectusError {
    pub message: String,
    pub extensions: Option<HashMap<String, serde_json::Value>>,
}

pub struct DirectusAuthClient {
    client: Client,
    base_url: String,
    api_key: String,
}

impl DirectusAuthClient {
    pub fn new(base_url: String, api_key: String) -> Self {
        Self {
            client: Client::new(),
            base_url,
            api_key,
        }
    }

    pub async fn login(&self, email: &str, password: &str) -> Result<DirectusUser, Box<dyn std::error::Error>> {
        let url = format!("{}/auth/login", self.base_url);
        let request = LoginRequest {
            email: email.to_string(),
            password: password.to_string(),
        };

        let response = self.client
            .post(&url)
            .header("Authorization", format!("Bearer {}", self.api_key))
            .json(&request)
            .send()
            .await?;

        if !response.status().is_success() {
            return Err(format!("Directus login failed: {}", response.status()).into());
        }

        let auth_response: DirectusAuthResponse = response.json().await?;

        if let Some(errors) = auth_response.errors {
            return Err(format!("Directus error: {:?}", errors).into());
        }

        auth_response.data.ok_or_else(|| "No user data returned".into())
    }

    pub async fn register(&self, email: &str, password: &str, first_name: Option<&str>, last_name: Option<&str>) -> Result<DirectusUser, Box<dyn std::error::Error>> {
        let url = format!("{}/users", self.base_url);
        let mut request = HashMap::new();
        request.insert("email", email);
        request.insert("password", password);
        if let Some(fname) = first_name {
            request.insert("first_name", fname);
        }
        if let Some(lname) = last_name {
            request.insert("last_name", lname);
        }

        let response = self.client
            .post(&url)
            .header("Authorization", format!("Bearer {}", self.api_key))
            .json(&request)
            .send()
            .await?;

        if !response.status().is_success() {
            return Err(format!("Directus registration failed: {}", response.status()).into());
        }

        let user: DirectusUser = response.json().await?;
        Ok(user)
    }

    pub async fn get_user(&self, user_id: &str) -> Result<DirectusUser, Box<dyn std::error::Error>> {
        let url = format!("{}/users/{}", self.base_url, user_id);

        let response = self.client
            .get(&url)
            .header("Authorization", format!("Bearer {}", self.api_key))
            .send()
            .await?;

        if !response.status().is_success() {
            return Err(format!("Directus get user failed: {}", response.status()).into());
        }

        let user: DirectusUser = response.json().await?;
        Ok(user)
    }

    pub async fn request_password_reset(&self, email: &str) -> Result<(), Box<dyn std::error::Error>> {
        let url = format!("{}/auth/password/request", self.base_url);
        let request = PasswordResetRequest {
            email: email.to_string(),
        };

        let response = self.client
            .post(&url)
            .json(&request)
            .send()
            .await?;

        if !response.status().is_success() {
            return Err(format!("Directus password reset request failed: {}", response.status()).into());
        }

        Ok(())
    }

    pub async fn reset_password(&self, token: &str, new_password: &str) -> Result<(), Box<dyn std::error::Error>> {
        let url = format!("{}/auth/password/reset", self.base_url);
        let request = PasswordResetConfirm {
            token: token.to_string(),
            password: new_password.to_string(),
        };

        let response = self.client
            .post(&url)
            .json(&request)
            .send()
            .await?;

        if !response.status().is_success() {
            return Err(format!("Directus password reset failed: {}", response.status()).into());
        }

        Ok(())
    }
}