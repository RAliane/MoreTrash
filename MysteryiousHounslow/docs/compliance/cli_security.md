# CLI Security Model

## Authentication
- All FastAPI calls use JWT authentication
- CLI never stores credentials locally
- Uses Podman secrets for sensitive operations

## Authorization
| Command Group       | Required Role          |
|---------------------|------------------------|
| Deployment          | admin                  |
| Database Operations | db_admin               |
| kNN Management      | ml_engineer            |
| Monitoring          | monitor                |
| Security Audits     | security_officer       |

## Network Security
- CLI only communicates with FastAPI (no direct DB access)
- All connections use TLS 1.2+
- Rate limited to prevent abuse

## UK-Specific Measures
- **Data Residency**: CLI verifies all services are UK-hosted
- **Timezone**: All operations use Europe/London
- **Compliance Checks**: `security uk` command verifies:
  - ICO registration
  - Data residency
  - GDPR requirements

## Input Validation
- **Pydantic models**: All command inputs validated
- **SQL injection prevention**: Parameterized queries only
- **Path traversal protection**: Safe file path handling
- **Type safety**: Rust compile-time guarantees

## Error Handling
- **No sensitive data in errors**: Error messages sanitized
- **Structured logging**: Security events logged appropriately
- **Graceful failure**: Commands fail safely without data exposure

## Audit Logging
```rust
// Security event logging
tracing::security!(
    command = "db backup",
    user = "admin@matchgorithm.co.uk",
    ip_address = "192.168.1.100",
    timestamp = chrono::Utc::now(),
    "Database backup initiated"
);
```

## Secret Management
- **No hardcoded secrets**: All secrets from environment
- **Podman secrets**: Integration with container secrets
- **Environment isolation**: Development/staging/production separation

## Vulnerability Scanning
- **Automated scanning**: `security scan` command
- **Dependency checking**: Regular updates and security patches
- **Container scanning**: Podman image vulnerability checks

## Incident Response
- **Automated alerts**: Security incidents trigger alerts
- **Audit trail preservation**: Incident data protected
- **Breach notification**: ICO notification within 72 hours
- **Forensic logging**: Detailed incident logs maintained

## Compliance Monitoring
- **Continuous monitoring**: Security posture continuously assessed
- **UK GDPR compliance**: Regular compliance checks
- **Reporting**: Security reports generated automatically
- **Remediation**: Automated security fixes where possible

## Zero-Trust Architecture
- **No implicit trust**: Every request authenticated and authorized
- **Least privilege**: Minimum required permissions
- **Network segmentation**: Services isolated by network policies
- **Regular rotation**: Credentials and secrets rotated regularly