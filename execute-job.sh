#!/bin/bash
# Execute the Cloud Run Job manually

set -e

PROJECT_ID="robotic-pact-466314-b3"
REGION="asia-southeast1"
JOB_NAME="news-extraction-and-parser-job"

echo "=================================================="
echo "▶️  Executing Cloud Run Job"
echo "=================================================="
echo ""
echo "Job: ${JOB_NAME}"
echo "Region: ${REGION}"
echo ""

gcloud run jobs execute ${JOB_NAME} \
    --region=${REGION} \
    --wait

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Job execution completed successfully!"
else
    echo ""
    echo "❌ Job execution failed!"
    exit 1
fi

echo ""
echo "To view logs:"
echo "  gcloud logging read \"resource.type=cloud_run_job AND resource.labels.job_name=${JOB_NAME}\" --limit=100 --format=json"
echo ""
