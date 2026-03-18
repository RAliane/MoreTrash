# Changelog

All notable changes to **Matchgorithm** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Complete repository restructure with standardized directory layout
- Git version control initialization with comprehensive history documentation
- Pre-commit and pre-push hooks for code quality control
- Professional README with full project context and setup instructions
- Comprehensive bug fixes for production readiness
- Security enhancements and network isolation
- Monitoring and alerting setup with Prometheus/Grafana
- Automated deployment and validation scripts

### Changed
- Repository structure reorganized for clarity and maintainability
- All import paths updated for new directory structure
- Documentation overhauled with professional presentation
- Authentication system enhanced with JWT and password reset

### Fixed
- Critical FastAPI logger import issue causing runtime crashes
- Database session dependency issues in API endpoints
- Directus port exposure security vulnerability
- Missing component imports causing frontend failures
- Password reset flow implementation
- Resource limits for container stability
- Authentication middleware for protected routes

### Security
- Directus admin interface secured behind nginx proxy
- Container resource limits implemented
- Network isolation with triple network separation
- Secrets management with Podman secrets
- Security scanning integrated into CI/CD pipeline

## [0.1.0] - 2026-01-14

### Added
- Initial project implementation
- Rust/Dioxus/Axum frontend
- FastAPI/XGBoost/OR-Tools/PyGAD backend
- PostgreSQL with PostGIS and pgvector
- Directus CMS and Hasura GraphQL integration
- Podman containerized deployment
- Basic authentication and user management
- ML optimization pipeline for matching algorithms
- Comprehensive security and DevSecOps setup

### Infrastructure
- Triple network isolation (edge-net, auth-net, db-net)
- SSL/TLS certificate management
- Monitoring infrastructure with Prometheus/Grafana
- Automated backup and recovery procedures
- CI/CD pipeline with security scanning
- Comprehensive logging and error handling

### Documentation
- Architecture documentation
- Deployment guides
- API documentation
- Security compliance reports
- Development setup instructions