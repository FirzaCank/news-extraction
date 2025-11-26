#!/usr/bin/env python3
"""
NEWS PARSER - Extract Quotes, Speakers, and Locations using AI (Gemini or OpenAI)
Flexible script that works with both Gemini and OpenAI
Config from env (local) or Secret Manager (cloud)
"""

import csv
import json
import os
import sys
import time
from datetime import datetime
from google.cloud import secretmanager

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
        # Fallback to environment variable
        env_key = secret_id.upper().replace("-", "_")
        env_value = os.environ.get(env_key)
        if env_value:
            print(f"✅ Using '{secret_id}' from environment variable")
            return env_value
        print(f"⚠️  Could not retrieve '{secret_id}': {str(e)}")
        return None

# ============================================================================
# CONFIGURATION
# ============================================================================
# AI Provider selection (gemini or openai)
AI_PROVIDER = os.environ.get("AI_PROVIDER", "gemini").lower()
print(f"\n🤖 AI Provider: {AI_PROVIDER.upper()}")

# Get API keys based on provider
if AI_PROVIDER == "gemini":
    API_KEY = get_secret("gemini-api-key")
    if not API_KEY:
        print("❌ ERROR: GEMINI_API_KEY not found!")
        sys.exit(1)
    MODEL_NAME = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash-exp")
    
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

# Import AI libraries based on provider
if AI_PROVIDER == "gemini":
    import google.generativeai as genai
    genai.configure(api_key=API_KEY)
elif AI_PROVIDER == "openai":
    try:
        from openai import OpenAI
        openai_client = OpenAI(api_key=API_KEY)
    except ImportError:
        print("❌ ERROR: openai package not installed. Run: pip install openai")
        sys.exit(1)

# Model settings
TEMPERATURE = float(os.environ.get("AI_TEMPERATURE", "0.1"))
MAX_CONTENT_LENGTH = int(os.environ.get("AI_MAX_CONTENT", "6000"))
DELAY_BETWEEN_REQUESTS = int(os.environ.get("AI_DELAY", "1"))

# File paths
INPUT_DIR = "output"
OUTPUT_DIR = "parsed"

# ============================================================================
# EXTRACTION PROMPT
# ============================================================================
EXTRACTION_PROMPT = """Kamu adalah asisten AI yang ahli dalam menganalisis berita berbahasa Indonesia.

Tugas kamu: Extract informasi terstruktur dari artikel berita berikut.

ARTIKEL:
{content}

INSTRUKSI:
1. Extract semua KUTIPAN/QUOTE yang ada (biasanya dalam tanda kutip "...")
2. Identifikasi SIAPA yang mengucapkan setiap kutipan (nama orang/jabatan)
3. Extract PROVINSI jika disebutkan dalam berita (contoh: Jawa Tengah, DKI Jakarta)
4. Extract KOTA/KABUPATEN jika disebutkan (contoh: Semarang, Jakarta, Surabaya)

RULES:
- Quotes dan speakers harus 1:1 mapping (urutan sama)
- Hanya extract informasi yang EKSPLISIT disebutkan, jangan menebak
- Jika tidak ada, gunakan empty array [] untuk quotes/speakers atau null untuk province/city
- Keep quotes concise, maksimal 3-5 quotes terpenting saja
- Extract only the MOST RELEVANT quotes, bukan semua

OUTPUT FORMAT (JSON only, no explanation, no markdown):
{{
  "quotes": ["kutipan 1", "kutipan 2"],
  "speakers": ["nama speaker 1", "nama speaker 2"],
  "province": "nama provinsi atau null",
  "city": "nama kota atau null"
}}

Respond ONLY dengan valid JSON, tidak ada teks lain."""

# ============================================================================
# AI EXTRACTION FUNCTIONS
# ============================================================================
def extract_info_with_ai(content: str, max_retries: int = 3) -> dict:
    """
    Extract information using configured AI provider
    
    Args:
        content: The news article text
        max_retries: Maximum retry attempts
    
    Returns:
        Dictionary with extracted info
    """
    if AI_PROVIDER == "gemini":
        return _extract_with_gemini(content, max_retries)
    else:
        return _extract_with_openai(content, max_retries)


def _extract_with_gemini(content: str, max_retries: int) -> dict:
    """Extract using Google Gemini"""
    for attempt in range(max_retries):
        try:
            model = genai.GenerativeModel(
                model_name=MODEL_NAME,
                generation_config={
                    "temperature": TEMPERATURE,
                    "top_p": 0.95,
                    "top_k": 40,
                    "max_output_tokens": 8192,
                }
            )
            
            prompt = EXTRACTION_PROMPT.format(content=content[:MAX_CONTENT_LENGTH])
            response = model.generate_content(prompt)
            
            # Check if response is valid
            if not response:
                print(f"      ⚠️  Empty response (attempt {attempt + 1})")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                return _empty_result()
            
            # Check if response was blocked or has no text
            if not response.candidates:
                print(f"      ⚠️  No candidates in response (attempt {attempt + 1})")
                # Check for prompt feedback (safety blocking)
                if hasattr(response, 'prompt_feedback'):
                    feedback = response.prompt_feedback
                    if hasattr(feedback, 'block_reason'):
                        block_reason_map = {
                            1: 'BLOCK_REASON_UNSPECIFIED',
                            2: 'SAFETY',
                            3: 'OTHER'
                        }
                        reason = block_reason_map.get(feedback.block_reason, f'UNKNOWN({feedback.block_reason})')
                        print(f"      🚫 Prompt blocked: {reason}")
                        if hasattr(feedback, 'safety_ratings'):
                            for rating in feedback.safety_ratings:
                                print(f"         - {rating.category.name}: {rating.probability.name}")
                return _empty_result()
            
            candidate = response.candidates[0]
            
            # Check finish reason
            if hasattr(candidate, 'finish_reason') and candidate.finish_reason != 1:  # 1 = STOP
                reason_map = {
                    0: 'FINISH_REASON_UNSPECIFIED',
                    1: 'STOP',
                    2: 'MAX_TOKENS',
                    3: 'SAFETY',
                    4: 'RECITATION',
                    5: 'OTHER'
                }
                reason = reason_map.get(candidate.finish_reason, f'UNKNOWN({candidate.finish_reason})')
                print(f"      ⚠️  Response stopped: {reason} (attempt {attempt + 1})")
                
                # Show safety ratings if available
                if hasattr(candidate, 'safety_ratings') and candidate.safety_ratings:
                    print(f"      🔒 Safety ratings:")
                    for rating in candidate.safety_ratings:
                        if hasattr(rating, 'category') and hasattr(rating, 'probability'):
                            print(f"         - {rating.category.name}: {rating.probability.name}")
                
                return _empty_result()
            
            # Try to get text - THIS is where the error happens
            try:
                response_text = response.text
            except (ValueError, AttributeError) as e:
                error_msg = str(e)
                print(f"      ⚠️  Cannot access response.text (attempt {attempt + 1})")
                print(f"         Error: {error_msg[:100]}")
                
                # Try to access parts directly
                try:
                    if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                        parts = candidate.content.parts
                        if parts and hasattr(parts[0], 'text'):
                            response_text = parts[0].text
                            print(f"      ✅ Retrieved text from parts")
                        else:
                            print(f"      ❌ No text in parts")
                            return _empty_result()
                    else:
                        print(f"      ❌ No content.parts available")
                        return _empty_result()
                except Exception as inner_e:
                    print(f"      ❌ Failed to extract text: {str(inner_e)[:50]}")
                    return _empty_result()
            
            if not response_text:
                print(f"      ⚠️  Empty response text (attempt {attempt + 1})")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                return _empty_result()
            
            return _parse_ai_response(response_text, attempt, max_retries)
        
        except Exception as e:
            print(f"      ⚠️  Gemini error: {str(e)[:80]} (attempt {attempt + 1})")
            print(f"         Full error: {type(e).__name__}: {str(e)[:150]}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
    
    return _empty_result()


def _extract_with_openai(content: str, max_retries: int) -> dict:
    """Extract using OpenAI"""
    for attempt in range(max_retries):
        try:
            response = openai_client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {
                        "role": "system",
                        "content": "Kamu adalah asisten AI yang ahli dalam menganalisis berita berbahasa Indonesia. Selalu respond dengan JSON yang valid."
                    },
                    {
                        "role": "user",
                        "content": EXTRACTION_PROMPT.format(content=content[:MAX_CONTENT_LENGTH])
                    }
                ],
                temperature=TEMPERATURE,
                max_tokens=2048,
                response_format={"type": "json_object"}
            )
            
            response_text = response.choices[0].message.content
            
            if not response_text:
                print(f"      ⚠️  Empty response (attempt {attempt + 1})")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                return _empty_result()
            
            return _parse_ai_response(response_text, attempt, max_retries)
        
        except Exception as e:
            print(f"      ⚠️  OpenAI error: {str(e)[:80]} (attempt {attempt + 1})")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
    
    return _empty_result()


def _parse_ai_response(response_text: str, attempt: int, max_retries: int) -> dict:
    """Parse and validate AI response"""
    response_text = response_text.strip()
    
    # Clean markdown code blocks if present
    if response_text.startswith("```json"):
        response_text = response_text.replace("```json", "").replace("```", "").strip()
    elif response_text.startswith("```"):
        response_text = response_text.replace("```", "").strip()
    
    try:
        result = json.loads(response_text)
        
        if not isinstance(result, dict):
            print(f"      ⚠️  Invalid structure (attempt {attempt + 1})")
            return _empty_result()
        
        # Ensure all required keys exist with proper defaults
        return {
            'quotes': result.get('quotes', []) or [],
            'speakers': result.get('speakers', []) or [],
            'province': result.get('province') or None,
            'city': result.get('city') or None
        }
        
    except json.JSONDecodeError as e:
        print(f"      ⚠️  JSON error: {str(e)[:50]} (attempt {attempt + 1})")
        return _empty_result()


def _empty_result() -> dict:
    """Return empty result structure"""
    return {
        'quotes': [],
        'speakers': [],
        'province': None,
        'city': None
    }

# ============================================================================
# CSV PROCESSING
# ============================================================================
def read_input_csv(file_path: str) -> list:
    """Read scraped news from CSV"""
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


def save_parsed_csv(results: list, input_filename: str):
    """Save parsed results to CSV"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Generate output filename
    if input_filename.startswith('output_'):
        output_filename = input_filename.replace('output_', 'parsed_', 1)
    else:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_filename = f"parsed_{timestamp}.csv"
    
    output_path = os.path.join(OUTPUT_DIR, output_filename)
    
    try:
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            fieldnames = [
                'id', 'date', 'source', 
                'quotes', 'speakers', 
                'province', 'city'
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for result in results:
                # Convert lists to JSON strings for CSV
                writer.writerow({
                    'id': result['id'],
                    'date': result['date'],
                    'source': result['source'],
                    'quotes': json.dumps(result['quotes'], ensure_ascii=False),
                    'speakers': json.dumps(result['speakers'], ensure_ascii=False),
                    'province': result['province'] or '',
                    'city': result['city'] or ''
                })
        
        print(f"✅ Saved parsed results to: {output_path}")
        return output_path
        
    except Exception as e:
        print(f"❌ Error saving CSV: {str(e)}")
        return None

# ============================================================================
# BATCH PROCESSING
# ============================================================================
def batch_parse(articles: list) -> list:
    """Process all articles with AI extraction"""
    results = []
    total = len(articles)
    
    print(f"\n📊 Processing {total} articles...")
    print("─" * 60)
    
    for i, article in enumerate(articles, 1):
        print(f"\n[{i}/{total}] ID: {article['id']} | Source: {article['source']}")
        
        # Skip if no content
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
        
        # Extract with AI
        print(f"   🔍 Extracting with {AI_PROVIDER.upper()}...")
        extracted = extract_info_with_ai(article['content'])
        
        # Merge with original data
        result = {
            'id': article['id'],
            'date': article['date'],
            'source': article['source'],
            'quotes': extracted['quotes'],
            'speakers': extracted['speakers'],
            'province': extracted['province'],
            'city': extracted['city']
        }
        
        results.append(result)
        
        # Print summary
        print(f"   ✅ Found: {len(extracted['quotes'])} quotes, "
              f"{len(extracted['speakers'])} speakers, "
              f"Province: {extracted['province'] or 'N/A'}, "
              f"City: {extracted['city'] or 'N/A'}")
        
        # Rate limiting
        if i < total:
            time.sleep(DELAY_BETWEEN_REQUESTS)
    
    print("\n" + "─" * 60)
    return results

# ============================================================================
# STATISTICS
# ============================================================================
def print_statistics(results: list):
    """Print parsing statistics"""
    total = len(results)
    with_quotes = sum(1 for r in results if r['quotes'])
    with_speakers = sum(1 for r in results if r['speakers'])
    with_province = sum(1 for r in results if r['province'])
    with_city = sum(1 for r in results if r['city'])
    
    total_quotes = sum(len(r['quotes']) for r in results)
    total_speakers = sum(len(r['speakers']) for r in results)
    
    print("\n📈 PARSING STATISTICS")
    print("═" * 60)
    print(f"Total articles:      {total}")
    print(f"With quotes:         {with_quotes} ({with_quotes/total*100:.1f}%)")
    print(f"With speakers:       {with_speakers} ({with_speakers/total*100:.1f}%)")
    print(f"With province:       {with_province} ({with_province/total*100:.1f}%)")
    print(f"With city:           {with_city} ({with_city/total*100:.1f}%)")
    print(f"─" * 60)
    print(f"Total quotes found:  {total_quotes}")
    print(f"Total speakers found: {total_speakers}")
    print(f"Avg quotes/article:  {total_quotes/total:.1f}")
    print("═" * 60)

# ============================================================================
# MAIN FUNCTION
# ============================================================================
def main():
    """Main execution function"""
    if len(sys.argv) < 2:
        # Find latest output file
        if not os.path.exists(INPUT_DIR):
            print(f"❌ Input directory '{INPUT_DIR}' not found!")
            sys.exit(1)
        
        csv_files = [f for f in os.listdir(INPUT_DIR) if f.endswith('.csv')]
        if not csv_files:
            print(f"❌ No CSV files found in '{INPUT_DIR}'")
            sys.exit(1)
        
        # Get most recent file
        csv_files.sort(reverse=True)
        input_file = os.path.join(INPUT_DIR, csv_files[0])
        print(f"📄 Using latest file: {csv_files[0]}")
    else:
        input_file = sys.argv[1]
        if not os.path.exists(input_file):
            print(f"❌ File not found: {input_file}")
            sys.exit(1)
    
    # Read input
    articles = read_input_csv(input_file)
    if not articles:
        print("❌ No articles to process!")
        sys.exit(1)
    
    # Parse with AI
    results = batch_parse(articles)
    
    # Save output
    input_filename = os.path.basename(input_file)
    output_path = save_parsed_csv(results, input_filename)
    
    if output_path:
        # Print statistics
        print_statistics(results)
        print(f"\n✨ Done! Output: {output_path}")
    else:
        print("\n❌ Failed to save output")
        sys.exit(1)

if __name__ == "__main__":
    main()
