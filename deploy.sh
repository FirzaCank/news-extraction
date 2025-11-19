#!/bin/bash

# Deploy News Scraper to Google Cloud Run
# Usage: ./deploy.sh

set -e

# Configuration
PROJECT_ID="robotic-pact-466314-b3"
REGION="asia-southeast1"
REPO_NAME="scraping-docker-repo"
IMAGE_NAME="news-extraction-scraper"
SERVICE_NAME="news-scraper"
BUCKET_NAME="asia-southeast1-news-extraction-scrape-data"

echo "=================================================="
echo "🚀 Deploying News Scraper to Cloud Run"
echo "=================================================="
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Image: $IMAGE_NAME"
echo "=================================================="

# 1. Set project
echo ""
echo "📋 Step 1: Setting GCP project..."
gcloud config set project $PROJECT_ID

# 2. Configure Docker authentication
echo ""
echo "🔐 Step 2: Configuring Docker authentication..."
gcloud auth configure-docker ${REGION}-docker.pkg.dev

# 3. Build Docker image
echo ""
echo "🔨 Step 3: Building Docker image..."
docker build --platform linux/amd64 -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${IMAGE_NAME}:latest .

# 4. Push to Artifact Registry
echo ""
echo "📤 Step 4: Pushing to Artifact Registry..."
docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${IMAGE_NAME}:latest

# 5. Deploy to Cloud Run
echo ""
echo "☁️  Step 5: Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
    --image=${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${IMAGE_NAME}:latest \
    --region=${REGION} \
    --platform=managed \
    --allow-unauthenticated \
    --memory=2Gi \
    --cpu=2 \
    --timeout=3600 \
    --max-instances=10 \
    --set-env-vars="GCS_BUCKET_NAME=${BUCKET_NAME},LOCAL_MODE=false,GCS_INPUT_PATH=input,GCS_OUTPUT_PATH=output" \
    --set-secrets="DIFFBOT_TOKEN=diffbot-key:latest"

# 6. Get service URL
echo ""
echo "=================================================="
echo "✅ Deployment completed!"
echo "=================================================="
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format='value(status.url)')
echo "Service URL: $SERVICE_URL"
echo ""
echo "To trigger scraping, run:"
echo "  curl $SERVICE_URL"
echo ""
echo "To view logs:"
echo "  gcloud logging read \"resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME\" --limit 50"
echo "=================================================="
