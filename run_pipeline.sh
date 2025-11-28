#!/bin/bash
set -e

echo "=================================================="
echo "🚀 NEWS EXTRACTION & PARSING PIPELINE"
echo "=================================================="
echo ""
echo "📅 Started at: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# Step 1: Extract news with Diffbot
echo "Step 1: Extracting news articles..."
echo "────────────────────────────────────────────────"
python extract_news.py
EXTRACT_EXIT_CODE=$?

if [ $EXTRACT_EXIT_CODE -ne 0 ]; then
    echo "❌ Extract news failed with exit code $EXTRACT_EXIT_CODE"
    exit $EXTRACT_EXIT_CODE
fi

echo ""
echo "Step 2: Parsing with AI (Gemini)..."
echo "────────────────────────────────────────────────"
python parse_news.py
PARSE_EXIT_CODE=$?

if [ $PARSE_EXIT_CODE -ne 0 ]; then
    echo "❌ Parse news failed with exit code $PARSE_EXIT_CODE"
    exit $PARSE_EXIT_CODE
fi

echo ""
echo "=================================================="
echo "✅ PIPELINE COMPLETED SUCCESSFULLY!"
echo "=================================================="
echo "📅 Finished at: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

exit 0
