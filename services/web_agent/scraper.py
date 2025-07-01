target_url = "https://hdmall.co.th/brands"

import requests
from bs4 import BeautifulSoup
import re
import time
import csv

# Add headers to mimic a real browser request
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
}

def extract_image_from_brand_page(brand_url, session):
    """Extract brand image from individual brand page"""
    try:
        if not brand_url.startswith('http'):
            brand_url = 'https://hdmall.co.th' + brand_url
            
        response = session.get(brand_url, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Common selectors for brand images
            image_selectors = [
                '.brand-logo img',
                '.hospital-logo img', 
                '.clinic-logo img',
                '.brand-header img',
                '.logo img',
                'img[alt*="logo"]',
                'img[alt*="Logo"]',
                '.brand-image img',
                '.hospital-image img',
                'header img',
                '.main-logo img'
            ]
            
            for selector in image_selectors:
                img = soup.select_one(selector)
                if img and img.get('src'):
                    src = img.get('src')
                    # Make URL absolute if relative
                    if src.startswith('/'):
                        return f"https://hdmall.co.th{src}"
                    elif src.startswith('http'):
                        return src
            
            # Fallback: look for any image in the header/top area
            header_area = soup.find(['header', 'div'], class_=re.compile(r'header|brand|logo', re.I))
            if header_area:
                img = header_area.find('img')
                if img and img.get('src'):
                    src = img.get('src')
                    if src.startswith('/'):
                        return f"https://hdmall.co.th{src}"
                    elif src.startswith('http'):
                        return src
                        
    except Exception as e:
        print(f"Error extracting image from {brand_url}: {e}")
    
    return None

def scrape_brands_with_images():
    print("🔍 Scraping HDmall brands with images (COMPLETE FIXED VERSION)...")
    
    # Create a session for better performance
    session = requests.Session()
    session.headers.update(headers)
    
    response = session.get(target_url)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code != 200:
        print(f"❌ Failed to fetch page. Status code: {response.status_code}")
        return []
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    print("\n📋 Using proper CSS selectors to find brand links...")
    
    all_brands = set()  # Use set to avoid duplicates
    
    # METHOD 1: Use the js-item-product-link class (most reliable)
    print("Method 1: Using js-item-product-link class...")
    product_links = soup.find_all('a', class_='js-item-product-link')
    print(f"Found {len(product_links)} product links")
    
    for link in product_links:
        href = link.get('href', '')
        text = link.get_text(strip=True)
        
        # Skip empty text
        if not text or len(text) < 3:
            continue
        
        # Make URL absolute if it's relative
        if href.startswith('/'):
            href = 'https://hdmall.co.th' + href
        
        if href and href.startswith('https://hdmall.co.th/') and not any(x in href for x in ['/tag', '/category', '/search']):
            all_brands.add((href, text))
    
    # METHOD 2: Look inside card-brand-item divs for additional brands
    print("Method 2: Looking inside card-brand-item divs...")
    card_divs = soup.find_all('div', class_=re.compile(r'card.*brand.*item', re.I))
    print(f"Found {len(card_divs)} card brand items")
    
    card_links_found = 0
    for card in card_divs:
        links = card.find_all('a', href=True)
        for link in links:
            href = link.get('href', '')
            text = link.get_text(strip=True)
            
            if not text or len(text) < 3:
                continue
                
            # Make URL absolute if it's relative
            if href.startswith('/'):
                href = 'https://hdmall.co.th' + href
            
            if href and href.startswith('https://hdmall.co.th/') and not any(x in href for x in ['/tag', '/category', '/search']):
                # Only add if it's not already in our set
                if (href, text) not in all_brands:
                    all_brands.add((href, text))
                    card_links_found += 1
    
    print(f"Found {card_links_found} additional links from card method")
    
    # Convert set back to list and sort
    brand_list = sorted(list(all_brands), key=lambda x: x[1])  # Sort by name
    
    print(f"\n✅ Found {len(brand_list)} unique brands/hospitals/clinics")
    
    if len(brand_list) == 0:
        print("❌ No valid brand links found. The page structure might have changed.")
        return []
    
    # Let's check if Bangkok Anti-Aging Center is in our list
    bangkok_found = any('Bangkok Anti-Aging' in name for _, name in brand_list)
    print(f"🔍 Bangkok Anti-Aging Center found: {bangkok_found}")
    
    print("🖼️ Now extracting brand images...")
    
    # Extract images for each brand
    brands_with_images = []
    total_brands = len(brand_list)
    
    for i, (url, name) in enumerate(brand_list, 1):
        print(f"📸 Processing {i}/{total_brands}: {name[:50]}...")
        
        # Extract image from brand page
        image_url = extract_image_from_brand_page(url, session)
        
        brands_with_images.append({
            'name': name,
            'url': url,
            'image_url': image_url or 'No image found'
        })
        
        # Add small delay to be respectful to the server
        time.sleep(0.3)
        
        # Show progress every 50 items
        if i % 50 == 0:
            print(f"  ✅ Processed {i}/{total_brands} brands...")
    
    print(f"\n🎯 Final Results:")
    brands_with_images_count = sum(1 for brand in brands_with_images if brand['image_url'] != 'No image found')
    print(f"  📊 Total brands: {len(brands_with_images)}")
    print(f"  🖼️ Brands with images: {brands_with_images_count}")
    print(f"  ❌ Brands without images: {len(brands_with_images) - brands_with_images_count}")
    
    return brands_with_images

def save_brands_with_images_to_file(brands, filename="hdmall_brands_complete_fixed.csv"):
    """Save brands with images to CSV file"""
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Name', 'URL', 'Image_URL'])  # Header
        
        for brand in brands:
            writer.writerow([brand['name'], brand['url'], brand['image_url']])
    
    print(f"💾 Saved {len(brands)} brands with images to {filename}")

if __name__ == "__main__":
    brands = scrape_brands_with_images()
    
    if brands:
        save_brands_with_images_to_file(brands)
        
        # Show some examples including Bangkok Anti-Aging if found
        print(f"\n🎯 Sample results:")
        bangkok_brands = [b for b in brands if 'Bangkok Anti-Aging' in b['name']]
        if bangkok_brands:
            print("✅ Found Bangkok Anti-Aging Center:")
            for brand in bangkok_brands:
                print(f"   Name: {brand['name']}")
                print(f"   URL: {brand['url']}")
                print(f"   Image: {brand['image_url']}")
                print()
        
        # Show first 5 brands
        for i, brand in enumerate(brands[:5]):
            print(f"{i+1}. {brand['name'][:60]}")
            print(f"   URL: {brand['url']}")
            print(f"   Image: {brand['image_url']}")
            print()
    else:
        print("❌ No brands found.") 