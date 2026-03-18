# Directus CMS for AI Agent Content Management
# Based on official Directus image with custom configuration

FROM directus/directus:10.8.3

LABEL maintainer="AI Agent Team"
LABEL description="Directus CMS for AI Agent course content management"

# Switch to root for setup
USER root

# Install additional dependencies
RUN apk add --no-cache \
    postgresql-client \
    curl \
    jq

# Create necessary directories
RUN mkdir -p /directus/extensions /directus/uploads /directus/database /directus/snapshots

# Copy Directus configuration
COPY directus/config.js /directus/config.js
COPY directus/schema.yml /directus/snapshots/schema.yml
COPY directus/seed-courses.js /directus/seed-courses.js

# Set proper permissions
RUN chown -R node:node /directus && \
    chmod -R 755 /directus

# Copy initialization script
COPY deploy/directus/init.sh /directus/init.sh
RUN chmod +x /directus/init.sh && \
    chown node:node /directus/init.sh

# Copy health check script
COPY deploy/directus/health-check.sh /directus/health-check.sh
RUN chmod +x /directus/health-check.sh && \
    chown node:node /directus/health-check.sh

# Environment configuration
ENV NODE_ENV=production
ENV PORT=8055

# Database defaults (will be overridden by environment variables)
ENV DB_CLIENT=pg
ENV DB_HOST=localhost
ENV DB_PORT=5432
ENV DB_DATABASE=directus
ENV DB_USER=directus
ENV DB_PASSWORD=

# Security defaults
ENV KEY=change-me-in-production
ENV SECRET=change-me-in-production
ENV ADMIN_EMAIL=admin@ai-agent.local
ENV ADMIN_PASSWORD=change-me-in-production

# CORS configuration
ENV CORS_ENABLED=true
ENV CORS_ORIGIN=true
ENV CORS_METHODS=GET,POST,PATCH,DELETE,OPTIONS
ENV CORS_ALLOWED_HEADERS=Content-Type,Authorization

# Rate limiting
ENV RATE_LIMITER_ENABLED=true
ENV RATE_LIMITER_POINTS=25
ENV RATE_LIMITER_DURATION=1

# Storage configuration (defaults to local)
ENV STORAGE_LOCATIONS=local
ENV STORAGE_LOCAL_DRIVER=local
ENV STORAGE_LOCAL_ROOT=/directus/uploads

# Cache configuration
ENV CACHE_ENABLED=true
ENV CACHE_STORE=memory
ENV CACHE_TTL=5m

# Session configuration
ENV SESSION_STORE=memory
ENV SESSION_COOKIE_SECURE=true
ENV SESSION_COOKIE_SAME_SITE=lax

# Log configuration
ENV LOG_LEVEL=info
ENV LOG_STYLE=raw

# Telemetry (disabled by default)
ENV TELEMETRY=false

# Switch back to node user
USER node

# Expose Directus port
EXPOSE 8055

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD /directus/health-check.sh

# Volume for uploads
VOLUME ["/directus/uploads", "/directus/extensions", "/directus/database"]

# Entrypoint
ENTRYPOINT ["/directus/init.sh"]
