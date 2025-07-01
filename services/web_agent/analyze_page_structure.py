import requests
from bs4 import BeautifulSoup
import re

url = 'https://hdmall.co.th/brands'
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

response = requests.get(url, headers=headers)
soup = BeautifulSoup(response.text, 'html.parser')

print('=== ANALYZING BRAND PAGE STRUCTURE ===')

# Look for different card patterns
print('\n1. CARD-BASED BRAND ITEMS:')
card_brands = soup.find_all('div', class_=re.compile(r'card.*brand.*item', re.I))
print(f"Found {len(card_brands)} card-brand-item elements")

if card_brands:
    for i, card in enumerate(card_brands[:5]):
        # Look for links within cards
        links = card.find_all('a', href=True)
        for link in links:
            href = link.get('href', '')
            text = link.get_text(strip=True)
            if text and len(text) > 3:
                print(f"  {i+1}. {text} -> {href}")

# Look for different link patterns
print('\n2. DIFFERENT LINK PATTERNS:')

patterns_to_check = [
    ('js-item-product-link', soup.find_all('a', class_='js-item-product-link')),
    ('js-external-link', soup.find_all('div', class_='js-external-link')),
    ('brand links with /h/', soup.find_all('a', href=re.compile(r'/[^/]+$'))),  # Single path segment
]

for pattern_name, elements in patterns_to_check:
    print(f"\n{pattern_name}: {len(elements)} elements")
    for i, elem in enumerate(elements[:5]):
        if elem.name == 'a':
            href = elem.get('href', '')
            text = elem.get_text(strip=True)
        else:
            # For div elements, find the link inside
            link = elem.find('a', href=True)
            if link:
                href = link.get('href', '')
                text = link.get_text(strip=True)
            else:
                continue
        
        if text and len(text) > 3:
            print(f"  {i+1}. {text[:60]} -> {href}")

# Search specifically for Bangkok Anti-Aging
print('\n3. SEARCHING FOR BANGKOK ANTI-AGING:')
bangkok_elements = soup.find_all(text=re.compile(r'Bangkok.*Anti.*Aging', re.I))
print(f"Found {len(bangkok_elements)} text matches")

for elem in bangkok_elements:
    parent = elem.parent
    if parent and parent.name == 'a':
        print(f"  Link: {elem.strip()} -> {parent.get('href', '')}")
    elif parent:
        # Look for nearby links
        link = parent.find('a', href=True) or parent.find_parent('a', href=True)
        if link:
            print(f"  Nearby link: {elem.strip()} -> {link.get('href', '')}")

# Look for all brand URLs in a different way
print('\n4. ALL LINKS CONTAINING BRAND NAMES:')
all_links = soup.find_all('a', href=True)
brand_links = []

for link in all_links:
    href = link.get('href', '')
    text = link.get_text(strip=True)
    
    # Look for links that go directly to individual pages (not categories)
    if href and '/' in href and not any(x in href.lower() for x in ['/tag', '/category', '/search', 'filter']):
        # Check if it looks like a brand/clinic page
        if any(word in text.lower() for word in ['clinic', 'hospital', 'center', 'คลินิก', 'โรงพยาบาล', 'ศูนย์']):
            if len(text) > 3:
                brand_links.append((text, href))

print(f"Found {len(brand_links)} potential brand links")
for i, (text, href) in enumerate(sorted(brand_links)[:10]):
    print(f"  {i+1}. {text[:60]} -> {href}")

# Check URL patterns
print('\n5. URL PATTERN ANALYSIS:')
url_patterns = {}
for link in all_links:
    href = link.get('href', '')
    if href and href.startswith('/') and href != '/':
        # Extract pattern (like /h/, /brand/, etc.)
        parts = href.split('/')
        if len(parts) >= 2:
            pattern = f"/{parts[1]}/"
            if pattern not in url_patterns:
                url_patterns[pattern] = []
            url_patterns[pattern].append(href)

for pattern, urls in sorted(url_patterns.items()):
    if len(urls) > 10:  # Only show patterns with many URLs
        print(f"  {pattern}: {len(urls)} URLs (sample: {urls[0]})") 