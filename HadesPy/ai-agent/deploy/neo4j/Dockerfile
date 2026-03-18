# Neo4j 5.15.0 Community Edition with APOC and GDS Plugins
# For Render.com private service deployment

FROM neo4j:5.15.0-community

LABEL maintainer="AI Agent Team"
LABEL description="Neo4j with APOC and Graph Data Science plugins for AI Agent"

# Install dependencies for plugin installation
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Set Neo4j version
ENV NEO4J_VERSION=5.15.0

# Download and install APOC plugin
RUN wget -O /tmp/apoc.jar "https://github.com/neo4j/apoc/releases/download/5.15.0/apoc-5.15.0-core.jar" && \
    mv /tmp/apoc.jar /var/lib/neo4j/plugins/apoc.jar

# Download and install Graph Data Science plugin
RUN wget -O /tmp/gds.jar "https://graphdatascience.ninja/neo4j-graph-data-science-2.5.0.jar" && \
    mv /tmp/gds.jar /var/lib/neo4j/plugins/gds.jar

# Set proper permissions
RUN chown -R neo4j:neo4j /var/lib/neo4j/plugins && \
    chmod 644 /var/lib/neo4j/plugins/*.jar

# Configure Neo4j
# Memory settings (can be overridden via environment variables)
ENV NEO4J_dbms_memory_heap_initial__size=512m
ENV NEO4J_dbms_memory_heap_max__size=1G
ENV NEO4J_dbms_memory_pagecache_size=512m

# Enable APOC and GDS
ENV NEO4J_dbms_security_procedures_unrestricted=apoc.*,gds.*
ENV NEO4J_dbms_security_procedures_allowlist=apoc.*,gds.*

# Network configuration
ENV NEO4J_dbms_connector_bolt_listen__address=0.0.0.0:7687
ENV NEO4J_dbms_connector_http_listen__address=0.0.0.0:7474
ENV NEO4J_dbms_connector_https_listen__address=0.0.0.0:7473

# Logging
ENV NEO4J_dbms_logs_debug_level=INFO

# APOC configuration
ENV NEO4J_apoc_export_file_enabled=true
ENV NEO4J_apoc_import_file_enabled=true
ENV NEO4J_apoc_import_file_use__neo4j__config=true

# GDS configuration
ENV NEO4J_gds_enterprise__license__file=/licenses/gds.license

# Create data directories
RUN mkdir -p /data/backups /data/import /data/logs /licenses && \
    chown -R neo4j:neo4j /data

# Copy initialization scripts
COPY deploy/neo4j/init/ /var/lib/neo4j/init/ 2>/dev/null || true
RUN chmod +x /var/lib/neo4j/init/*.sh 2>/dev/null || true

# Health check script
COPY deploy/neo4j/health-check.sh /usr/local/bin/health-check.sh
RUN chmod +x /usr/local/bin/health-check.sh

# Expose ports
# 7474: HTTP
# 7473: HTTPS
# 7687: Bolt
EXPOSE 7474 7473 7687

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD /usr/local/bin/health-check.sh

# Switch to neo4j user
USER neo4j

# Data volume
VOLUME ["/data"]

# Default command
CMD ["neo4j"]
