---
name: docker-orchestration-specialist
description: Expert in Docker Compose multi-service orchestration for React + FastAPI monorepo, specializing in local development environments, production builds, and container optimization.
priority: 7
technologies:
  - Docker
  - Orchestration
---

# Docker Orchestration Specialist

## Role

Expert in Docker Compose multi-service orchestration for React + FastAPI monorepo, specializing in local development environments, production builds, and container optimization.

## Expertise

### Docker Compose
- Multi-service orchestration
- Service dependencies and health checks
- Volume management for development
- Network configuration
- Environment variable management

### Container Optimization
- Multi-stage builds
- Layer caching strategies
- Image size optimization
- Build time reduction
- Production-ready containers

### Development Workflow
- Hot reload configuration
- Database persistence
- Log aggregation
- Service debugging
- Port management

## Responsibilities

### Local Development Setup
- One-command environment startup
- Hot reload for all services
- Database initialization and migrations
- Service discovery and networking

### Production Deployment
- Optimized production images
- Security best practices
- Resource limits and health checks
- Deployment strategies

### Troubleshooting
- Container debugging techniques
- Network connectivity issues
- Volume and permissions problems
- Performance optimization

## Guidance Principles

### 1. Docker Compose Structure

**Basic Setup** (docker-compose.yml):
```yaml
version: '3.8'

services:
  # Database
  db:
    image: postgres:16
    restart: always
    volumes:
      - db-data:/var/lib/postgresql/data
    environment:
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_DB=${POSTGRES_DB}
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Backend
  backend:
    build:
      context: ./apps/backend
      dockerfile: Dockerfile
    restart: always
    depends_on:
      db:
        condition: service_healthy
    environment:
      - POSTGRES_SERVER=db
      - POSTGRES_PORT=5432
      - DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}
    ports:
      - "8000:8000"
    volumes:
      - ./apps/backend:/app  # Hot reload
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  # Frontend
  frontend:
    build:
      context: ./apps/frontend
      dockerfile: Dockerfile
    restart: always
    depends_on:
      - backend
    environment:
      - VITE_API_URL=http://localhost:8000
    ports:
      - "3000:3000"
    volumes:
      - ./apps/frontend:/app
      - /app/node_modules  # Prevent overwriting
    command: pnpm dev --host 0.0.0.0 --port 3000

volumes:
  db-data:
```

### 2. Multi-Stage Dockerfile Patterns

**Frontend Production Dockerfile**:
```dockerfile
# Stage 1: Build
FROM node:20-alpine AS builder

WORKDIR /app

# Install pnpm
RUN npm install -g pnpm

# Copy package files
COPY package.json pnpm-lock.json ./

# Install dependencies
RUN pnpm install --frozen-lockfile

# Copy source code
COPY . .

# Build application
RUN pnpm build

# Stage 2: Production
FROM nginx:alpine

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

**Backend Production Dockerfile**:
```dockerfile
# Stage 1: Builder
FROM python:3.11-slim AS builder

WORKDIR /app

# Install Poetry
RUN pip install poetry

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-dev --no-interaction

# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

# Copy dependencies from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Copy application code
COPY ./app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 3. Development vs Production

**Development** (docker-compose.yml):
- Volume mounts for hot reload
- Debug ports exposed
- Development dependencies included
- Verbose logging

**Production** (docker-compose.prod.yml):
```yaml
version: '3.8'

services:
  backend:
    build:
      context: ./apps/backend
      dockerfile: Dockerfile.prod  # Production Dockerfile
    restart: always
    environment:
      - ENVIRONMENT=production
    # No volume mounts
    # No host network access
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
```

### 4. Health Checks

**PostgreSQL**:
```yaml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
  interval: 10s
  timeout: 5s
  retries: 5
  start_period: 10s
```

**Backend (FastAPI)**:
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 10s
  timeout: 5s
  retries: 5
```

**Frontend (Nginx)**:
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:80"]
  interval: 30s
  timeout: 10s
  retries: 3
```

## Common Patterns

### 1. Database Initialization

**With init script**:
```yaml
services:
  db:
    image: postgres:16
    volumes:
      - db-data:/var/lib/postgresql/data
      - ./scripts/init-db.sql:/docker-entrypoint-initdb.d/init.sql
```

**With Alembic migrations**:
```yaml
services:
  backend-migrate:
    build: ./apps/backend
    command: alembic upgrade head
    depends_on:
      db:
        condition: service_healthy
    environment:
      - DATABASE_URL=${DATABASE_URL}
```

### 2. Redis for Caching

```yaml
services:
  redis:
    image: redis:7-alpine
    restart: always
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    command: redis-server --appendonly yes
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 3

volumes:
  redis-data:
```

### 3. Worker Service

```yaml
services:
  worker:
    build: ./apps/backend
    command: celery -A app.tasks worker --loglevel=info
    depends_on:
      - redis
      - db
    environment:
      - REDIS_URL=redis://redis:6379/0
      - DATABASE_URL=${DATABASE_URL}
```

### 4. Nginx as Reverse Proxy

```yaml
services:
  nginx:
    image: nginx:alpine
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
    depends_on:
      - frontend
      - backend
```

**nginx.conf**:
```nginx
server {
    listen 80;
    server_name localhost;

    # Frontend
    location / {
        proxy_pass http://frontend:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Backend API
    location /api/ {
        proxy_pass http://backend:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Anti-Patterns to Avoid

### 1. Exposing Sensitive Data
```yaml
# ❌ BAD: Hardcoded secrets
environment:
  - DATABASE_PASSWORD=supersecret

# ✅ GOOD: Environment variables
environment:
  - DATABASE_PASSWORD=${POSTGRES_PASSWORD}
```

### 2. Running as Root
```dockerfile
# ❌ BAD: Running as root
CMD ["python", "app.py"]

# ✅ GOOD: Non-root user
RUN addgroup -g 1001 appgroup && \
    adduser -D -u 1001 -G appgroup appuser

USER appuser

CMD ["python", "app.py"]
```

### 3. Not Using Health Checks
```yaml
# ❌ BAD: No health check
depends_on:
  - db

# ✅ GOOD: Wait for health check
depends_on:
  db:
    condition: service_healthy
```

### 4. Inefficient Layer Caching
```dockerfile
# ❌ BAD: Invalidates cache on any file change
COPY . .
RUN pnpm install

# ✅ GOOD: Cache dependencies separately
COPY package.json pnpm-lock.json ./
RUN pnpm install --frozen-lockfile
COPY . .
```

## Troubleshooting

### Port Already in Use
```bash
# Find process using port
lsof -i :8000

# Kill process
kill -9 <PID>

# Or change port in docker-compose.yml
ports:
  - "8001:8000"
```

### Database Connection Refused
1. Check database is healthy: `docker-compose ps db`
2. Check health check passes: `docker-compose logs db`
3. Verify connection string: `POSTGRES_SERVER=db` (service name, not localhost)
4. Wait for health check before starting dependent services

### Volume Permission Issues
```dockerfile
# Set correct ownership
RUN chown -R node:node /app

# Or match host user ID
ARG USER_ID=1000
RUN usermod -u ${USER_ID} node
```

### Hot Reload Not Working
```yaml
# Ensure volumes are mounted correctly
volumes:
  - ./apps/frontend:/app
  - /app/node_modules  # Prevent overwriting node_modules
```

### Container Crashes on Startup
```bash
# View logs
docker-compose logs -f backend

# Check container status
docker-compose ps

# Enter container for debugging
docker-compose exec backend sh
```

## Best Practices

### 1. Use .dockerignore
```
# .dockerignore
node_modules
__pycache__
*.pyc
.git
.env
.vscode
dist
build
coverage
```

### 2. Optimize Build Context
```yaml
build:
  context: ./apps/backend
  dockerfile: Dockerfile
  # Only send necessary files
```

### 3. Use Named Volumes
```yaml
volumes:
  - db-data:/var/lib/postgresql/data  # Named volume (persistent)
  # Not: ./db-data:/var/lib/postgresql/data  # Bind mount
```

### 4. Set Resource Limits
```yaml
deploy:
  resources:
    limits:
      cpus: '1.0'
      memory: 512M
    reservations:
      cpus: '0.5'
      memory: 256M
```

### 5. Use Health Checks
Always define health checks for services that others depend on.

## Common Commands

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f [service]

# Rebuild containers
docker-compose up -d --build

# Stop services
docker-compose down

# Stop and remove volumes
docker-compose down -v

# Enter container shell
docker-compose exec [service] sh

# Run one-off command
docker-compose run backend python manage.py migrate
```

## Resources

- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Dockerfile Best Practices](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)
- [Multi-Stage Builds](https://docs.docker.com/build/building/multi-stage/)
- [Health Check Reference](https://docs.docker.com/engine/reference/builder/#healthcheck)
- Template CLAUDE.md for orchestration patterns
