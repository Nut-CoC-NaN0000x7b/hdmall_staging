import os
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_random_exponential
import logging
from anthropic import AsyncAnthropicBedrock

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

load_dotenv()

class Config:
    AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY')
    AWS_SECRET_KEY = os.getenv('AWS_SECRET_KEY')
    REGION = 'us-west-2'
    MODEL = {
        "sonnet_4": "us.anthropic.claude-sonnet-4-20250514-v1:0",
        "sonnet_3_7": "us.anthropic.claude-3-7-sonnet-20250219-v1:0",
    }
    MAX_TOKENS = 8000
    MAX_REASONING_TOKENS = 4000
    TEMP = 0.0
client = AsyncAnthropicBedrock(
            aws_access_key=Config.AWS_ACCESS_KEY,
            aws_secret_key=Config.AWS_SECRET_KEY,
            aws_region=Config.REGION
        )


@retry(
    wait=wait_random_exponential(min=1, max=60),
    stop=stop_after_attempt(3),
)
async def call_claude(*args, **kwargs):
    return await client.messages.create(**kwargs)

async def p_forward(user_message: str, scraped_content: str):
    try:
        logger.info("Starting p_forward function")
        logger.info(f"User message: {user_message[:200]}...")  # Log first 200 chars
        logger.info(f"Scraped content length: {len(scraped_content)} characters")
        
        # Try to load from services/summarization first, then fallback to root
        content_agent_prompt = open("services/summarization/content_agent_system_prompt.txt").read()

        messages = [
            {"role": "user", "content": "<user_message>\n"+user_message+"\n</user_message>\n\n"},
            {"role": "user", "content": "<scraped_content>\n"+scraped_content+"\n</scraped_content>\n\n"}
        ]

        response = await call_claude(
            system=content_agent_prompt,
            messages=messages,
            model=Config.MODEL["sonnet_4"],
            max_tokens=Config.MAX_TOKENS,
            thinking={
                "type": "enabled",
                "budget_tokens": Config.MAX_REASONING_TOKENS
            }
        )

        for block in response.content:
            if block.type == "text":
                logger.info(f"Response: {block.text}")
        return response
        
    except Exception as e:
        logger.error(f"Error in p_forward function: {str(e)}", exc_info=True)
        raise 