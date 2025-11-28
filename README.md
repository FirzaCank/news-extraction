# News Extraction Scraper & Parser

Hybrid news scraper menggunakan Diffbot API dan Trafilatura dengan dukungan multi-page scraping, GCS integration, dan AI-powered parsing untuk extract quotes, speakers, dan lokasi.

## Features

### Scraper
- ✅ Multi-page article scraping
- ✅ Hybrid approach: Diffbot (reliable) → Trafilatura (fallback)
- ✅ Automatic pagination detection
- ✅ Auto-retry for 403 errors (up to 3x)
- ✅ GCS integration for Cloud Run
- ✅ Support for Tribun and generic pagination formats

### Parser
- ✅ **Flexible AI provider** - Switch between Gemini or OpenAI
- ✅ **Smart extraction** - Quotes, speakers, province, city
- ✅ **Latest models** - gemini-2.5-flash, gpt-4o-mini
- ✅ **Auto-retry** - Exponential backoff with error handling
- ✅ **Safety filters** - Graceful handling for blocked content
- ✅ **Structured output** - JSON validation and CSV export
- ✅ **Logging** - Detailed logs saved to `log/parser.log`
- ✅ **Dual config** - Env variables (local) + Secret Manager (cloud)

## Requirements

- Python 3.13+
- Diffbot API Token (for scraping)
- Gemini API Key or OpenAI API Key (for AI parsing)
- Google Cloud Project (optional, for Cloud Run deployment)

## Installation

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Setup environment variables
cp .env.example .env
# Edit .env and configure:
# - DIFFBOT_TOKEN (required for scraping)
# - AI_PROVIDER (gemini or openai)
# - GEMINI_API_KEY or OPENAI_API_KEY (required for parsing)
# - GEMINI_MODEL (default: gemini-2.5-flash)
# - OPENAI_MODEL (default: gpt-4o-mini)

# Create input directory and file
mkdir -p input
# Create input/input.csv with columns: ID, date, source

# Run scraper
make test

# Run parser (after scraping)
make parse

# View parser logs
tail -f log/parser.log
```

## Quick Start with Makefile

```bash
# === SCRAPER ===
# Test scraper locally
make test

# Run scraper in background
make run-bg

# === PARSER ===
# Parse latest scraped data with AI (auto-detect from output/)
make parse

# Parse specific file
make parse-file FILE=output/output_20241126_230736.csv

# Force use Gemini (override AI_PROVIDER)
make parse-gemini

# Force use OpenAI (override AI_PROVIDER)
make parse-openai

# View parser logs
tail -f log/parser.log

# === DEPLOYMENT ===
# Build, push, and deploy to Cloud Run
make build
make push
make deploy

# Clean logs
make clean
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

# Create secret for Gemini API key (if using Gemini)
echo -n "your-gemini-key" | gcloud secrets create gemini-api-key \
    --data-file=- \
    --replication-policy="automatic"

# Create secret for OpenAI API key (if using OpenAI)
echo -n "your-openai-key" | gcloud secrets create openai-api-key \
    --data-file=- \
    --replication-policy="automatic"

# Grant access to Cloud Run service account
PROJECT_NUMBER=$(gcloud projects describe robotic-pact-466314-b3 --format="value(projectNumber)")
gcloud secrets add-iam-policy-binding diffbot-key \
    --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding gemini-api-key \
    --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding openai-api-key \
    --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
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
    --set-env-vars="GCS_BUCKET_NAME=your-bucket-name,LOCAL_MODE=false,AI_PROVIDER=gemini" \
    --set-secrets="DIFFBOT_TOKEN=diffbot-key:latest,GEMINI_API_KEY=gemini-api-key:latest"

# Or for OpenAI:
#   --set-env-vars="GCS_BUCKET_NAME=your-bucket-name,LOCAL_MODE=false,AI_PROVIDER=openai" \
#   --set-secrets="DIFFBOT_TOKEN=diffbot-key:latest,OPENAI_API_KEY=openai-api-key:latest"
```

### 5. Trigger Scraping

```bash
# Trigger via HTTP
curl https://news-scraper-xxxxx-xx.a.run.app

# Or via gcloud
gcloud run services proxy news-scraper --region=${REGION}
```

## AI Parsing

### How It Works

Parser (`parse_news.py`) menggunakan AI untuk extract informasi terstruktur dari artikel berita:

1. **Reads scraped data** from `output/output_*.csv`
2. **Sends article** to AI (Gemini/OpenAI) dengan structured prompt
3. **Extracts** quotes, speakers, province, city
4. **Validates** JSON response dan mapping quotes↔speakers
5. **Saves** to `parsed/parsed_*.csv`

### Supported AI Providers

| Provider | Model | Free Tier | Best For |
|----------|-------|-----------|----------|
| **Gemini** | gemini-2.5-flash | 15 RPM, 1.5M tokens/day | Indonesian text, fast |
| **Gemini** | gemini-2.0-flash-exp | 10 RPM, 4M tokens/day | Experimental, powerful |
| **OpenAI** | gpt-4o-mini | 500 RPM, 200k tokens/day | Structured output |
| **OpenAI** | gpt-4o | 500 RPM (paid) | Highest accuracy |

### Parser Commands

```bash
# Parse latest file (auto-detect from output/)
make parse

# Parse specific file
make parse-file FILE=output/output_20241126_230736.csv

# Force Gemini
make parse-gemini

# Force OpenAI
make parse-openai

# Direct Python
python parse_news.py output/output_20241126_230736.csv
```

### Error Handling

Parser handles common issues gracefully:

- **MAX_TOKENS**: Auto-increased to 8192 tokens
- **Safety filters**: Returns empty result for blocked content
- **Rate limits**: 1-second delay between requests
- **API errors**: 3 retries with exponential backoff
- **Invalid JSON**: Falls back to empty result

All errors logged to `log/parser.log` with detailed info.

### Example Output

```json
{
  "quotes": [
    "Harga minyak goreng masih tinggi di atas HET",
    "Kami terus monitor perkembangan harga"
  ],
  "speakers": [
    "Kepala BPS",
    "Menteri Perdagangan"
  ],
  "province": "DKI Jakarta",
  "city": "Jakarta"
}
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

### Scraper Output (`output/output_*.csv`)

CSV file dengan kolom:
- `ID`: Same as input
- `date_article`: Date from input
- `ingestion_time`: Scraping timestamp
- `source`: Article URL
- `content`: Extracted article content

### Parser Output (`parsed/parsed_*.csv`)

CSV file dengan kolom (1 quote per row):
- `id`: Article ID
- `date`: Article date
- `source`: Article URL
- `quote`: Single extracted quote
- `speaker`: Speaker for this quote
- `province`: Detected or inferred province - `"Sumatera Utara"`
- `city`: Detected city/regency - `"Asahan"`

**Important**: Each quote creates a separate row. Article dengan 3 quotes = 3 rows.

Example:
```csv
id,date,source,quote,speaker,province,city
91605609591,2024-11-26,https://example.com/article,"Harga minyak goreng masih tinggi","Kepala BPS","DKI Jakarta","Jakarta"
91605609591,2024-11-26,https://example.com/article,"Kami terus monitor","Menteri","DKI Jakarta","Jakarta"
91607975102,2024-11-26,https://example.com/article2,"Quote dari Asahan","Sekda","Sumatera Utara","Asahan"
```

## Configuration

Edit environment variables in `.env` or set during deployment:

```bash
# === SCRAPER ===
# Required
DIFFBOT_TOKEN=your-token

# GCS (optional for local mode)
GCS_BUCKET_NAME=your-bucket-name
GCS_INPUT_PATH=input
GCS_OUTPUT_PATH=output
LOCAL_MODE=true

# Scraper settings (optional)
MAX_PAGES=5
DELAY_BETWEEN_URLS=8
DELAY_BETWEEN_PAGES=6
MAX_RETRIES=3
RETRY_DELAY=5

# === PARSER ===
# AI Provider (gemini or openai)
AI_PROVIDER=gemini

# API Keys (based on provider)
GEMINI_API_KEY=your-gemini-key
OPENAI_API_KEY=your-openai-key

# AI Model Selection
GEMINI_MODEL=gemini-2.5-flash      # Latest: gemini-2.5-flash, gemini-2.0-flash-exp
OPENAI_MODEL=gpt-4o-mini            # Alternatives: gpt-4o, gpt-4-turbo

# AI Generation Settings
AI_TEMPERATURE=0.1                  # 0.0-1.0, lower = more consistent
AI_MAX_CONTENT=6000                 # Max chars from article to send
AI_DELAY=1                          # Delay between requests (seconds)
```

## Switching AI Providers

### Local Development

Edit `.env`:
```bash
# For Gemini (default)
AI_PROVIDER=gemini
GEMINI_API_KEY=your_key_here

# For OpenAI
AI_PROVIDER=openai
OPENAI_API_KEY=your_key_here
```

### Cloud Run

Update environment variables:
```bash
# Switch to Gemini
gcloud run services update news-scraper \
    --region=asia-southeast1 \
    --update-env-vars="AI_PROVIDER=gemini" \
    --update-secrets="GEMINI_API_KEY=gemini-api-key:latest"

# Switch to OpenAI
gcloud run services update news-scraper \
    --region=asia-southeast1 \
    --update-env-vars="AI_PROVIDER=openai" \
    --update-secrets="OPENAI_API_KEY=openai-api-key:latest"
```

## Troubleshooting

### Scraper Issues

#### 403 Errors
Script automatically retries 403 errors up to 3 times. If still failing:
- Increase `RETRY_DELAY`
- Add user-agent rotation
- Check website's robots.txt

#### Rate Limiting
If you see rate limit errors:
- Increase `DELAY_BETWEEN_URLS` (default: 8s)
- Increase `DELAY_BETWEEN_PAGES` (default: 6s)
- Check your Diffbot plan limits

### Parser Issues

#### "MAX_TOKENS" Error
Response too long, already fixed with `max_output_tokens=8192`. If still happening:
- Reduce `AI_MAX_CONTENT` (default: 6000)
- Article might be extremely long

#### "SAFETY" Filter Blocking
Some political/sensitive content blocked by AI safety filters:
- Parser returns empty result gracefully
- Check `log/parser.log` for safety ratings
- Normal behavior, no action needed

#### "Model not found" Error
Model deprecated or unavailable:
```bash
# List available Gemini models
curl "https://generativelanguage.googleapis.com/v1beta/models?key=YOUR_API_KEY"

# Update .env with valid model
GEMINI_MODEL=gemini-2.5-flash
```

#### Rate Limit (429 Error)
Free tier limits exceeded:
- Gemini: 15 RPM, 1.5M tokens/day
- OpenAI: 500 RPM, 200k tokens/day
- Increase `AI_DELAY` or wait

#### API Key Invalid
```bash
# Verify Gemini key
curl "https://generativelanguage.googleapis.com/v1beta/models?key=YOUR_API_KEY"

# Verify OpenAI key
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### Cloud Run Issues

#### GCS Permission Errors
Ensure Cloud Run service account has:
- `roles/storage.objectViewer` for reading input
- `roles/storage.objectCreator` for writing output
- `roles/secretmanager.secretAccessor` for secrets

```bash
# Grant permissions
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
    --role="roles/storage.objectAdmin"
```

## License

MIT
