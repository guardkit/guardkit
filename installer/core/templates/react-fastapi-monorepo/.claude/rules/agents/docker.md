---
paths: **/Dockerfile, docker-compose*
---

# Docker Orchestration Specialist Agent

## Purpose

Docker Compose multi-service orchestration for local development and production deployments.

## Technologies

- **Docker Compose**: Multi-container orchestration
- **PostgreSQL**: Database service
- **FastAPI**: Backend service
- **React/Vite**: Frontend service

## Boundaries

### ALWAYS
- ✅ Use health checks for dependent services (ensure services start in correct order)
- ✅ Mount source code as volumes in development (enable hot reload)
- ✅ Use named volumes for persistent data (prevent data loss on restart)
- ✅ Configure restart policies for production (ensure service availability)
- ✅ Expose only necessary ports (minimize security surface)

### NEVER
- ❌ Never start services without health checks (causes race conditions)
- ❌ Never commit sensitive data in docker-compose.yml (use environment variables)
- ❌ Never use volume mounts in production (security risk)
- ❌ Never expose internal ports to host unnecessarily (security risk)
- ❌ Never run containers as root in production (privilege escalation risk)

### ASK
- ⚠️ Additional services needed: Ask about Redis, Elasticsearch, message queues, etc.
- ⚠️ Production deployment strategy: Ask about orchestration platform (K8s, ECS, etc.)
- ⚠️ Resource limits required: Ask about memory/CPU constraints for services
- ⚠️ Multi-environment configs: Ask about dev, staging, production differences

## Key Patterns

### Service Dependencies with Health Checks

```yaml
services:
  db:
    image: postgres:16
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  backend:
    depends_on:
      db:
        condition: service_healthy  # Wait for DB health check
```

### Development vs Production

**Development** (docker-compose.yml):
```yaml
backend:
  build:
    context: ./apps/backend
  volumes:
    - ./apps/backend:/app  # Hot reload
  command: uvicorn app.main:app --reload
```

**Production** (docker-compose.prod.yml):
```yaml
backend:
  image: backend:prod
  command: uvicorn app.main:app --workers 4
  restart: unless-stopped
  # No volume mounts
```

### Named Volumes for Persistence

```yaml
services:
  db:
    volumes:
      - postgres-data:/var/lib/postgresql/data  # Named volume

volumes:
  postgres-data:  # Persists across container restarts
```

## Common Tasks

### Start All Services

```bash
docker-compose up -d
```

### View Service Logs

```bash
docker-compose logs -f backend
docker-compose logs -f frontend
```

### Restart Service

```bash
docker-compose restart backend
```

### Rebuild Service

```bash
docker-compose up -d --build backend
```

### Reset Database

```bash
docker-compose down -v  # Remove volumes
docker-compose up db -d
```

### Access Service Shell

```bash
# Backend shell
docker-compose exec backend bash

# Database shell
docker-compose exec db psql -U postgres -d app
```

### Add New Service

```yaml
services:
  redis:
    image: redis:7
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s

volumes:
  redis-data:
```

## Troubleshooting

### Issue: Service fails to start

**Check logs**:
```bash
docker-compose logs backend
```

**Check health**:
```bash
docker-compose ps
```

**Rebuild**:
```bash
docker-compose down
docker-compose up -d --build
```

### Issue: Database connection refused

**Check DB health**:
```bash
docker-compose exec db pg_isready -U postgres
```

**Check backend config**:
```bash
# Ensure POSTGRES_SERVER=db in backend environment
docker-compose exec backend env | grep POSTGRES
```

### Issue: Port already in use

**Find process**:
```bash
lsof -i :5432  # or :3000, :8000
```

**Change port in docker-compose.yml**:
```yaml
ports:
  - "5433:5432"  # Use different host port
```

## Integration with GuardKit

When working on Docker tasks:
1. Always verify health checks before testing
2. Use `docker-compose down -v` for clean slate testing
3. Check service logs for debugging
4. Use `/task-work` for infrastructure changes with quality gates
