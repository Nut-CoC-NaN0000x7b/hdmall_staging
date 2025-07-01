import openai
from pydantic import BaseModel
from openai.types.chat import ChatCompletion
import os
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_random_exponential
from .tools import build_package_query_function, is_language_detector, extract_language
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

load_dotenv()

class Script(BaseModel):
    thinking_for_content: str
    summarized_content: str
    thinking_for_script: str
    script: str

class ScriptResponse(BaseModel):
    script: list[Script]

openai_chat_client = openai.AsyncAzureOpenAI(
    api_version='2025-01-01-preview',
    azure_endpoint=os.getenv('GPT_MINI_ENDPOINT'),
    api_key=os.getenv('GPT_MINI_API_KEY'),
)

openai_chat_model = "gpt-4.1-mini"

@retry(
    wait=wait_random_exponential(min=1, max=60),
    stop=stop_after_attempt(3),
)
async def openai_chat_completion(*args, **kwargs) -> ChatCompletion:
    try:

        response = await openai_chat_client.chat.completions.create(*args, **kwargs)
        logger.info("Successfully received response from OpenAI")
        return response
    except Exception as e:
        logger.error(f"Error in OpenAI chat completion: {str(e)}", exc_info=True)
        raise

async def co_pilot_run(data):
    try:
        content_list = data.get('messages')
        token_limit = 4096
        logger.info(f"Using token limit: {token_limit}")

        chat_completion: ChatCompletion = await openai_chat_completion(
            messages=content_list,
            model=openai_chat_model,
            temperature=0.3,
            max_tokens=token_limit,
            n=1
        )

        response = chat_completion.choices[0].message.content
        return response
        
    except Exception as e:
        logger.error(f"Error in co_pilot function: {str(e)}", exc_info=True)
        raise









