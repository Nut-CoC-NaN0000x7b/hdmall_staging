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
    api_version=os.getenv("AZURE_OPENAI_VERSION"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_deployment=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT"),
)

openai_chat_model = os.getenv("AZURE_OPENAI_CHAT_MODEL")

@retry(
    wait=wait_random_exponential(min=1, max=60),
    stop=stop_after_attempt(3),
)
async def openai_chat_completion(*args, **kwargs) -> ChatCompletion:
    try:
        logger.info("Starting OpenAI chat completion request")
        logger.debug(f"Request arguments: {args}")
        logger.debug(f"Request keyword arguments: {kwargs}")
        response = await openai_chat_client.beta.chat.completions.parse(*args, **kwargs)
        logger.info("Successfully received response from OpenAI")
        return response
    except Exception as e:
        logger.error(f"Error in OpenAI chat completion: {str(e)}", exc_info=True)
        raise

async def p_forward(user_message: str, scraped_content: str):
    try:
        logger.info("Starting p_forward function")
        logger.info(f"User message: {user_message[:200]}...")  # Log first 200 chars
        logger.info(f"Scraped content length: {len(scraped_content)} characters")
        
        p_grand_covenant = open("p_prompt.txt").read()
        logger.info("Successfully loaded p_prompt.txt")

        messages = [
            {"role": "system", "content": p_grand_covenant},
            {"role": "user", "content": "<user_message>\n"+user_message+"\n</user_message>\n\n"},
            {"role": "user", "content": "<scraped_content>\n"+scraped_content+"\n</scraped_content>\n\n"}
        ]
        logger.info("Constructed messages for OpenAI API")

        token_limit = 4096
        logger.info(f"Using token limit: {token_limit}")

        logger.info("Making request to OpenAI API")
        chat_completion: ChatCompletion = await openai_chat_completion(
            messages=messages,
            model=openai_chat_model,
            temperature=0.3,
            max_tokens=token_limit,
            n=1,
            response_format=ScriptResponse
        )

        logger.info("Processing OpenAI response")
        response = chat_completion.choices[0].message.parsed
        
        logger.info("Successfully processed response")
        logger.debug(f"Response content: {response}")
        return response
        
    except Exception as e:
        logger.error(f"Error in p_forward function: {str(e)}", exc_info=True)
        raise









