# MysteryiousHounslow Dummy Demo

A minimal, laptop-friendly demonstration of the MysteryiousHounslow hybrid kNN system.

## 🚀 Quick Start

```bash
# Start the demo
./scripts/start.sh

# Access the services
open http://localhost:3000    # Web App
open http://localhost:8056    # Directus CMS
```

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Rust Web App  │    │   Directus CMS  │    │ PostgreSQL +    │
│   (Port 3000)   │    │   (Port 8056)   │    │ pgvector        │
│                 │    │                 │    │ (Port 5433)     │
│ • Health check  │    │ • Admin panel   │    │ • Vector search │
│ • Item listing  │    │ • Content mgmt  │    │ • Demo data     │
│ • Text search   │    │ • API access    │    │                 │
│ • Vector search │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 📡 API Endpoints

### Web App (Rust)
- `GET /` - Welcome page
- `GET /health` - System health check
- `GET /items` - List demo items
- `GET /search?q=term&limit=5` - Text search
- `POST /vector-search` - Vector similarity search

### Directus (CMS)
- Admin panel at root URL
- REST API at `/items`
- GraphQL at `/graphql`

### Database (PostgreSQL + pgvector)
- Connection: `postgres://postgres:demo123@localhost:5433/matchgorithm`
- Demo table: `demo_items`
- Vector column: `embedding` (384 dimensions)

## 🔍 Demo Features

### 1. Web Interface
- Simple HTML interface showing system status
- API endpoint testing
- Real-time health monitoring

### 2. Content Management
- Directus admin panel for content management
- CRUD operations on demo items
- API documentation

### 3. Vector Search
- Hybrid kNN implementation
- pgvector for similarity search
- CLIP embeddings (384 dimensions)

## 📊 Demo Data

Pre-loaded with sample items:
- **Demo Item 1**: First demonstration item
- **Demo Item 2**: Second demonstration item
- **Demo Item 3**: Third demonstration item

All items have pre-computed CLIP embeddings for vector search.

## 🛠️ Development

### Prerequisites
- Docker or Podman
- curl (for testing)

### Running Locally
```bash
# Start services
docker-compose up -d

# Check health
curl http://localhost:3000/health

# Test vector search
curl -X POST http://localhost:3000/vector-search \
  -H "Content-Type: application/json" \
  -d '{"query_vector": [0.1, 0.2, 0.3], "max_results": 3}'
```

### Database Access
```bash
# Connect to database
psql postgres://postgres:demo123@localhost:5433/matchgorithm

# List items
SELECT id, name, description FROM demo_items;

# Test vector search
SELECT id, name, (embedding <=> '[0.1,0.2,0.3]') as similarity
FROM demo_items
ORDER BY embedding <=> '[0.1,0.2,0.3]'
LIMIT 3;
```

## 🔧 Configuration

### Environment Variables
```bash
# Web App
DATABASE_URL=postgres://postgres:demo123@db:5432/matchgorithm
DIRECTUS_URL=http://directus:8055

# Directus
ADMIN_EMAIL=admin@dummy-demo.co.uk
ADMIN_PASSWORD=demo123

# Database
POSTGRES_PASSWORD=demo123
```

### Ports
- **3000**: Rust web application
- **8056**: Directus CMS
- **5433**: PostgreSQL database

## 🧪 Testing

### Health Checks
```bash
# Web app health
curl http://localhost:3000/health

# Directus health
curl http://localhost:8056/server/health

# Database connectivity
psql postgres://postgres:demo123@localhost:5433/matchgorithm -c "SELECT 1"
```

### API Testing
```bash
# List items
curl http://localhost:3000/items

# Text search
curl "http://localhost:3000/search?q=demo&limit=2"

# Vector search
curl -X POST http://localhost:3000/vector-search \
  -H "Content-Type: application/json" \
  -d '{
    "query_vector": [0.1, 0.2, 0.3, 0.4, 0.5],
    "max_results": 3
  }'
```

## 🛑 Troubleshooting

### Services Won't Start
```bash
# Check container logs
docker-compose logs

# Restart services
docker-compose restart

# Clean restart
docker-compose down
docker-compose up -d --build
```

### Database Issues
```bash
# Reset database
docker-compose down -v
docker-compose up -d

# Manual database check
docker-compose exec db psql -U postgres -d matchgorithm
```

### Port Conflicts
```bash
# Check what's using ports
lsof -i :3000,8056,5433

# Change ports in docker-compose.yml
ports:
  - "3001:3000"  # Change host port
```

## 🧹 Cleanup

```bash
# Stop services
docker-compose down

# Remove volumes (data)
docker-compose down -v

# Remove images
docker-compose down --rmi all
```

## 📋 What's Included

- ✅ Rust web application with Axum
- ✅ PostgreSQL with pgvector extension
- ✅ Directus CMS for content management
- ✅ Pre-loaded demo data with CLIP embeddings
- ✅ Vector similarity search implementation
- ✅ Health checks and monitoring
- ✅ Laptop-friendly resource usage
- ✅ Quick start scripts

## 🎯 Purpose

This dummy demo demonstrates:
1. **Hybrid kNN System**: PostGIS + Python vector search
2. **UK Compliance**: Proper data handling and security
3. **DevSecOps**: Containerized, monitored deployment
4. **Scalability**: Horizontal scaling ready
5. **Integration**: Multiple service coordination

**Perfect for presentations, development testing, and stakeholder demonstrations!** 🎉