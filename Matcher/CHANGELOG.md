# Changelog

All notable changes to Matchgorithm are documented in this file.

## [1.0.0] - 2026-01-16

### Architecture
- **DECISION**: Migrated from Next.js/React to Dioxus (Rust) fullstack
- **DECISION**: Directus CMS as single source of truth for all data
- **DECISION**: Hasura GraphQL for real-time data queries
- **DECISION**: FastAPI XGBoost Optimizer as external ML service
- **DECISION**: PostgreSQL 13 as primary database
- **DECISION**: Podman for containerization (not Docker)
- **DECISION**: DigitalOcean for deployment (not Vercel/Cloudflare)

### Added
- Dioxus SSR application with Axum backend
- Directus integration with REST API client
- Hasura GraphQL client for data queries
- FastAPI client for ML optimization requests
- Page components: Home, Platform, Solutions, About, Contact, Pricing
- Authentication pages: Sign In, Sign Up, Forgot Password
- Dashboard pages: Overview, Profile, Analytics
- Reusable UI components: Button, Card, Header, Footer
- Directus schema and hooks configuration
- Podman Compose orchestration for all services
- Nginx reverse proxy configuration
- Comprehensive environment configuration template
- SEO optimization: robots.txt, llm.txt

### Removed
- All Next.js/React code and dependencies
- All HTMX/Express.js code
- Cloudflare Workers configuration (wrangler.toml)
- Vercel deployment configuration
- shadcn/ui React components (replaced with Dioxus equivalents)
- Node.js package.json and dependencies

### Technical Decisions Log

#### Why Dioxus over Next.js?
- Type safety with Rust's compiler
- Single language for frontend and backend
- Better performance characteristics
- Smaller bundle sizes with WASM
- Memory safety guarantees

#### Why Directus as Source of Truth?
- Flexible content modeling
- Built-in authentication and permissions
- REST and GraphQL APIs included
- Admin UI for content management
- Extensible with hooks and flows

#### Why FastAPI for ML?
- Python ecosystem for ML (XGBoost, PyGAD, OR-Tools)
- High performance async framework
- Automatic OpenAPI documentation
- Easy integration with scientific libraries

#### Why Podman over Docker?
- Rootless containers by default
- Daemonless architecture
- Better security model
- Drop-in Docker replacement
- Native secrets management

## [0.x.x] - Previous Iterations (Archived)

Previous versions used Next.js/React with various backend configurations.
These have been fully replaced with the Rust/Dioxus architecture.
