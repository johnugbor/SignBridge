# Deployment Guide for SignBridge Live

## Local Development Setup

### Quick Start with Docker Compose

The easiest way to get the entire stack running locally:

```bash
cd signbridge-backend
docker-compose up --build
```

This will start:
- **Backend API**: http://localhost:8000
- **Frontend**: http://localhost:5173 (if configured in docker-compose)
- **Redis** (optional, for session storage)

### Manual Setup (Without Docker)

#### 1. Backend Setup

```bash
cd signbridge-backend

# Create Python virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your Google Cloud credentials

# Run development server
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### 2. Frontend Setup

```bash
cd signbridge-frontend

# Install Node dependencies
npm install

# Set up environment variables
cp .env.example .env

# Start Vite dev server
npm run dev
```

Access the application at: http://localhost:5173

## Building for Production

### Backend Docker Image

```bash
cd signbridge-backend

# Build the Docker image
docker build -f docker/Dockerfile -t our-registry/signbridge-backend:v1.0.0 .

# Push to container registry
docker push our-registry/signbridge-backend:v1.0.0
```

### Frontend Build

```bash
cd signbridge-frontend

# Create optimized production build
npm run build

# Preview the build locally
npm run preview

# Output is in `dist/` directory
```

To serve the frontend, copy the `dist/` folder contents to a web server.

## Google Cloud Deployment

### Prerequisites

- Google Cloud project with billing enabled
- `gcloud` CLI installed and configured
- Vertex AI API enabled
- Cloud Run API enabled
- Cloud Storage bucket for assets

### Deploy Backend to Cloud Run

```bash
cd signbridge-backend

# Set project ID
export PROJECT_ID="your-gcp-project-id"
export REGION="us-central1"

# Authenticate with Google Cloud
gcloud auth login
gcloud config set project $PROJECT_ID

# Build and push image to Container Registry
gcloud builds submit --tag gcr.io/$PROJECT_ID/signbridge-backend

# Deploy to Cloud Run
gcloud run deploy signbridge-backend \
  --image gcr.io/$PROJECT_ID/signbridge-backend \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --set-env-vars=GOOGLE_CLOUD_PROJECT=$PROJECT_ID \
  --set-env-vars=ENVIRONMENT=production \
  --memory 2Gi \
  --cpu 2 \
  --concurrency 100 \
  --timeout 3600
```

### Deploy Frontend to Cloud Storage + Cloud CDN

```bash
cd signbridge-frontend

# Build the frontend
npm run build

# Create a Cloud Storage bucket
gsutil mb -l $REGION gs://$PROJECT_ID-frontend/

# Upload frontend files (with caching headers)
gsutil -m cp -r dist/* gs://$PROJECT_ID-frontend/

# Set appropriate cache headers
gsutil -m setmeta -h "Cache-Control:public, max-age=3600" gs://$PROJECT_ID-frontend/*.html
gsutil -m setmeta -h "Cache-Control:public, max-age=31536000" gs://$PROJECT_ID-frontend/*.js
gsutil -m setmeta -h "Cache-Control:public, max-age=31536000" gs://$PROJECT_ID-frontend/*.css

# Make bucket public
gsutil iam ch serviceAccount:$PROJECT_ID@appspot.gserviceaccount.com:objectViewer gs://$PROJECT_ID-frontend/

# Enable Cloud CDN (optional, via Google Cloud Console)
# Cloud Load Balancing > Enable Cloud CDN on the bucket
```

### Configure CORS

```bash
# Create a CORS JSON file
cat > cors.json << EOF
[
  {
    "origin": ["*"],
    "method": ["GET", "HEAD", "DELETE"],
    "responseHeader": ["Content-Type"],
    "maxAgeSeconds": 3600
  }
]
EOF

# Apply CORS configuration
gsutil cors set cors.json gs://$PROJECT_ID-frontend/
```

### Set Up Cloud Run Services Connection

Update the frontend `.env` to point to the deployed backend:

```
VITE_API_URL=https://signbridge-backend-[xxxx]-us-central1.a.run.app
VITE_WS_URL=wss://signbridge-backend-[xxxx]-us-central1.a.run.app/ws
```

Rebuild and redeploy the frontend.

## Monitoring & Logging

### View Backend Logs

```bash
# Stream logs from Cloud Run
gcloud run logs read signbridge-backend --limit 100 --region $REGION

# Or use Cloud Logging
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=signbridge-backend" --limit 50
```

### Set Up Alerts

```bash
# Create alert for high error rate
gcloud alpha monitoring policies create \
  --notification-channels=YOUR_CHANNEL_ID \
  --display-name="SignBridge Backend Errors" \
  --condition-display-name="Error Rate > 5%" \
  --condition-threshold-value=5
```

### Performance Monitoring

- **Cloud Monitoring Dashboard**: Set up in Google Cloud Console
- **Latency tracking**: Monitor WebSocket connection times
- **Error tracking**: Use Cloud Error Reporting

## Scaling Configuration

### Auto-scaling for Backend

```bash
# Set up Cloud Run auto-scaling
gcloud run services update signbridge-backend \
  --min-instances=1 \
  --max-instances=100 \
  --region=$REGION
```

### Database/Cache Layer (Redis)

For production session persistence:

```bash
# Create Cloud Memorystore Redis instance
gcloud redis instances create signbridge-cache \
  --size=2 \
  --region=$REGION \
  --redis-version=7.0
```

Connect from Cloud Run:

```bash
# Update docker-compose or Cloud Run environment
REDIS_URL=redis://YOUR_REDIS_IP:6379
```

## Security Considerations

### 1. Authentication & Authorization
- Implement OAuth 2.0 or authentication headers
- Use Cloud Identity for service accounts

### 2. CORS Configuration
- Restrict origins to your frontend domain
- Keep credentials handling secure

### 3. API Rate Limiting
- Implement in FastAPI with `slowapi`
- Use Cloud Armor for DDoS protection

### 4. Secrets Management
- Use Google Secret Manager for sensitive data
- Never hardcode credentials

```bash
# Store secrets
gcloud secrets create google-cloud-key --data-file=/path/to/key.json

# Reference in Cloud Run
gcloud run deploy signbridge-backend \
  --set-secrets=GOOGLE_CREDENTIALS=google-cloud-key:latest
```

### 5. Network Security
- Use VPC connectors for private resources
- Enable Binary Authorization
- Use Cloud Armor for DDoS/WAF

## Continuous Integration/Deployment

### GitHub Actions Example

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy SignBridge

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Deploy Backend
        run: |
          gcloud auth configure-docker
          gcloud builds submit signbridge-backend --tag gcr.io/${{ secrets.GCP_PROJECT }}/signbridge-backend
          gcloud run deploy signbridge-backend --image gcr.io/${{ secrets.GCP_PROJECT }}/signbridge-backend
      
      - name: Deploy Frontend
        run: |
          cd signbridge-frontend
          npm install
          npm run build
          gsutil -m cp -r dist/* gs://${{ secrets.GCP_PROJECT }}-frontend/
```

## Troubleshooting Deployment

### Backend fails to start
```bash
# Check logs
gcloud run logs read signbridge-backend --limit=50

# Verify environment variables
gcloud run services describe signbridge-backend --region=$REGION
```

### WebSocket connection fails in production
- Check CORS settings
- Verify Cloud Run allows WebSocket upgrades
- Check firewall/security group rules

### Frontend can't reach backend
- Verify API URL in frontend .env
- Check CORS headers from backend
- Ensure Cloud Run service is publicly accessible

## Cost Optimization

- Use Cloud Run's auto-scaling to pay only for what you use
- Enable Cloud CDN for frontend assets
- Use Committed Use Discounts for predictable load
- Monitor and optimize database queries

## References

- [Google Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Vertex AI Gemini API](https://cloud.google.com/vertex-ai/generative-ai/docs/gemini-api)
- [Cloud Speech-to-Text](https://cloud.google.com/speech-to-text)
- [Cloud Text-to-Speech](https://cloud.google.com/text-to-speech)
