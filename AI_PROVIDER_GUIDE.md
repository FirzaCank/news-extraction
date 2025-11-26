# AI Provider Configuration Guide

Script `parse_news.py` mendukung dua AI provider: **Google Gemini** dan **OpenAI**. Kamu bisa switch antara keduanya dengan mudah.

## 🔄 How It Works

Script secara otomatis:
1. Membaca environment variable `AI_PROVIDER` (default: `gemini`)
2. Ambil API key dari Secret Manager (cloud) atau environment variable (local)
3. Load library yang sesuai (google-generativeai atau openai)
4. Gunakan model yang tepat berdasarkan provider

## 📋 Configuration Options

### Local Development (via `.env`)

```bash
# AI Provider (gemini or openai)
AI_PROVIDER=gemini

# Gemini Configuration (if using gemini)
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-1.5-flash  # optional, defaults to gemini-1.5-flash

# OpenAI Configuration (if using openai)
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini  # optional, defaults to gpt-4o-mini

# Shared Settings
AI_TEMPERATURE=0.1      # Lower = more consistent, Higher = more creative
AI_MAX_CONTENT=6000     # Max characters from article to send to AI
AI_DELAY=1              # Delay in seconds between API requests
```

### Cloud Run (via Secret Manager + Environment Variables)

```bash
# 1. Create secrets in Secret Manager
echo -n "your-gemini-key" | gcloud secrets create gemini-api-key \
    --data-file=- --replication-policy="automatic"

echo -n "your-openai-key" | gcloud secrets create openai-api-key \
    --data-file=- --replication-policy="automatic"

# 2. Grant access to Cloud Run service account
PROJECT_NUMBER=$(gcloud projects describe YOUR_PROJECT_ID --format="value(projectNumber)")

gcloud secrets add-iam-policy-binding gemini-api-key \
    --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding openai-api-key \
    --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

# 3. Deploy with Gemini
gcloud run services update YOUR_SERVICE \
    --region=asia-southeast1 \
    --update-env-vars="AI_PROVIDER=gemini,GEMINI_MODEL=gemini-1.5-flash" \
    --update-secrets="GEMINI_API_KEY=gemini-api-key:latest"

# 4. Or deploy with OpenAI
gcloud run services update YOUR_SERVICE \
    --region=asia-southeast1 \
    --update-env-vars="AI_PROVIDER=openai,OPENAI_MODEL=gpt-4o-mini" \
    --update-secrets="OPENAI_API_KEY=openai-api-key:latest"
```

## 🎯 Provider Comparison

| Feature | Google Gemini | OpenAI |
|---------|--------------|---------|
| **Default Model** | `gemini-1.5-flash` | `gpt-4o-mini` |
| **Response Format** | Text (manual JSON parsing) | Native `json_object` mode |
| **Free Tier** | ✅ Generous (60 req/min) | ❌ Limited |
| **Cost** | 💰 Cheap | 💰💰 More expensive |
| **Speed** | ⚡ Fast | ⚡ Fast |
| **Bahasa Indonesia** | ✅ Good | ✅ Excellent |
| **JSON Reliability** | 🟡 Good (needs cleanup) | 🟢 Excellent |

## 🚀 Quick Start Examples

### 1. Use Gemini (Default - Recommended)

```bash
# Edit .env
echo "AI_PROVIDER=gemini" >> .env
echo "GEMINI_API_KEY=your_key_here" >> .env

# Run parser
make parse
```

### 2. Switch to OpenAI

```bash
# Edit .env
echo "AI_PROVIDER=openai" >> .env
echo "OPENAI_API_KEY=your_key_here" >> .env

# Install OpenAI package if not installed
pip install openai

# Run parser
make parse
```

### 3. Test Both Providers

```bash
# Test with Gemini
AI_PROVIDER=gemini make parse

# Test with OpenAI
AI_PROVIDER=openai make parse
```

## 📊 Model Options

### Gemini Models
- `gemini-1.5-flash` (default) - Fast, cheap, good for batch processing
- `gemini-1.5-pro` - More accurate, slower, more expensive
- `gemini-2.0-flash-exp` - Latest experimental model

### OpenAI Models
- `gpt-4o-mini` (default) - Fast, cheap, good quality
- `gpt-4o` - Best quality, most expensive
- `gpt-3.5-turbo` - Cheapest, lower quality

## 🔧 Troubleshooting

### Error: "GEMINI_API_KEY not found!"
```bash
# Check your .env file
cat .env | grep GEMINI_API_KEY

# Or set manually
export GEMINI_API_KEY=your_key_here
```

### Error: "openai package not installed"
```bash
pip install openai
```

### Error: "Invalid AI_PROVIDER"
```bash
# Make sure AI_PROVIDER is either 'gemini' or 'openai'
export AI_PROVIDER=gemini
```

### Rate Limiting
```bash
# Increase delay between requests
export AI_DELAY=2  # 2 seconds between requests
```

## 💡 Best Practices

1. **For Production**: Use Gemini (cheaper, faster, good enough)
2. **For High Accuracy**: Use OpenAI GPT-4o
3. **For Development**: Use Gemini (free tier)
4. **For Cost Optimization**: 
   - Reduce `AI_MAX_CONTENT` to send less text
   - Lower `AI_TEMPERATURE` for consistency
   - Use Flash models instead of Pro/GPT-4

## 📝 Environment Variable Priority

Script checks in this order:
1. Secret Manager (cloud only)
2. Environment variable (e.g., `GEMINI_API_KEY`)
3. `.env` file (loaded automatically)

Example:
```python
# Cloud: Checks Secret Manager first, then env var
API_KEY = get_secret("gemini-api-key") or os.environ.get("GEMINI_API_KEY")

# Local: Gets from .env (loaded as env var)
API_KEY = os.environ.get("GEMINI_API_KEY")
```

## 🎓 Advanced Configuration

### Custom Model Parameters

```bash
# For more creative responses
export AI_TEMPERATURE=0.5

# For shorter articles
export AI_MAX_CONTENT=4000

# For faster processing (more risk of rate limiting)
export AI_DELAY=0.5
```

### Switch Provider at Runtime

```bash
# Without editing .env
AI_PROVIDER=openai OPENAI_API_KEY=sk-xxx python parse_news.py output/output_xxx.csv
```

### Use Different Models

```bash
# Use Gemini Pro instead of Flash
export GEMINI_MODEL=gemini-1.5-pro

# Use GPT-4o instead of mini
export OPENAI_MODEL=gpt-4o
```

## 📖 Example Output

```
🤖 AI Provider: GEMINI
📦 Model: gemini-1.5-flash
✅ Using 'gemini-api-key' from environment variable
📄 Using latest file: output_20241126_230736.csv
✅ Read 10 articles from output_20241126_230736.csv

📊 Processing 10 articles...
────────────────────────────────────────────────────────────

[1/10] ID: 1 | Source: https://example.com/article1
   🔍 Extracting with GEMINI...
   ✅ Found: 3 quotes, 2 speakers, Province: Jawa Tengah, City: Semarang

[2/10] ID: 2 | Source: https://example.com/article2
   🔍 Extracting with GEMINI...
   ✅ Found: 1 quotes, 1 speakers, Province: N/A, City: N/A
```

## 🔗 Resources

- [Google Gemini API Docs](https://ai.google.dev/docs)
- [OpenAI API Docs](https://platform.openai.com/docs)
- [Gemini Pricing](https://ai.google.dev/pricing)
- [OpenAI Pricing](https://openai.com/pricing)
