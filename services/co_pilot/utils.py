import re
import requests
from bs4 import BeautifulSoup
from typing import List, Union
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def parse_url(message : str) -> list:
    """
    Parse the message to extract the URL.
    """
    logger.info(f"Parsing message for URLs: {message[:100]}...")  # Log first 100 chars of message
    urls = re.findall(r'https?://[^\s]+', message)
    
    # check if list is empty
    if urls:
        urls = [url[:-1] for url in urls]
        logger.info(f"Found {len(urls)} URLs: {urls}")
        concat_scraped_content = ""
        for index, url in enumerate(urls):
            logger.info(f"Scraping content from URL {index + 1}/{len(urls)}: {url}")
            scraped_content = scrape_url_content(url)
            concat_scraped_content += f""" 
            <content index={index} url={url}>
            {scraped_content}
            </content>
            """
            logger.info(f"Successfully scraped content from URL {index + 1}")

        return concat_scraped_content
    else:
        logger.warning("No URLs found in message")
        return "ผมไม่เห็นลิ้งเลย ส่งลิ้งให้ผมทีครับ"

def scrape_url_content(url: str) -> str:
    """
    Scrape the content from a given URL and return it as a string.
    
    Args:
        url (str): The URL to scrape
        
    Returns:
        str: The scraped content as a string, or an error message if scraping fails
    """
    try:
        logger.info(f"Making request to URL: {url}")
        # Send a GET request to the URL
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Raise an exception for bad status codes
        logger.info(f"Successfully received response from URL: {url}")
        
        # Parse the HTML content
        logger.info("Parsing HTML content")
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove script and style elements
        logger.info("Removing script and style elements")
        for script in soup(["script", "style"]):
            script.decompose()
            
        # Get text content
        logger.info("Extracting text content")
        text = soup.get_text()
        
        # Clean up the text
        logger.info("Cleaning up text content")
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        logger.info(f"Successfully scraped content from URL. Content length: {len(text)} characters")
        return text
    except requests.RequestException as e:
        logger.error(f"Request error for URL {url}: {str(e)}")
        return f"เออเร่อคับ ลิ้งนี้ดูไม่ได้คับ: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error for URL {url}: {str(e)}")
        return f"เออเร่อคับ ลิ้งนี้ดูไม่ได้คับ: {str(e)}"
