#!/bin/bash
# Setup Google Cloud Infrastructure
# Service Account, Secrets, GCS Bucket, Permissions

set -e

PROJECT_ID="robotic-pact-466314-b3"
REGION="asia-southeast1"
SERVICE_ACCOUNT="news-extraction-sa@${PROJECT_ID}.iam.gserviceaccount.com"
GCS_BUCKET="asia-southeast1-v2-news-extraction-plus-parser-data"

echo "=================================================="
echo "🔧 Setting up Google Cloud Infrastructure"
echo "=================================================="
echo ""
echo "Project: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo ""

# Set project
gcloud config set project ${PROJECT_ID}

# Enable required APIs
echo "📡 Enabling required APIs..."
gcloud services enable run.googleapis.com
gcloud services enable artifactregistry.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable storage-api.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable cloudscheduler.googleapis.com

echo "✅ APIs enabled"
echo ""

# Create Artifact Registry repository (if not exists)
echo "📦 Creating Artifact Registry repository..."
if gcloud artifacts repositories describe scraping-docker-repo --location=${REGION} 2>/dev/null; then
    echo "✅ Repository already exists"
else
    gcloud artifacts repositories create scraping-docker-repo \
        --repository-format=docker \
        --location=${REGION} \
        --description="Docker repository for news extraction and parser"
    echo "✅ Repository created"
fi
echo ""

# Create Service Account (if not exists)
echo "👤 Creating service account..."
if gcloud iam service-accounts describe ${SERVICE_ACCOUNT} 2>/dev/null; then
    echo "✅ Service account already exists"
else
    gcloud iam service-accounts create news-extraction-sa \
        --display-name="News Extraction Service Account"
    echo "✅ Service account created"
fi
echo ""

# Grant permissions
echo "🔐 Granting permissions to service account..."

# Storage Admin
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/storage.objectAdmin" \
    --condition=None \
    >/dev/null 2>&1

# Secret Manager Secret Accessor
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/secretmanager.secretAccessor" \
    --condition=None \
    >/dev/null 2>&1

# Cloud Run Invoker
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/run.invoker" \
    --condition=None \
    >/dev/null 2>&1

# Logging Log Writer
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/logging.logWriter" \
    --condition=None \
    >/dev/null 2>&1

echo "✅ Permissions granted"
echo ""

# Create GCS Bucket (if not exists)
echo "🪣 Creating GCS bucket..."
if gsutil ls -b gs://${GCS_BUCKET} 2>/dev/null; then
    echo "✅ Bucket already exists"
else
    gsutil mb -p ${PROJECT_ID} -c STANDARD -l ${REGION} gs://${GCS_BUCKET}
    echo "✅ Bucket created"
fi
echo ""

# Create folder structure
echo "📁 Creating folder structure in GCS..."
echo "" | gsutil cp - gs://${GCS_BUCKET}/link_input/.keep 2>/dev/null || true
echo "" | gsutil cp - gs://${GCS_BUCKET}/text_output/.keep 2>/dev/null || true
echo "" | gsutil cp - gs://${GCS_BUCKET}/final_output/.keep 2>/dev/null || true
echo "" | gsutil cp - gs://${GCS_BUCKET}/whitelist_input/.keep 2>/dev/null || true
echo "✅ Folders created"
echo ""

# Grant bucket access to service account
echo "🔓 Granting bucket access to service account..."
gsutil iam ch serviceAccount:${SERVICE_ACCOUNT}:objectAdmin gs://${GCS_BUCKET}
echo "✅ Bucket access granted"
echo ""

# Check if secrets exist
echo "🔑 Checking secrets..."
DIFFBOT_EXISTS=$(gcloud secrets list --filter="name:diffbot-key" --format="value(name)" || true)
GEMINI_EXISTS=$(gcloud secrets list --filter="name:gemini-api-key" --format="value(name)" || true)

if [ -z "$DIFFBOT_EXISTS" ]; then
    echo ""
    echo "⚠️  diffbot-key secret not found!"
    echo "   Please create it manually:"
    echo "   echo -n 'YOUR_DIFFBOT_TOKEN' | gcloud secrets create diffbot-key --data-file=-"
    echo ""
else
    echo "✅ diffbot-key exists"
    # Grant access
    gcloud secrets add-iam-policy-binding diffbot-key \
        --member="serviceAccount:${SERVICE_ACCOUNT}" \
        --role="roles/secretmanager.secretAccessor" \
        >/dev/null 2>&1 || true
fi

if [ -z "$GEMINI_EXISTS" ]; then
    echo ""
    echo "⚠️  gemini-api-key secret not found!"
    echo "   Please create it manually:"
    echo "   echo -n 'YOUR_GEMINI_API_KEY' | gcloud secrets create gemini-api-key --data-file=-"
    echo ""
else
    echo "✅ gemini-api-key exists"
    # Grant access
    gcloud secrets add-iam-policy-binding gemini-api-key \
        --member="serviceAccount:${SERVICE_ACCOUNT}" \
        --role="roles/secretmanager.secretAccessor" \
        >/dev/null 2>&1 || true
fi
echo ""

echo "=================================================="
echo "✅ SETUP COMPLETED!"
echo "=================================================="
echo ""
echo "Next steps:"
echo "  1. Upload input files to GCS:"
echo "     gsutil cp link_input/input.csv gs://${GCS_BUCKET}/link_input/"
echo "     gsutil cp whitelist_input/whitelist.csv gs://${GCS_BUCKET}/whitelist_input/"
echo ""
echo "  2. Create secrets (if not done yet):"
echo "     echo -n 'YOUR_DIFFBOT_TOKEN' | gcloud secrets create diffbot-key --data-file=-"
echo "     echo -n 'YOUR_GEMINI_API_KEY' | gcloud secrets create gemini-api-key --data-file=-"
echo ""
echo "  3. Deploy:"
echo "     make all-deploy"
echo ""
