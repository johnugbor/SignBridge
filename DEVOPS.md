# DevOps & Infrastructure Guide

## Docker Setup

### Building Images

#### Backend Image

```bash
cd signbridge-backend

# Standard build
docker build -f docker/Dockerfile -t signbridge-backend:latest .

# Build with BuildKit (faster)
DOCKER_BUILDKIT=1 docker build -f docker/Dockerfile -t signbridge-backend:latest .

# Multi-stage production build
docker build \
  --target production \
  -f docker/Dockerfile \
  -t signbridge-backend:prod \
  .
```

#### Frontend Image

```bash
cd signbridge-frontend

docker build -t signbridge-frontend:latest .
```

### Running Containers

#### Individual Services

```bash
# Backend
docker run -p 8000:8000 \
  -e GOOGLE_CLOUD_PROJECT=dev-project \
  --name signbridge-backend \
  signbridge-backend:latest

# Frontend
docker run -p 5173:5173 \
  -e VITE_API_URL=http://localhost:8000 \
  --name signbridge-frontend \
  signbridge-frontend:latest

# Redis (session store)
docker run -p 6379:6379 \
  --name signbridge-redis \
  redis:7-alpine
```

#### Full Stack (Docker Compose)

```bash
cd signbridge-backend

# Start all services
docker-compose up

# Start in background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Remove volumes
docker-compose down -v
```

### Image Management

```bash
# List images
docker images

# Remove image
docker rmi signbridge-backend:latest

# Tag image
docker tag signbridge-backend:latest gcr.io/my-project/signbridge-backend:v1.0

# Push to registry
docker push gcr.io/my-project/signbridge-backend:v1.0
```

## Container Registry

### Google Container Registry (GCR)

```bash
# Authenticate
gcloud auth configure-docker

# Push image
docker push gcr.io/MY_PROJECT_ID/signbridge-backend:latest

# Pull image
docker pull gcr.io/MY_PROJECT_ID/signbridge-backend:latest

# View images
gcloud container images list
```

### Docker Hub

```bash
# Login
docker login

# Tag image
docker tag signbridge-backend:latest myusername/signbridge-backend:latest

# Push
docker push myusername/signbridge-backend:latest
```

## Kubernetes Deployment (Optional)

### Create Kubernetes Manifest

```yaml
# backend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: signbridge-backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: signbridge-backend
  template:
    metadata:
      labels:
        app: signbridge-backend
    spec:
      containers:
      - name: backend
        image: gcr.io/MY_PROJECT/signbridge-backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: GOOGLE_CLOUD_PROJECT
          value: "MY_PROJECT_ID"
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: signbridge-backend
spec:
  selector:
    app: signbridge-backend
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

### Deploy to Kubernetes

```bash
# Create cluster
gcloud container clusters create signbridge \
  --num-nodes=3 \
  --machine-type=e2-standard-4 \
  --region=us-central1

# Deploy
kubectl apply -f backend-deployment.yaml

# Check status
kubectl get deployments
kubectl get pods
kubectl get services

# View logs
kubectl logs -f deployment/signbridge-backend

# Scale
kubectl scale deployment signbridge-backend --replicas=5

# Update image
kubectl set image deployment/signbridge-backend \
  backend=gcr.io/MY_PROJECT/signbridge-backend:v1.1
```

## Monitoring & Logging

### Google Cloud Logging

```bash
# View backend logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=signbridge-backend" \
  --limit=50 \
  --format=json

# Create log sink (export to BigQuery)
gcloud logging sinks create signbridge-sink \
  bigquery.googleapis.com/projects/MY_PROJECT/datasets/signbridge \
  --log-filter='resource.type="cloud_run_revision"'
```

### Application Performance Monitoring (APM)

**Backend (FastAPI):**

```python
# Add instrumentation
from google.cloud import trace
from google.cloud import monitoring_v3

# Initialize tracer
tracer = trace.Client()

# Trace requests
with tracer.trace('request-processing'):
    # Your code here
    pass
```

**Frontend (React):**

```typescript
// Track performance
window.addEventListener('load', () => {
  const perfData = window.performance.timing
  const pageLoadTime = perfData.loadEventEnd - perfData.navigationStart
  console.log('Page load time:', pageLoadTime)
  
  // Send to monitoring service
  fetch('/api/metrics', {
    method: 'POST',
    body: JSON.stringify({ pageLoadTime })
  })
})
```

## Backup & Disaster Recovery

### Database Backups

```bash
# Backup Redis
docker exec signbridge-redis redis-cli BGSAVE

# Backup to cloud
gsutil cp dump.rdb gs://my-bucket/backups/redis-$(date +%Y%m%d).rdb
```

### Disaster Recovery Plan

1. **Regular Backups**: Daily automated backups to Cloud Storage
2. **Replication**: Multi-region replication for critical data
3. **Recovery Tests**: Monthly disaster recovery drills
4. **RTO/RPO**: Define Recovery Time/Point Objectives

## CI/CD Pipeline

### GitHub Actions Example

```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install backend dependencies
        run: |
          cd signbridge-backend
          pip install -r requirements.txt
      
      - name: Run backend tests
        run: |
          cd signbridge-backend
          pytest --cov=app --cov-report=xml
      
      - name: Set up Node
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      
      - name: Install frontend dependencies
        run: |
          cd signbridge-frontend
          npm ci
      
      - name: Run frontend tests
        run: |
          cd signbridge-frontend
          npm test

  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Cloud SDK
        uses: google-github-actions/setup-gcloud@v1
        with:
          project_id: ${{ secrets.GCP_PROJECT_ID }}
          service_account_key: ${{ secrets.GCP_SA_KEY }}
          export_default_credentials: true
      
      - name: Configure Docker
        run: gcloud auth configure-docker
      
      - name: Build and push backend
        run: |
          docker build -f signbridge-backend/docker/Dockerfile \
            -t gcr.io/${{ secrets.GCP_PROJECT_ID }}/signbridge-backend:${{ github.sha }} \
            signbridge-backend/
          docker push gcr.io/${{ secrets.GCP_PROJECT_ID }}/signbridge-backend:${{ github.sha }}
      
      - name: Deploy to Cloud Run
        run: |
          gcloud run deploy signbridge-backend \
            --image gcr.io/${{ secrets.GCP_PROJECT_ID }}/signbridge-backend:${{ github.sha }} \
            --platform managed \
            --region us-central1
```

## Secrets Management

### Using Google Secret Manager

```bash
# Create secret
gcloud secrets create google-cloud-key --data-file=key.json

# Grant access
gcloud secrets add-iam-policy-binding google-cloud-key \
  --member=serviceAccount:my-sa@my-project.iam.gserviceaccount.com \
  --role=roles/secretmanager.secretAccessor

# Use in Cloud Run
gcloud run deploy signbridge-backend \
  --set-secrets=GOOGLE_CREDENTIALS=google-cloud-key:latest
```

### Using .env Files (Development Only)

```bash
# Create .env
echo "GOOGLE_CLOUD_PROJECT=dev-project" > .env

# Load in Python
from dotenv import load_dotenv
load_dotenv()
```

## Load Testing

### Using Apache Bench

```bash
# Test API endpoint
ab -n 1000 -c 10 http://localhost:8000/health

# With headers
ab -n 1000 -c 10 -H "Authorization: Bearer token" http://localhost:8000/api
```

### Using k6

```javascript
import http from 'k6/http'
import { check } from 'k6'

export let options = {
  vus: 10,
  duration: '30s'
}

export default function () {
  let res = http.get('http://localhost:8000/health')
  check(res, {
    'status is 200': (r) => r.status === 200
  })
}
```

Run: `k6 run load-test.js`

---

See [DEPLOYMENT.md](./DEPLOYMENT.md) for production deployment guide.
