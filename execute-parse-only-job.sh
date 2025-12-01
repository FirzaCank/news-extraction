#!/bin/bash

# Execute Self Content Parser Cloud Run Job

set -e

JOB_NAME="self-content-parser-job"
REGION="asia-southeast1"
PROJECT_ID="robotic-pact-466314-b3"

echo "=================================================="
echo "🚀 Executing Self Content Parser Job"
echo "=================================================="
echo ""
echo "Job: ${JOB_NAME}"
echo "Region: ${REGION}"
echo ""

gcloud run jobs execute ${JOB_NAME} \
    --region=${REGION} \
    --project=${PROJECT_ID} \
    --wait

echo ""
echo "=================================================="
echo "✅ Job execution completed!"
echo "=================================================="
echo ""
echo "To view logs:"
echo "  make logs-parse-only"
echo "  or"
echo "  gcloud logging read \"resource.type=cloud_run_job AND resource.labels.job_name=${JOB_NAME}\" --limit=50"
