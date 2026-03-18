use axum::{
    http::{HeaderMap, Method, StatusCode},
    response::Response,
};
use tower_http::cors::{CorsLayer, Any};

pub fn create_cors_layer() -> CorsLayer {
    // In production, restrict origins
    // For development, allow localhost
    #[cfg(debug_assertions)]
    let cors = CorsLayer::new()
        .allow_origin(Any) // Allow any origin in development
        .allow_methods([
            Method::GET,
            Method::POST,
            Method::PUT,
            Method::DELETE,
            Method::OPTIONS,
        ])
        .allow_headers(Any)
        .max_age(std::time::Duration::from_secs(3600));

    #[cfg(not(debug_assertions))]
    let cors = CorsLayer::new()
        .allow_origin([
            "https://yourdomain.com".parse().unwrap(),
            "https://www.yourdomain.com".parse().unwrap(),
        ])
        .allow_methods([
            Method::GET,
            Method::POST,
            Method::PUT,
            Method::DELETE,
            Method::OPTIONS,
        ])
        .allow_headers([
            "content-type",
            "authorization",
            "x-requested-with",
        ])
        .allow_credentials(true)
        .max_age(std::time::Duration::from_secs(3600));

    cors
}

// Custom CORS validation for additional security
pub fn validate_cors_request(headers: &HeaderMap) -> Result<(), StatusCode> {
    // Check for suspicious headers that might indicate attacks
    let suspicious_headers = [
        "x-forwarded-host",
        "x-forwarded-proto",
        "x-forwarded-scheme",
        "x-original-url",
        "x-rewrite-url",
    ];

    for header in suspicious_headers {
        if headers.contains_key(header) {
            tracing::warn!("Suspicious header detected: {}", header);
            return Err(StatusCode::BAD_REQUEST);
        }
    }

    // Additional CORS validation can be added here
    Ok(())
}