use axum::{
    extract::Request,
    http::{header::AUTHORIZATION, HeaderMap, StatusCode},
    middleware::Next,
    response::{IntoResponse, Response},
};
use crate::services::auth::jwt::JwtService;

pub struct AuthMiddleware {
    jwt_service: JwtService,
}

impl AuthMiddleware {
    pub fn new(jwt_service: JwtService) -> Self {
        Self { jwt_service }
    }

    pub async fn auth_middleware(&self, headers: HeaderMap, mut request: Request, next: Next) -> Response {
        let auth_header = match headers.get(AUTHORIZATION) {
            Some(header) => header.to_str().unwrap_or(""),
            None => "",
        };

        if !auth_header.starts_with("Bearer ") {
            return (StatusCode::UNAUTHORIZED, "Missing or invalid token").into_response();
        }

        let token = &auth_header[7..]; // Remove "Bearer " prefix

        match self.jwt_service.verify_token(token) {
            Ok(claims) => {
                // Add user_id to request extensions for downstream handlers
                request.extensions_mut().insert(claims.sub);
                next.run(request).await
            }
            Err(_) => (StatusCode::UNAUTHORIZED, "Invalid token").into_response(),
        }
    }
}

// Helper function to extract user_id from request extensions
pub fn get_user_id(request: &Request) -> Option<String> {
    request.extensions().get::<String>().cloned()
}