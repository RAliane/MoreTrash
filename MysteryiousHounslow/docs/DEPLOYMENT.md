# Deployment Guide

This guide covers deploying Matchgorithm using Podman containers on a Linux server (Ubuntu/Debian recommended).

## Prerequisites

### System Requirements
- **OS**: Linux (Ubuntu 22.04+ or RHEL 8+)
- **CPU**: 2+ cores (4+ recommended)
- **RAM**: 4GB+ (8GB+ recommended)
- **Storage**: 20GB+ available disk space
- **Network**: Public IP with DNS configured

### Software Dependencies
```bash
# Install Podman and dependencies
sudo apt update
sudo apt install -y podman podman-compose curl wget

# Install Docker Compose compatibility (optional)
sudo apt install -y docker-compose

# Verify installation
podman --version
podman-compose --version
```

### DNS Configuration
Configure your domain to point to the server:
```
matchgorithm.yourdomain.com A your-server-ip
```

## Podman Secrets Setup

Create external secrets for sensitive configuration:

```bash
# Database credentials
printf "your_db_user" | podman secret create postgres_user -
printf "your_secure_db_password" | podman secret create postgres_password -
printf "matchgorithm_db" | podman secret create postgres_db -

# Directus configuration
printf "your_directus_api_key" | podman secret create directus_token -
printf "http://directus:8055" | podman secret create directus_url -
printf "your_directus_secret" | podman secret create directus_secret -
printf "admin@yourdomain.com" | podman secret create directus_admin_email -
printf "secure_admin_password" | podman secret create directus_admin_password -

# Hasura configuration
printf "http://hasura:8080" | podman secret create hasura_endpoint -
printf "your_hasura_admin_secret" | podman secret create hasura_admin_secret -

# JWT RSA keys (generate with OpenSSL)
# Private key
openssl genrsa -out private.pem 2048
openssl rsa -in private.pem -pubout -out public.pem
podman secret create jwt_private_key_pem < private.pem
podman secret create jwt_public_key_pem < public.pem

# Optional: AI API keys
printf "your_groq_api_key" | podman secret create groq_api_key -
printf "your_openrouter_key" | podman secret create openrouter_api_key -
printf "your_google_client_id" | podman secret create google_client_id -
printf "your_google_client_secret" | podman secret create google_client_secret -
# ... add other OAuth secrets as needed
```

## Environment Configuration

Create a `.env` file for non-sensitive configuration:

```bash
# Server configuration
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
RUST_LOG=info

# Optional AI services
GROQ_API_KEY_FILE=/run/secrets/groq_api_key
OPENROUTER_API_KEY_FILE=/run/secrets/openrouter_api_key

# OAuth providers (configure as needed)
GOOGLE_CLIENT_ID_FILE=/run/secrets/google_client_id
GOOGLE_CLIENT_SECRET_FILE=/run/secrets/google_client_secret
GITHUB_CLIENT_ID_FILE=/run/secrets/github_client_id
GITHUB_CLIENT_SECRET_FILE=/run/secrets/github_client_secret
APPLE_CLIENT_ID_FILE=/run/secrets/apple_client_id
APPLE_TEAM_ID_FILE=/run/secrets/apple_team_id
APPLE_KEY_ID_FILE=/run/secrets/apple_key_id
```

## SSL/TLS Certificate Setup

### Using Let's Encrypt (Recommended)

```bash
# Install Certbot
sudo apt install -y certbot

# Get certificate (replace with your domain)
sudo certbot certonly --standalone -d matchgorithm.yourdomain.com

# Create cert directory for Nginx
sudo mkdir -p /etc/nginx/certs
sudo cp /etc/letsencrypt/live/matchgorithm.yourdomain.com/fullchain.pem /etc/nginx/certs/
sudo cp /etc/letsencrypt/live/matchgorithm.yourdomain.com/privkey.pem /etc/nginx/certs/

# Set proper permissions
sudo chown -R 101:101 /etc/nginx/certs
```

### Manual Certificate Setup

If you have existing certificates:

```bash
sudo mkdir -p /etc/nginx/certs
sudo cp your-cert.pem /etc/nginx/certs/fullchain.pem
sudo cp your-key.pem /etc/nginx/certs/privkey.pem
sudo chown -R 101:101 /etc/nginx/certs
```

## Database Initialization

The PostgreSQL container will initialize automatically, but you may want to create initial schema:

```bash
# Wait for PostgreSQL to be ready
podman-compose up -d postgres
sleep 30

# Connect to database (adjust connection string)
podman exec -it matchgorithm-postgres psql -U your_db_user -d matchgorithm_db

# Run initial migrations (if any)
# \i /path/to/migrations.sql
```

## Application Deployment

### Build and Deploy

```bash
# Clone the repository
git clone https://github.com/your-org/matchgorithm.git
cd matchgorithm

# Build the application container
podman build -t matchgorithm:latest .

# Start all services
podman-compose up -d

# Monitor startup logs
podman-compose logs -f
```

### Verify Deployment

```bash
# Check service health
podman-compose ps

# Test health endpoint
curl -f http://localhost/api/health

# Check application logs
podman-compose logs app

# Test web interface
curl -I http://localhost/
```

## Nginx Configuration

The `nginx.conf` file is mounted into the Nginx container. Ensure the SSL certificates are properly mounted:

```yaml
nginx:
  # ... other config
  volumes:
    - ./nginx.conf:/etc/nginx/nginx.conf:ro
    - ./nginx/conf.d/app.conf:/etc/nginx/conf.d/app.conf:ro
    - ./certs:/etc/nginx/certs:ro
```

## Service Configuration

### Directus Setup

After first deployment, access Directus admin at `http://your-domain/directus/` and:

1. Complete the setup wizard
2. Create content types for blog posts, user profiles, etc.
3. Configure roles and permissions
4. Set up file storage if needed

### Hasura Console

Access Hasura console at `http://your-domain/api/graphql` and:

1. Connect to PostgreSQL database
2. Create tables and relationships
3. Set up permissions and roles
4. Configure remote schemas if needed

### n8n Workflows

Access n8n at `http://your-domain/n8n/` and:

1. Create user account
2. Import workflow templates
3. Configure integrations
4. Set up webhooks and triggers

## Monitoring and Maintenance

### Health Checks

```bash
# Check all services
podman-compose ps

# Individual service logs
podman-compose logs postgres
podman-compose logs app
podman-compose logs directus

# System resource usage
podman stats
```

### Backup Strategy

```bash
# Database backup
podman exec matchgorithm-postgres pg_dump -U your_user matchgorithm_db > backup.sql

# Volume backups
podman run --rm -v matchgorithm_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup.tar.gz -C /data .
```

### Updates

```bash
# Pull latest images
podman-compose pull

# Rebuild application (after code changes)
podman-compose build app

# Rolling restart
podman-compose up -d --no-deps app
```

## Troubleshooting

### Common Issues

**Port conflicts:**
```bash
# Check what's using ports
sudo netstat -tulpn | grep :80
sudo netstat -tulpn | grep :443

# Stop conflicting services or change ports in compose file
```

**Permission issues:**
```bash
# Fix secret permissions
sudo chown -R 1000:1000 /run/secrets/

# Check Podman socket permissions
sudo usermod -aG podman $USER
```

**SSL certificate issues:**
```bash
# Renew Let's Encrypt certificates
sudo certbot renew

# Reload Nginx configuration
podman-compose exec nginx nginx -s reload
```

**Database connection issues:**
```bash
# Test database connectivity
podman-compose exec app nc -zv postgres 5432

# Check database logs
podman-compose logs postgres
```

### Performance Tuning

**Podman Configuration:**
```bash
# Increase Podman limits
echo "unqualified-search-registries = ['docker.io']" >> ~/.config/containers/registries.conf

# Enable Podman socket for Docker compatibility
systemctl --user enable podman.socket
```

**Nginx Optimization:**
- Adjust worker processes and connections in `nginx.conf`
- Configure appropriate buffer sizes
- Set up rate limiting rules

**Application Tuning:**
- Adjust SQLx connection pool size in code
- Configure appropriate log levels
- Set up monitoring endpoints

## Security Hardening

### Firewall Configuration

```bash
# UFW example
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable

# Or iptables
sudo iptables -A INPUT -p tcp --dport 80 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 443 -j ACCEPT
```

### SSL/TLS Best Practices

- Use strong ciphers in Nginx config
- Enable HSTS headers
- Regularly renew certificates
- Monitor for SSL/TLS vulnerabilities

### Container Security

- Run containers as non-root users
- Use read-only filesystems where possible
- Regularly update base images
- Scan for vulnerabilities with Trivy

## Scaling

### Horizontal Scaling

```yaml
# Scale application instances
podman-compose up -d --scale app=3
```

### Load Balancing

Configure Nginx upstream for multiple app instances:

```nginx
upstream matchgorithm_app {
    server app:8000;
    server app2:8000;
    server app3:8000;
}
```

### Database Scaling

- Use PostgreSQL read replicas
- Implement connection pooling
- Consider database sharding for large datasets

## Disaster Recovery

### Backup Strategy

- Daily database backups
- Weekly volume snapshots
- Offsite backup storage
- Documented recovery procedures

### Recovery Procedures

1. Stop all services
2. Restore database from backup
3. Restore persistent volumes
4. Start services in dependency order
5. Verify application functionality

This deployment guide provides a production-ready setup for Matchgorithm. Monitor your deployment closely after initial setup and adjust configurations based on your specific requirements and traffic patterns.