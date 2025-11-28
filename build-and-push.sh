#!/bin/bash
# Build and Push Docker Image to Artifact Registry
# For Cloud Run Job Deployment

set -e

# Configuration
PROJECT_ID="robotic-pact-466314-b3"
REGION="asia-southeast1"
REPO_NAME="scraping-docker-repo"
IMAGE_NAME="news-extraction-and-parser"
ARTIFACT_REGISTRY="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${IMAGE_NAME}"

echo "=================================================="
echo "🐳 Building Docker Image for Cloud Run Job"
echo "=================================================="
echo ""
echo "Project ID: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Repository: ${REPO_NAME}"
echo "Image: ${IMAGE_NAME}"
echo "Full Path: ${ARTIFACT_REGISTRY}:latest"
echo ""

# Check if gcloud is authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo "❌ Not authenticated with gcloud. Please run: gcloud auth login"
    exit 1
fi

# Set project
echo "📌 Setting project..."
gcloud config set project ${PROJECT_ID}

# Configure Docker for Artifact Registry
echo "🔐 Configuring Docker authentication..."
gcloud auth configure-docker ${REGION}-docker.pkg.dev

# Build Docker image
echo ""
echo "🔨 Building Docker image..."
docker build --platform linux/amd64 -t ${ARTIFACT_REGISTRY}:latest .

if [ $? -ne 0 ]; then
    echo "❌ Docker build failed!"
    exit 1
fi

echo ""
echo "✅ Docker image built successfully!"
echo ""

# Push to Artifact Registry
echo "📤 Pushing image to Artifact Registry..."
docker push ${ARTIFACT_REGISTRY}:latest

if [ $? -ne 0 ]; then
    echo "❌ Docker push failed!"
    exit 1
fi

echo ""
echo "=================================================="
echo "✅ BUILD & PUSH COMPLETED!"
echo "=================================================="
echo ""
echo "Image pushed to:"
echo "  ${ARTIFACT_REGISTRY}:latest"
echo ""
echo "Next steps:"
echo "  1. Run: make deploy-job"
echo "  2. Or manually: ./deploy-cloud-run-job.sh"
echo ""
