#!/bin/bash

# Build and test Docker image locally
# Usage: ./build.sh

set -e

IMAGE_NAME="news-scraper"

echo "================================================="="
 echo "🔨 Building Docker Image"
 echo "================================================="="

# Build image with platform flag for Cloud Run compatibility
docker build --platform linux/amd64 -t ${IMAGE_NAME}:latest .

echo ""
echo "✅ Build completed!"
echo ""
echo "To run locally with input folder:"
echo "  docker run -v \$(pwd)/input:/app/input -v \$(pwd)/output:/app/output -e LOCAL_MODE=true -e DIFFBOT_TOKEN=your-token ${IMAGE_NAME}:latest"
echo ""
echo "To test with GCS:"
echo "  docker run -v ~/.config/gcloud:/root/.config/gcloud -e DIFFBOT_TOKEN=your-token -e GCS_BUCKET_NAME=your-bucket ${IMAGE_NAME}:latest"
echo ""
echo "=================================================="
