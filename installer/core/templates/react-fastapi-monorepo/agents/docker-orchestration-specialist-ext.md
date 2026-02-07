# docker-orchestration-specialist - Extended Reference

This file contains detailed documentation for the `docker-orchestration-specialist` agent.
Load this file when you need comprehensive examples and guidance.

```bash
cat agents/docker-orchestration-specialist-ext.md
```


## Guidance Principles

### 1. Docker Compose Structure

```yaml
version: '3.8'

services:
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

  backend:
    build:
      context: ./apps/backend
      dockerfile: Dockerfile
    restart: always
    depends_on:
      db:
        condition: service_healthy
    environment:
      - DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}
    ports:
      - "8000:8000"
    volumes:
      - ./apps/backend:/app
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

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
      - /app/node_modules
    command: pnpm dev --host 0.0.0.0 --port 3000

volumes:
  db-data:
```

### 2. Multi-Stage Dockerfile (Frontend)

```dockerfile
# Stage 1: Build
FROM node:20-alpine AS builder
WORKDIR /app
RUN npm install -g pnpm
COPY package.json pnpm-lock.json ./
RUN pnpm install --frozen-lockfile
COPY . .
RUN pnpm build

# Stage 2: Production
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### 3. Multi-Stage Dockerfile (Backend)

```dockerfile
FROM python:3.11-slim AS builder
WORKDIR /app
RUN pip install poetry
COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false && poetry install --no-dev --no-interaction

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY ./app ./app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 4. Health Checks

```yaml
# PostgreSQL
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
  interval: 10s
  timeout: 5s
  retries: 5
  start_period: 10s

# Backend (FastAPI)
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 10s
  timeout: 5s
  retries: 5
```


## Common Patterns

### Database Initialization

**With Alembic migrations**:
```yaml
backend-migrate:
  build: ./apps/backend
  command: alembic upgrade head
  depends_on:
    db:
      condition: service_healthy
```

### Redis for Caching

```yaml
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
```

### Nginx Reverse Proxy

```nginx
server {
    listen 80;
    location / {
        proxy_pass http://frontend:3000;
        proxy_set_header Host $host;
    }
    location /api/ {
        proxy_pass http://backend:8000/;
        proxy_set_header Host $host;
    }
}
```


## Related Templates

- **templates/docker/docker-compose.service.yml.template** - Service definitions with ports, volumes, health checks
- **templates/apps/frontend/component.tsx.template** - Frontend containerized with hot-reload
- **templates/apps/backend/router.py.template** - Backend health check endpoints
- **templates/apps/backend/crud.py.template** - DB operations requiring PostgreSQL orchestration
- **templates/apps/backend/model.py.template** - Models guiding volume mounting strategies


## Anti-Patterns to Avoid

### 1. Exposing Sensitive Data
```yaml
# BAD: hardcoded secrets
environment:
  - DATABASE_PASSWORD=supersecret
# GOOD: environment variables
environment:
  - DATABASE_PASSWORD=${POSTGRES_PASSWORD}
```

### 2. Running as Root
```dockerfile
# BAD: running as root
CMD ["python", "app.py"]
# GOOD: non-root user
RUN addgroup -g 1001 appgroup && adduser -D -u 1001 -G appgroup appuser
USER appuser
CMD ["python", "app.py"]
```

### 3. Not Using Health Checks
```yaml
# BAD: no health check
depends_on:
  - db
# GOOD: wait for healthy
depends_on:
  db:
    condition: service_healthy
```

### 4. Inefficient Layer Caching
```dockerfile
# BAD: invalidates cache on any file change
COPY . .
RUN pnpm install
# GOOD: cache dependencies separately
COPY package.json pnpm-lock.json ./
RUN pnpm install --frozen-lockfile
COPY . .
```

### 5. Using `latest` Tags in Production
```yaml
# BAD: version drift risk
image: postgres:latest
# GOOD: reproducible builds
image: postgres:15.4-alpine
```


## Troubleshooting

- **Port in use**: `lsof -i :8000` then `kill -9 <PID>` or change port
- **DB connection refused**: Check `docker-compose ps db`, verify `POSTGRES_SERVER=db` (service name)
- **Volume permissions**: `RUN chown -R node:node /app` in Dockerfile
- **Hot reload not working**: Ensure volumes mounted, check `/app/node_modules` exclusion
- **Container crashes**: `docker-compose logs -f backend`, `docker-compose exec backend sh`


## Best Practices

- Use `.dockerignore` to exclude `node_modules`, `.git`, `__pycache__`, `.env`
- Use named volumes for persistent data (not bind mounts)
- Set resource limits in production (`deploy.resources.limits`)
- Always define health checks for services others depend on
- Maintain separate compose files: `docker-compose.yml` (dev) + `docker-compose.prod.yml`
