# Matchgorithm - Production Containerfile for Dioxus (Rust)

# Stage 1: Build
FROM docker.io/library/rust:1.75-alpine AS builder

# Install build dependencies
RUN apk add --no-cache \
    musl-dev \
    openssl-dev \
    pkgconfig

WORKDIR /app

# Copy dependency manifests
COPY Cargo.toml Cargo.lock ./

# Create dummy src to cache dependencies
RUN mkdir src && \
    echo "fn main() {}" > src/main.rs && \
    cargo build --release && \
    rm -rf src

# Copy actual source code
COPY src ./src

# Build release binary
RUN cargo build --release --bin matchgorithm

# Stage 2: Runtime
FROM docker.io/library/alpine:latest

# Install runtime dependencies
RUN apk add --no-cache \
    ca-certificates \
    libgcc

# Create non-root user
RUN addgroup -g 1000 matchgorithm && \
    adduser -D -u 1000 -G matchgorithm matchgorithm

WORKDIR /app

# Copy binary from builder
COPY --from=builder /app/target/release/matchgorithm /app/matchgorithm

# Copy static assets (if any)
# COPY --chown=matchgorithm:matchgorithm static ./static

# Set ownership
RUN chown -R matchgorithm:matchgorithm /app

USER matchgorithm

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8000/api/health || exit 1

ENTRYPOINT ["/app/matchgorithm"]
