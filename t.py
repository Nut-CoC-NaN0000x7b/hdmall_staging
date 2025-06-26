#test
from src.RAG import RAG
from src.google_searcher import GoogleSearcher
from tools import Tools
from prompt_generator import PromptGenerator
from anthropic import AsyncAnthropicBedrock
from dotenv import load_dotenv
from tenacity import before_sleep_log, retry, stop_after_attempt, wait_random_exponential
import re
import os
import httpx
import base64
import logging
import requests
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional, Union

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY')
AWS_SECRET_KEY = os.getenv('AWS_SECRET_KEY')
REGION = 'us-east-1' #east-1, east-2, us-west-2
MODEL = {
        "sonnet_3_7":"us.anthropic.claude-3-7-sonnet-20250219-v1:0",
        'sonnet': "anthropic.claude-3-5-sonnet-20240620-v1:0",
        'haiku': "anthropic.claude-3-haiku-20240307-v1:0",
        'sonnet_3_6': 'us.anthropic.claude-3-5-sonnet-20241022-v2:0'
    }
MAX_TOKENS = 8000



client = AsyncAnthropicBedrock(
            aws_access_key=AWS_ACCESS_KEY,
            aws_secret_key=AWS_SECRET_KEY,
            aws_region=REGION
        )


@retry(
    wait=wait_random_exponential(min=1, max=300),
    stop=stop_after_attempt(10))
async def tell_claude():
    return await client.messages.create(
        model=MODEL['sonnet_3_7'],
        max_tokens=4000,
        thinking= {
            "type": "enabled",
            "budget_tokens": 2000
        },
        messages=[{
            "role": "user",
            "content": "Solve this puzzle: Three people check into a hotel. They pay $30 to the manager. The manager finds out that the room only costs $25 so he gives $5 to the bellboy to return to the three people. The bellboy, however, decides to keep $2 and gives $1 back to each person. Now, each person paid $10 and got back $1, so they paid $9 each, totaling $27. The bellboy kept $2, which makes $29. Where is the missing $1?"
        }]
    )

async def claude_reason(chats):

    resp = await tell_claude(
        model=MODEL['sonnet_3_7'],
        max_tokens=3000,
        thinking= {
            "type": "enabled",
            "budget_tokens": 2000
        },
        messages=chats
        )
    return resp.content[0].text
async def main():
    resp = await tell_claude()
    print(resp)
    print(resp.content[0].text)

if __name__ == "__main__":
    asyncio.run(main())