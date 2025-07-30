import re
import json
import hashlib
import hmac
import base64
import requests
from datetime import datetime
import os







# Build the API Signature
def build_signature(customer_id, shared_key, date, content_length, method="POST", content_type="application/json", resource="/api/logs"):
    x_headers = f"x-ms-date:{date}"
    string_to_hash = f"{method}\n{str(content_length)}\n{content_type}\n{x_headers}\n{resource}"
    bytes_to_hash = bytes(string_to_hash, encoding="utf-8")
    decoded_key = base64.b64decode(shared_key)
    encoded_hash = base64.b64encode(hmac.new(decoded_key, bytes_to_hash, digestmod=hashlib.sha256).digest()).decode()
    return f"SharedKey {customer_id}:{encoded_hash}"

# Post data to Azure Log Analytics
def post_data(customer_id, shared_key, log_type, json_data):
    date = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
    body = json.dumps(json_data)
    content_length = len(body)
    signature = build_signature(customer_id, shared_key, date, content_length)

    uri = f"https://{customer_id}.ods.opinsights.azure.com/api/logs?api-version=2016-04-01"
    headers = {
        "Content-Type": "application/json",
        "Authorization": signature,
        "Log-Type": log_type,
        "x-ms-date": date
    }

    response = requests.post(uri, data=body, headers=headers)
    if response.status_code == 200:
        print("Log entry sent successfully.")
    else:
        print(f"Failed to send log entry: {response.status_code}, {response.text}")




def update_urls_with_utm(content: str, pattern: str, utm_source: str = "ai-chat") -> str:
    urls = re.findall(pattern, content)
    updated_urls = [add_utm_param(url, utm_source) for url in urls]

    for old_url, new_url in zip(urls, updated_urls):
        # Use re.sub to ensure we replace the exact URL without altering similar URLs
        content = re.sub(rf"(?<![^\s]){re.escape(old_url)}(?![^\s])", new_url, content)
    return content


def add_utm_param(url: str, utm_source: str = "ai-chat") -> str:
    url = url.rstrip(".")
    if "utm_source=" in url:
        return url
    if "?" in url:
        return f"{url}&utm_source={utm_source}"
    else:
        return f"{url}?utm_source={utm_source}"


def remove_markdown_elements(content: str) -> str:
    # Remove code blocks (```...```)
    cleaned_content = re.sub(r"```.*?```", "", content, flags=re.DOTALL)

    # Remove inline code (`...`)
    cleaned_content = re.sub(r"`([^`]*)`", r"\1", cleaned_content)

    # Remove headers (e.g., # Header)
    cleaned_content = re.sub(r"^\s*#+\s*(.*)", r"\1", cleaned_content, flags=re.MULTILINE)

    # Remove bold and italic (**text**, *text*, __text__, _text_)
    cleaned_content = re.sub(r"\*\*(.*?)\*\*", r"\1", cleaned_content)
    cleaned_content = re.sub(r"\*(.*?)\*", r"\1", cleaned_content)
    
    # Remove strikethrough (~~text~~)
    cleaned_content = re.sub(r"~~(.*?)~~", r"\1", cleaned_content)

    return cleaned_content.strip()

import requests




def shorten_url(api_key, original_url):
    try:
        response = requests.post(
            'https://api.short.io/links',
            json={
                'domain': 's.hdmall.co.th',
                'originalURL': original_url,
                'folderId': '3OOd8Xs2Dy54lhP3xZlF9'
            },
            headers={
                'Content-Type': 'application/json',
                'Authorization': api_key
            }
        )
        
        # Check if request was successful
        response.raise_for_status()
        
        print('✅ Shortened URL:', response.json()['shortURL'])

        return response.json()['shortURL']
        
    except requests.exceptions.RequestException as error:
        if hasattr(error, 'response'):
            print('❌ API Error:', error.response.status_code, error.response.json())
        else:
            print('❌ Error:', str(error))

