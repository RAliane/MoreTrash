use matchgorithm::utils::validation::*;

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_password_validation() {
        // Valid passwords
        assert!(validate_password("StrongPass123").is_ok());
        assert!(validate_password("Complex!Password456").is_ok());

        // Invalid passwords
        assert!(validate_password("weak").is_err()); // Too short
        assert!(validate_password("nouppercase123").is_err()); // No uppercase
        assert!(validate_password("NOLOWERCASE123").is_err()); // No lowercase
        assert!(validate_password("NoNumbers").is_err()); // No numbers
    }

    #[test]
    fn test_email_domain_validation() {
        assert!(validate_email_domain("user@example.com").is_ok());
        assert!(validate_email_domain("user@subdomain.example.com").is_ok());
        assert!(validate_email_domain("invalid-email").is_err());
        assert!(validate_email_domain("user@").is_err());
    }

    #[test]
    fn test_login_request_validation() {
        // Valid request
        let valid_req = LoginRequest {
            email: "test@example.com".to_string(),
            password: "ValidPass123".to_string(),
        };
        assert!(validate_request(&valid_req).is_ok());

        // Invalid email
        let invalid_email = LoginRequest {
            email: "invalid-email".to_string(),
            password: "ValidPass123".to_string(),
        };
        assert!(validate_request(&invalid_email).is_err());

        // Empty password
        let empty_password = LoginRequest {
            email: "test@example.com".to_string(),
            password: "".to_string(),
        };
        assert!(validate_request(&empty_password).is_err());
    }

    #[test]
    fn test_register_request_validation() {
        // Valid request
        let valid_req = RegisterRequest {
            email: "test@example.com".to_string(),
            password: "StrongPass123".to_string(),
            first_name: Some("John".to_string()),
            last_name: Some("Doe".to_string()),
        };
        assert!(validate_request(&valid_req).is_ok());

        // Weak password
        let weak_pass = RegisterRequest {
            email: "test@example.com".to_string(),
            password: "weak".to_string(),
            first_name: Some("John".to_string()),
            last_name: Some("Doe".to_string()),
        };
        assert!(validate_request(&weak_pass).is_err());

        // Invalid email
        let invalid_email = RegisterRequest {
            email: "invalid-email".to_string(),
            password: "StrongPass123".to_string(),
            first_name: Some("John".to_string()),
            last_name: Some("Doe".to_string()),
        };
        assert!(validate_request(&invalid_email).is_err());
    }

    #[test]
    fn test_string_sanitization() {
        let input = "Hello <script>alert('xss')</script> World!";
        let sanitized = sanitize_html(input);
        assert!(!sanitized.contains("<script>"));
        assert!(sanitized.contains("Hello"));
        assert!(sanitized.contains("World!"));
    }

    #[test]
    fn test_rate_limit_placeholder() {
        // Test the placeholder implementation
        assert!(check_rate_limit("test_key", 10, 60));
    }
}