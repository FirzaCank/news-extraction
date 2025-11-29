#!/bin/bash
# Deploy Cloud Run Job
# Full pipeline: Extract news → Parse with AI

set -e

# Configuration
PROJECT_ID="robotic-pact-466314-b3"
REGION="asia-southeast1"
REPO_NAME="scraping-docker-repo"
IMAGE_NAME="news-extraction-and-parser"
JOB_NAME="news-extraction-and-parser-job"
SERVICE_ACCOUNT="news-extraction-sa@${PROJECT_ID}.iam.gserviceaccount.com"
GCS_BUCKET="asia-southeast1-v2-news-extraction-plus-parser-data"

ARTIFACT_REGISTRY="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${IMAGE_NAME}"

echo "=================================================="
echo "🚀 Deploying Cloud Run Job"
echo "=================================================="
echo ""
echo "Job Name: ${JOB_NAME}"
echo "Image: ${ARTIFACT_REGISTRY}:latest"
echo "Region: ${REGION}"
echo "GCS Bucket: ${GCS_BUCKET}"
echo ""

# Check if image exists in Artifact Registry (simplified check)
echo "🔍 Checking if image exists..."
if gcloud artifacts docker images list ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${IMAGE_NAME} --limit=1 &>/dev/null; then
    echo "✅ Image found in Artifact Registry"
else
    echo "⚠️  Could not verify image (but will proceed with deployment)"
    echo "   If deployment fails, run: make build-push or ./build-and-push.sh"
fi
echo ""

# Deploy/Update Cloud Run Job
echo "📦 Deploying Cloud Run Job..."
echo ""

gcloud run jobs deploy ${JOB_NAME} \
    --image=${ARTIFACT_REGISTRY}:latest \
    --region=${REGION} \
    --service-account=${SERVICE_ACCOUNT} \
    --set-env-vars="GCS_BUCKET_NAME=${GCS_BUCKET}" \
    --set-env-vars="GCS_INPUT_PATH=text_output" \
    --set-env-vars="GCS_OUTPUT_PATH=final_output" \
    --set-env-vars="AI_PROVIDER=gemini" \
    --set-env-vars="GEMINI_MODEL=gemini-2.5-flash" \
    --set-env-vars="AI_TEMPERATURE=0.1" \
    --set-env-vars="AI_MAX_CONTENT=6000" \
    --set-env-vars="AI_DELAY=1" \
    --set-env-vars="DELAY_BETWEEN_URLS=15" \
    --set-env-vars="DELAY_BETWEEN_PAGES=10" \
    --set-env-vars="MAX_PAGES=5" \
    --set-env-vars="MAX_RETRIES=3" \
    --set-env-vars="RETRY_DELAY=5" \
    --set-env-vars="LOCAL_MODE=false" \
    --set-secrets="DIFFBOT_TOKEN=diffbot-key:latest" \
    --set-secrets="GEMINI_API_KEY=gemini-api-key:latest" \
    --max-retries=0 \
    --task-timeout=3600 \
    --memory=2Gi \
    --cpu=2 \
    --parallelism=1 \
    --tasks=1

if [ $? -ne 0 ]; then
    echo "❌ Cloud Run Job deployment failed!"
    exit 1
fi

echo ""
echo "=================================================="
echo "✅ DEPLOYMENT COMPLETED!"
echo "=================================================="
echo ""
echo "Job Details:"
echo "  Name: ${JOB_NAME}"
echo "  Region: ${REGION}"
echo "  Image: ${ARTIFACT_REGISTRY}:latest"
echo "  Timeout: 1 hour"
echo "  Memory: 2Gi"
echo "  CPU: 2"
echo ""
echo "Secrets:"
echo "  • diffbot-key → DIFFBOT_TOKEN"
echo "  • gemini-api-key → GEMINI_API_KEY"
echo ""
echo "GCS Configuration:"
echo "  • Bucket: ${GCS_BUCKET}"
echo "  • Input: link_input/"
echo "  • Text Output: text_output/"
echo "  • Final Output: final_output/"
echo "  • Whitelist: whitelist_input/"
echo ""
echo "To run the job:"
echo "  gcloud run jobs execute ${JOB_NAME} --region=${REGION}"
echo ""
echo "To view logs:"
echo "  gcloud logging read \"resource.type=cloud_run_job AND resource.labels.job_name=${JOB_NAME}\" --limit=50 --format=json"
echo ""
