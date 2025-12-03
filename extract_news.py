#!/usr/bin/env python3
"""
HYBRID NEWS SCRAPER - Diffbot + Trafilatura Multi-Page
Best of both worlds: Reliability + Multi-page support
With AUTO-RETRY for 403 errors
With GCS Integration for Cloud Run
"""

import requests
import trafilatura
import time
import csv
import io
from datetime import datetime
import os
import sys
from google.cloud import storage
from google.cloud import secretmanager

# ============================================================================
# SECRET MANAGER UTILITIES
# ============================================================================
def get_secret(secret_id, project_id="robotic-pact-466314-b3", version="latest"):
    """
    Retrieve secret from Google Cloud Secret Manager
    Falls back to environment variable if Secret Manager fails
    """
    try:
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{secret_id}/versions/{version}"
        response = client.access_secret_version(request={"name": name})
        secret_value = response.payload.data.decode("UTF-8")
        print(f"✅ Retrieved secret '{secret_id}' from Secret Manager")
        return secret_value
    except Exception as e:
        print(f"⚠️  Could not retrieve secret '{secret_id}' from Secret Manager: {str(e)}")
        # Fallback to environment variable
        env_value = os.environ.get(secret_id.upper().replace("-", "_"))
        if env_value:
            print(f"✅ Using '{secret_id}' from environment variable")
            return env_value
        print(f"❌ No secret or environment variable found for '{secret_id}'")
        return None

# ============================================================================
# CONFIGURATION
# ============================================================================
# Try to get DIFFBOT_TOKEN from Secret Manager, fallback to env var
DIFFBOT_TOKEN = get_secret("diffbot-key") or os.environ.get("DIFFBOT_TOKEN")

if not DIFFBOT_TOKEN:
    print("❌ ERROR: DIFFBOT_TOKEN not found!")
    print("   Please set it in Secret Manager (diffbot-key) or environment variable (DIFFBOT_TOKEN)")
    sys.exit(1)

# GCS Configuration
GCS_BUCKET_NAME = os.environ.get("GCS_BUCKET_NAME", "asia-southeast1-news-extraction-scrape-data")
GCS_INPUT_PATH = os.environ.get("GCS_INPUT_PATH", "link_input/input.csv")
GCS_OUTPUT_PATH = os.environ.get("GCS_OUTPUT_PATH", "text_output")

# Local fallback for development
LOCAL_MODE = os.environ.get("LOCAL_MODE", "false").lower() == "true"
INPUT_FILE = "link_input/input.csv"

# Scraper settings
MAX_PAGES = 5
DELAY_BETWEEN_URLS = int(os.environ.get("DELAY_BETWEEN_URLS", "13"))
DELAY_BETWEEN_PAGES = int(os.environ.get("DELAY_BETWEEN_PAGES", "8"))
MAX_RETRIES = 3
RETRY_DELAY = 5

# ============================================================================
# GCS UTILITIES
# ============================================================================
def get_gcs_client():
    """Initialize GCS client"""
    try:
        return storage.Client()
    except Exception as e:
        print(f"⚠️  Warning: Could not initialize GCS client: {str(e)}")
        return None

def get_latest_input_file(bucket_name, input_folder='link_input'):
    """Get the latest input file from GCS based on creation or modification time"""
    try:
        client = get_gcs_client()
        if not client:
            print("❌ GCS client not available")
            return None, None
        
        bucket = client.bucket(bucket_name)
        
        # List all blobs in input folder
        blobs = list(bucket.list_blobs(prefix=f"{input_folder}/"))
        
        print(f"\n🔍 Debug: Found {len(blobs)} total blobs in {input_folder}/")
        
        # Filter only CSV files (exclude directories and hidden files)
        csv_blobs = []
        for blob in blobs:
            filename = blob.name.split('/')[-1]
            print(f"   Checking: {blob.name}")
            
            # Skip directories (end with /)
            if blob.name.endswith('/'):
                print(f"      ⏭️  Skipped (directory)")
                continue
            
            # Skip hidden files (.keep, .gitkeep, etc)
            if filename.startswith('.'):
                print(f"      ⏭️  Skipped (hidden file)")
                continue
            
            # Must be CSV
            if not filename.endswith('.csv'):
                print(f"      ⏭️  Skipped (not CSV)")
                continue
            
            csv_blobs.append(blob)
            print(f"      ✅ Added to list")
        
        if not csv_blobs:
            print(f"❌ No CSV files found in gs://{bucket_name}/{input_folder}/")
            return None, None
        
        print(f"\n📊 Valid CSV files found: {len(csv_blobs)}")
        
        # Show all files with timestamps
        for blob in csv_blobs:
            latest_time = max(blob.time_created, blob.updated)
            print(f"\n   📄 {blob.name.split('/')[-1]}")
            print(f"      Created: {blob.time_created}")
            print(f"      Updated: {blob.updated}")
            print(f"      Latest:  {latest_time}")
        
        # Sort by latest timestamp (max of created or updated) descending
        csv_blobs.sort(key=lambda x: max(x.time_created, x.updated), reverse=True)
        
        latest_blob = csv_blobs[0]
        latest_filename = latest_blob.name.split('/')[-1]
        latest_time = max(latest_blob.time_created, latest_blob.updated)
        
        print(f"\n📌 SELECTED FILE: {latest_filename}")
        print(f"📅 Latest timestamp: {latest_time}")
        print(f"   - Created: {latest_blob.time_created}")
        print(f"   - Updated: {latest_blob.updated}")
        
        return latest_blob, latest_filename
        
    except Exception as e:
        print(f"❌ Error finding latest input file: {str(e)}")
        import traceback
        traceback.print_exc()
        return None, None

def read_input_from_gcs(bucket_name, input_folder='link_input'):
    """Read URLs with ID and date from the latest CSV file in GCS link_input folder"""
    url_data = []  # List of dicts with {id, date, url}
    
    try:
        # Get latest input file
        latest_blob, latest_filename = get_latest_input_file(bucket_name, input_folder)
        
        if not latest_blob:
            print("❌ No input file found, trying local mode...")
            return read_input_csv(INPUT_FILE), None
        
        # Download as string
        content = latest_blob.download_as_text()
        
        # Parse CSV
        reader = csv.DictReader(io.StringIO(content))
        
        required_cols = ['ID', 'date', 'source']
        missing_cols = [col for col in required_cols if col not in reader.fieldnames]
        if missing_cols:
            print(f"❌ Error: Columns {missing_cols} not found in CSV!")
            return url_data, None
        
        for row in reader:
            url = row['source'].strip().strip("'\"")
            if url and url.startswith('http'):
                url_data.append({
                    'id': row['ID'].strip(),
                    'date': row['date'].strip(),
                    'url': url
                })
        
        print(f"✅ Successfully read {len(url_data)} URLs from GCS: {latest_filename}")
        return url_data, latest_filename
        
    except Exception as e:
        print(f"❌ Error reading from GCS: {str(e)}")
        print(f"   Trying local fallback...")
        return read_input_csv(INPUT_FILE), None

# ============================================================================
# READ INPUT CSV (LOCAL)
# ============================================================================
def read_input_csv(file_path):
    """Read URLs with ID and date from local CSV file"""
    url_data = []  # List of dicts with {id, date, url}
    
    if not os.path.exists(file_path):
        print(f"❌ Error: File '{file_path}' not found!")
        return url_data
    
    try:
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            
            required_cols = ['ID', 'date', 'source']
            missing_cols = [col for col in required_cols if col not in reader.fieldnames]
            if missing_cols:
                print(f"❌ Error: Columns {missing_cols} not found in CSV!")
                return url_data
            
            for row in reader:
                url = row['source'].strip().strip("'\"")
                if url and url.startswith('http'):
                    url_data.append({
                        'id': row['ID'].strip(),
                        'date': row['date'].strip(),
                        'url': url
                    })
        
        print(f"✅ Successfully read {len(url_data)} URLs from {file_path}")
        return url_data
        
    except Exception as e:
        print(f"❌ Error reading CSV: {str(e)}")
        return url_data

# ============================================================================
# METHOD 1: DIFFBOT API (Most Reliable) WITH RETRY
# ============================================================================
def scrape_with_diffbot(url, token, retry_count=0):
    """Scrape using Diffbot API with retry mechanism for 403 errors"""
    api_url = "https://api.diffbot.com/v3/article"
    params = {
        'token': token,
        'url': url,
        'fields': 'title,text,author,date,siteName',
        'timeout': 30000
    }

    try:
        response = requests.get(api_url, params=params, timeout=45)
        
        if response.status_code == 200:
            data = response.json()
            
            if 'error' in data:
                error_msg = data.get('error', 'Unknown error')
                if 'rate limit' in error_msg.lower() or '429' in str(error_msg):
                    return {'error': 'RATE_LIMIT', 'message': error_msg}
                elif '403' in str(error_msg) or 'forbidden' in error_msg.lower():
                    # Retry untuk error 403
                    if retry_count < MAX_RETRIES:
                        return {'error': 'FORBIDDEN_RETRY', 'message': error_msg, 'retry_count': retry_count}
                    return {'error': 'FORBIDDEN', 'message': error_msg}
                elif 'could not download' in error_msg.lower():
                    return {'error': 'DOWNLOAD_FAILED', 'message': error_msg}
                else:
                    return {'error': 'API_ERROR', 'message': error_msg}
            
            if 'objects' in data and data['objects']:
                article = data['objects'][0]
                return {
                    'title': article.get('title', ''),
                    'content': article.get('text', ''),
                    'date': article.get('date', ''),
                    'author': article.get('author', ''),
                    'method': 'diffbot'
                }
            else:
                return {'error': 'NO_CONTENT', 'message': 'No article content found'}
        
        elif response.status_code == 429:
            return {'error': 'RATE_LIMIT', 'message': f'HTTP 429 - Too Many Requests'}
        elif response.status_code == 403:
            # Retry untuk HTTP 403
            if retry_count < MAX_RETRIES:
                return {'error': 'FORBIDDEN_RETRY', 'message': f'HTTP 403 - Access Forbidden', 'retry_count': retry_count}
            return {'error': 'FORBIDDEN', 'message': f'HTTP 403 - Access Forbidden'}
        elif response.status_code == 500:
            return {'error': 'SERVER_ERROR', 'message': f'HTTP 500 - Server Error'}
        else:
            return {'error': 'HTTP_ERROR', 'message': f'HTTP {response.status_code}'}
            
    except requests.exceptions.Timeout:
        return {'error': 'TIMEOUT', 'message': 'Request timeout (>45s)'}
    except requests.exceptions.ConnectionError:
        return {'error': 'CONNECTION_ERROR', 'message': 'Network connection failed'}
    except Exception as e:
        return {'error': 'EXCEPTION', 'message': str(e)[:100]}

# ============================================================================
# METHOD 2: TRAFILATURA (Fallback)
# ============================================================================
def scrape_with_trafilatura(url):
    """Extract article content using Trafilatura"""
    try:
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return None
        
        result = trafilatura.extract(downloaded, include_comments=False)
        
        if result:
            meta = trafilatura.bare_extraction(downloaded) if downloaded else None
            
            return {
                'title': meta.get('title', '') if meta else '',
                'content': result,
                'date': meta.get('date', '') if meta else '',
                'author': meta.get('author', '') if meta else '',
                'method': 'trafilatura'
            }
        return None
            
    except Exception as e:
        return None

# ============================================================================
# PAGINATION DETECTION
# ============================================================================
def detect_pagination(base_url):
    """Detect pagination format"""
    pages = [base_url]
    
    # Tribun format: url?page=2&s=paging_new
    if 'tribunnews.com' in base_url:
        for page_num in range(2, MAX_PAGES + 1):
            page_url = f"{base_url}?page={page_num}&s=paging_new"
            pages.append(page_url)
    else:
        # Generic patterns
        for page_num in range(2, MAX_PAGES + 1):
            pages.append(f"{base_url}?page={page_num}")
    
    return pages

# ============================================================================
# MULTI-PAGE SCRAPER
# ============================================================================
def scrape_all_pages(url, token):
    """Scrape article across all pages with retry mechanism"""
    print(f"   📄 Scraping multiple pages...")
    
    all_content = []
    extracted_data = {
        'title': '',
        'content': '',
        'date': '',
        'author': '',
        'pages_scraped': 0,
        'method': 'diffbot'
    }
    
    page_urls = detect_pagination(url)
    
    for i, page_url in enumerate(page_urls, 1):
        if i == 1:
            display_url = url[:50] + "..."
        else:
            display_url = page_url[-50:]
        
        print(f"      Page {i}: {display_url}", end=" ", flush=True)
        
        # Use Diffbot with retry mechanism
        result = None
        for attempt in range(MAX_RETRIES + 1):
            result = scrape_with_diffbot(page_url, token, retry_count=attempt)
            
            # Jika perlu retry
            if result and result.get('error') == 'FORBIDDEN_RETRY':
                retry_num = attempt + 1
                print(f"⚠️  403 (retry {retry_num}/{MAX_RETRIES})", end=" ", flush=True)
                time.sleep(RETRY_DELAY)
                continue
            else:
                # Success or error final
                break
        
        # Check if result has error
        if result and 'error' in result:
            error_type = result['error']
            error_msg = result['message']
            
            if error_type == 'RATE_LIMIT':
                print(f"⚠️  RATE LIMIT")
                print(f"         Error: {error_msg}")
                print(f"         Recommendation: Increase DELAY_BETWEEN_URLS or DELAY_BETWEEN_PAGES")
                if i == 1:
                    print(f"      Trying Trafilatura as fallback...")
                    traf_result = scrape_with_trafilatura(page_url)
                    if traf_result and traf_result['content'] and len(traf_result['content']) > 100:
                        all_content.append(traf_result['content'])
                        extracted_data['title'] = traf_result['title']
                        extracted_data['date'] = traf_result['date']
                        extracted_data['author'] = traf_result['author']
                        extracted_data['method'] = 'trafilatura'
                        words = len(traf_result['content'].split())
                        print(f"      ✅ Trafilatura success ({words} words)")
                    else:
                        print(f"      ❌ Trafilatura also failed")
                        break
                else:
                    print(f"      Stopping - rate limited on page {i}")
                    break
            
            elif error_type == 'FORBIDDEN':
                print(f"❌ FORBIDDEN (after {MAX_RETRIES} retries)")
                print(f"         Website blocked all retry attempts")
                if i == 1:
                    print(f"      Trying Trafilatura...")
                    traf_result = scrape_with_trafilatura(page_url)
                    if traf_result and traf_result['content'] and len(traf_result['content']) > 100:
                        all_content.append(traf_result['content'])
                        extracted_data['title'] = traf_result['title']
                        extracted_data['date'] = traf_result['date']
                        extracted_data['author'] = traf_result['author']
                        extracted_data['method'] = 'trafilatura'
                        words = len(traf_result['content'].split())
                        print(f"      ✅ Trafilatura success ({words} words)")
                    else:
                        print(f"      ❌ Trafilatura also failed")
                        break
                else:
                    print(f"      Stopping - page forbidden")
                    break
            
            elif error_type == 'NO_CONTENT':
                print(f"❌ NO CONTENT")
                if i > 1:
                    print(f"      Stopping - no more pages found")
                    break
                else:
                    print(f"      Trying Trafilatura...")
                    traf_result = scrape_with_trafilatura(page_url)
                    if traf_result and traf_result['content'] and len(traf_result['content']) > 100:
                        all_content.append(traf_result['content'])
                        extracted_data['title'] = traf_result['title']
                        extracted_data['date'] = traf_result['date']
                        extracted_data['author'] = traf_result['author']
                        extracted_data['method'] = 'trafilatura'
                        words = len(traf_result['content'].split())
                        print(f"      ✅ Trafilatura success ({words} words)")
                    else:
                        print(f"      ❌ Trafilatura also failed")
                        break
            
            else:
                print(f"❌ {error_type}")
                print(f"         {error_msg[:70]}")
                if i > 1:
                    print(f"      Stopping")
                    break
                else:
                    print(f"      Trying Trafilatura...")
                    traf_result = scrape_with_trafilatura(page_url)
                    if traf_result and traf_result['content'] and len(traf_result['content']) > 100:
                        all_content.append(traf_result['content'])
                        extracted_data['title'] = traf_result['title']
                        extracted_data['date'] = traf_result['date']
                        extracted_data['author'] = traf_result['author']
                        extracted_data['method'] = 'trafilatura'
                        words = len(traf_result['content'].split())
                        print(f"      ✅ Trafilatura success ({words} words)")
                    else:
                        print(f"      ❌ Trafilatura also failed")
                        break
        
        elif result and result['content'] and len(result['content']) > 100:
            # Check if content is duplicate of previous page
            if all_content and result['content'] == all_content[-1]:
                print(f"❌ DUPLICATE")
                print(f"      Content same as previous page - stopping")
                break
            
            all_content.append(result['content'])

            # Get metadata form the 1st page
            if i == 1:
                extracted_data['title'] = result['title']
                extracted_data['date'] = result['date']
                extracted_data['author'] = result['author']
            
            words = len(result['content'].split())
            print(f"✅ ({words} words)")
        
        else:
            print(f"❌ EMPTY")
            if i > 1:
                print(f"      Stopping - no more pages found")
                break
            else:
                print(f"      Page 1 is empty")
                break
        
        if i < len(page_urls):
            time.sleep(DELAY_BETWEEN_PAGES)
    
    # Combine all page
    if all_content:
        extracted_data['content'] = "\n\n---PAGE BREAK---\n\n".join(all_content)
        extracted_data['pages_scraped'] = len(all_content)
        return extracted_data
    
    return None

# ============================================================================
# BATCH PROCESSING
# ============================================================================
def batch_scrape(url_data_list, token):
    """Batch scraping dengan hybrid approach
    
    Args:
        url_data_list: List of dicts with {id, date, url}
        token: Diffbot API token
    """
    results = []
    ingestion_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    print("\n" + "=" * 80)
    print(f"🚀 HYBRID NEWS SCRAPER (Diffbot + Trafilatura)")
    print("=" * 80)
    print(f"📋 Total URLs: {len(url_data_list)}")
    print(f"📄 Max pages per article: {MAX_PAGES}")
    print(f"🔄 Priority: Diffbot → Trafilatura (fallback)")
    print(f"🔁 Retry: {MAX_RETRIES}x for 403 errors (delay {RETRY_DELAY}s)")
    print(f"⏰ Start time: {ingestion_time}")
    print("=" * 80)
    
    for i, url_data in enumerate(url_data_list, 1):
        url = url_data['url']
        record_id = url_data['id']
        record_date = url_data['date']
        
        print(f"\n[{i}/{len(url_data_list)}] ID:{record_id}")
        print(f"   URL: {url}")
        
        article_data = scrape_all_pages(url, token)
        
        if article_data and article_data['content']:
            results.append({
                'success': True,
                'id': record_id,
                'date_article': record_date,  # Use date from input
                'url': url,
                'title': article_data['title'],
                'author': article_data['author'],
                'content': article_data['content'],
                'pages_scraped': article_data['pages_scraped'],
                'method': article_data['method'],
                'ingestion_time': ingestion_time
            })
            
            word_count = len(article_data['content'].split())
            print(f"\n✅ SUCCESS via {article_data['method'].upper()}")
            print(f"   Title: {article_data['title'][:60]}...")
            print(f"   Pages: {article_data['pages_scraped']}")
            print(f"   Words: {word_count:,}")
        else:
            results.append({
                'success': False,
                'id': record_id,
                'date_article': record_date,
                'url': url,
                'error': 'All methods failed',
                'ingestion_time': ingestion_time
            })
            print(f"\n❌ FAILED")
        
        if i < len(url_data_list):
            print(f"⏳ Waiting {DELAY_BETWEEN_URLS}s before next URL...")
            time.sleep(DELAY_BETWEEN_URLS)
    
    return results

# ============================================================================
# CHECKPOINT SAVE (every 100 items)
# ============================================================================
def save_checkpoint_to_gcs(results, bucket_name, input_filename, checkpoint_num):
    """Save checkpoint results to GCS checkpoint/ folder"""
    try:
        client = get_gcs_client()
        if not client:
            print(f"      ⚠️  Cannot save checkpoint {checkpoint_num} - GCS client unavailable")
            return None
        
        bucket = client.bucket(bucket_name)
        
        # Generate checkpoint filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        if input_filename and input_filename.startswith('input_'):
            base_name = input_filename.replace('input_', 'checkpoint_', 1).replace('.csv', '')
        else:
            base_name = 'checkpoint'
        
        checkpoint_filename = f"{base_name}_{checkpoint_num:03d}_{timestamp}.csv"
        blob_path = f"checkpoint_extraction/{checkpoint_filename}"
        blob = bucket.blob(blob_path)
        
        # Create CSV in memory
        import io
        output = io.StringIO()
        writer = csv.writer(output, delimiter=',', quoting=csv.QUOTE_ALL)
        writer.writerow(['ID', 'date_article', 'ingestion_time', 'source', 'content'])
        
        success_count = 0
        for result in results:
            if result['success']:
                writer.writerow([
                    result['id'],
                    result['date'],
                    result['ingestion_time'],
                    result['url'],
                    result['content']
                ])
                success_count += 1
        
        # Upload to GCS
        blob.upload_from_string(output.getvalue(), content_type='text/csv')
        
        gcs_uri = f"gs://{bucket_name}/{blob_path}"
        print(f"      💾 Checkpoint {checkpoint_num} saved: {checkpoint_filename} ({success_count} articles)")
        
        return gcs_uri
        
    except Exception as e:
        print(f"      ⚠️  Error saving checkpoint {checkpoint_num}: {str(e)}")
        return None

# ============================================================================
# SAVE RESULTS
# ============================================================================
def save_to_gcs(results, bucket_name, output_path, input_filename=None):
    """Save results to GCS with output filename based on input filename"""
    try:
        client = get_gcs_client()
        if not client:
            print("⚠️  GCS client not available, saving locally...")
            return save_results_csv(results, input_filename=input_filename)
        
        bucket = client.bucket(bucket_name)
        
        # Generate output filename based on input filename
        if input_filename and input_filename.startswith('input_'):
            # Replace 'input_' with 'text_output_'
            output_filename = input_filename.replace('input_', 'text_output_', 1)
            print(f"📝 Input:  {input_filename}")
            print(f"📝 Output: {output_filename}")
        else:
            # Fallback to timestamp-based naming
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_filename = f"text_output_{timestamp}.csv"
            print(f"⚠️  No input filename provided, using: {output_filename}")
        
        # Force output path to text_output for extract phase
        blob_path = f"text_output/{output_filename}"
        blob = bucket.blob(blob_path)
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output, delimiter=',', quoting=csv.QUOTE_ALL)
        writer.writerow(['ID', 'date_article', 'ingestion_time', 'source', 'content'])
        
        success_count = 0
        for result in results:
            if result['success']:
                writer.writerow([
                    result['id'],
                    result['date_article'],
                    result['ingestion_time'],
                    result['url'],
                    result['content']
                ])
                success_count += 1
        
        # Upload to GCS
        blob.upload_from_string(output.getvalue(), content_type='text/csv')
        
        gcs_uri = f"gs://{bucket_name}/{blob_path}"
        print(f"\n💾 CSV saved to GCS: {gcs_uri}")
        print(f"📊 {success_count} articles exported")
        
        return gcs_uri
        
    except Exception as e:
        print(f"❌ Error saving to GCS: {str(e)}")
        print(f"   Saving locally as fallback...")
        return save_results_csv(results)

def save_results_csv(results, output_dir='text_output', input_filename=None):
    """Save results to local CSV (fallback)"""
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate output filename based on input filename
    if input_filename and input_filename.startswith('input_'):
        output_filename = input_filename.replace('input_', 'text_output_', 1)
    else:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_filename = f"text_output_{timestamp}.csv"
    
    csv_file = f"{output_dir}/{output_filename}"
    
    with open(csv_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f, delimiter=',', quoting=csv.QUOTE_ALL)
        writer.writerow([
            'ID',
            'date_article', 
            'ingestion_time', 
            'source', 
            'content'
        ])
        
        success_count = 0
        for result in results:
            if result['success']:
                writer.writerow([
                    result['id'],
                    result['date_article'],
                    result['ingestion_time'],
                    result['url'],
                    result['content']
                ])
                success_count += 1
    
    print(f"\n💾 CSV saved: {csv_file}")
    print(f"📊 {success_count} articles exported")
    return csv_file

# ============================================================================
# STATISTICS
# ============================================================================
def print_statistics(results):
    """Print scraping statistics"""
    success = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]
    
    print("\n" + "=" * 80)
    print("📊 SCRAPING STATISTICS")
    print("=" * 80)
    print(f"Total URLs: {len(results)}")
    print(f"✅ Success: {len(success)} ({len(success)/len(results)*100:.1f}%)" if results else "✅ Success: 0")
    print(f"❌ Failed: {len(failed)} ({len(failed)/len(results)*100:.1f}%)" if results else "❌ Failed: 0")
    
    if success:
        total_pages = sum(r['pages_scraped'] for r in success)
        total_words = sum(len(r['content'].split()) for r in success)
        avg_pages = total_pages / len(success)
        
        methods = {}
        for r in success:
            method = r.get('method', 'unknown')
            methods[method] = methods.get(method, 0) + 1
        
        print(f"\n📄 Pages Statistics:")
        print(f"   - Total pages: {total_pages}")
        print(f"   - Average per article: {avg_pages:.1f}")
        print(f"   - Total words: {total_words:,}")
        
        print(f"\n🔧 Success by method:")
        for method, count in methods.items():
            print(f"   - {method.upper()}: {count}")

# ============================================================================
# MAIN
# ============================================================================
if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("🚀 HYBRID NEWS SCRAPER (Diffbot + Trafilatura)")
    print("LET'S GO! 🚀")
    print("=" * 80)
    print(f"✨ Features:")
    print(f"   ✅ Multi-page article scraping")
    print(f"   ✅ Hybrid approach: Diffbot (reliable) → Trafilatura (fallback)")
    print(f"   ✅ Automatic pagination detection")
    print(f"   ✅ Auto-retry for 403 errors (up to {MAX_RETRIES}x)")
    print(f"   ✅ GCS integration for Cloud Run")
    
    # Read input
    input_filename = None
    if LOCAL_MODE:
        print(f"\n🏠 LOCAL MODE: Reading from {INPUT_FILE}")
        urls = read_input_csv(INPUT_FILE)
        input_filename = os.path.basename(INPUT_FILE)
    else:
        print(f"\n☁️  CLOUD MODE: Reading latest file from gs://{GCS_BUCKET_NAME}/link_input/")
        urls, input_filename = read_input_from_gcs(GCS_BUCKET_NAME, 'link_input')
    
    # Add input_filename to each url_data for checkpoint naming
    if urls and input_filename:
        for url_data in urls:
            url_data['input_filename'] = input_filename
    
    if not urls:
        print("\n❌ No valid URLs found. Exiting...")
        sys.exit(1)
    
    start_time = time.time()
    results = batch_scrape(urls, DIFFBOT_TOKEN)
    
    # Save results
    if LOCAL_MODE:
        csv_file = save_results_csv(results, input_filename=input_filename)
    else:
        csv_file = save_to_gcs(results, GCS_BUCKET_NAME, GCS_OUTPUT_PATH, input_filename=input_filename)
    
    print_statistics(results)
    
    duration = time.time() - start_time
    
    print("\n" + "=" * 80)
    print("✅ SCRAPING COMPLETED!")
    print("=" * 80)
    print(f"⏱️  Duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")
    print(f"📁 Results: {csv_file}")
    print("=" * 80 + "\n")