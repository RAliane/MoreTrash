# CLI Usage Examples

## Deploy to Staging
```bash
matchgorithm deploy staging
```

## Test Hybrid kNN
```bash
matchgorithm knn test --vector 0.1,0.2,0.3,0.4,0.5 --max-results 5
```

## Benchmark kNN Performance
```bash
matchgorithm knn benchmark --test-vectors 1000 --probes 10
```

## Call FastAPI Endpoint
```bash
matchgorithm fastapi call /api/v1/hybrid_knn \
  --body '{"query_vector": [0.1, 0.2, 0.3, 0.4, 0.5], "max_results": 3}' \
  --method POST
```

## Check System Health
```bash
matchgorithm monitor health
```

## Run Security Scan
```bash
matchgorithm security scan
```

## Check UK Compliance
```bash
matchgorithm security uk
```

## Database Operations
```bash
# Run migrations
matchgorithm db migrate

# Create backup
matchgorithm db backup

# Open database shell
matchgorithm db shell
```

## Interactive Commands
```bash
# Rollback with version selection
matchgorithm deploy rollback

# Tail logs with service selection
matchgorithm monitor logs

# Call FastAPI with interactive input
matchgorithm fastapi knn
```