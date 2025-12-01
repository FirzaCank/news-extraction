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
	@echo "Docker & Cloud Run Job Deployment:"
	@echo "  make build-push  - Build and push Docker image to Artifact Registry"
	@echo "  make deploy-job  - Deploy/Update Cloud Run Job"
	@echo "  make all-deploy  - Build + Push + Deploy (all in one)"
	@echo "  make execute-job - Execute the Cloud Run Job manually"
	@echo "  make logs-job    - View Cloud Run Job logs"
	@echo ""
	@echo "Parse-Only Job (Self Content):"
	@echo "  make build-push-parse-only  - Build and push Parse-Only Docker image"
	@echo "  make deploy-parse-only      - Deploy/Update Parse-Only Cloud Run Job"
	@echo "  make all-deploy-parse-only  - Build + Push + Deploy Parse-Only (all in one)"
	@echo "  make execute-parse-only     - Execute Parse-Only Job manually"
	@echo "  make logs-parse-only        - View Parse-Only Job logs"
	@echo ""
	@echo "Parsing (AI-powered):"
	@echo "  make parse       - Parse latest output CSV (uses AI_PROVIDER from .env)"
	@echo "  make parse-file  - Parse specific file: make parse-file FILE=output/file.csv"
	@echo "  make parse-gemini - Parse with Google Gemini (explicit override)"
	@echo "  make parse-openai - Parse with OpenAI (explicit override)"
	@echo ""
	@echo "Full Pipeline:"
	@echo "  make full-run    - Run complete pipeline: Scrape → Parse (auto)"
	@echo "  make scrape-parse - Alias for full-run"
	@echo ""
	@echo "Utilities:"
	@echo "  make clean       - Clean output files and logs"
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
	@if [ ! -f link_input/input.csv ]; then \
		echo "❌ Error: link_input/input.csv not found!"; \
		exit 1; \
	fi
	@echo "📂 Input: link_input/input.csv"
	@echo "📝 Log: local_test_run.log"
	@echo ""
	@export $$(cat .env | grep -v '^\#' | xargs) && \
		./venv/bin/python extract_news.py 2>&1 | tee local_test_run.log
	@echo ""
	@echo "✅ Test completed!"
	@echo "📄 Log: local_test_run.log"
	@echo "📁 Output: text_output/"

# Run in background with nohup
run-bg:
	@echo "=================================================="
	@echo "🚀 Running News Scraper in Background"
	@echo "=================================================="
	@if [ ! -f .env ]; then \
		echo "❌ Error: .env file not found!"; \
		exit 1; \
	fi
	@if [ ! -f link_input/input.csv ]; then \
		echo "❌ Error: link_input/input.csv not found!"; \
		exit 1; \
	fi
	@mkdir -p log
	@echo "📂 Input: link_input/input.csv"
	@echo "📝 Log: log/scraper.log"
	@echo ""
	@export $$(cat .env | grep -v '^\#' | xargs) && \
		nohup env PYTHONUNBUFFERED=1 ./venv/bin/python extract_news.py > log/scraper.log 2>&1 &
	@echo "✅ Scraper started in background!"
	@echo "📊 Check status: ps aux | grep extract_news.py"
	@echo "📄 View log: tail -f log/scraper.log"
	@echo "🛑 Stop: pkill -f extract_news.py"

# Build and Push Docker image to Artifact Registry
build-push:
	@chmod +x build-and-push.sh
	@./build-and-push.sh

# Deploy Cloud Run Job
deploy-job:
	@chmod +x deploy-cloud-run-job.sh
	@./deploy-cloud-run-job.sh

# Build + Push + Deploy (all in one)
all-deploy: build-push deploy-job
	@echo ""
	@echo "=================================================="
	@echo "✅ Full deployment completed!"
	@echo "=================================================="

# Build and Push Parse-Only Docker image
build-push-parse-only:
	@chmod +x build-and-push-parse-only.sh
	@./build-and-push-parse-only.sh

# Deploy Parse-Only Cloud Run Job
deploy-parse-only:
	@chmod +x deploy-parse-only-job.sh
	@./deploy-parse-only-job.sh

# Build + Push + Deploy Parse-Only (all in one)
all-deploy-parse-only: build-push-parse-only deploy-parse-only
	@echo ""
	@echo "=================================================="
	@echo "✅ Parse-Only deployment completed!"
	@echo "=================================================="

# Execute Cloud Run Job
execute-job:
	@chmod +x execute-job.sh
	@./execute-job.sh

# Execute Parse-Only Cloud Run Job
execute-parse-only:
	@chmod +x execute-parse-only-job.sh
	@./execute-parse-only-job.sh

# View Cloud Run Job logs
logs-job:
	@echo "📋 Fetching recent Cloud Run Job logs..."
	gcloud logging read \
		"resource.type=cloud_run_job AND resource.labels.job_name=news-extraction-and-parser-job" \
		--limit 100 \
		--project=robotic-pact-466314-b3 \
		--format=json

# View Parse-Only Cloud Run Job logs
logs-parse-only:
	@echo "📋 Fetching recent Parse-Only Job logs..."
	gcloud logging read \
		"resource.type=cloud_run_job AND resource.labels.job_name=self-content-parser-job" \
		--limit 100 \
		--project=robotic-pact-466314-b3 \
		--format=json

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

# Full pipeline: Scrape → Parse
full-run:
	@echo "=================================================="
	@echo "🚀 FULL PIPELINE: Scraping → Parsing"
	@echo "=================================================="
	@echo ""
	@echo "Step 1: Running scraper..."
	@echo "────────────────────────────────────────────────"
	@if [ ! -f .env ]; then \
		echo "❌ Error: .env file not found!"; \
		exit 1; \
	fi
	@if [ ! -f link_input/input.csv ]; then \
		echo "❌ Error: link_input/input.csv not found!"; \
		exit 1; \
	fi
	@mkdir -p log
	@export $$(cat .env | grep -v '^\#' | xargs) && \
		(./venv/bin/python extract_news.py 2>&1 && echo "" && echo "Step 2: Running parser..." && echo "────────────────────────────────────────────────" && ./venv/bin/python parse_news.py 2>&1) | tee log/full_pipeline.log
	@echo ""
	@echo "=================================================="
	@echo "✅ FULL PIPELINE COMPLETED!"
	@echo "=================================================="
	@echo "📄 Scraper output: text_output/text_output_extraction_*.csv"
	@echo "📄 Parser output: final_output/final_output_parsed_*.csv"
	@echo "📄 Log: log/full_pipeline.log"
	@echo ""

# Alias for full-run
scrape-parse: full-run

# Clean output and logs
clean:
	@echo "🧹 Cleaning output files and logs..."
	rm -rf text_output/text_output_extraction_*.csv
	rm -rf final_output/final_output_parsed_*.csv
	rm -f local_test_run.log
	rm -f log/parser*.log
	rm -f log/full_pipeline.log
	@echo "✅ Clean completed!"
