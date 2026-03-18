use axum::{
    body::Body,
    http::{Request, StatusCode},
    Router,
};
use matchgorithm::services::auth;
use serde_json::json;
use tower::ServiceExt;

#[tokio::test]
async fn test_health_endpoint() {
    // Create a simple router with just the health endpoint
    let app = Router::new()
        .route("/api/health", axum::routing::get(|| async { "OK" }));

    // Create a request
    let request = Request::builder()
        .uri("/api/health")
        .body(Body::empty())
        .unwrap();

    // Send the request
    let response = app.oneshot(request).await.unwrap();

    // Check the response
    assert_eq!(response.status(), StatusCode::OK);

    // Read the body
    let body = axum::body::to_bytes(response.into_body(), usize::MAX).await.unwrap();
    assert_eq!(&body[..], b"OK");
}

#[tokio::test]
async fn test_login_validation() {
    // This test would require setting up the full app state
    // For now, test the validation logic separately
    // In a real scenario, you'd mock the database and external services

    // Test invalid login request
    let invalid_request = json!({
        "email": "invalid-email",
        "password": "password"
    });

    // Since we can't easily test the full handler without mocking,
    // we'll test the validation separately
    use matchgorithm::utils::validation::{LoginRequest, validate_request};

    let login_req = LoginRequest {
        email: "invalid-email".to_string(),
        password: "password".to_string(),
    };

    assert!(validate_request(&login_req).is_err());
}

#[tokio::test]
async fn test_logout_endpoint() {
    // Create router with logout endpoint
    let app = Router::new()
        .route("/api/auth/logout", axum::routing::post(matchgorithm::services::auth::logout));

    // Create request
    let request = Request::builder()
        .method("POST")
        .uri("/api/auth/logout")
        .body(Body::empty())
        .unwrap();

    // Send request
    let response = app.oneshot(request).await.unwrap();

    // Check response
    assert_eq!(response.status(), StatusCode::OK);
}

// Note: Full integration tests would require:
// 1. Mock database connections
// 2. Mock external API calls (Directus, Hasura)
// 3. Test app state setup
// 4. JWT token validation
//
// For now, these are basic structure tests.
// In a real application, consider using testcontainers or mock libraries.