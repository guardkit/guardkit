---
paths: **/Dockerfile, docker-compose*
---

# Docker Compose Development Environment

## Multi-Service Orchestration

Docker Compose manages all services for local development:

```yaml
services:
  db:
    image: postgres:16
    ports:
      - "5432:5432"
    environment:
      POSTGRES_DB: app
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: changethis
    volumes:
      - postgres-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  backend:
    build:
      context: ./apps/backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy
    environment:
      POSTGRES_SERVER: db
      POSTGRES_PORT: 5432
    volumes:
      - ./apps/backend:/app
    command: uvicorn app.main:app --host 0.0.0.0 --reload

  frontend:
    build:
      context: ./apps/frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    depends_on:
      - backend
    volumes:
      - ./apps/frontend:/app
      - /app/node_modules
    command: pnpm dev --host

volumes:
  postgres-data:
```

## Service Configuration

### Database Service
- **Image**: PostgreSQL 16
- **Port**: 5432
- **Health check**: Ensures DB ready before backend starts
- **Volume**: Persists data between restarts

### Backend Service
- **Port**: 8000
- **Hot reload**: Code changes trigger restart
- **Dependencies**: Waits for healthy database
- **Volume mount**: Live code updates

### Frontend Service
- **Port**: 3000
- **Hot reload**: Vite dev server
- **Dependencies**: Waits for backend
- **Volume mount**: Live code updates

## Common Commands

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Stop all services
docker-compose down

# Rebuild and restart
docker-compose up -d --build

# Stop and remove volumes (reset database)
docker-compose down -v
```

## Development Workflow

### 1. Initial Setup
```bash
# Start all services
pnpm docker:up

# Services available at:
# - Frontend: http://localhost:3000
# - Backend: http://localhost:8000
# - Database: localhost:5432
```

### 2. View Service Status
```bash
docker-compose ps
```

### 3. Access Service Shells
```bash
# Backend shell
docker-compose exec backend bash

# Database shell
docker-compose exec db psql -U postgres -d app
```

### 4. Reset Database
```bash
docker-compose down -v
docker-compose up db -d
```

## Volume Management

### Code Volumes (Hot Reload)
```yaml
volumes:
  - ./apps/backend:/app  # Backend code
  - ./apps/frontend:/app  # Frontend code
  - /app/node_modules    # Exclude node_modules
```

### Data Volumes (Persistence)
```yaml
volumes:
  - postgres-data:/var/lib/postgresql/data
```

## Health Checks

### Database Health Check
```yaml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U postgres"]
  interval: 5s
  timeout: 5s
  retries: 5
```

### Service Dependencies
```yaml
backend:
  depends_on:
    db:
      condition: service_healthy  # Wait for health check
```

## Environment Variables

### Backend
```yaml
environment:
  POSTGRES_SERVER: db
  POSTGRES_PORT: 5432
  POSTGRES_DB: app
  POSTGRES_USER: postgres
  POSTGRES_PASSWORD: changethis
```

### Frontend
```yaml
environment:
  VITE_API_URL: http://backend:8000
```

## Production vs Development

### Development (docker-compose.yml)
- Hot reload enabled
- Volume mounts for code
- Debug ports exposed
- Verbose logging

### Production (docker-compose.prod.yml)
```yaml
backend:
  build:
    context: ./apps/backend
    dockerfile: Dockerfile.prod
  command: uvicorn app.main:app --host 0.0.0.0 --workers 4
  volumes: []  # No code mounts
```

## Troubleshooting

### Issue: Port already in use
**Check**: `lsof -i :3000,8000,5432`
**Solution**: Stop conflicting service or change port

### Issue: Database connection refused
**Check**: `docker-compose logs db`
**Solution**: Wait for health check to pass

### Issue: Hot reload not working
**Check**: Volume mounts configured correctly
**Solution**: Verify volume paths in `docker-compose.yml`

### Issue: Stale containers
**Solution**: Rebuild from scratch
```bash
docker-compose down -v
docker-compose up -d --build
```
