from shared.rag import RAG
import os
import logging
import json
import openai
from openai.types.chat import ChatCompletion
from dotenv import load_dotenv
from tenacity import before_sleep_log, retry, stop_after_attempt, wait_random_exponential
from .ads_tools import AdsTools
import asyncio
from typing import Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Validate environment variables
class Config:
    API_KEY = os.getenv('GPT_MINI_API_KEY')
    ENDPOINT = os.getenv('GPT_MINI_ENDPOINT')
    API_VERSION = '2025-01-01-preview'
    MODEL = "gpt-4.1-mini"
    TOKENS_LIMIT = 4096

class AdsAgent:
    def __init__(self, global_storage):
        self.client = openai.AsyncAzureOpenAI(
            api_version=Config.API_VERSION,
            azure_endpoint=Config.ENDPOINT,
            api_key=Config.API_KEY,
        )

        #initalize rag
        self.rag = RAG(global_storage=global_storage)

        # Get the directory where ads_agent.py is located
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Load system prompt
        system_prompt_path = os.path.join(current_dir, 'system_prompt.txt')
        try:
            with open(system_prompt_path, 'r', encoding='utf-8') as file:
                self.system_prompt = file.read()
        except FileNotFoundError:
            logger.error(f"System prompt file not found at {system_prompt_path}")
            raise
        except Exception as e:
            logger.error(f"Error reading system prompt: {str(e)}")
            raise
        
        # Load messages
        messages_path = os.path.join(current_dir, 'message_prompt.txt')
        try:
            with open(messages_path, 'r', encoding='utf-8') as file:
                self.messages_prompt = file.read()
        except FileNotFoundError:
            logger.error(f"Messages file not found at {messages_path}")
            raise
        except Exception as e:
            logger.error(f"Error reading messages: {str(e)}")
            raise
    
    @retry(
        wait=wait_random_exponential(min=1, max=60),  # Reduced max wait time
        stop=stop_after_attempt(5),  # Reduced from 15 to 5 attempts
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    async def gpt_forward(self, messages):
        """Send a request to GPT-4.1-mini model with retry logic - optimized for high load."""
        try:
            # Add timeout to prevent hanging requests
            response = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model=Config.MODEL,
                    max_tokens=Config.TOKENS_LIMIT,
                    messages=messages,
                    temperature=0.0,
                    tools=[AdsTools().extraction]
                ),
                timeout=120  # 2 minutes timeout
            )
            return response
        except asyncio.TimeoutError:
            logger.error("GPT API call timed out after 2 minutes")
            raise
        except Exception as e:
            logger.error(f"Error in GPT API call: {str(e)}")
            raise

    async def forward(self, request):
        """Async forward method to handle requests - optimized version."""
        try:
            #unfold inputs JSON
            logger.info(f"Unfolding inputs {request}")
            thread_name = request['thread_name']
            messages = ""
            for message in request['conversation']:
                role = message['role']
                content = message['content']
                messages += f"{role}: {content}\n"
            
            # Create a copy of the message prompt to avoid modifying the original
            current_message_prompt = self.messages_prompt.replace("{{thread_name}}", thread_name)
            current_message_prompt = current_message_prompt.replace("{{messages}}", messages)

            logger.info(f"Successfully on thread : {thread_name}")
            logger.info(f"Unfolded successfully the message prompt is : {current_message_prompt}")
            
            # Build messages with proper OpenAI format
            messages_list = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": current_message_prompt}
            ]
        except Exception as e:
            logger.error(f"Error in unfolding inputs {request} with error {e}")
            raise
            
        try:
            response = await self.gpt_forward(messages_list)
            
            # Parse OpenAI response format
            chat_resp = response.model_dump()
            response_content = chat_resp["choices"][0]["message"]["content"]
            finish_reason = chat_resp["choices"][0]["finish_reason"]
            
            logger.info(f"GPT finish reason: {finish_reason}")
            
            if finish_reason == "tool_calls":
                logger.info("GPT is calling tools...")
                tool_calls = chat_resp["choices"][0]["message"]["tool_calls"]
                
                # Handle tool calls
                result = None
                for tool_call in tool_calls:
                    if tool_call["function"]["name"] == "extraction":
                        logger.info(f"Processing extraction tool call...")
                        tool_arguments = json.loads(tool_call["function"]["arguments"])
                        logger.info(f"Tool arguments: {tool_arguments}")
                        
                        # Run RAG operation in thread pool to avoid blocking
                        loop = asyncio.get_event_loop()
                        result = await loop.run_in_executor(None, self.rag.ads_forward, tool_arguments)
                        break
                
                if result:
                    return result
                else:
                    logger.info("No valid tool results, returning empty result")
                    return []
            else:
                logger.info("GPT provided direct response without tool calls")
                if response_content:
                    logger.info(f"Response content: {response_content}")
                    return response_content
                else:
                    logger.info("No response content, returning empty result")
                    return []
                    
        except Exception as e:
            logger.error(f"Error in forward method: {str(e)}")
            # Return empty result instead of raising exception to prevent cascading failures
            return []
    