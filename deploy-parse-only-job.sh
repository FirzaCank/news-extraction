#!/bin/bash

# Deploy Self Content Parser Cloud Run Job (Optimized)

set -e

echo "=================================================="
echo "🚀 Deploying Self Content Parser Cloud Run Job"
echo "=================================================="
echo ""

# Configuration
JOB_NAME="self-content-parser-job"
PROJECT_ID="robotic-pact-466314-b3"
REGION="asia-southeast1"
IMAGE_PATH="asia-southeast1-docker.pkg.dev/${PROJECT_ID}/scraping-docker-repo/self-content-parser:latest"
SERVICE_ACCOUNT="news-extraction-sa@${PROJECT_ID}.iam.gserviceaccount.com"
GCS_BUCKET="asia-southeast1-v2-news-extraction-plus-parser-data"

echo "Job Name: ${JOB_NAME}"
echo "Image: ${IMAGE_PATH}"
echo "Region: ${REGION}"
echo "GCS Bucket: ${GCS_BUCKET}"
echo ""

# Check if image exists
echo "🔍 Checking if image exists..."
if gcloud artifacts docker images describe ${IMAGE_PATH} --project=${PROJECT_ID} > /dev/null 2>&1; then
    echo "✅ Image found in Artifact Registry"
else
    echo "❌ Image not found! Please run: make build-push-parse-only"
    exit 1
fi

# Deploy Cloud Run Job
echo ""
echo "📦 Deploying Cloud Run Job with OPTIMIZED settings..."
echo ""

gcloud run jobs deploy ${JOB_NAME} \
    --image=${IMAGE_PATH} \
    --region=${REGION} \
    --project=${PROJECT_ID} \
    --service-account=${SERVICE_ACCOUNT} \
    --set-env-vars="GCS_BUCKET_NAME=${GCS_BUCKET},GCS_INPUT_PATH=self_content_input,GCS_OUTPUT_PATH=final_output,LOCAL_MODE=false,AI_PROVIDER=gemini,GEMINI_MODEL=gemini-2.5-flash,AI_TEMPERATURE=0.1,AI_MAX_CONTENT=6000,AI_DELAY=0.3,AI_TIMEOUT=45,AI_MAX_RETRIES=2,PARSING_THREADS=4" \
    --set-secrets="GEMINI_API_KEY=gemini-api-key:latest" \
    --max-retries=0 \
    --task-timeout=86400 \
    --memory=4Gi \
    --cpu=4

echo ""
echo "=================================================="
echo "✅ DEPLOYMENT COMPLETED!"
echo "=================================================="
echo ""
echo "Job Details:"
echo "  Name: ${JOB_NAME}"
echo "  Region: ${REGION}"
echo "  Image: ${IMAGE_PATH}"
echo "  Timeout: 24 hours (86400s)"
echo "  Memory: 4Gi"
echo "  CPU: 4"
echo "  Max Retries: 0"
echo ""
echo "Multithreading Settings:"
echo "  • Parsing Threads: 4 (parallel AI parsing)"
echo ""
echo "Optimized AI Settings:"
echo "  • AI Delay: 0.3s per request (reduced from 0.5s)"
echo "  • AI Timeout: 45s per article (reduced from 60s)"
echo "  • AI Max Retries: 2 (reduced from 3)"
echo ""
echo "Secrets:"
echo "  • gemini-api-key → GEMINI_API_KEY"
echo ""
echo "GCS Configuration:"
echo "  • Bucket: ${GCS_BUCKET}"
echo "  • Input: self_content_input/"
echo "  • Output: final_output/"
echo ""
echo "To run the job:"
echo "  gcloud run jobs execute ${JOB_NAME} --region=${REGION}"
echo ""
echo "To view logs:"
echo "  gcloud logging read \"resource.type=cloud_run_job AND resource.labels.job_name=${JOB_NAME}\" --limit=50 --format=json"
echo ""