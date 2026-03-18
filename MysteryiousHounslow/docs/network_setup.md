# Triple Network Separation Implementation

## Overview
Matchgorithm implements triple network separation following zero-trust security principles, isolating public-facing, internal API, and database services into separate network segments.

## Network Architecture

### Edge Network (`edge-net`)
**Subnet**: `10.0.1.0/24`
**Purpose**: Public-facing services and reverse proxies
**Services**:
- ✅ Nginx (reverse proxy)
- ✅ Axum (Rust web application)
- ✅ FastAPI (public endpoints)

**Network Rules**:
- **Inbound**: HTTP (80), HTTPS (443), Axum (8000), ICMP
- **Outbound**: Auth network (API calls)
- **Isolation**: No direct database access

### Auth Network (`auth-net`)
**Subnet**: `10.0.2.0/24`
**Internal**: `true` (no external access)
**Purpose**: Internal API services and authentication
**Services**:
- ✅ Hasura (GraphQL API)
- ✅ Directus (REST API)
- ✅ n8n (workflow automation)

**Network Rules**:
- **Inbound**: Edge network (authenticated API calls)
- **Outbound**: Database network (data operations)
- **Isolation**: No public internet access

### Database Network (`db-net`)
**Subnet**: `10.0.3.0/24`
**Internal**: `true` (no external access)
**Purpose**: Data storage and processing
**Services**:
- ✅ PostgreSQL
- ✅ pgvector (vector extensions)
- ✅ PostGIS (geospatial extensions)

**Network Rules**:
- **Inbound**: Auth network only (Hasura/Directus)
- **Outbound**: None (data services don't initiate connections)
- **Isolation**: Complete network isolation

## Implementation

### Podman Network Creation

```bash
# Create networks with proper subnets
podman network create --subnet=10.0.1.0/24 edge-net
podman network create --subnet=10.0.2.0/24 --internal auth-net
podman network create --subnet=10.0.3.0/24 --internal db-net

# Verify networks
podman network ls
```

### Service Assignment

```yaml
# podman-compose.yml network assignments
services:
  nginx:
    networks:
      - edge-net
      - auth-net  # For internal proxying

  axum:
    networks:
      - edge-net

  hasura:
    networks:
      - auth-net
      - db-net

  directus:
    networks:
      - auth-net
      - db-net

  postgres:
    networks:
      - db-net

  n8n:
    networks:
      - auth-net
```

### Firewall Rules

Execute the security script to implement network isolation:

```bash
# Apply network security rules
./scripts/network_security.sh

# Verify rules
iptables -L -v
```

## Security Benefits

### 1. Lateral Movement Prevention
- **Before**: Compromised web app could access database directly
- **After**: Web app isolated from database network
- **Impact**: Prevents data breaches from application vulnerabilities

### 2. Attack Surface Reduction
- **Before**: All services on single network
- **After**: Segmented networks with minimal exposure
- **Impact**: Limits blast radius of security incidents

### 3. Compliance Alignment
- **Zero Trust**: Network-level access controls
- **Defense in Depth**: Multiple isolation layers
- **Audit Trail**: Packet logging for security monitoring

### 4. Operational Security
- **Service Isolation**: Independent failure domains
- **Traffic Control**: Explicit allow/deny rules
- **Monitoring**: Network-level security events

## Testing Network Isolation

### 1. Service Connectivity Tests

```bash
# Test edge network services
curl http://localhost/          # Nginx (edge-net)
curl http://localhost:8000/api/health  # Axum (edge-net)

# Test auth network services (should fail from outside)
curl http://localhost:8080/v1/graphql  # Hasura (auth-net) - should be blocked

# Test database isolation
psql -h localhost -U user -d db  # Should fail (db-net isolated)
```

### 2. Inter-Network Communication

```bash
# Test allowed communication
# Nginx (edge) → Axum (edge) ✅
# Axum (edge) → Hasura (auth) ✅
# Hasura (auth) → PostgreSQL (db) ✅

# Test blocked communication
# Axum (edge) → PostgreSQL (db) ❌
# Nginx (edge) → PostgreSQL (db) ❌
```

### 3. Security Monitoring

```bash
# Check dropped packets
iptables -L -v | grep DROP

# Monitor network traffic
podman network inspect edge-net
podman network inspect auth-net
podman network inspect db-net
```

## Deployment Checklist

- [ ] Create Podman networks with correct subnets
- [ ] Update `podman-compose.yml` with network assignments
- [ ] Apply firewall rules using security script
- [ ] Test service connectivity within networks
- [ ] Verify inter-network communication restrictions
- [ ] Enable packet logging for auditing
- [ ] Document network architecture for operations team

## Troubleshooting

### Common Issues

#### Services Can't Communicate
```bash
# Check network membership
podman network inspect edge-net
podman network inspect auth-net
podman network inspect db-net

# Verify service network assignment
podman-compose ps
```

#### Firewall Blocking Legitimate Traffic
```bash
# Check iptables rules
iptables -L -v

# Temporarily disable rules for testing
iptables -F  # ⚠️  Use with caution
```

#### DNS Resolution Issues
```bash
# Check Podman DNS
podman network inspect <network> | grep dns

# Test service discovery
podman exec <container> nslookup <service_name>
```

### Emergency Access
If network isolation blocks necessary access:

```bash
# Temporary full access (use with caution)
iptables -F
iptables -P INPUT ACCEPT
iptables -P FORWARD ACCEPT
iptables -P OUTPUT ACCEPT

# Reapply rules after fixing
./scripts/network_security.sh
```

## Maintenance

### Network Updates
```bash
# Recreate networks (requires service restart)
podman network rm edge-net auth-net db-net
podman network create --subnet=10.0.1.0/24 edge-net
podman network create --subnet=10.0.2.0/24 --internal auth-net
podman network create --subnet=10.0.3.0/24 --internal db-net
```

### Rule Updates
```bash
# Modify rules in network_security.sh
# Reapply rules
./scripts/network_security.sh
```

### Monitoring
- Regular network traffic analysis
- Security event log review
- Periodic connectivity testing
- Firewall rule audits

This network architecture provides enterprise-grade security while maintaining operational flexibility and service discoverability within authorized network segments.