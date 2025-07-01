from datetime import datetime
import requests
import threading
import os
import asyncio
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Note: Redis and other dependencies might need to be added based on actual usage
try:
    import redis
    redis_host = os.environ.get("REDISHOST", "localhost")
    redis_port = int(os.environ.get("REDISPORT", 6379))
    redis_client = redis.Redis(host=redis_host, port=redis_port)
except ImportError:
    logger.warning("Redis not available - some features may not work")
    redis_client = None

# Import actual functions from the new files
try:
    from .summarization_utils import parse_url, scrape_url_content
    logger.info("Successfully imported summarization_utils")
except ImportError:
    logger.warning("parse_url not found - will use placeholder")
    def parse_url(message):
        return "Parsed content placeholder"

try:
    from .p_p import p_forward
    logger.info("Successfully imported p_p")
except ImportError:
    logger.warning("p_forward not found - will use placeholder")
    async def p_forward(message, content):
        class MockResponse:
            def __init__(self):
                self.script = []
        return MockResponse()

try:
    from .slack_utils import send_slack_message
    logger.info("Successfully imported slack_utils")
except ImportError:
    logger.warning("send_slack_message not found - will use placeholder")
    def send_slack_message(channel, message, ts):
        logger.info(f"Would send to Slack: {message[:100]}...")

def process_slack_event(event):
    try:
        if event.get('type') == 'app_mention':
            message = event.get('text')
            user = event.get('user')
            channel = event.get('channel') 
            ts = event.get('ts')

            logger.info(f"Processing message from {user} in channel {channel}: {message[:100]}...")
            
            scraped_content = parse_url(message)
            logger.info(f"Scraped content length: {len(str(scraped_content))} characters")
            
            try:
                response = asyncio.run(p_forward(message, scraped_content))
                logger.info("Successfully processed message with LLM")
                
                script = response.script
                final_text_response = ""
                for s in script:
                    final_text_response += "สรุปเนื้อหาของบทความนี้! : " + s.summarized_content + "\n\n\n\n"
                    final_text_response += "สคริปจ้า!! : " + s.script + "\n\n\n\n\n\n\n"
                if final_text_response == "":
                    final_text_response = "บอทไม่ได้สรุปและสร้างสคริปให้ นี้คือความคิดของบอท :"
                    for s in script:
                        final_text_response += s.thinking_for_content + "\n\n"
                        final_text_response += s.thinking_for_script + "\n\n"
                logger.info("Sending response to Slack")
                logger.info(f"Final response: {final_text_response}")
                send_slack_message(channel, final_text_response, ts)
            except Exception as e:
                logger.error(f"Error processing message with LLM: {str(e)}", exc_info=True)
                send_slack_message(channel, "ขออภัยครับ เกิดข้อผิดพลาดในการประมวลผล กรุณาลองใหม่อีกครั้ง", ts)
                
    except Exception as e:
        logger.error(f"Error in background processing: {str(e)}", exc_info=True)
        # Try to send error message if we have channel info
        if 'channel' in event and 'ts' in event:
            send_slack_message(event['channel'], "ขออภัยครับ เกิดข้อผิดพลาดในการประมวลผล กรุณาลองใหม่อีกครั้ง", event['ts'])

# Flask routes removed - now using FastAPI routes in api/routes/summarization_routes.py
