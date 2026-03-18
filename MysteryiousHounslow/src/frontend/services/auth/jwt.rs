use jsonwebtoken::{decode, encode, Algorithm, DecodingKey, EncodingKey, Header, Validation};
use serde::{Deserialize, Serialize};
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Debug, Serialize, Deserialize)]
pub struct Claims {
    pub sub: String, // user id
    pub exp: usize,  // expiration time
    pub iat: usize,  // issued at
}

pub struct JwtService {
    encoding_key: EncodingKey,
    decoding_key: DecodingKey,
}

impl JwtService {
    pub fn new(private_key_pem: &str, public_key_pem: &str) -> Result<Self, jsonwebtoken::errors::Error> {
        let encoding_key = EncodingKey::from_rsa_pem(private_key_pem.as_bytes())?;
        let decoding_key = DecodingKey::from_rsa_pem(public_key_pem.as_bytes())?;
        Ok(Self {
            encoding_key,
            decoding_key,
        })
    }

    pub fn create_token(&self, user_id: &str) -> Result<String, jsonwebtoken::errors::Error> {
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_secs() as usize;

        let claims = Claims {
            sub: user_id.to_string(),
            exp: now + 3600, // 1 hour
            iat: now,
        };

        let header = Header::new(Algorithm::RS256);
        encode(&header, &claims, &self.encoding_key)
    }

    pub fn verify_token(&self, token: &str) -> Result<Claims, jsonwebtoken::errors::Error> {
        let mut validation = Validation::new(Algorithm::RS256);
        validation.validate_exp = true;

        let token_data = decode::<Claims>(token, &self.decoding_key, &validation)?;
        Ok(token_data.claims)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // Generate test RSA keys for testing
    const TEST_PRIVATE_KEY: &str = "-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEAwJ8Z+Yq5Q6Q6Y6Y6Y6Y6Y6Y6Y6Y6Y6Y6Y6Y6Y6Y6Y6Y6Y6Y
... (truncated for brevity, use real key in production)
-----END RSA PRIVATE KEY-----";

    const TEST_PUBLIC_KEY: &str = "-----BEGIN RSA PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAwJ8Z+Yq5Q6Q6Y6Y6Y6Y6Y
6Y6Y6Y6Y6Y6Y6Y6Y6Y6Y6Y6Y6Y
... (truncated)
-----END RSA PUBLIC KEY-----";

    #[test]
    fn test_jwt_creation_and_verification() {
        let service = JwtService::new(TEST_PRIVATE_KEY, TEST_PUBLIC_KEY).unwrap();
        let token = service.create_token("user123").unwrap();
        let claims = service.verify_token(&token).unwrap();
        assert_eq!(claims.sub, "user123");
    }
}