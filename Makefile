.PHONY: help setup test run-local run-bg build push deploy clean

# Default target
help:
	@echo "=================================================="
	@echo "📋 News Extraction Scraper - Available Commands"
	@echo "=================================================="
	@echo ""
	@echo "Local Development:"
	@echo "  make setup       - Setup virtual environment and install dependencies"
	@echo "  make run-local   - Run scraper locally and save log to local_test_run.log"
	@echo "  make run-bg      - Run scraper in background with nohup (log/scraper.log)"
	@echo ""
	@echo "Docker & Deployment:"
	@echo "  make build       - Build Docker image (platform linux/amd64)"
	@echo "  make push        - Push Docker image to Artifact Registry"
	@echo "  make deploy      - Deploy to Cloud Run Job"
	@echo "  make all-deploy  - Build + Push + Deploy (all in one)"
	@echo ""
	@echo "Parsing (AI-powered):"
	@echo "  make parse       - Parse latest output CSV (uses AI_PROVIDER from .env)"
	@echo "  make parse-file  - Parse specific file: make parse-file FILE=output/file.csv"
	@echo "  make parse-gemini - Parse with Google Gemini (explicit override)"
	@echo "  make parse-openai - Parse with OpenAI (explicit override)"
	@echo ""
	@echo "Utilities:"
	@echo "  make clean       - Clean output files and logs"
	@echo "  make logs        - View recent Cloud Run Job logs"
	@echo "  make execute     - Execute Cloud Run Job"
	@echo ""
	@echo "=================================================="

# Setup virtual environment
setup:
	@echo "🔧 Setting up virtual environment..."
	python3 -m venv venv
	./venv/bin/pip install --upgrade pip
	./venv/bin/pip install -r requirements.txt
	@echo "✅ Setup completed!"

# Run local test with logging
run-local:
	@echo "=================================================="
	@echo "🧪 Running News Scraper (Local Mode)"
	@echo "=================================================="
	@if [ ! -f .env ]; then \
		echo "❌ Error: .env file not found!"; \
		echo "   Please create .env file with DIFFBOT_TOKEN"; \
		exit 1; \
	fi
	@if [ ! -f input/input.csv ]; then \
		echo "❌ Error: input/input.csv not found!"; \
		exit 1; \
	fi
	@echo "📂 Input: input/input.csv"
	@echo "📝 Log: local_test_run.log"
	@echo ""
	@export $$(cat .env | grep -v '^\#' | xargs) && \
		./venv/bin/python main.py 2>&1 | tee local_test_run.log
	@echo ""
	@echo "✅ Test completed!"
	@echo "📄 Log: local_test_run.log"
	@echo "📁 Output: output/"

# Run in background with nohup
run-bg:
	@echo "=================================================="
	@echo "🚀 Running News Scraper in Background"
	@echo "=================================================="
	@if [ ! -f .env ]; then \
		echo "❌ Error: .env file not found!"; \
		exit 1; \
	fi
	@if [ ! -f input/input.csv ]; then \
		echo "❌ Error: input/input.csv not found!"; \
		exit 1; \
	fi
	@mkdir -p log
	@echo "📂 Input: input/input.csv"
	@echo "📝 Log: log/scraper.log"
	@echo ""
	@export $$(cat .env | grep -v '^\#' | xargs) && \
		nohup env PYTHONUNBUFFERED=1 ./venv/bin/python main.py > log/scraper.log 2>&1 &
	@echo "✅ Scraper started in background!"
	@echo "📊 Check status: ps aux | grep main.py"
	@echo "📄 View log: tail -f log/scraper.log"
	@echo "🛑 Stop: pkill -f main.py"

# Build Docker image
build:
	@echo "🔨 Building Docker image..."
	docker build --platform linux/amd64 \
		-t asia-southeast1-docker.pkg.dev/robotic-pact-466314-b3/scraping-docker-repo/news-extraction-scraper:latest .
	@echo "✅ Build completed!"

# Push to Artifact Registry
push:
	@echo "📤 Pushing to Artifact Registry..."
	docker push asia-southeast1-docker.pkg.dev/robotic-pact-466314-b3/scraping-docker-repo/news-extraction-scraper:latest
	@echo "✅ Push completed!"

# Deploy to Cloud Run Job
deploy:
	@echo "☁️  Deploying to Cloud Run Job..."
	gcloud run jobs update news-extraction-scraper-job \
		--image=asia-southeast1-docker.pkg.dev/robotic-pact-466314-b3/scraping-docker-repo/news-extraction-scraper:latest \
		--region=asia-southeast1
	@echo "✅ Deploy completed!"

# Build + Push + Deploy
all-deploy: build push deploy
	@echo ""
	@echo "=================================================="
	@echo "✅ Full deployment completed!"
	@echo "=================================================="

# Execute Cloud Run Job
execute:
	@echo "🚀 Executing Cloud Run Job..."
	gcloud run jobs execute news-extraction-scraper-job \
		--region=asia-southeast1

# View logs
logs:
	@echo "📋 Fetching recent Cloud Run Job logs..."
	gcloud logging read \
		"resource.type=cloud_run_job AND resource.labels.job_name=news-extraction-scraper-job" \
		--limit 50 \
		--project=robotic-pact-466314-b3

# Parse latest output CSV with AI (respects AI_PROVIDER from .env)
parse:
	@echo "🤖 Parsing latest output CSV with AI..."
	@if [ ! -f .env ]; then \
		echo "❌ Error: .env file not found!"; \
		exit 1; \
	fi
	@mkdir -p log
	@export $$(cat .env | grep -v '^\#' | xargs) && \
		./venv/bin/python parse_news.py 2>&1 | tee log/parser.log
	@echo "📄 Log saved to: log/parser.log"

# Parse specific file
parse-file:
	@if [ -z "$(FILE)" ]; then \
		echo "❌ Error: FILE parameter required"; \
		echo "   Usage: make parse-file FILE=output/output_20251126_230736.csv"; \
		exit 1; \
	fi
	@echo "🤖 Parsing $(FILE) with AI..."
	@mkdir -p log
	@export $$(cat .env | grep -v '^\#' | xargs) && \
		./venv/bin/python parse_news.py $(FILE) 2>&1 | tee log/parser.log
	@echo "📄 Log saved to: log/parser.log"

# Parse with Gemini (explicit)
parse-gemini:
	@echo "🤖 Parsing with Google Gemini..."
	@if [ ! -f .env ]; then \
		echo "❌ Error: .env file not found!"; \
		exit 1; \
	fi
	@mkdir -p log
	@export $$(cat .env | grep -v '^\#' | xargs) && \
		AI_PROVIDER=gemini ./venv/bin/python parse_news.py 2>&1 | tee log/parser_gemini.log
	@echo "📄 Log saved to: log/parser_gemini.log"

# Parse with OpenAI (explicit)
parse-openai:
	@echo "🤖 Parsing with OpenAI..."
	@if [ ! -f .env ]; then \
		echo "❌ Error: .env file not found!"; \
		exit 1; \
	fi
	@mkdir -p log
	@export $$(cat .env | grep -v '^\#' | xargs) && \
		AI_PROVIDER=openai ./venv/bin/python parse_news.py 2>&1 | tee log/parser_openai.log
	@echo "📄 Log saved to: log/parser_openai.log"

# Clean output and logs
clean:
	@echo "🧹 Cleaning output files and logs..."
	rm -rf output/*.csv
	rm -rf parsed/*.csv
	rm -f local_test_run.log
	rm -f log/parser*.log
	@echo "✅ Clean completed!"
