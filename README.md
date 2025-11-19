# News Extraction Scraper

Hybrid news scraper menggunakan Diffbot API dan Trafilatura dengan dukungan multi-page scraping dan GCS integration.

## Features

- ✅ Multi-page article scraping
- ✅ Hybrid approach: Diffbot (reliable) → Trafilatura (fallback)
- ✅ Automatic pagination detection
- ✅ Auto-retry for 403 errors (up to 3x)
- ✅ GCS integration for Cloud Run
- ✅ Support for Tribun and generic pagination formats

## Requirements

- Python 3.11+
- Diffbot API Token
- Google Cloud Project (optional, for GCS)

## Installation

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Setup environment variables
cp .env.example .env
# Edit .env and add your DIFFBOT_TOKEN

# Create input directory and file
mkdir -p input
# Create input/input.csv with columns: ID, date, source

# Run locally
export LOCAL_MODE=true
python main_from_container.py
```

### Docker

```bash
# Build image
docker build -t news-scraper .

# Run container (local mode)
docker run -v $(pwd)/input:/app/input \
           -v $(pwd)/output:/app/output \
           -e LOCAL_MODE=true \
           -e DIFFBOT_TOKEN=your-token \
           news-scraper

# Run container (GCS mode)
docker run -v ~/.config/gcloud:/root/.config/gcloud \
           -e DIFFBOT_TOKEN=your-token \
           -e GCS_BUCKET_NAME=your-bucket \
           news-scraper
```

## Deploy to Google Cloud Run

### 1. Setup GCS Bucket

```bash
# Create bucket
gsutil mb -l asia-southeast1 gs://your-bucket-name

# Create folders
gsutil mkdir gs://your-bucket-name/input
gsutil mkdir gs://your-bucket-name/output

# Upload input file
gsutil cp input/input_20241120.csv gs://your-bucket-name/input/
```

### 2. Setup Secret Manager

```bash
# Create secret for Diffbot token
echo -n "your-diffbot-token" | gcloud secrets create diffbot-key \
    --data-file=- \
    --replication-policy="automatic"

# Grant access to Cloud Run service account
gcloud secrets add-iam-policy-binding diffbot-key \
    --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

### 3. Build and Push to Artifact Registry

```bash
# Set variables
export PROJECT_ID=robotic-pact-466314-b3
export REGION=asia-southeast1
export REPO_NAME=scraping-docker-repo
export IMAGE_NAME=news-extraction-scraper

# Configure Docker auth
gcloud auth configure-docker ${REGION}-docker.pkg.dev

# Build and tag
docker build -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${IMAGE_NAME}:latest .

# Push to Artifact Registry
docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${IMAGE_NAME}:latest
```

### 4. Deploy to Cloud Run

```bash
gcloud run deploy news-scraper \
    --image=${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${IMAGE_NAME}:latest \
    --region=${REGION} \
    --platform=managed \
    --allow-unauthenticated \
    --memory=2Gi \
    --cpu=2 \
    --timeout=3600 \
    --set-env-vars="GCS_BUCKET_NAME=your-bucket-name,LOCAL_MODE=false" \
    --set-secrets="DIFFBOT_TOKEN=diffbot-key:latest"
```

### 5. Trigger Scraping

```bash
# Trigger via HTTP
curl https://news-scraper-xxxxx-xx.a.run.app

# Or via gcloud
gcloud run services proxy news-scraper --region=${REGION}
```

## Input Format

CSV file dengan kolom:
- `ID`: Unique identifier
- `date`: Article date (YYYY-MM-DD)
- `source`: Article URL

Example:
```csv
ID,date,source
1,2024-10-19,https://www.tribunnews.com/nasional/2024/10/19/article-title
2,2024-10-20,https://news.example.com/article/12345
```

## Output Format

CSV file dengan kolom:
- `ID`: Same as input
- `date_article`: Date from input
- `ingestion_time`: Scraping timestamp
- `source`: Article URL
- `content`: Extracted article content

## Configuration

Edit environment variables in `.env` or set during deployment:

```bash
# Required
DIFFBOT_TOKEN=your-token

# GCS (optional for local mode)
GCS_BUCKET_NAME=your-bucket-name
GCS_INPUT_PATH=input
GCS_OUTPUT_PATH=output

# Scraper settings (optional)
MAX_PAGES=5
DELAY_BETWEEN_URLS=8
DELAY_BETWEEN_PAGES=6
MAX_RETRIES=3
RETRY_DELAY=5
```

## Troubleshooting

### 403 Errors
Script automatically retries 403 errors up to 3 times. If still failing:
- Increase `RETRY_DELAY`
- Add user-agent rotation
- Check website's robots.txt

### Rate Limiting
If you see rate limit errors:
- Increase `DELAY_BETWEEN_URLS` (default: 8s)
- Increase `DELAY_BETWEEN_PAGES` (default: 6s)
- Check your Diffbot plan limits

### GCS Permission Errors
Ensure Cloud Run service account has:
- `roles/storage.objectViewer` for reading input
- `roles/storage.objectCreator` for writing output
- `roles/secretmanager.secretAccessor` for Diffbot token

```bash
# Grant permissions
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
    --role="roles/storage.objectAdmin"
```

## License

MIT
