# Step-by-Step: Build Docker & Update Cloud Run Job

Panduan lengkap untuk build Docker image, push ke Artifact Registry, dan update Cloud Run Job.

---

## Prerequisites

Pastikan Anda sudah:
- ✅ Install Docker Desktop dan sudah running
- ✅ Install gcloud CLI
- ✅ Login ke GCP: `gcloud auth login`
- ✅ Docker auth sudah configured: `gcloud auth configure-docker asia-southeast1-docker.pkg.dev`

---

## Step 1: Set GCP Project

```bash
gcloud config set project robotic-pact-466314-b3
```

**Output:**
```
Updated property [core/project].
```

---

## Step 2: Build Docker Image (Platform AMD64)

⚠️ **Penting:** Gunakan `--platform linux/amd64` untuk Cloud Run compatibility

```bash
docker build --platform linux/amd64 \
  -t asia-southeast1-docker.pkg.dev/robotic-pact-466314-b3/scraping-docker-repo/news-extraction-scraper:latest .
```

**Output:**
```
[+] Building 40.1s (14/14) FINISHED
...
=> exporting to image
✓ Successfully built image
```

**Estimasi waktu:** 30-60 detik (tergantung koneksi internet)

---

## Step 3: Push Image ke Artifact Registry

```bash
docker push asia-southeast1-docker.pkg.dev/robotic-pact-466314-b3/scraping-docker-repo/news-extraction-scraper:latest
```

**Output:**
```
The push refers to repository [asia-southeast1-docker.pkg.dev/...]
6edd47b19b99: Pushed
...
latest: digest: sha256:290768d803db... size: 856
```

**Estimasi waktu:** 1-3 menit (tergantung koneksi internet)

---

## Step 4: Update Cloud Run Job

```bash
gcloud run jobs update news-extraction-scraper-job \
  --image=asia-southeast1-docker.pkg.dev/robotic-pact-466314-b3/scraping-docker-repo/news-extraction-scraper:latest \
  --region=asia-southeast1
```

**Output:**
```
Updating Cloud Run job [news-extraction-scraper-job]...
✓ Updating job... Done.
Job [news-extraction-scraper-job] has successfully been updated.
```

**Estimasi waktu:** 10-20 detik

---

## Step 5: Execute Job (Optional - untuk test)

```bash
gcloud run jobs execute news-extraction-scraper-job \
  --region=asia-southeast1
```

**Output:**
```
✓ Creating execution... Done.
✓ Routing traffic...
Execution [news-extraction-scraper-job-xxxxx] has successfully started running.

To view logs:
  gcloud logging read "resource.labels.job_name=news-extraction-scraper-job" --limit 50
```

---

## Step 6: Monitor Logs (Optional)

### Real-time logs:
```bash
gcloud logging tail \
  "resource.type=cloud_run_job AND resource.labels.job_name=news-extraction-scraper-job" \
  --project=robotic-pact-466314-b3
```

### Last 50 logs:
```bash
gcloud logging read \
  "resource.type=cloud_run_job AND resource.labels.job_name=news-extraction-scraper-job" \
  --limit 50 \
  --project=robotic-pact-466314-b3
```

### Via Console:
https://console.cloud.google.com/run/jobs/details/asia-southeast1/news-extraction-scraper-job?project=robotic-pact-466314-b3

---

## Quick Commands (All in One)

Jika ingin menjalankan semua step sekaligus:

```bash
# Set project
gcloud config set project robotic-pact-466314-b3

# Build
docker build --platform linux/amd64 \
  -t asia-southeast1-docker.pkg.dev/robotic-pact-466314-b3/scraping-docker-repo/news-extraction-scraper:latest .

# Push
docker push asia-southeast1-docker.pkg.dev/robotic-pact-466314-b3/scraping-docker-repo/news-extraction-scraper:latest

# Update job
gcloud run jobs update news-extraction-scraper-job \
  --image=asia-southeast1-docker.pkg.dev/robotic-pact-466314-b3/scraping-docker-repo/news-extraction-scraper:latest \
  --region=asia-southeast1

# Execute (optional)
gcloud run jobs execute news-extraction-scraper-job --region=asia-southeast1

echo "✅ Deployment completed!"
```

---

## Troubleshooting

### Error: "Container manifest must support amd64/linux"
**Solusi:** Tambahkan `--platform linux/amd64` saat build
```bash
docker build --platform linux/amd64 -t <image-name> .
```

### Error: "permission denied"
**Solusi:** Configure Docker authentication
```bash
gcloud auth configure-docker asia-southeast1-docker.pkg.dev
```

### Error: "Docker daemon not running"
**Solusi:** Start Docker Desktop
```bash
open -a Docker  # macOS
```

### Error: "Image not found" saat update job
**Solusi:** Pastikan push berhasil, cek di Artifact Registry:
```bash
gcloud artifacts docker images list \
  asia-southeast1-docker.pkg.dev/robotic-pact-466314-b3/scraping-docker-repo/news-extraction-scraper
```

---

## Environment Variables (Cloud Run Job)

Job sudah dikonfigurasi dengan env vars berikut:

| Variable | Value |
|----------|-------|
| `GCS_BUCKET_NAME` | `asia-southeast1-news-extraction-scrape-data` |
| `GCS_OUTPUT_PATH` | `output` |
| `LOCAL_MODE` | `false` |
| `DIFFBOT_TOKEN` | From Secret Manager: `diffbot-key:latest` |

Untuk update env vars:
```bash
gcloud run jobs update news-extraction-scraper-job \
  --set-env-vars="KEY=VALUE" \
  --region=asia-southeast1
```

---

## Notes

- **Image size:** ~400MB (Python 3.11 + dependencies)
- **Build time:** 30-60 seconds
- **Push time:** 1-3 minutes
- **Deploy time:** 10-20 seconds
- **Platform:** linux/amd64 (Cloud Run compatible)
- **Memory limit:** 2Gi
- **CPU limit:** 1 core
- **Timeout:** 3600 seconds (1 hour)
- **Max retries:** 2

---

## Version History

| Date | Digest | Changes |
|------|--------|---------|
| 2025-11-20 | `sha256:290768d8...` | Update main.py logic |
| 2025-10-19 | `sha256:d03ddaa6...` | Initial version |

---

## Related Links

- **Artifact Registry:** https://console.cloud.google.com/artifacts/docker/robotic-pact-466314-b3/asia-southeast1/scraping-docker-repo/news-extraction-scraper
- **Cloud Run Job:** https://console.cloud.google.com/run/jobs/details/asia-southeast1/news-extraction-scraper-job?project=robotic-pact-466314-b3
- **GitHub Repo:** https://github.com/FirzaCank/news-extraction

---

## Contact

Jika ada masalah, hubungi: vislog360@gmail.com
