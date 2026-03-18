# FastAPI ↔ Hasura/Directus Integration

## Overview
FastAPI serves as a stateless orchestrator for the AI-powered matching pipeline, pulling data from Hasura GraphQL and pushing results back, while using Directus for content management operations.

## Architecture

```
FastAPI (Stateless Orchestrator)
├── Input: Hasura GraphQL queries
├── Processing: XGBoost → OR-Tools → PyGAD
├── Output: Hasura mutations + Directus updates
└── Content: Directus REST API for CMS operations
```

## Hasura Integration

### GraphQL Client
- **Library**: `gql[httpx]` for async GraphQL operations
- **Authentication**: Admin secret via `x-hasura-admin-secret` header
- **Operations**: Queries for data fetching, mutations for result storage

### Key Queries

#### Fetch Candidates
```graphql
query FetchCandidates($lat: float8!, $lng: float8!, $radius: Int!, $filters: jsonb) {
  candidates(
    where: {
      location: { _st_d_within: { point: { lat: $lat, lng: $lng }, distance: $radius } }
      status: { _eq: "active" }
      _and: $filters
    }
    limit: 1000
  ) {
    id
    embedding
    metadata
    constraints
  }
}
```

#### Update Match Results
```graphql
mutation UpdateMatchResults($user_id: String!, $matches: jsonb!, $match_count: Int!) {
  update_users(
    where: { id: { _eq: $user_id } }
    _set: {
      matches: $matches,
      last_match_update: "now()",
      match_count: $match_count
    }
  ) {
    affected_rows
  }
}
```

## Directus Integration

### REST Client
- **Library**: `aiohttp` for async REST operations
- **Authentication**: Bearer token via `Authorization` header
- **Operations**: CRUD operations for content management

### Key Endpoints

#### Get Pending Items
```
GET /items?filter[status][_eq]=pending
```

#### Update Item Status
```
PATCH /items/{item_id}
Content-Type: application/json

{
  "status": "processed"
}
```

#### Create Content
```
POST /items/{collection}
Content-Type: application/json

{
  "title": "New Content",
  "content": "..."
}
```

## FastAPI Endpoints

### Optimization Pipeline
```http
POST /api/v1/optimize
Content-Type: application/json

{
  "user_id": "user123",
  "location": {
    "lat": 51.5,
    "lng": -0.1,
    "radius": 5000
  },
  "constraints": {
    "max_matches": 5,
    "categories": ["premium"]
  }
}
```

**Response:**
```json
{
  "user_id": "user123",
  "matches": [
    {
      "candidate_id": "cand456",
      "score": 0.87,
      "rank": 1,
      "constraints_satisfied": true
    }
  ],
  "optimization_score": 0.92,
  "total_candidates": 150
}
```

### Fetch Candidates (Debug)
```http
GET /api/v1/candidates?lat=51.5&lng=-0.1&radius=5000
```

## Environment Variables

### Required
- `HASURA_URL`: Hasura GraphQL endpoint
- `HASURA_ADMIN_SECRET`: Hasura admin authentication
- `DIRECTUS_URL`: Directus API endpoint
- `DIRECTUS_API_KEY`: Directus API authentication

### Optional
- `FASTAPI_DEBUG`: Enable debug mode
- `FASTAPI_CORS_ORIGINS`: CORS allowed origins

## Data Flow

1. **Input**: FastAPI receives optimization request
2. **Fetch**: Query Hasura GraphQL for candidate data
3. **Process**: Run XGBoost ranking, OR-Tools constraints, PyGAD optimization
4. **Store**: Write results back to Hasura via mutations
5. **Content**: Update Directus for any CMS-related changes
6. **Response**: Return optimized matches to client

## Error Handling

- **Hasura Errors**: GraphQL validation and execution errors
- **Directus Errors**: REST API response errors
- **Processing Errors**: ML pipeline failures with detailed logging
- **Network Errors**: Connection timeouts and retries

## Monitoring

- **Health Checks**: `/health` endpoint validates all integrations
- **Metrics**: Request counts, processing times, error rates
- **Logging**: Structured logs for debugging and auditing

## Security

- **No Direct DB Access**: FastAPI never touches PostgreSQL directly
- **Scoped Permissions**: Hasura/Directus handle authorization
- **Token Management**: Secure API key handling
- **Input Validation**: Comprehensive request validation

This integration ensures FastAPI remains a pure computation orchestrator while leveraging Hasura for data access and Directus for content management.