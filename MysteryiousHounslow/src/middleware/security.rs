use axum::{
    http::{header, HeaderMap, StatusCode},
    response::Response,
};
use tower_http::set_header::SetResponseHeaderLayer;

// Security headers middleware
pub fn create_security_headers_layer() -> SetResponseHeaderLayer<HeaderMap> {
    let mut headers = HeaderMap::new();

    // Content Security Policy
    headers.insert(
        header::CONTENT_SECURITY_POLICY,
        "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: https:; connect-src 'self' https://api.yourdomain.com; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
            .parse().unwrap(),
    );

    // HTTP Strict Transport Security
    headers.insert(
        header::STRICT_TRANSPORT_SECURITY,
        "max-age=31536000; includeSubDomains; preload"
            .parse().unwrap(),
    );

    // X-Frame-Options
    headers.insert(
        header::X_FRAME_OPTIONS,
        "DENY".parse().unwrap(),
    );

    // X-Content-Type-Options
    headers.insert(
        header::X_CONTENT_TYPE_OPTIONS,
        "nosniff".parse().unwrap(),
    );

    // Referrer-Policy
    headers.insert(
        header::REFERRER_POLICY,
        "strict-origin-when-cross-origin".parse().unwrap(),
    );

    // Permissions-Policy (formerly Feature-Policy)
    headers.insert(
        "Permissions-Policy",
        "geolocation=(), microphone=(), camera=()".parse().unwrap(),
    );

    // Remove server header
    headers.insert(
        header::SERVER,
        "Matchgorithm".parse().unwrap(),
    );

    SetResponseHeaderLayer::overriding(headers)
}

// Additional security validation
pub fn validate_security_headers(headers: &HeaderMap) -> Result<(), StatusCode> {
    // Check for potentially malicious headers
    if let Some(user_agent) = headers.get(header::USER_AGENT) {
        let ua_str = user_agent.to_str().unwrap_or("");
        if ua_str.contains("sqlmap") || ua_str.contains("nmap") || ua_str.contains("masscan") {
            tracing::warn!("Suspicious User-Agent detected: {}", ua_str);
            return Err(StatusCode::FORBIDDEN);
        }
    }

    // Check Content-Length for potential DoS
    if let Some(content_length) = headers.get(header::CONTENT_LENGTH) {
        if let Ok(length) = content_length.to_str().unwrap_or("0").parse::<u64>() {
            const MAX_BODY_SIZE: u64 = 10 * 1024 * 1024; // 10MB
            if length > MAX_BODY_SIZE {
                tracing::warn!("Request body too large: {} bytes", length);
                return Err(StatusCode::PAYLOAD_TOO_LARGE);
            }
        }
    }

    Ok(())
}

// Security event logging
pub fn log_security_event(event: &str, details: &str) {
    tracing::warn!("SECURITY EVENT: {} - {}", event, details);
}

// Rate limiting helper (basic implementation)
pub struct RateLimiter {
    requests: std::collections::HashMap<String, Vec<std::time::Instant>>,
}

impl RateLimiter {
    pub fn new() -> Self {
        Self {
            requests: std::collections::HashMap::new(),
        }
    }

    pub fn check_rate_limit(&mut self, key: &str, max_requests: usize, window: std::time::Duration) -> bool {
        let now = std::time::Instant::now();
        let entry = self.requests.entry(key.to_string()).or_insert_with(Vec::new);

        // Remove old requests outside the window
        entry.retain(|&time| now.duration_since(time) < window);

        // Check if under limit
        if entry.len() < max_requests {
            entry.push(now);
            true
        } else {
            log_security_event("RATE_LIMIT_EXCEEDED", &format!("Key: {}", key));
            false
        }
    }
}

impl Default for RateLimiter {
    fn default() -> Self {
        Self::new()
    }
}