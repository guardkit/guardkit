# devops-specialist - Extended Reference

This file contains detailed documentation for the `devops-specialist` agent.
Load this file when you need comprehensive examples and guidance.

```bash
cat agents/devops-specialist-ext.md
```


## Implementation Patterns

### GitHub Actions CI/CD Pipeline
```yaml

# .github/workflows/ci-cd.yml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  release:
    types: [created]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}
  NODE_VERSION: '18'
  DOTNET_VERSION: '8.0'
  PYTHON_VERSION: '3.11'

jobs:
  # Code Quality Checks
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Run Super Linter
        uses: github/super-linter@v5
        env:
          DEFAULT_BRANCH: main
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          VALIDATE_ALL_CODEBASE: false
          VALIDATE_DOCKERFILE_HADOLINT: true
          VALIDATE_YAML: true
          VALIDATE_JSON: true
          VALIDATE_MARKDOWN: true
      
      - name: Security Scan with Trivy
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          format: 'sarif'
          output: 'trivy-results.sarif'
      
      - name: Upload Trivy results
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: 'trivy-results.sarif'

  # Unit Tests - Multi-language
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        project: [backend, frontend, api]
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node.js
        if: matrix.project == 'frontend'
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json
      
      - name: Setup .NET
        if: matrix.project == 'api'
        uses: actions/setup-dotnet@v4
        with:
          dotnet-version: ${{ env.DOTNET_VERSION }}
      
      - name: Setup Python
        if: matrix.project == 'backend'
        uses: actions/setup-python@v4
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: 'pip'
      
      - name: Install dependencies
        run: |
          if [ "${{ matrix.project }}" = "frontend" ]; then
            cd frontend && npm ci
          elif [ "${{ matrix.project }}" = "api" ]; then
            cd api && dotnet restore
          elif [ "${{ matrix.project }}" = "backend" ]; then
            cd backend && pip install -r requirements.txt
          fi
      
      - name: Run tests
        run: |
          if [ "${{ matrix.project }}" = "frontend" ]; then
            cd frontend && npm run test:ci
          elif [ "${{ matrix.project }}" = "api" ]; then
            cd api && dotnet test --collect:"XPlat Code Coverage"
          elif [ "${{ matrix.project }}" = "backend" ]; then
            cd backend && pytest --cov=src --cov-report=xml
          fi
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./**/coverage.xml
          flags: ${{ matrix.project }}

  # Build and Push Docker Images
  build:
    needs: [quality, test]
    runs-on: ubuntu-latest
    if: github.event_name == 'push'
    permissions:
      contents: read
      packages: write
    strategy:
      matrix:
        service: [frontend, backend, api]
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      
      - name: Log in to Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}-${{ matrix.service }}
          tags: |
            type=ref,event=branch
            type=ref,event=pr
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=sha,prefix={{branch}}-
      
      - name: Build and push Docker image
        uses: docker/build-push-action@v5
        with:
          context: ./${{ matrix.service }}
          file: ./${{ matrix.service }}/Dockerfile
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
          build-args: |
            VERSION=${{ github.sha }}
            BUILD_DATE=${{ github.event.head_commit.timestamp }}

  # Deploy to Staging
  deploy-staging:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/develop'
    environment:
      name: staging
      url: https://staging.example.com
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Kubectl
        uses: azure/setup-kubectl@v3
        with:
          version: 'latest'
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      
      - name: Update kubeconfig
        run: |
          aws eks update-kubeconfig --name staging-cluster --region us-east-1
      
      - name: Deploy with Helm
        run: |
          helm upgrade --install app ./helm \
            --namespace staging \
            --create-namespace \
            --set image.tag=${{ github.sha }} \
            --set ingress.host=staging.example.com \
            --wait --timeout 10m

  # Deploy to Production
  deploy-production:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    environment:
      name: production
      url: https://example.com
    steps:
      - uses: actions/checkout@v4
      
      - name: Deploy to Production
        run: |
          # Production deployment with approval
          echo "Deploying to production..."
```

### Docker Multi-Stage Build
```dockerfile

# Dockerfile for .NET microservice
FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /src

# Copy csproj and restore dependencies
COPY ["API/API.csproj", "API/"]
COPY ["Domain/Domain.csproj", "Domain/"]
COPY ["Infrastructure/Infrastructure.csproj", "Infrastructure/"]
RUN dotnet restore "API/API.csproj"

# Copy source code
COPY . .

# Build
WORKDIR "/src/API"
RUN dotnet build "API.csproj" -c Release -o /app/build

# Run tests
FROM build AS test
WORKDIR /src
RUN dotnet test --no-restore --verbosity normal

# Publish
FROM build AS publish
RUN dotnet publish "API.csproj" -c Release -o /app/publish /p:UseAppHost=false

# Runtime image
FROM mcr.microsoft.com/dotnet/aspnet:8.0 AS final
WORKDIR /app

# Install curl for health checks
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN addgroup --gid 1000 dotnet && \
    adduser --uid 1000 --gid 1000 --disabled-password --gecos "" dotnet

# Copy published app
COPY --from=publish --chown=dotnet:dotnet /app/publish .

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1

# Run as non-root
USER dotnet

EXPOSE 8080
ENTRYPOINT ["dotnet", "API.dll"]
```

### Kubernetes Deployment
```yaml

# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-deployment
  namespace: production
  labels:
    app: api
    version: v1
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: api
  template:
    metadata:
      labels:
        app: api
        version: v1
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8080"
        prometheus.io/path: "/metrics"
    spec:
      serviceAccountName: api-service-account
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
      containers:
      - name: api
        image: ghcr.io/myorg/api:latest
        imagePullPolicy: Always
        ports:
        - containerPort: 8080
          name: http
          protocol: TCP
        env:
        - name: ASPNETCORE_ENVIRONMENT
          value: "Production"
        - name: DATABASE_CONNECTION
          valueFrom:
            secretKeyRef:
              name: api-secrets
              key: database-connection
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
        volumeMounts:
        - name: config
          mountPath: /app/config
          readOnly: true
        - name: secrets
          mountPath: /app/secrets
          readOnly: true
      volumes:
      - name: config
        configMap:
          name: api-config
      - name: secrets
        secret:
          secretName: api-secrets
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchExpressions:
                - key: app
                  operator: In
                  values:
                  - api
              topologyKey: kubernetes.io/hostname

---
apiVersion: v1
kind: Service
metadata:
  name: api-service
  namespace: production
  labels:
    app: api
spec:
  type: ClusterIP
  ports:
  - port: 80
    targetPort: 8080
    protocol: TCP
    name: http
  selector:
    app: api

---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: api-hpa
  namespace: production
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api-deployment
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
      - type: Percent
        value: 100
        periodSeconds: 30
```

### Terraform Infrastructure
```hcl

# infrastructure/main.tf
terraform {
  required_version = ">= 1.5"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }
  }
  
  backend "s3" {
    bucket         = "terraform-state-bucket"
    key            = "production/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-state-lock"
  }
}

# EKS Cluster
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 19.0"
  
  cluster_name    = var.cluster_name
  cluster_version = "1.28"
  
  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets
  
  enable_irsa = true
  
  eks_managed_node_group_defaults = {
    instance_types = ["t3.medium"]
    
    # Security group rules
    attach_cluster_primary_security_group = true
    vpc_security_group_ids                = [aws_security_group.node_group_additional.id]
  }
  
  eks_managed_node_groups = {
    general = {
      desired_size = 3
      min_size     = 2
      max_size     = 10
      
      instance_types = ["t3.large"]
      capacity_type  = "SPOT"
      
      labels = {
        Environment = var.environment
        NodeGroup   = "general"
      }
      
      taints = []
      
      update_config = {
        max_unavailable_percentage = 33
      }
    }
  }
  
  # Cluster addons
  cluster_addons = {
    coredns = {
      most_recent = true
    }
    kube-proxy = {
      most_recent = true
    }
    vpc-cni = {
      most_recent = true
    }
    aws-ebs-csi-driver = {
      most_recent = true
    }
  }
  
  # OIDC Provider for IRSA
  cluster_endpoint_public_access = true
  
  tags = local.tags
}

# RDS Database
module "rds" {
  source = "terraform-aws-modules/rds/aws"
  
  identifier = "${var.project_name}-${var.environment}-db"
  
  engine            = "postgres"
  engine_version    = "15.4"
  instance_class    = var.db_instance_class
  allocated_storage = 100
  storage_encrypted = true
  
  db_name  = var.db_name
  username = var.db_username
  port     = "5432"
  
  vpc_security_group_ids = [aws_security_group.rds.id]
  
  maintenance_window = "Mon:00:00-Mon:03:00"
  backup_window      = "03:00-06:00"
  
  backup_retention_period = 30
  
  enabled_cloudwatch_logs_exports = ["postgresql"]
  
  create_db_subnet_group = true
  subnet_ids            = module.vpc.database_subnets
  
  family = "postgres15"
  major_engine_version = "15"
  
  deletion_protection = var.environment == "production"
  
  tags = local.tags
}

# Redis Cache
resource "aws_elasticache_cluster" "redis" {
  cluster_id           = "${var.project_name}-${var.environment}-redis"
  engine              = "redis"
  node_type           = var.redis_node_type
  num_cache_nodes     = 1
  parameter_group_name = aws_elasticache_parameter_group.redis.name
  engine_version      = "7.0"
  port                = 6379
  
  subnet_group_name = aws_elasticache_subnet_group.redis.name
  security_group_ids = [aws_security_group.redis.id]
  
  snapshot_retention_limit = var.environment == "production" ? 5 : 0
  
  tags = local.tags
}

# S3 Buckets
module "s3_bucket" {
  source = "terraform-aws-modules/s3-bucket/aws"
  
  bucket = "${var.project_name}-${var.environment}-assets"
  acl    = "private"
  
  versioning = {
    enabled = true
  }
  
  lifecycle_rule = [
    {
      id      = "archive"
      enabled = true
      
      transition = [
        {
          days          = 30
          storage_class = "STANDARD_IA"
        },
        {
          days          = 90
          storage_class = "GLACIER"
        }
      ]
      
      expiration = {
        days = 365
      }
    }
  ]
  
  server_side_encryption_configuration = {
    rule = {
      apply_server_side_encryption_by_default = {
        sse_algorithm = "AES256"
      }
    }
  }
  
  tags = local.tags
}

# CloudWatch Alarms
resource "aws_cloudwatch_metric_alarm" "high_cpu" {
  alarm_name          = "${var.project_name}-${var.environment}-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name        = "CPUUtilization"
  namespace          = "AWS/EKS"
  period             = "300"
  statistic          = "Average"
  threshold          = "80"
  alarm_description  = "This metric monitors EKS node CPU utilization"
  alarm_actions      = [aws_sns_topic.alerts.arn]
  
  dimensions = {
    ClusterName = module.eks.cluster_name
  }
}
```

### Monitoring Stack (Prometheus + Grafana)
```yaml

# monitoring/prometheus-values.yaml
prometheus:
  prometheusSpec:
    retention: 30d
    resources:
      requests:
        cpu: 500m
        memory: 2Gi
      limits:
        cpu: 2000m
        memory: 4Gi
    
    storageSpec:
      volumeClaimTemplate:
        spec:
          accessModes: ["ReadWriteOnce"]
          resources:
            requests:
              storage: 50Gi
    
    serviceMonitorSelectorNilUsesHelmValues: false
    podMonitorSelectorNilUsesHelmValues: false
    ruleSelectorNilUsesHelmValues: false
    
    additionalScrapeConfigs:
    - job_name: 'kubernetes-pods'
      kubernetes_sd_configs:
      - role: pod
      relabel_configs:
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: true
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
        action: replace
        target_label: __metrics_path__
        regex: (.+)
      - source_labels: [__address__, __meta_kubernetes_pod_annotation_prometheus_io_port]
        action: replace
        regex: ([^:]+)(?::\d+)?;(\d+)
        replacement: $1:$2
        target_label: __address__

grafana:
  enabled: true
  adminPassword: ${GRAFANA_ADMIN_PASSWORD}
  
  persistence:
    enabled: true
    size: 10Gi
  
  datasources:
    datasources.yaml:
      apiVersion: 1
      datasources:
      - name: Prometheus
        type: prometheus
        url: http://prometheus-server:9090
        isDefault: true
      - name: Loki
        type: loki
        url: http://loki:3100
      - name: Elasticsearch
        type: elasticsearch
        url: http://elasticsearch:9200
  
  dashboardProviders:
    dashboardproviders.yaml:
      apiVersion: 1
      providers:
      - name: 'default'
        orgId: 1
        folder: ''
        type: file
        disableDeletion: false
        updateIntervalSeconds: 10
        options:
          path: /var/lib/grafana/dashboards/default
  
  dashboards:
    default:
      kubernetes-cluster:
        gnetId: 7249
        revision: 1
        datasource: Prometheus
      node-exporter:
        gnetId: 1860
        revision: 27
        datasource: Prometheus

alertmanager:
  enabled: true
  config:
    global:
      resolve_timeout: 5m
    
    route:
      group_by: ['alertname', 'cluster', 'service']
      group_wait: 10s
      group_interval: 10s
      repeat_interval: 12h
      receiver: 'team-notifications'
      routes:
      - match:
          severity: critical
        receiver: 'pagerduty'
      - match:
          severity: warning
        receiver: 'slack'
    
    receivers:
    - name: 'team-notifications'
      webhook_configs:
      - url: ${WEBHOOK_URL}
    
    - name: 'pagerduty'
      pagerduty_configs:
      - service_key: ${PAGERDUTY_KEY}
    
    - name: 'slack'
      slack_configs:
      - api_url: ${SLACK_WEBHOOK}
        channel: '#alerts'
```

### GitOps with ArgoCD
```yaml

# argocd/application.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: production-app
  namespace: argocd
  finalizers:
    - resources-finalizer.argocd.argoproj.io
spec:
  project: default
  
  source:
    repoURL: https://github.com/myorg/k8s-manifests
    targetRevision: main
    path: production
    
    helm:
      valueFiles:
      - values-production.yaml
      
      parameters:
      - name: image.tag
        value: ${ARGOCD_APP_REVISION}
  
  destination:
    server: https://kubernetes.default.svc
    namespace: production
  
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
      allowEmpty: false
    
    syncOptions:
    - CreateNamespace=true
    - PrunePropagationPolicy=foreground
    - PruneLast=true
    
    retry:
      limit: 5
      backoff:
        duration: 5s
        factor: 2
        maxDuration: 3m
  
  revisionHistoryLimit: 3
  
  ignoreDifferences:
  - group: apps
    kind: Deployment
    jsonPointers:
    - /spec/replicas
  
  info:
  - name: 'Environment'
    value: 'Production'
  - name: 'Team'
    value: 'Platform'
```

### CI/CD
1. Implement feature branch workflows
2. Automate everything possible
3. Use semantic versioning
4. Implement rollback strategies
5. Monitor deployment metrics
6. Use blue-green or canary deployments

### Infrastructure
1. Use Infrastructure as Code
2. Implement least privilege access
3. Encrypt data at rest and in transit
4. Use managed services when possible
5. Implement disaster recovery
6. Monitor costs continuously

### Containerization
1. Use multi-stage builds
2. Run as non-root user
3. Scan for vulnerabilities
4. Keep images minimal
5. Use specific version tags
6. Implement health checks

### Monitoring
1. Implement the four golden signals
2. Set up meaningful alerts
3. Use distributed tracing
4. Centralize logging
5. Create runbooks
6. Implement SLIs/SLOs


## Related Templates

This agent leverages the following DevOps templates from the codebase:

### Primary Templates

1. **nextjs-fullstack/templates/workflows-ci.yml.template**
   - **Relevance**: Complete GitHub Actions CI/CD pipeline for Next.js applications
   - **Patterns**: Multi-stage jobs (lint, type-check, test, build), dependency caching, parallel execution
   - **Technologies**: GitHub Actions, Node.js, pnpm, TypeScript
   - **Use Cases**: Automated testing, build validation, deployment preparation

2. **react-fastapi-monorepo/templates/docker/docker-compose.service.yml.template**
   - **Relevance**: Production-ready Docker Compose service configuration
   - **Patterns**: Health checks, resource limits, restart policies, networking
   - **Technologies**: Docker Compose, containerization
   - **Use Cases**: Local development, service orchestration, multi-container deployments

### How to Use These Templates

```bash

# Generate GitHub Actions workflow
/task-work --template=nextjs-fullstack --mode=ci-workflow

# Generate Docker Compose configuration
/task-work --template=react-fastapi-monorepo --mode=docker-services
```

---


## Template Code Examples

### GitHub Actions CI/CD

#### ✅ DO: Parallel Job Execution with Dependency Caching

```yaml

# Based on: nextjs-fullstack/templates/workflows-ci.yml.template
name: CI Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  # Install dependencies once, cache for all jobs
  setup:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'pnpm'

      - name: Install dependencies
        run: pnpm install --frozen-lockfile

      - name: Cache node_modules
        uses: actions/cache@v3
        with:
          path: node_modules
          key: ${{ runner.os }}-node-${{ hashFiles('**/pnpm-lock.yaml') }}

  # Run linting in parallel with type-checking
  lint:
    needs: setup
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Restore cache
        uses: actions/cache@v3
        with:
          path: node_modules
          key: ${{ runner.os }}-node-${{ hashFiles('**/pnpm-lock.yaml') }}

      - name: Run ESLint
        run: pnpm lint

      - name: Run Prettier
        run: pnpm format:check

  type-check:
    needs: setup
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Restore cache
        uses: actions/cache@v3
        with:
          path: node_modules
          key: ${{ runner.os }}-node-${{ hashFiles('**/pnpm-lock.yaml') }}

      - name: TypeScript type checking
        run: pnpm type-check

  test:
    needs: setup
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Restore cache
        uses: actions/cache@v3
        with:
          path: node_modules
          key: ${{ runner.os }}-node-${{ hashFiles('**/pnpm-lock.yaml') }}

      - name: Run tests
        run: pnpm test:ci

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage/coverage-final.json

  build:
    needs: [lint, type-check, test]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Restore cache
        uses: actions/cache@v3
        with:
          path: node_modules
          key: ${{ runner.os }}-node-${{ hashFiles('**/pnpm-lock.yaml') }}

      - name: Build application
        run: pnpm build
        env:
          NODE_ENV: production

      - name: Upload build artifacts
        uses: actions/upload-artifact@v3
        with:
          name: build-output
          path: .next/
          retention-days: 7
```

**Why this works**:
- **Parallel execution**: lint, type-check, and test run simultaneously after setup
- **Dependency caching**: node_modules cached and restored across jobs (3-5x faster builds)
- **Build artifacts**: .next/ output saved for deployment stage
- **Fail-fast**: Build only runs if all quality checks pass

#### ❌ DON'T: Serial Job Execution Without Caching

```yaml

# Anti-pattern: Everything runs sequentially, no caching
name: Slow CI Pipeline

on: [push]

jobs:
  ci:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      # Install for linting (5-10 minutes)
      - name: Install dependencies
        run: pnpm install

      - name: Lint
        run: pnpm lint

      # Install AGAIN for type-checking (5-10 minutes)
      - name: Install dependencies
        run: pnpm install

      - name: Type check
        run: pnpm type-check

      # Install AGAIN for testing (5-10 minutes)
      - name: Install dependencies
        run: pnpm install

      - name: Test
        run: pnpm test

      # Install AGAIN for building (5-10 minutes)
      - name: Install dependencies
        run: pnpm install

      - name: Build
        run: pnpm build
```

**Why this fails**:
- **15-40 minutes wasted**: Installing dependencies 4 times instead of once
- **No parallelization**: Lint, type-check, test could run simultaneously
- **No caching**: Every run downloads packages from scratch
- **Single point of failure**: One step fails, whole pipeline restarts from beginning

---

### Docker Compose Service Configuration

#### ✅ DO: Production-Ready Service with Health Checks

```yaml

# Based on: react-fastapi-monorepo/templates/docker/docker-compose.service.yml.template
version: '3.8'

services:
  api:
    image: my-api:latest
    container_name: api-service
    restart: unless-stopped

    # Resource limits prevent runaway containers
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M

    # Health check ensures service is actually ready
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - LOG_LEVEL=${LOG_LEVEL:-info}

    # Use secrets for sensitive data
    secrets:
      - db_password
      - api_key

    networks:
      - backend

    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started

    # Non-root user for security
    user: "1000:1000"

    volumes:
      - ./logs:/app/logs:rw
      - app-data:/app/data:rw

  postgres:
    image: postgres:16-alpine
    container_name: postgres-db
    restart: unless-stopped

    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5

    environment:
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD_FILE=/run/secrets/db_password
      - POSTGRES_DB=${POSTGRES_DB}

    secrets:
      - db_password

    volumes:
      - postgres-data:/var/lib/postgresql/data

    networks:
      - backend

  redis:
    image: redis:7-alpine
    container_name: redis-cache
    restart: unless-stopped

    command: redis-server --requirepass ${REDIS_PASSWORD} --maxmemory 256mb --maxmemory-policy allkeys-lru

    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5

    networks:
      - backend

networks:
  backend:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16

volumes:
  postgres-data:
    driver: local
  app-data:
    driver: local

secrets:
  db_password:
    file: ./secrets/db_password.txt
  api_key:
    file: ./secrets/api_key.txt
```

**Why this works**:
- **Health checks**: Services won't receive traffic until actually ready
- **Resource limits**: Prevents one container from consuming all host resources
- **Secrets management**: Sensitive data never in environment variables or code
- **Dependency ordering**: API waits for postgres to be healthy, not just started
- **Non-root user**: Reduces attack surface if container is compromised
- **Restart policies**: Automatic recovery from crashes

#### ❌ DON'T: Insecure Service Configuration

```yaml

# Anti-pattern: Multiple security and reliability issues
version: '3.8'

services:
  api:
    image: my-api:latest
    restart: "no"  # Won't recover from crashes

    # No resource limits - can consume all host memory

    # No health check - traffic routed even if service is broken

    environment:
      # Hardcoded secrets in plain text
      - DATABASE_URL=postgres://admin:password123@postgres:5432/mydb
      - API_KEY=secret-key-12345
      - AWS_SECRET_KEY=AKIAIOSFODNN7EXAMPLE

    # Running as root user (security risk)

    depends_on:
      # Just checks if container started, not if postgres is ready
      - postgres

  postgres:
    image: postgres:16-alpine
    # No restart policy - manual intervention needed after crash

    environment:
      # Plain text password
      - POSTGRES_PASSWORD=password123

    # No volume - data lost on container restart
```

**Why this fails**:
- **Hardcoded secrets**: Credentials visible in logs, process lists, container inspect
- **No health checks**: Load balancer sends traffic to broken services
- **No resource limits**: One container can OOM-kill the entire host
- **Root user**: If compromised, attacker has full container privileges
- **No restart policy**: Manual intervention needed for every crash
- **No data persistence**: Database data lost on container restart

---

### Multi-Stage Docker Builds

#### ✅ DO: Optimized Multi-Stage Build with Layer Caching

```dockerfile

# Stage 1: Base image with dependencies
FROM node:20-alpine AS base
WORKDIR /app

# Install dependencies in separate layer for caching
COPY package.json pnpm-lock.yaml ./
RUN corepack enable pnpm && \
    pnpm install --frozen-lockfile --prod=false

# Stage 2: Build the application
FROM base AS builder
WORKDIR /app

# Copy source code
COPY . .

# Build with production optimizations
RUN pnpm build && \
    pnpm prune --prod

# Stage 3: Production runtime
FROM node:20-alpine AS runner
WORKDIR /app

# Create non-root user
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# Copy only production artifacts
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nodejs /app/public ./public

# Switch to non-root user
USER nextjs

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD node -e "require('http').get('http://localhost:3000/api/health', (r) => {process.exit(r.statusCode === 200 ? 0 : 1)})"

ENV NODE_ENV=production
ENV PORT=3000

CMD ["node", "server.js"]
```

**Why this works**:
- **Multi-stage**: Final image only contains production runtime (90% smaller)
- **Layer caching**: Dependencies cached separately from source code
- **Non-root user**: Security best practice
- **Health check**: Container orchestration can detect failures
- **Production-only deps**: Development dependencies excluded from final image

#### ❌ DON'T: Single-Stage Build with Security Issues

```dockerfile

# Anti-pattern: Everything in one stage, running as root
FROM node:20

WORKDIR /app

# Copy everything (including .git, node_modules, .env)
COPY . .

# Install all dependencies including devDependencies
RUN npm install

# Build application
RUN npm run build

# Running as root user

# No health check

# Image contains source code, tests, build tools, secrets

EXPOSE 3000

CMD ["npm", "start"]
```

**Why this fails**:
- **500MB+ larger image**: Contains dev dependencies, source code, build tools
- **Security risks**: Running as root, may include secrets in .env files
- **No layer caching**: Entire rebuild on any file change
- **Slower deployments**: Larger images take longer to push/pull
- **No health check**: No way to detect service failures

---

### CI/CD Pipeline for Monorepos

#### ✅ DO: Selective Job Execution with Path Filters

```yaml

# Optimized monorepo CI - only test changed services
name: Monorepo CI

on:
  pull_request:
    branches: [main]

jobs:
  detect-changes:
    runs-on: ubuntu-latest
    outputs:
      api: ${{ steps.filter.outputs.api }}
      web: ${{ steps.filter.outputs.web }}
      shared: ${{ steps.filter.outputs.shared }}
    steps:
      - uses: actions/checkout@v4
      - uses: dorny/paths-filter@v2
        id: filter
        with:
          filters: |
            api:
              - 'services/api/**'
              - 'packages/shared/**'
            web:
              - 'apps/web/**'
              - 'packages/shared/**'
            shared:
              - 'packages/shared/**'

  test-api:
    needs: detect-changes
    if: needs.detect-changes.outputs.api == 'true'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        run: |
          cd services/api
          pip install -r requirements.txt
          pip install -r requirements-dev.txt

      - name: Run API tests
        run: |
          cd services/api
          pytest --cov=. --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          flags: api

  test-web:
    needs: detect-changes
    if: needs.detect-changes.outputs.web == 'true'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'pnpm'

      - name: Install dependencies
        run: |
          cd apps/web
          pnpm install --frozen-lockfile

      - name: Run web tests
        run: |
          cd apps/web
          pnpm test:ci

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          flags: web

  build-images:
    needs: [test-api, test-web]
    if: always() && !cancelled()
    runs-on: ubuntu-latest
    strategy:
      matrix:
        service: [api, web]
    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to Container Registry
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          file: ./services/${{ matrix.service }}/Dockerfile
          push: true
          tags: ghcr.io/${{ github.repository }}/${{ matrix.service }}:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

**Why this works**:
- **Path filtering**: Only tests services that changed (saves 70% CI time)
- **Parallel execution**: API and web tests run simultaneously
- **Build caching**: Docker layer cache persisted in GitHub Actions cache
- **Matrix builds**: Multiple services built in parallel
- **Conditional execution**: Skips unnecessary jobs

---

### Secret Management

#### ✅ DO: Secure Secret Handling with External Vault

```yaml

# GitHub Actions with HashiCorp Vault integration
name: Secure Deployment

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      id-token: write  # Required for OIDC
      contents: read
    steps:
      - uses: actions/checkout@v4

      # Authenticate with Vault using OIDC (no long-lived secrets)
      - name: Import secrets from Vault
        uses: hashicorp/vault-action@v2
        with:
          url: https://vault.example.com
          method: jwt
          role: github-actions
          secrets: |
            secret/data/production/db password | DB_PASSWORD ;
            secret/data/production/api key | API_KEY ;
            secret/data/production/aws access_key | AWS_ACCESS_KEY_ID ;
            secret/data/production/aws secret_key | AWS_SECRET_ACCESS_KEY

      - name: Deploy to production
        run: |
          # Secrets available as environment variables
          # Never echoed or logged
          ./deploy.sh
        env:
          DB_PASSWORD: ${{ env.DB_PASSWORD }}
          API_KEY: ${{ env.API_KEY }}

      # Secrets automatically masked in logs
      - name: Verify deployment
        run: |
          echo "Deployment completed"
          # This would show: "Password: ***" in logs
          echo "Password: $DB_PASSWORD"
```

**Dockerfile with secret mounting**:
```dockerfile

# Use BuildKit secret mounts (never stored in layers)
FROM node:20-alpine

WORKDIR /app

COPY package.json pnpm-lock.yaml ./

# Mount secret during build, not stored in image
RUN --mount=type=secret,id=npmrc,dst=/root/.npmrc \
    corepack enable pnpm && \
    pnpm install --frozen-lockfile

COPY . .

RUN pnpm build

# Final image contains no secrets
```

**Build with secrets**:
```bash

# Secret provided at build time, not in Dockerfile
docker buildx build \
  --secret id=npmrc,src=$HOME/.npmrc \
  -t my-app:latest .
```

**Why this works**:
- **OIDC authentication**: No long-lived credentials in GitHub
- **Secret rotation**: Vault secrets can be rotated without code changes
- **Automatic masking**: GitHub Actions masks secrets in logs
- **BuildKit mounts**: Secrets never stored in Docker image layers
- **Audit trail**: Vault logs all secret access

---

### Kubernetes Deployment Strategies

#### ✅ DO: Blue-Green Deployment with Health Checks

```yaml

# Blue-Green deployment for zero-downtime updates
apiVersion: v1
kind: Service
metadata:
  name: my-app
  namespace: production
spec:
  selector:
    app: my-app
    version: blue  # Switch to 'green' for cutover
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8080
  type: LoadBalancer

---

# Blue deployment (current production)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app-blue
  namespace: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: my-app
      version: blue
  template:
    metadata:
      labels:
        app: my-app
        version: blue
    spec:
      containers:
      - name: app
        image: my-app:v1.5.0
        ports:
        - containerPort: 8080

        # Liveness probe - restart if unhealthy
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3

        # Readiness probe - remove from service if not ready
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 3
          successThreshold: 1
          failureThreshold: 2

        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"

        env:
        - name: DB_HOST
          valueFrom:
            secretKeyRef:
              name: database-config
              key: host

        # Graceful shutdown
        lifecycle:
          preStop:
            exec:
              command: ["/bin/sh", "-c", "sleep 15"]
```

**Deployment script**:
```bash
#!/bin/bash
set -e

# Deploy green environment
kubectl apply -f deployment-green.yaml

# Wait for green to be healthy
kubectl wait --for=condition=available --timeout=300s \
  deployment/my-app-green -n production

# Run smoke tests against green
./smoke-tests.sh http://my-app-green.production.svc.cluster.local

# Switch traffic to green
kubectl patch service my-app -n production \
  -p '{"spec":{"selector":{"version":"green"}}}'

echo "Traffic switched to green. Monitor for 15 minutes."
echo "To rollback: kubectl patch service my-app -n production -p '{\"spec\":{\"selector\":{\"version\":\"blue\"}}}'"
```

**Why this works**:
- **Zero downtime**: New version deployed alongside old version
- **Instant rollback**: Switch service selector back to blue if issues found
- **Health checks**: Traffic only sent to healthy pods
- **Resource limits**: Prevents runaway pods from affecting cluster
- **Graceful shutdown**: 15-second sleep allows in-flight requests to complete

---

### Terraform Infrastructure as Code

#### ✅ DO: Modular Infrastructure with Remote State

```hcl

# terraform/main.tf
terraform {
  required_version = ">= 1.5.0"

  backend "s3" {
    bucket         = "my-terraform-state"
    key            = "production/terraform.tfstate"
    region         = "us-west-2"
    encrypt        = true
    dynamodb_table = "terraform-locks"

    # State versioning enabled for rollback
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Environment = var.environment
      ManagedBy   = "Terraform"
      Project     = "my-app"
    }
  }
}

# Use modules for reusability
module "vpc" {
  source = "./modules/vpc"

  environment         = var.environment
  vpc_cidr            = var.vpc_cidr
  availability_zones  = var.availability_zones
  enable_nat_gateway  = true
  enable_vpn_gateway  = false
}

module "eks_cluster" {
  source = "./modules/eks"

  cluster_name       = "${var.environment}-cluster"
  cluster_version    = "1.28"
  vpc_id             = module.vpc.vpc_id
  subnet_ids         = module.vpc.private_subnet_ids
  node_groups        = var.node_groups

  depends_on = [module.vpc]
}

module "rds_database" {
  source = "./modules/rds"

  identifier          = "${var.environment}-postgres"
  engine              = "postgres"
  engine_version      = "16.1"
  instance_class      = var.db_instance_class
  allocated_storage   = var.db_allocated_storage

  vpc_id             = module.vpc.vpc_id
  subnet_ids         = module.vpc.database_subnet_ids

  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "Mon:04:00-Mon:05:00"

  # Secrets stored in AWS Secrets Manager
  master_username = "dbadmin"
  master_password = data.aws_secretsmanager_secret_version.db_password.secret_string

  deletion_protection = var.environment == "production" ? true : false

  depends_on = [module.vpc]
}

# Output for other systems
output "eks_cluster_endpoint" {
  value       = module.eks_cluster.cluster_endpoint
  description = "EKS cluster API endpoint"
  sensitive   = true
}

output "rds_endpoint" {
  value       = module.rds_database.endpoint
  description = "RDS database endpoint"
  sensitive   = true
}
```

**CI/CD integration**:
```yaml

# .github/workflows/terraform.yml
name: Terraform

on:
  pull_request:
    paths:
      - 'terraform/**'
  push:
    branches: [main]
    paths:
      - 'terraform/**'

jobs:
  terraform:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read
      pull-requests: write
    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/github-actions
          aws-region: us-west-2

      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: 1.5.7

      - name: Terraform fmt
        run: terraform fmt -check -recursive

      - name: Terraform init
        run: terraform init

      - name: Terraform validate
        run: terraform validate

      - name: Terraform plan
        id: plan
        run: terraform plan -no-color -out=tfplan

      - name: Post plan to PR
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v7
        with:
          script: |
            const output = `#### Terraform Plan 📖
            \`\`\`
            ${{ steps.plan.outputs.stdout }}
            \`\`\`
            `;
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: output
            })

      - name: Terraform apply
        if: github.ref == 'refs/heads/main' && github.event_name == 'push'
        run: terraform apply -auto-approve tfplan
```

**Why this works**:
- **Remote state**: Team can collaborate, state locked during changes
- **Modular design**: VPC, EKS, RDS modules reusable across environments
- **Version control**: Infrastructure changes tracked in Git
- **Plan before apply**: Review changes in PR before production
- **Environment protection**: Production has deletion protection

---


## Template Best Practices

### CI/CD Pipeline Design

1. **Parallel Job Execution**
   - Run independent checks (lint, type-check, test) simultaneously
   - Use `needs` to define dependencies between jobs
   - Reduces total pipeline time by 50-70%

2. **Dependency Caching**
   - Cache `node_modules`, pip packages, Docker layers
   - Use lock file hashes as cache keys (`pnpm-lock.yaml`, `requirements.txt`)
   - First job installs dependencies, subsequent jobs restore from cache

3. **Artifact Management**
   - Upload build artifacts (binaries, Docker images, test reports)
   - Retention policies: 7 days for branches, 90 days for releases
   - Use artifacts between jobs to avoid rebuilding

4. **Fail-Fast with Quality Gates**
   - Build only runs if lint, type-check, and test pass
   - Use branch protection rules to enforce status checks
   - Prevent broken code from reaching production

5. **Matrix Builds**
   - Test across multiple Node/Python versions
   - Build for multiple architectures (amd64, arm64)
   - Parallel execution with `strategy.matrix`

### Docker Image Optimization

1. **Multi-Stage Builds**
   - Build stage: Install all dependencies, compile code
   - Runtime stage: Only copy production artifacts
   - Results in 10x smaller images (500MB → 50MB)

2. **Layer Caching**
   - Copy dependency files first, then source code
   - Dependencies cached until `package.json` changes
   - Source changes don't invalidate dependency layers

3. **BuildKit Features**
   - `--mount=type=cache` for package manager caches
   - `--mount=type=secret` for credentials (never in layers)
   - `--platform` for multi-architecture builds

4. **Base Image Selection**
   - Use Alpine Linux for smallest images (5MB base)
   - Use Distroless for security (no shell, no package manager)
   - Pin specific versions, not `latest`

5. **Security Scanning**
   - Scan images with Trivy, Snyk, or Grype
   - Fail builds on critical/high vulnerabilities
   - Scan both base images and final artifacts

### Secret Management

1. **Never Commit Secrets**
   - Use `.gitignore` for `.env`, `secrets/`, `*.key`
   - Scan commits with GitGuardian or TruffleHog
   - Rotate any accidentally committed secrets immediately

2. **External Secret Storage**
   - HashiCorp Vault, AWS Secrets Manager, Azure Key Vault
   - Secrets rotated independently of code deployments
   - Audit logs for all secret access

3. **GitHub Actions Best Practices**
   - Use OIDC for cloud provider authentication (no keys)
   - Store secrets in GitHub Secrets (encrypted at rest)
   - Use `environment` with protection rules for production

4. **Docker Secret Handling**
   - Use BuildKit secret mounts (`--secret id=...`)
   - Use Docker Compose secrets (file-based)
   - Never use `ENV` for secrets (visible in `docker inspect`)

5. **Kubernetes Secrets**
   - Use External Secrets Operator to sync from Vault
   - Encrypt secrets at rest (KMS integration)
   - Use RBAC to restrict secret access

### Infrastructure as Code

1. **State Management**
   - Always use remote state (S3, Terraform Cloud, Azure Blob)
   - Enable state locking (DynamoDB, Consul)
   - Version state files for rollback capability

2. **Modular Design**
   - Create reusable modules for VPC, EKS, RDS, etc.
   - Test modules independently
   - Publish internal modules to registry

3. **Environment Separation**
   - Separate state files per environment
   - Use workspaces or separate directories
   - Never share infrastructure between dev/prod

4. **Change Review Process**
   - `terraform plan` on every PR
   - Manual approval required for `apply`
   - Slack/Teams notifications for infrastructure changes

5. **Drift Detection**
   - Run `terraform plan` on schedule (daily)
   - Alert on drift (manual changes outside Terraform)
   - Auto-remediate or require manual review

### Monitoring and Observability

1. **Health Checks Everywhere**
   - HTTP endpoints: `/health`, `/ready`
   - Container health checks in Dockerfile
   - Kubernetes liveness and readiness probes

2. **Structured Logging**
   - JSON logs with consistent fields (timestamp, level, request_id)
   - Centralize logs (CloudWatch, Datadog, Splunk)
   - Set up log-based alerts (error rate, latency spikes)

3. **Metrics Collection**
   - Prometheus for scraping application metrics
   - Expose metrics at `/metrics` endpoint
   - Dashboard in Grafana for visualization

4. **Distributed Tracing**
   - Instrument code with OpenTelemetry
   - Send traces to Jaeger, Zipkin, or Datadog
   - Correlate logs, metrics, and traces with request ID

5. **Alerting Strategy**
   - SLO-based alerts (error rate, latency, availability)
   - Tiered severity: critical (page), high (ticket), low (aggregate)
   - Runbooks linked from alert descriptions

---


## Template Anti-Patterns

### ❌ Running Tests Serially

**Problem**: Tests run one after another, wasting time

```yaml

# Anti-pattern
jobs:
  test:
    steps:
      - run: npm run lint
      - run: npm run type-check
      - run: npm run test
      - run: npm run build
```

**Solution**: Use parallel jobs
```yaml
jobs:
  lint:
    steps:
      - run: npm run lint

  type-check:
    steps:
      - run: npm run type-check

  test:
    steps:
      - run: npm run test
```

**Impact**: 15-minute pipeline → 5-minute pipeline

---

### ❌ No Dependency Caching

**Problem**: Installing dependencies from scratch every time

```yaml

# Anti-pattern
- run: npm install
- run: npm test
```

**Solution**: Cache dependencies
```yaml
- uses: actions/cache@v3
  with:
    path: node_modules
    key: ${{ hashFiles('package-lock.json') }}
- run: npm install
- run: npm test
```

**Impact**: 5-minute installs → 30-second cache restore

---

### ❌ Hardcoded Secrets

**Problem**: Credentials in code, config files, or environment variables

```yaml

# Anti-pattern
env:
  DATABASE_URL: postgres://admin:password123@db:5432/mydb
  API_KEY: sk_live_abc123
```

**Solution**: Use secret management
```yaml
env:
  DATABASE_URL: ${{ secrets.DATABASE_URL }}
  API_KEY: ${{ secrets.API_KEY }}
```

**Impact**: Prevents credential leaks, enables rotation

---

### ❌ Running Containers as Root

**Problem**: Security vulnerability if container is compromised

```dockerfile

# Anti-pattern
FROM node:20
COPY . /app
CMD ["node", "server.js"]
```

**Solution**: Create and use non-root user
```dockerfile
FROM node:20
RUN adduser --system --uid 1001 nodejs
USER nodejs
COPY --chown=nodejs:nodejs . /app
CMD ["node", "server.js"]
```

**Impact**: Limits damage from container escape or exploit

---

### ❌ Missing Health Checks

**Problem**: Load balancer sends traffic to broken services

```yaml

# Anti-pattern
services:
  api:
    image: my-api:latest
    ports:
      - "8000:8000"
```

**Solution**: Add health checks
```yaml
services:
  api:
    image: my-api:latest
    ports:
      - "8000:8000"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

**Impact**: Prevents 503 errors during deployments

---

### ❌ No Rollback Strategy

**Problem**: Can't quickly revert broken deployments

```bash

# Anti-pattern
kubectl set image deployment/my-app app=my-app:latest
```

**Solution**: Blue-green or canary deployments
```bash

# Deploy to green environment
kubectl apply -f deployment-green.yaml
kubectl wait --for=condition=available deployment/my-app-green

# Switch traffic
kubectl patch service my-app -p '{"spec":{"selector":{"version":"green"}}}'

# Rollback if needed
kubectl patch service my-app -p '{"spec":{"selector":{"version":"blue"}}}'
```

**Impact**: 30-minute outages → instant rollback

---

### ❌ Single-Stage Docker Builds

**Problem**: Final image contains build tools, source code, dev dependencies

```dockerfile

# Anti-pattern
FROM node:20
COPY . .
RUN npm install && npm run build
CMD ["npm", "start"]
```

**Solution**: Multi-stage build
```dockerfile
FROM node:20 AS builder
COPY . .
RUN npm install && npm run build

FROM node:20-alpine
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
CMD ["node", "dist/server.js"]
```

**Impact**: 800MB image → 80MB image (10x smaller)

---

### ❌ Using `latest` Tag

**Problem**: Unpredictable deployments, can't rollback

```yaml

# Anti-pattern
image: my-app:latest
```

**Solution**: Use semantic versioning or commit SHA
```yaml
image: my-app:v1.5.0

# or
image: my-app:sha-a3f2c1d
```

**Impact**: Reproducible deployments, clear rollback targets

---

### ❌ No Resource Limits

**Problem**: One container can consume all host resources

```yaml

# Anti-pattern
services:
  api:
    image: my-api:latest
```

**Solution**: Set resource limits
```yaml
services:
  api:
    image: my-api:latest
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M
```

**Impact**: Prevents OOM crashes, predictable performance

---

### ❌ Monolithic CI/CD Files

**Problem**: 1000+ line workflow file, hard to maintain

```yaml

# Anti-pattern: everything in one file
name: Monolithic Pipeline
jobs:
  all:
    steps:
      - run: lint
      - run: test-api
      - run: test-web
      - run: test-mobile
      - run: build-api
      - run: build-web
      - run: deploy
```

**Solution**: Split by responsibility
```yaml

# .github/workflows/ci.yml
name: CI
jobs:
  lint: ...
  test: ...

# .github/workflows/deploy.yml
name: Deploy
jobs:
  deploy: ...
```

**Impact**: Easier to maintain, reusable workflows


## Extended Documentation

For detailed examples, patterns, and implementation guides, load the extended documentation:

```bash
cat devops-specialist-ext.md
```

Or in Claude Code:
```
Please read devops-specialist-ext.md for detailed examples.
```
