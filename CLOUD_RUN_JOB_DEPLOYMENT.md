# Cloud Run Job Deployment Guide

Panduan lengkap untuk deploy **News Extraction & Parser** ke Google Cloud Run Job.

## 📋 Prerequisites

### 1. Google Cloud Project Setup
- **Project ID**: `robotic-pact-466314-b3`
- **Region**: `asia-southeast1`

### 2. Enable Required APIs
```bash
gcloud services enable run.googleapis.com
gcloud services enable artifactregistry.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable storage-api.googleapis.com
```

### 3. Create Artifact Registry Repository
```bash
gcloud artifacts repositories create scraping-docker-repo \
    --repository-format=docker \
    --location=asia-southeast1 \
    --description="Docker repository for news extraction and parser"
```

### 4. Create Service Account
```bash
# Create service account
gcloud iam service-accounts create news-extraction-sa \
    --display-name="News Extraction Service Account"

# Grant necessary permissions
PROJECT_ID="robotic-pact-466314-b3"
SERVICE_ACCOUNT="news-extraction-sa@${PROJECT_ID}.iam.gserviceaccount.com"

# Storage permissions
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/storage.objectAdmin"

# Secret Manager permissions
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/secretmanager.secretAccessor"

# Cloud Run permissions
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/run.invoker"

# Logging permissions
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/logging.logWriter"
```

### 5. Create Secret Manager Secrets
```bash
# Create Diffbot API key secret
echo -n "YOUR_DIFFBOT_TOKEN" | gcloud secrets create diffbot-key \
    --data-file=- \
    --replication-policy="automatic"

# Create Gemini API key secret
echo -n "YOUR_GEMINI_API_KEY" | gcloud secrets create gemini-api-key \
    --data-file=- \
    --replication-policy="automatic"

# Grant access to service account
gcloud secrets add-iam-policy-binding diffbot-key \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding gemini-api-key \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/secretmanager.secretAccessor"
```

### 6. Create GCS Bucket & Folders
```bash
# Create bucket
gsutil mb -p ${PROJECT_ID} -c STANDARD -l asia-southeast1 \
    gs://asia-southeast1-v2-news-extraction-plus-parser-data

# Create folder structure (upload empty placeholder files)
echo "" | gsutil cp - gs://asia-southeast1-v2-news-extraction-plus-parser-data/link_input/.keep
echo "" | gsutil cp - gs://asia-southeast1-v2-news-extraction-plus-parser-data/text_output/.keep
echo "" | gsutil cp - gs://asia-southeast1-v2-news-extraction-plus-parser-data/final_output/.keep
echo "" | gsutil cp - gs://asia-southeast1-v2-news-extraction-plus-parser-data/whitelist_input/.keep

# Grant service account access
gsutil iam ch serviceAccount:${SERVICE_ACCOUNT}:objectAdmin \
    gs://asia-southeast1-v2-news-extraction-plus-parser-data
```

### 7. Upload Input Files
```bash
# Upload input URLs CSV
gsutil cp link_input/input.csv \
    gs://asia-southeast1-v2-news-extraction-plus-parser-data/link_input/input_$(date +%Y%m%d_%H%M%S).csv

# Upload whitelist CSV
gsutil cp whitelist_input/whitelist.csv \
    gs://asia-southeast1-v2-news-extraction-plus-parser-data/whitelist_input/whitelist.csv
```

## 🚀 Deployment Steps

### Option 1: One Command (Recommended)
```bash
make all-deploy
```

### Option 2: Step by Step
```bash
# Step 1: Build and push Docker image
make build-push

# Step 2: Deploy Cloud Run Job
make deploy-job
```

### Option 3: Manual Commands
```bash
# 1. Build and push
./build-and-push.sh

# 2. Deploy job
./deploy-cloud-run-job.sh
```

## ▶️ Running the Job

### Execute Job Manually
```bash
# Using Makefile
make execute-job

# Using script
./execute-job.sh

# Using gcloud directly
gcloud run jobs execute news-extraction-and-parser-job \
    --region=asia-southeast1 \
    --wait
```

### Schedule with Cloud Scheduler
```bash
# Create a schedule (daily at 2 AM)
gcloud scheduler jobs create http news-extraction-daily \
    --location=asia-southeast1 \
    --schedule="0 2 * * *" \
    --time-zone="Asia/Jakarta" \
    --uri="https://asia-southeast1-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/robotic-pact-466314-b3/jobs/news-extraction-and-parser-job:run" \
    --http-method=POST \
    --oauth-service-account-email="news-extraction-sa@robotic-pact-466314-b3.iam.gserviceaccount.com"
```

## 📊 Monitoring & Logs

### View Logs
```bash
# Using Makefile
make logs-job

# Using gcloud
gcloud logging read \
    "resource.type=cloud_run_job AND resource.labels.job_name=news-extraction-and-parser-job" \
    --limit=100 \
    --format=json
```

### Check Job Status
```bash
gcloud run jobs describe news-extraction-and-parser-job \
    --region=asia-southeast1
```

### List Executions
```bash
gcloud run jobs executions list \
    --job=news-extraction-and-parser-job \
    --region=asia-southeast1
```

## 📁 GCS Folder Structure

```
gs://asia-southeast1-v2-news-extraction-plus-parser-data/
├── link_input/           # Input URLs
│   ├── input_20251129_100000.csv
│   └── input_20251129_110000.csv
├── text_output/          # Scraped articles (Diffbot output)
│   ├── text_output_20251129_100000.csv
│   └── text_output_20251129_110000.csv
├── final_output/         # Parsed results (AI output)
│   ├── final_output_20251129_100000.csv
│   └── final_output_20251129_110000.csv
└── whitelist_input/      # Speaker database
    └── whitelist.csv
```

## 🔧 Configuration

### Environment Variables (Set in Cloud Run Job)
- `GCS_BUCKET_NAME`: Cloud Storage bucket name
- `AI_PROVIDER`: gemini or openai
- `GEMINI_MODEL`: gemini-2.0-flash-exp
- `DELAY_BETWEEN_URLS`: 15 (seconds)
- `DELAY_BETWEEN_PAGES`: 10 (seconds)
- `MAX_PAGES`: 5
- `LOCAL_MODE`: false

### Secrets (From Secret Manager)
- `diffbot-key` → `DIFFBOT_TOKEN`
- `gemini-api-key` → `GEMINI_API_KEY`

## 🔄 Update & Redeploy

### Update Code
```bash
# 1. Make code changes
# 2. Rebuild and redeploy
make all-deploy
```

### Update Environment Variables Only
```bash
gcloud run jobs update news-extraction-and-parser-job \
    --region=asia-southeast1 \
    --set-env-vars="DELAY_BETWEEN_URLS=20"
```

### Update Secrets
```bash
# Update secret value
echo -n "NEW_API_KEY" | gcloud secrets versions add gemini-api-key --data-file=-

# Job will automatically use latest version
```

## 📈 Resource Configuration

- **Memory**: 2Gi
- **CPU**: 2 vCPU
- **Timeout**: 1 hour (3600s)
- **Max Retries**: 2
- **Parallelism**: 1 (sequential execution)
- **Tasks**: 1

## 💰 Cost Estimation

**Cloud Run Job Pricing (asia-southeast1)**:
- Memory: $0.0000025 per GiB-second
- CPU: $0.00002500 per vCPU-second
- Requests: First 1M free, then $0.40 per million

**Example**: 1 hour job with 2Gi RAM + 2 vCPU
- Memory: 2 × 3600 × $0.0000025 = $0.018
- CPU: 2 × 3600 × $0.000025 = $0.18
- **Total per run**: ~$0.20

**Daily cost** (1 run/day): ~$6/month

## 🐛 Troubleshooting

### Job Fails Immediately
```bash
# Check logs
make logs-job

# Common issues:
# - Missing secrets
# - Wrong GCS bucket permissions
# - Invalid environment variables
```

### No Input Files Found
```bash
# Verify files exist in GCS
gsutil ls gs://asia-southeast1-v2-news-extraction-plus-parser-data/link_input/

# Upload if missing
gsutil cp link_input/input.csv gs://asia-southeast1-v2-news-extraction-plus-parser-data/link_input/
```

### Rate Limit Errors
```bash
# Increase delays in job configuration
gcloud run jobs update news-extraction-and-parser-job \
    --region=asia-southeast1 \
    --set-env-vars="DELAY_BETWEEN_URLS=20,DELAY_BETWEEN_PAGES=15"
```

## 📞 Support

- **Logs**: `make logs-job`
- **GCP Console**: https://console.cloud.google.com/run/jobs
- **Documentation**: https://cloud.google.com/run/docs/create-jobs
