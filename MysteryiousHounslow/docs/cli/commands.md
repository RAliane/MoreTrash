# Matchgorithm CLI Commands

## Deployment Management
| Command               | Description                          |
|-----------------------|--------------------------------------|
| `deploy staging`      | Deploy to staging environment       |
| `deploy production`  | Deploy to production (with confirm) |
| `deploy status`       | Show deployment status              |
| `deploy rollback`     | Rollback to previous version        |

## Hybrid kNN Management
| Command               | Description                          |
|-----------------------|--------------------------------------|
| `knn test`            | Test hybrid kNN with sample vector   |
| `knn benchmark`       | Benchmark kNN performance            |
| `knn rebuild`        | Rebuild kNN indices                  |
| `knn health`          | Check kNN system health             |

## FastAPI Integration
| Command               | Description                          |
|-----------------------|--------------------------------------|
| `fastapi call`        | Call any FastAPI endpoint            |
| `fastapi status`      | Check FastAPI service status        |
| `fastapi logs`        | View FastAPI service logs           |
| `fastapi knn`         | Call kNN service through FastAPI    |

## Database Operations
| Command               | Description                          |
|-----------------------|--------------------------------------|
| `db migrate`          | Run database migrations              |
| `db backup`           | Create database backup               |
| `db restore`         | Restore from backup                 |
| `db shell`            | Open database shell                  |

## Security Audits
| Command               | Description                          |
|-----------------------|--------------------------------------|
| `security scan`       | Run comprehensive security scan      |
| `security sql`        | Check for SQL injection vulnerabilities |
| `security network`    | Verify network isolation             |
| `security uk`         | Check UK compliance                  |

## Monitoring
| Command               | Description                          |
|-----------------------|--------------------------------------|
| `monitor health`      | Check system health                  |
| `monitor metrics`     | Show performance metrics             |
| `monitor alerts`      | List active alerts                   |
