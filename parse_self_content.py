#!/usr/bin/env python3
"""
SELF CONTENT PARSER - Parse user-uploaded content directly (skip extraction)
Reads from self_content_input/ folder in GCS, processes with AI, outputs to final_output/
"""

import csv
import json
import os
import sys
import time
from datetime import datetime
from google.cloud import secretmanager
from google.cloud import storage

# ============================================================================
# SECRET MANAGER UTILITIES
# ============================================================================
def get_secret(secret_id, project_id="robotic-pact-466314-b3", version="latest"):
    """Retrieve secret from Google Cloud Secret Manager with env fallback"""
    try:
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{secret_id}/versions/{version}"
        response = client.access_secret_version(request={"name": name})
        secret_value = response.payload.data.decode("UTF-8")
        print(f"✅ Retrieved '{secret_id}' from Secret Manager")
        return secret_value
    except Exception as e:
        env_key = secret_id.upper().replace("-", "_")
        env_value = os.environ.get(env_key)
        if env_value:
            print(f"✅ Using '{secret_id}' from environment variable")
            return env_value
        print(f"⚠️  Could not retrieve '{secret_id}': {str(e)}")
        return None

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

def get_latest_file_from_gcs(bucket_name, folder_path):
    """Get the latest file from GCS folder"""
    try:
        client = get_gcs_client()
        if not client:
            return None, None
        
        bucket = client.bucket(bucket_name)
        blobs = list(bucket.list_blobs(prefix=f"{folder_path}/"))
        
        # Debug: print all files found
        print("DEBUG: Files found in GCS:")
        for b in blobs:
            print(f"  {b.name} - created: {b.time_created}, updated: {b.updated}")
        
        # Filter only CSV files
        csv_blobs = [b for b in blobs if b.name.endswith('.csv') and not b.name.endswith('/')]
        
        if not csv_blobs:
            print(f"❌ No CSV files found in gs://{bucket_name}/{folder_path}/")
            return None, None
        
        # Sort by latest timestamp (max of created/updated)
        csv_blobs.sort(key=lambda x: max(x.time_created, x.updated), reverse=True)
        latest_blob = csv_blobs[0]
        latest_filename = latest_blob.name.split('/')[-1]
        
        print(f"📄 Found {len(csv_blobs)} file(s) in GCS")
        print(f"📌 Latest file: {latest_filename}")
        print(f"📅 Created: {latest_blob.time_created}, Updated: {latest_blob.updated}")
        
        return latest_blob, latest_filename
        
    except Exception as e:
        print(f"❌ Error finding latest file in GCS: {str(e)}")
        return None, None

def download_from_gcs(bucket_name, folder_path, local_dir="self_content_input"):
    """Download latest CSV from GCS to local"""
    try:
        latest_blob, latest_filename = get_latest_file_from_gcs(bucket_name, folder_path)
        
        if not latest_blob:
            return None
        
        os.makedirs(local_dir, exist_ok=True)
        local_path = os.path.join(local_dir, latest_filename)
        latest_blob.download_to_filename(local_path)
        
        print(f"✅ Downloaded from GCS: {latest_filename}")
        return local_path
        
    except Exception as e:
        print(f"❌ Error downloading from GCS: {str(e)}")
        return None

def upload_to_gcs(local_file, bucket_name, folder_path):
    """Upload file to GCS"""
    try:
        client = get_gcs_client()
        if not client:
            return None
        
        bucket = client.bucket(bucket_name)
        filename = os.path.basename(local_file)
        blob_path = f"{folder_path}/{filename}"
        blob = bucket.blob(blob_path)
        
        blob.upload_from_filename(local_file)
        
        gcs_uri = f"gs://{bucket_name}/{blob_path}"
        print(f"✅ Uploaded to GCS: {gcs_uri}")
        return gcs_uri
        
    except Exception as e:
        print(f"❌ Error uploading to GCS: {str(e)}")
        return None

# ============================================================================
# CONFIGURATION
# ============================================================================
AI_PROVIDER = os.environ.get("AI_PROVIDER", "gemini").lower()
print(f"\n🤖 AI Provider: {AI_PROVIDER.upper()}")

if AI_PROVIDER == "gemini":
    API_KEY = get_secret("gemini-api-key")
    if not API_KEY:
        print("❌ ERROR: GEMINI_API_KEY not found!")
        sys.exit(1)
    MODEL_NAME = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    
elif AI_PROVIDER == "openai":
    API_KEY = get_secret("openai-api-key")
    if not API_KEY:
        print("❌ ERROR: OPENAI_API_KEY not found!")
        sys.exit(1)
    MODEL_NAME = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    
else:
    print(f"❌ ERROR: Invalid AI_PROVIDER '{AI_PROVIDER}'. Use 'gemini' or 'openai'")
    sys.exit(1)

print(f"📦 Model: {MODEL_NAME}")

# Import AI libraries
if AI_PROVIDER == "gemini":
    import google.generativeai as genai
    genai.configure(api_key=API_KEY)
elif AI_PROVIDER == "openai":
    try:
        from openai import OpenAI
        openai_client = OpenAI(api_key=API_KEY)
    except ImportError:
        print("❌ ERROR: openai package not installed")
        sys.exit(1)

TEMPERATURE = float(os.environ.get("AI_TEMPERATURE", "0.1"))
MAX_CONTENT_LENGTH = int(os.environ.get("AI_MAX_CONTENT", "6000"))
DELAY_BETWEEN_REQUESTS = float(os.environ.get("AI_DELAY", "1"))
AI_TIMEOUT = int(os.environ.get("AI_TIMEOUT", "60"))
AI_MAX_RETRIES = int(os.environ.get("AI_MAX_RETRIES", "3"))

OUTPUT_DIR = "final_output"
WHITELIST_DIR = "whitelist_input"

LOCAL_MODE = os.environ.get("LOCAL_MODE", "false").lower() == "true"
GCS_BUCKET_NAME = os.environ.get("GCS_BUCKET_NAME", "asia-southeast1-v2-news-extraction-plus-parser-data")
GCS_INPUT_PATH = os.environ.get("GCS_INPUT_PATH", "self_content_input")
GCS_OUTPUT_PATH = os.environ.get("GCS_OUTPUT_PATH", "final_output")

# ============================================================================
# EXTRACTION PROMPT (same as parse_news.py)
# ============================================================================
EXTRACTION_PROMPT = """Kamu adalah asisten AI yang ahli dalam menganalisis berita berbahasa Indonesia ataupun bahasa inggris.
Setara dengan professor ahli linguistik bahasa indonesia dan bahasa inggris.

Tugas kamu: Extract informasi terstruktur dari artikel berita berikut.

ARTIKEL:
{content}

INSTRUKSI:
1. Extract semua KUTIPAN/QUOTE yang ada (biasanya dalam tanda kutip "...")
2. Identifikasi SIAPA yang mengucapkan setiap kutipan:
   - Gunakan NAMA PERSIS seperti yang disebutkan di artikel (short form)
   - Contoh: "ujar Amalia" → speaker: "Amalia" (BUKAN full name)
   - Contoh: "kata Zainal" → speaker: "Zainal"
   - Contoh: "menurut Sekda" → speaker: "Sekda"
   - PENTING: Jika quote hanya diikuti kata sambung seperti "tegasnya", "katanya", "ungkapnya", "ujarnya", "tambahnya" TANPA nama:
     * Cek kalimat/paragraf SEBELUMNYA untuk mencari nama pembicara terdekat
     * Gunakan nama pembicara yang paling dekat disebutkan sebelum quote tersebut
     * Contoh: Paragraf 1: "...kata Zainal Arifin..." → Paragraf 2: "Kemerdekaan harus dijaga, tegasnya." → speaker: "Zainal Arifin"
3. Extract KOTA/KABUPATEN jika disebutkan (contoh: Semarang, Jakarta, Surabaya, Asahan)
4. Extract PROVINSI:
   - Jika provinsi disebutkan eksplisit, gunakan itu (contoh: Jawa Tengah, DKI Jakarta)
   - Jika TIDAK disebutkan tapi ada kota/kabupaten, INFER provinsinya
   - Contoh: Asahan → Sumatera Utara, Semarang → Jawa Tengah, Jakarta → DKI Jakarta

RULES:
- Quotes dan speakers harus 1:1 mapping (urutan sama) - SETIAP quote HARUS punya speaker
- Extract informasi yang EKSPLISIT disebutkan
- Untuk provinsi: boleh infer dari nama kota/kabupaten jika tidak disebutkan
- Jika tidak ada, gunakan empty array [] untuk quotes/speakers atau null untuk province/city
- Keep quotes concise, maksimal 3-5 quotes terpenting saja
- Extract only the MOST RELEVANT quotes, bukan semua

OUTPUT FORMAT (JSON only, no explanation, no markdown):
{{
  "quotes": ["kutipan"],
  "speakers": ["nama speaker"],
  "province": "nama provinsi atau null",
  "city": "nama kota atau null"
}}

Respond ONLY dengan valid JSON, tidak ada teks lain."""

# Import only helper functions from parse_news
from parse_news import (
    load_whitelist,
    match_speaker,
    print_statistics,
    _extract_with_gemini,
    _extract_with_openai
)

# ============================================================================
# AI EXTRACTION WITH TIMEOUT
# ============================================================================
def extract_info_with_ai(content: str, max_retries: int = None, timeout: int = None) -> dict:
    """
    Extract information using configured AI provider with timeout and better error handling
    
    Args:
        content: The news article text
        max_retries: Maximum retry attempts (uses AI_MAX_RETRIES env if None)
        timeout: Maximum time in seconds for one article (uses AI_TIMEOUT env if None)
    
    Returns:
        Dictionary with extracted info or error indicator
    """
    import signal
    from datetime import datetime
    
    # Use env defaults if not provided
    if max_retries is None:
        max_retries = AI_MAX_RETRIES
    if timeout is None:
        timeout = AI_TIMEOUT
    
    def timeout_handler(signum, frame):
        raise TimeoutError("AI extraction timeout")
    
    start_time = datetime.now()
    
    for attempt in range(max_retries):
        # Set timeout alarm (only works on Unix-like systems)
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout)
        
        try:
            if attempt > 0:
                print(f"      🔄 Retry attempt {attempt + 1}/{max_retries}")
                time.sleep(2)  # Small delay before retry
            
            if AI_PROVIDER == "gemini":
                result = _extract_with_gemini(content, max_retries=1)  # No nested retries
            else:
                result = _extract_with_openai(content, max_retries=1)
            
            signal.alarm(0)  # Cancel alarm
            elapsed = (datetime.now() - start_time).total_seconds()
            print(f"      ⏱️  Completed in {elapsed:.1f}s")
            return result
            
        except TimeoutError:
            signal.alarm(0)  # Cancel alarm
            elapsed = (datetime.now() - start_time).total_seconds()
            
            if attempt < max_retries - 1:
                print(f"      ⏱️  Timeout after {timeout}s (attempt {attempt + 1}) - retrying...")
                continue
            else:
                print(f"      ⏱️  Final timeout after {elapsed:.1f}s total - skipping")
                return {
                    'quotes': [],
                    'speakers': [],
                    'province': 'ERROR TIMEOUT',
                    'city': 'ERROR TIMEOUT',
                    'error': 'timeout'
                }
                
        except Exception as e:
            signal.alarm(0)  # Cancel alarm
            error_msg = str(e)[:100]
            
            if attempt < max_retries - 1:
                print(f"      ❌ Error: {error_msg} - retrying...")
                continue
            else:
                print(f"      ❌ Final error: {error_msg}")
                return {
                    'quotes': [],
                    'speakers': [],
                    'province': 'ERROR',
                    'city': 'ERROR',
                    'error': 'exception'
                }
    
    # Should not reach here
    return {
        'quotes': [],
        'speakers': [],
        'province': 'ERROR',
        'city': 'ERROR',
        'error': 'unknown'
    }

# ============================================================================
# CSV PROCESSING
# ============================================================================
def read_input_csv(file_path: str) -> list:
    """Read user-uploaded content CSV"""
    articles = []
    
    try:
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                articles.append({
                    'id': row.get('ID', ''),
                    'date': row.get('date_article', ''),
                    'source': row.get('source', ''),
                    'content': row.get('content', '')
                })
        
        print(f"✅ Read {len(articles)} articles from {os.path.basename(file_path)}")
        return articles
        
    except Exception as e:
        print(f"❌ Error reading CSV: {str(e)}")
        return []

def save_parsed_csv(results: list, input_filename: str, whitelist: list):
    """Save parsed results to CSV"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_filename = f"self_final_output_{timestamp}.csv"
    output_path = os.path.join(OUTPUT_DIR, output_filename)
    
    try:
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            fieldnames = [
                'id', 'date', 'source', 
                'quote', 'spoke_person', 
                'province', 'city',
                'jabatan', 'category', 'alias', 'fullname'
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for result in results:
                quotes = result['quotes']
                speakers = result['speakers']
                
                # Check if timeout error
                if result.get('error') == 'timeout':
                    writer.writerow({
                        'id': result['id'],
                        'date': result['date'],
                        'source': result['source'],
                        'quote': 'ERROR TIMEOUT',
                        'spoke_person': 'ERROR TIMEOUT',
                        'province': 'ERROR TIMEOUT',
                        'city': 'ERROR TIMEOUT',
                        'jabatan': '',
                        'category': '',
                        'alias': '',
                        'fullname': ''
                    })
                elif not quotes:
                    writer.writerow({
                        'id': result['id'],
                        'date': result['date'],
                        'source': result['source'],
                        'quote': '',
                        'spoke_person': '',
                        'province': result['province'] or '',
                        'city': result['city'] or '',
                        'jabatan': '',
                        'category': '',
                        'alias': '',
                        'fullname': ''
                    })
                else:
                    for i, quote in enumerate(quotes):
                        spoke_person = speakers[i] if i < len(speakers) else ''
                        match = match_speaker(spoke_person, whitelist)
                        
                        writer.writerow({
                            'id': result['id'],
                            'date': result['date'],
                            'source': result['source'],
                            'quote': quote,
                            'spoke_person': spoke_person,
                            'province': result['province'] or '',
                            'city': result['city'] or '',
                            'jabatan': match['jabatan'],
                            'category': match['category'],
                            'alias': match['alias'],
                            'fullname': match['fullname']
                        })
        
        print(f"✅ Saved parsed results to: {output_path}")
        return output_path
        
    except Exception as e:
        print(f"❌ Error saving CSV: {str(e)}")
        return None

def batch_parse(articles: list) -> list:
    """Process all articles with AI extraction"""
    results = []
    total = len(articles)
    
    print(f"\n📊 Processing {total} articles...")
    print("─" * 60)
    
    for i, article in enumerate(articles, 1):
        print(f"\n[{i}/{total}] ID: {article['id']} | Source: {article['source']}")
        
        if not article['content'] or article['content'].strip() == '':
            print("   ⏭️  Skipped (no content)")
            results.append({
                'id': article['id'],
                'date': article['date'],
                'source': article['source'],
                'quotes': [],
                'speakers': [],
                'province': None,
                'city': None
            })
            continue
        
        print(f"   🔍 Extracting with {AI_PROVIDER.upper()}...")
        extracted = extract_info_with_ai(article['content'], timeout=60)
        
        result = {
            'id': article['id'],
            'date': article['date'],
            'source': article['source'],
            'quotes': extracted['quotes'],
            'speakers': extracted['speakers'],
            'province': extracted['province'],
            'city': extracted['city'],
            'error': extracted.get('error', '')
        }
        
        results.append(result)
        
        if extracted.get('error') == 'timeout':
            print(f"   ⏱️  TIMEOUT - Skipped after 60s")
        else:
            print(f"   ✅ Found: {len(extracted['quotes'])} quotes, "
                  f"{len(extracted['speakers'])} speakers, "
                  f"Province: {extracted['province'] or 'N/A'}, "
                  f"City: {extracted['city'] or 'N/A'}")
        
        if i < total:
            time.sleep(DELAY_BETWEEN_REQUESTS)
    
    print("\n" + "─" * 60)
    return results

# ============================================================================
# MAIN
# ============================================================================
def main():
    """Main execution"""
    print("\n" + "=" * 60)
    print("🚀 SELF CONTENT PARSER (Skip Extraction)")
    print("=" * 60)
    
    if not LOCAL_MODE:
        print(f"☁️  Cloud mode: Reading from gs://{GCS_BUCKET_NAME}/{GCS_INPUT_PATH}/")
        input_file = download_from_gcs(GCS_BUCKET_NAME, GCS_INPUT_PATH)
        if not input_file:
            print("❌ Failed to download from GCS!")
            sys.exit(1)
    else:
        print(f"🏠 Local mode: Reading from self_content_input/")
        if not os.path.exists("self_content_input"):
            print("❌ self_content_input/ directory not found!")
            sys.exit(1)
        
        csv_files = [f for f in os.listdir("self_content_input") if f.endswith('.csv')]
        if not csv_files:
            print("❌ No CSV files found in self_content_input/")
            sys.exit(1)
        
        csv_files.sort(reverse=True)
        input_file = os.path.join("self_content_input", csv_files[0])
        print(f"📄 Using latest file: {csv_files[0]}")
    
    whitelist = load_whitelist()
    articles = read_input_csv(input_file)
    
    if not articles:
        print("❌ No articles to process!")
        sys.exit(1)
    
    results = batch_parse(articles)
    input_filename = os.path.basename(input_file)
    output_path = save_parsed_csv(results, input_filename, whitelist)
    
    if output_path:
        if not LOCAL_MODE:
            gcs_uri = upload_to_gcs(output_path, GCS_BUCKET_NAME, GCS_OUTPUT_PATH)
            if gcs_uri:
                print_statistics(results)
                print(f"\n✨ Done! Output: {gcs_uri}")
            else:
                print(f"\n⚠️  Local output saved but GCS upload failed: {output_path}")
        else:
            print_statistics(results)
            print(f"\n✨ Done! Output: {output_path}")
    else:
        print("\n❌ Failed to save output")
        sys.exit(1)

if __name__ == "__main__":
    main()
