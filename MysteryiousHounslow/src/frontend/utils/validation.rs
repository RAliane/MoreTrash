use validator::{Validate, ValidationError};

// Custom validation functions
pub fn validate_password(password: &str) -> Result<(), ValidationError> {
    if password.len() < 8 {
        return Err(ValidationError::new("Password must be at least 8 characters long"));
    }
    if !password.chars().any(|c| c.is_uppercase()) {
        return Err(ValidationError::new("Password must contain at least one uppercase letter"));
    }
    if !password.chars().any(|c| c.is_lowercase()) {
        return Err(ValidationError::new("Password must contain at least one lowercase letter"));
    }
    if !password.chars().any(|c| c.is_numeric()) {
        return Err(ValidationError::new("Password must contain at least one number"));
    }
    Ok(())
}

pub fn validate_email_domain(email: &str) -> Result<(), ValidationError> {
    let parts: Vec<&str> = email.split('@').collect();
    if parts.len() != 2 {
        return Err(ValidationError::new("Invalid email format"));
    }
    let domain = parts[1];
    if domain.is_empty() || !domain.contains('.') {
        return Err(ValidationError::new("Invalid email domain"));
    }
    // Additional domain validation can be added here
    Ok(())
}

// Validated request structs
#[derive(Debug, Validate, serde::Deserialize)]
pub struct LoginRequest {
    #[validate(email)]
    pub email: String,
    #[validate(length(min = 1))]
    pub password: String,
}

#[derive(Debug, Validate, serde::Deserialize)]
pub struct RegisterRequest {
    #[validate(email)]
    pub email: String,
    #[validate(custom = "validate_password")]
    pub password: String,
    #[validate(length(min = 1, max = 50))]
    pub first_name: Option<String>,
    #[validate(length(min = 1, max = 50))]
    pub last_name: Option<String>,
}

#[derive(Debug, Validate, serde::Deserialize)]
pub struct UpdateProfileRequest {
    #[validate(length(min = 1, max = 100))]
    pub first_name: Option<String>,
    #[validate(length(min = 1, max = 100))]
    pub last_name: Option<String>,
    #[validate(length(min = 10, max = 500))]
    pub bio: Option<String>,
}

#[derive(Debug, Validate, serde::Deserialize)]
pub struct ChangePasswordRequest {
    #[validate(custom = "validate_password")]
    pub current_password: String,
    #[validate(custom = "validate_password")]
    pub new_password: String,
}

#[derive(Debug, Validate, serde::Deserialize)]
pub struct ContactFormRequest {
    #[validate(length(min = 1, max = 100))]
    pub name: String,
    #[validate(email)]
    pub email: String,
    #[validate(length(min = 10, max = 1000))]
    pub message: String,
}

#[derive(Debug, Validate, serde::Deserialize)]
pub struct CreatePostRequest {
    #[validate(length(min = 1, max = 200))]
    pub title: String,
    #[validate(length(min = 1, max = 10000))]
    pub content: String,
    #[validate(length(min = 1, max = 50))]
    pub category: Option<String>,
}

// Validation helper function
pub fn validate_request<T: Validate>(request: &T) -> Result<(), validator::ValidationErrors> {
    request.validate()
}

// Sanitization functions
pub fn sanitize_string(input: &str) -> String {
    // Remove potentially dangerous characters
    input.chars()
        .filter(|&c| c.is_alphanumeric() || c.is_whitespace() || c == '-' || c == '_' || c == '@' || c == '.')
        .collect()
}

pub fn sanitize_html(input: &str) -> String {
    // Basic HTML sanitization - remove script tags and other dangerous elements
    input.replace("<script", "")
        .replace("</script>", "")
        .replace("<iframe", "")
        .replace("</iframe>", "")
        .replace("javascript:", "")
        .replace("onload=", "")
        .replace("onerror=", "")
}

// Rate limiting helpers
pub fn check_rate_limit(key: &str, max_requests: u32, window_seconds: u64) -> bool {
    // This would integrate with a rate limiting store (Redis, etc.)
    // For now, return true (allow) - implement actual rate limiting in production
    true
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_valid_email() {
        let req = LoginRequest {
            email: "test@example.com".to_string(),
            password: "password123".to_string(),
        };
        assert!(validate_request(&req).is_ok());
    }

    #[test]
    fn test_invalid_email() {
        let req = LoginRequest {
            email: "invalid-email".to_string(),
            password: "password123".to_string(),
        };
        assert!(validate_request(&req).is_err());
    }

    #[test]
    fn test_password_validation() {
        assert!(validate_password("StrongPass123").is_ok());
        assert!(validate_password("weak").is_err());
        assert!(validate_password("nouppercase123").is_err());
        assert!(validate_password("NOLOWERCASE123").is_err());
        assert!(validate_password("NoNumbers").is_err());
    }

    #[test]
    fn test_string_sanitization() {
        let input = "<script>alert('xss')</script>Hello World!";
        let sanitized = sanitize_html(input);
        assert!(!sanitized.contains("<script>"));
        assert!(sanitized.contains("Hello World!"));
    }
}