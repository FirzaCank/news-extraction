#!/bin/bash

# Build and Push Docker Image for Self Content Parser (Parse-Only)

set -e

echo "=================================================="
echo "🐳 Building Docker Image for Self Content Parser"
echo "=================================================="
echo ""

# Project configuration
PROJECT_ID="robotic-pact-466314-b3"
REGION="asia-southeast1"
REPOSITORY="scraping-docker-repo"
IMAGE_NAME="self-content-parser"
IMAGE_TAG="latest"
FULL_IMAGE_PATH="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${IMAGE_NAME}:${IMAGE_TAG}"

echo "Project ID: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Repository: ${REPOSITORY}"
echo "Image: ${IMAGE_NAME}"
echo "Full Path: ${FULL_IMAGE_PATH}"
echo ""

# Set active project
echo "📌 Setting project..."
gcloud config set project ${PROJECT_ID}

# Configure Docker for Artifact Registry
echo "🔐 Configuring Docker authentication..."
gcloud auth configure-docker ${REGION}-docker.pkg.dev

# Build Docker image
echo "🔨 Building Docker image..."
docker build --platform linux/amd64 -f Dockerfile.parse-only -t ${FULL_IMAGE_PATH} .

echo ""
echo "✅ Docker image built successfully!"
echo ""

# Push to Artifact Registry
echo "📤 Pushing image to Artifact Registry..."
docker push ${FULL_IMAGE_PATH}

echo ""
echo "=================================================="
echo "✅ BUILD & PUSH COMPLETED!"
echo "=================================================="
echo ""
echo "Image pushed to:"
echo "  ${FULL_IMAGE_PATH}"
echo ""
echo "Next steps:"
echo "  1. Run: make deploy-parse-only"
echo "  2. Or manually: ./deploy-parse-only-job.sh"
