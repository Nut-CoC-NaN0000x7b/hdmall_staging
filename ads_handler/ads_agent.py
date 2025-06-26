from src.RAG import RAG
import os
import logging
import json
from dotenv import load_dotenv
from anthropic import AsyncAnthropicBedrock
from tenacity import before_sleep_log, retry, stop_after_attempt, wait_random_exponential
from ads_handler.ads_tools import AdsTools
from src.RAG import RAG
import asyncio
from typing import Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Validate environment variables
AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY')
AWS_SECRET_KEY = os.getenv('AWS_SECRET_KEY')

if not AWS_ACCESS_KEY or not AWS_SECRET_KEY:
    raise ValueError("AWS credentials not found in environment variables")

REGION = 'us-west-2'
MODEL = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"

class AdsAgent:
    def __init__(self, global_storage):
        self.client = AsyncAnthropicBedrock(
            aws_access_key=AWS_ACCESS_KEY,
            aws_secret_key=AWS_SECRET_KEY,
            aws_region=REGION
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
    async def claude_forward(self, system_prompt, messages):
        """Send a request to Claude model with retry logic - optimized for high load."""
        try:
            # Add timeout to prevent hanging requests
            response = await asyncio.wait_for(
                self.client.messages.create(
                    model=MODEL,
                    max_tokens=20000,
                    thinking={
                        "type": "enabled",
                        "budget_tokens": 4000 
                    },
                    system=system_prompt,
                    messages=[{"role": "user", "content": messages}],
                    tools=[AdsTools().extraction]
                ),
                timeout=120.0  # 2 minute timeout
            )
            return response
        except asyncio.TimeoutError:
            logger.error("Claude API call timed out after 2 minutes")
            raise
        except Exception as e:
            logger.error(f"Error in Claude API call: {str(e)}")
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
            
        except Exception as e:
            logger.error(f"Error in unfolding inputs {request} with error {e}")
            raise
            
        try:
            response = await self.claude_forward(self.system_prompt, current_message_prompt)
            result = None
            
            for block in response.content:
                type = block.type
                if type == "text":
                    text = block.text
                    logger.info(f"Text: {text}")
                elif type == "tool_use":
                    logger.info(f"Tools calling. . .")
                    tool_use_input = block.input
                    logger.info(f"Tool use inputs : {tool_use_input}")
                    # Run RAG operation in thread pool to avoid blocking
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(None, self.rag.ads_forward, tool_use_input)
                else:
                    logger.info(f"Thinking Block : {block.thinking}")
                    
            if result:
                return result
            else:
                logger.info(f"No tools calling. . . returning empty result instead of re-calling")
                # Instead of re-calling Claude, return a default response to prevent cascading delays
                return []
                
        except Exception as e:
            logger.error(f"Error in forward method: {str(e)}")
            # Return empty result instead of raising exception to prevent cascading failures
            return []
    