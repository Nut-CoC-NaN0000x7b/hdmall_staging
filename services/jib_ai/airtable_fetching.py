#ATB url = https://airtable.com/app2CSihSxsRF1acK/tblfqJRo9JmbRh9NU/viwvS94l2hmDJCJyr?blocks=hide
import os
import requests
import asyncio
import anthropic
import base64
import httpx
from typing import Dict, List, Any, Optional
from anthropic import AsyncAnthropicBedrock

AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
BASE_ID = "app2CSihSxsRF1acK"
MAIN_TABLE_ID = "tblfqJRo9JmbRh9NU"

# Configuration for AWS Bedrock (matching sonnet4_bot.py)
class Config:
    AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY')
    AWS_SECRET_KEY = os.getenv('AWS_SECRET_KEY')
    REGION = 'us-west-2'
    MODEL = {
        "sonnet_4": "us.anthropic.claude-sonnet-4-20250514-v1:0",
        "sonnet_3_7": "us.anthropic.claude-3-7-sonnet-20250219-v1:0",
    }
    MAX_TOKENS = 1000
    TEMP = 0.0

def fetch_by_url(url):
    headers = {
        "Authorization": f"Bearer {AIRTABLE_API_KEY}"
    }
    # Filter records where SKU URL matches the provided url
    filter_formula = f"FIND('{url}', {{SKU URL}}) > 0"
    params = {
        "filterByFormula": filter_formula
    }
    atb_url = f"https://api.airtable.com/v0/{BASE_ID}/{MAIN_TABLE_ID}"
    response = requests.get(atb_url, headers=headers, params=params)
    return response.json()

def fetch_linked_record(record_id: str, table_id: str) -> Dict[str, Any]:
    """Fetch a linked record by its ID from a specific table"""
    headers = {
        "Authorization": f"Bearer {AIRTABLE_API_KEY}"
    }
    url = f"https://api.airtable.com/v0/{BASE_ID}/{table_id}/{record_id}"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    return {}

def decode_linked_records(record_ids: List[str], table_id: str) -> List[Dict[str, Any]]:
    """Decode multiple linked records"""
    decoded_records = []
    for record_id in record_ids:
        linked_record = fetch_linked_record(record_id, table_id)
        if linked_record:
            decoded_records.append(linked_record)
    return decoded_records

def extract_attachment_urls(attachments: List[Dict]) -> List[str]:
    """Extract URLs from attachment fields, using large thumbnails (~1024px) for optimal AI analysis"""
    urls = []
    for attachment in attachments:
        if 'url' in attachment:
            # Check if thumbnails are available
            thumbnails = attachment.get('thumbnails', {})
            
            if thumbnails and 'large' in thumbnails:
                # Use large thumbnail (~1024px) - optimal for AI analysis, not too small
                urls.append(thumbnails['large']['url'])
                print(f"🖼️ [THUMBNAIL-LARGE] Using large thumbnail (~1024px) for optimal AI analysis")
            else:
                # Use full URL as fallback (will be resized by _url_to_base64_content)
                urls.append(attachment['url'])
                print(f"🖼️ [FULL-URL] No large thumbnail available, using full URL (will be resized to 500x500)")
    
    return urls

def extract_attachment_info(attachments: List[Dict]) -> List[Dict]:
    """Extract useful info from attachments (filename, url, size) and include thumbnail URLs"""
    attachment_info = []
    for att in attachments:
        if 'url' in att:
            info = {
                'filename': att.get('filename', ''),
                'url': att['url'],
                'size': att.get('size', 0),
                'type': att.get('type', '')
            }
            
            # Add thumbnail URLs if available
            thumbnails = att.get('thumbnails', {})
            if thumbnails:
                # Airtable provides: small (~72px), large (~1024px), full (original)
                # Use large thumbnail for AI analysis (~1024px - optimal size)
                if 'large' in thumbnails:
                    info['thumbnail_large'] = thumbnails['large']['url']
                if 'small' in thumbnails:
                    info['thumbnail_small'] = thumbnails['small']['url']
                if 'full' in thumbnails:
                    info['thumbnail_full'] = thumbnails['full']['url']
                    
            attachment_info.append(info)
    
    return attachment_info

def decode_airtable_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """Decode a single Airtable record, converting linked records and attachments"""
    fields = record.get('fields', {})
    decoded_fields = {}
    
    for field_name, field_value in fields.items():
        if field_name == 'Campaign Name' and isinstance(field_value, list):
            # These are linked records - you'd need to know the table ID to fetch them
            # For now, just keep the IDs but mark them as linked records
            decoded_fields[field_name] = {
                'type': 'linked_records',
                'record_ids': field_value,
                'note': 'Use decode_linked_records() to fetch full data'
            }
        elif 'Artwork' in field_name and isinstance(field_value, list) and field_value:
            # These are attachment fields
            if isinstance(field_value[0], dict) and 'url' in field_value[0]:
                decoded_fields[f"{field_name}_urls"] = extract_attachment_urls(field_value)
                decoded_fields[f"{field_name}_info"] = extract_attachment_info(field_value)
        else:
            decoded_fields[field_name] = field_value
    
    return {
        'id': record.get('id'),
        'createdTime': record.get('createdTime'),
        'fields': decoded_fields
    }

def fetch_and_decode(url: str) -> Dict[str, Any]:
    """Fetch records and decode them for easier use"""
    raw_data = fetch_by_url(url)
    
    if 'records' in raw_data:
        decoded_records = []
        for record in raw_data['records']:
            decoded_records.append(decode_airtable_record(record))
        
        return {
            'records': decoded_records,
            'count': len(decoded_records)
        }
    
    return raw_data

async def test_image_explanation_workflow(package_url: str):
    """
    Test the complete workflow: fetch ATB record -> explain Campaign Name images -> print results
    
    Args:
        package_url: Package URL to test with
    """
    print("🚀 Starting Airtable Image Explanation Workflow")
    print("=" * 80)
    print(f"📦 Package URL: {package_url}")
    print("-" * 80)
    
    # Step 1: Fetch and decode Airtable data
    print("🔍 STEP 1: Fetching data from Airtable...")
    try:
        decoded_result = fetch_and_decode(package_url)
        print(f"✅ Found {decoded_result.get('count', 0)} record(s)")
        
        if 'records' not in decoded_result or not decoded_result['records']:
            print("❌ No records found for this URL")
            return
            
        record = decoded_result['records'][0]
        print(f"📋 Record ID: {record['id']}")
        
        # Check for Campaign Name artwork
        campaign_artwork_field = 'Artwork (from Campaign Name)_urls'
        if campaign_artwork_field in record['fields']:
            campaign_images = record['fields'][campaign_artwork_field]
            if isinstance(campaign_images, list) and campaign_images:
                print(f"🎨 Found {len(campaign_images)} Campaign Name artwork image(s)")
                for i, url in enumerate(campaign_images, 1):
                    print(f"   Image {i}: {url}")
            else:
                print("🎨 No Campaign Name artwork images found")
                return
        else:
            print("🎨 No Campaign Name artwork field found")
            return
            
    except Exception as e:
        print(f"❌ Error fetching Airtable data: {e}")
        return
    
    # Step 2: Explain images with Sonnet
    print(f"\n🤖 STEP 2: Analyzing images with Sonnet 4...")
    print("-" * 80)
    
    try:
        explanations = await explain_airtable_images(package_url)
        
        print(f"\n📝 STEP 3: Image Analysis Results")
        print("=" * 80)
        
        if not explanations:
            print("❌ No explanations generated")
            return
            
        for i, result in enumerate(explanations, 1):
            if 'error' in result:
                print(f"❌ Error: {result['error']}")
            elif 'message' in result:
                print(f"ℹ️  {result['message']}")
            else:
                print(f"\n🖼️  IMAGE {i}")
                print(f"🔗 URL: {result.get('image_url', 'N/A')}")
                print(f"📁 Field: {result.get('field_name', 'N/A')}")
                print(f"📋 EXPLANATION:")
                print(result.get('explanation', 'No explanation available'))
                print("-" * 60)
                
        print(f"\n✅ Workflow completed successfully! Analyzed {len([r for r in explanations if 'explanation' in r])} image(s)")
        
    except Exception as e:
        print(f"❌ Error during image analysis: {e}")

# ======================================
# Image Content Explanation Functions
# ======================================

async def explain_image_content(image_input, use_sonnet_4=True):
    """
    Simple function to call Sonnet 4 with image input and explain the content using AWS Bedrock
    
    Args:
        image_input: Can be either:
            - URL string (e.g., "https://example.com/image.jpg")
            - Base64 string with data URI (e.g., "data:image/jpeg;base64,...")
            - Dict with image data {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": "..."}}
        use_sonnet_4: Whether to use Sonnet 4 or Sonnet 3.7 (default: True)
    
    Returns:
        str: Explanation of the image content
    """
    
    # Check AWS credentials
    if not Config.AWS_ACCESS_KEY or not Config.AWS_SECRET_KEY:
        return "Error: AWS credentials not found. Set AWS_ACCESS_KEY and AWS_SECRET_KEY environment variables."
    
    # Create Bedrock client (matching sonnet4_bot.py)
    client = AsyncAnthropicBedrock(
        aws_access_key=Config.AWS_ACCESS_KEY,
        aws_secret_key=Config.AWS_SECRET_KEY,
        aws_region=Config.REGION
    )
    
    try:
        # Process image input
        image_content = await _process_image_input(image_input)
        
        if not image_content:
            return "Error: Could not process image input"
        
        # Create message with image
        messages = [
            {
                "role": "user",
                "content": [
                    image_content,
                    {
                        "type": "text",
                        "text": """กรุณาอธิบายเนื้อหาในรูปภาพนี้ให้ฟังค่ะ โดยเฉพาะ:

1. สิ่งที่เห็นในรูปโดยทั่วไป
2. ข้อความหรือตัวอักษรที่มีในรูป (ถ้ามี)
3. ข้อมูลสำคัญหรือรายละเอียดที่น่าสนใจ
4. บริบทหรือจุดประสงค์ของรูปภาพ (ถ้าสามารถคาดเดาได้)

กรุณาตอบเป็นภาษาไทยค่ะ"""
                    }
                ]
            }
        ]
        
        # Select model based on parameter
        model = Config.MODEL["sonnet_4"] if use_sonnet_4 else Config.MODEL["sonnet_3_7"]
        
        # Call Claude via Bedrock
        response = await client.messages.create(
            model=model,
            max_tokens=Config.MAX_TOKENS,
            temperature=Config.TEMP,
            messages=messages
        )
        
        # 📊 ACTUAL TOKEN USAGE from Sonnet response
        if hasattr(response, 'usage'):
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            total_tokens = input_tokens + output_tokens
            
            print(f"📊 [ACTUAL-TOKENS] Input: {input_tokens:,}, Output: {output_tokens:,}")
            print(f"📊 [TOTAL-TOKENS] {total_tokens:,} tokens used by Sonnet")
            print(f"💰 [TOKEN-COST] ~${total_tokens * 0.000015:.4f} (rough estimate)")
        
        return response.content[0].text
        
    except Exception as e:
        return f"Error explaining image: {str(e)}"

async def _process_image_input(image_input) -> Optional[Dict]:
    """Process different types of image input into Claude-compatible format"""
    
    if isinstance(image_input, str):
        if image_input.startswith('http'):
            # URL input - convert to base64
            return await _url_to_base64_content(image_input)
        elif image_input.startswith('data:image'):
            # Data URI input
            try:
                header, data = image_input.split(',', 1)
                media_type = header.split(';')[0].split(':')[1]
                return {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": data
                    }
                }
            except:
                return None
        else:
            # Assume base64 string
            return {
                "type": "image", 
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",  # Default assumption
                    "data": image_input
                }
            }
    
    elif isinstance(image_input, dict):
        # Already in Claude format
        return image_input
    
    return None

async def _url_to_base64_content(url: str) -> Optional[Dict]:
    """Convert image URL to base64 content for Claude"""
    try:
        # Use original URL without resizing for better quality
        # Medium thumbnails from Airtable are already optimally sized (~500x500)
        modified_url = url
        
        # Only apply manual resizing for non-Airtable URLs or as absolute fallback
        if 'airtableusercontent.com' in url and not any(size in url for size in ['medium', 'small', 'large']):
            # This is a full-size Airtable URL - apply conservative resizing only as fallback
            if '?' in url:
                modified_url = f"{url}&w=500&h=500&fit=crop&q=85"  # Higher quality, larger size
            else:
                modified_url = f"{url}?w=500&h=500&fit=crop&q=85"  # Higher quality, larger size
            
            print(f"🔧 [URL-DEBUG] Full-size Airtable URL detected, applying fallback resize")
            print(f"🔧 [URL-DEBUG] Original: {url[:100]}...")
            print(f"🔧 [URL-DEBUG] Modified: {modified_url[:100]}...")
            print(f"🔧 [URL-DEBUG] Parameters: w=500&h=500&fit=crop&q=85 (high quality fallback)")
        else:
            # Use original URL (likely medium thumbnail or external URL)
            print(f"🖼️ [ORIGINAL-URL] Using original URL for best quality: {url[:80]}...")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(modified_url)
            response.raise_for_status()
            
            # Get content type
            content_type = response.headers.get('content-type', 'image/jpeg')
            if not content_type.startswith('image/'):
                return None
            
            # Check image size before converting to base64
            file_size_bytes = len(response.content)
            file_size_mb = file_size_bytes / (1024 * 1024)
            
            if file_size_bytes > 5 * 1024 * 1024:  # 5MB limit
                print(f"❌ [IMAGE-SIZE] Image too large: {file_size_mb:.2f}MB (limit: 5MB) - {url[:80]}...")
                return None  # Skip oversized images
            
            # Convert to base64
            image_data = base64.b64encode(response.content).decode('utf-8')
            
            # 🔍 TOKEN COUNTING: Estimate tokens for this base64 image
            # Base64 encoding increases size by ~33%, and each token ≈ 4 characters
            estimated_tokens = len(image_data) // 3  # Conservative estimate: 3 chars per token
            file_size_kb = len(response.content) / 1024
            
            print(f"🖼️ [IMAGE-TOKENS] URL: {url[:80]}...")
            print(f"📊 [IMAGE-SIZE] File: {file_size_kb:.1f}KB ({file_size_mb:.2f}MB), Base64: {len(image_data):,} chars")
            print(f"🎯 [TOKEN-ESTIMATE] ~{estimated_tokens:,} tokens for this image")
            print(f"✅ [SIZE-CHECK] Image size validation passed (original quality preserved)")
            
            return {
                "type": "image",
                "source": {
                    "type": "base64", 
                    "media_type": content_type,
                    "data": image_data
                }
            }
    except Exception as e:
        print(f"❌ [IMAGE-ERROR] Failed to fetch {url}: {e}")
        return None

async def explain_airtable_images(url: str) -> List[Dict[str, str]]:
    """
    Fetch Airtable record by URL and explain all artwork images found
    
    Args:
        url: Package URL to search for in Airtable
        
    Returns:
        List of dictionaries with image_url and explanation
    """
    try:
        # Fetch and decode the Airtable record
        decoded_result = fetch_and_decode(url)
        
        if 'records' not in decoded_result or not decoded_result['records']:
            return [{"error": "No records found for this URL"}]
        
        record = decoded_result['records'][0]
        explanations = []
        
        # Look for artwork URLs in the record - only from Campaign Name
        for field_name, field_value in record['fields'].items():
            if field_name == 'Artwork (from Campaign Name)_urls':
                if isinstance(field_value, list):
                    for img_url in field_value:
                        try:
                            explanation = await explain_image_content(img_url)
                            explanations.append({
                                "image_url": img_url,
                                "explanation": explanation,
                                "field_name": field_name
                            })
                        except Exception as e:
                            explanations.append({
                                "image_url": img_url,
                                "explanation": f"Error explaining image: {str(e)}",
                                "field_name": field_name
                            })
        
        return explanations if explanations else [{"message": "No artwork images found in this record"}]
        
    except Exception as e:
        return [{"error": f"Error processing Airtable record: {str(e)}"}]

# Usage Examples:
"""
# Explain single image with Sonnet 4 (default)
result = await explain_image_content("https://example.com/image.jpg")
print(result)

# Explain single image with Sonnet 3.7
result = await explain_image_content("https://example.com/image.jpg", use_sonnet_4=False)
print(result)

# Explain all images from Airtable record
results = await explain_airtable_images("https://hdmall.co.th/package/example")
for result in results:
    print(f"Image: {result['image_url']}")
    print(f"Explanation: {result['explanation']}")
    print("---")
"""

# Example usage and testing
if __name__ == "__main__":
    import sys
    
    # Default test URLs
    test_urls = [
        "https://hdmall.co.th/health-checkup/45-health-checks-for-basic-program-for-those-aged-15-years-and-over-medical-line-lab",
        # Add more test URLs here if needed
    ]
    
    # Allow command line URL input
    if len(sys.argv) > 1:
        # Use URL from command line argument
        test_url = sys.argv[1]
        print(f"Using URL from command line: {test_url}")
        asyncio.run(test_image_explanation_workflow(test_url))
    else:
        # Test with default URLs
        print("🧪 Testing with default URLs...")
        print("💡 Tip: You can also run: python airtable_fetching.py 'your_package_url_here'")
        print()
        
        for i, url in enumerate(test_urls, 1):
            print(f"\n{'='*20} TEST {i}/{len(test_urls)} {'='*20}")
            asyncio.run(test_image_explanation_workflow(url))
            
            if i < len(test_urls):
                print(f"\n{'='*50}")
                input("Press Enter to continue to next test...")  # Pause between tests