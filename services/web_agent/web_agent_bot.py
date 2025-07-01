from shared.rag import RAG
from shared.rag import GoogleSearcher
from .tools import Tools
from .cart import create_cart_curl, add_package_to_cart, delete_package_curl, list_cart_packages_curl, delete_cart_curl, create_order_curl
from shared.utils.prompt_generator import PromptGenerator
from anthropic import AsyncAnthropicBedrock
from dotenv import load_dotenv
from tenacity import before_sleep_log, retry, stop_after_attempt, wait_random_exponential
import re
import os
import httpx
import base64
import logging
import requests
import json
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional, Union
import asyncio
from anthropic import AsyncAnthropicVertex
from pydantic import BaseModel, ValidationError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configuration constants
class Config:
    AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY')
    AWS_SECRET_KEY = os.getenv('AWS_SECRET_KEY')
    #REGION = 'us-east-1' #east-1, east-2, us-west-2
    REGION = 'us-west-2'
    PROJECT_ID = 'omnichannel-ai-integration'
    LOCATION = 'us-east5'
    API_KEY = "AIzaSyCgupEgvHnvynd_oTyDYVUPNbPUZS0nFFo"
    MODEL = {
        "sonnet_3_7":"us.anthropic.claude-3-7-sonnet-20250219-v1:0",
        "sonnet_4" : "us.anthropic.claude-sonnet-4-20250514-v1:0",
        'sonnet_3_6': 'us.anthropic.claude-3-5-sonnet-20241022-v2:0'
    }
    MAX_TOKENS = 8000
    TEMP = 0.0
    MAX_REASONING_TOKENS = 4000

class JibAIResponse(BaseModel):
    """Pydantic model for JibAI JSON response structure."""
    thinking: str
    response: str
    image: List[str]

class ResponseParser:
    """Simple and reliable parser for JibAI JSON responses."""
    
    @staticmethod
    def parse_response(text_response: str) -> Dict[str, Any]:
        """
        Parse the AI response to extract structured data.
        Handles both pure JSON and mixed text with JSON embedded.
        """
        logger.info("Parsing JSON response...")
        logger.info(f"Original response: {text_response}")
        
        # Method 1: Try parsing entire response as JSON first
        try:
            parsed_data = json.loads(text_response)
            # Validate structure with Pydantic
            validated_response = JibAIResponse(**parsed_data)
            logger.info(f"Parsed response: {validated_response.response}")
            logger.info(f"Images: {validated_response.image}")
            return {
                "response": validated_response.response,
                "thinking": validated_response.thinking,
                "image": validated_response.image
            }
        except (json.JSONDecodeError, ValidationError) as e:
            logger.debug(f"Method 1 failed: {e}")
        
        # Method 2: Extract JSON from mixed content using regex
        try:
            import re
            # Find JSON block using regex - more robust than bracket counting
            json_pattern = r'\{(?:[^{}]|{[^{}]*})*\}'
            json_matches = re.findall(json_pattern, text_response, re.DOTALL)
            
            for json_match in json_matches:
                try:
                    parsed_data = json.loads(json_match)
                    # Check if this looks like our expected structure
                    if isinstance(parsed_data, dict) and 'response' in parsed_data:
                        validated_response = JibAIResponse(**parsed_data)
                        logger.info(f"Parsed response: {validated_response.response}")
                        logger.info(f"Images: {validated_response.image}")
                        return {
                            "response": validated_response.response,
                            "thinking": validated_response.thinking,
                            "image": validated_response.image
                        }
                except (json.JSONDecodeError, ValidationError):
                    continue
        except Exception as e:
            logger.debug(f"Method 2 failed: {e}")
        
        # Method 3: Extract JSON from mixed content using bracket matching (fallback)
        try:
            # Find the JSON boundaries
            first_brace = text_response.find('{')
            last_brace = text_response.rfind('}')
            
            if first_brace != -1 and last_brace != -1 and first_brace < last_brace:
                json_part = text_response[first_brace:last_brace + 1]
                
                parsed_data = json.loads(json_part)
                # Validate structure with Pydantic  
                validated_response = JibAIResponse(**parsed_data)
                logger.info(f"Parsed response: {validated_response.response}")
                logger.info(f"Images: {validated_response.image}")
                return {
                    "response": validated_response.response,
                    "thinking": validated_response.thinking,
                    "image": validated_response.image
                }
        except (json.JSONDecodeError, ValidationError) as e:
            logger.debug(f"Method 3 failed: {e}")
            # Log the JSON string that failed for debugging
            logger.error(f"JSON parsing failed: {e}")
            if 'json_part' in locals():
                logger.error(f"JSON string: {json_part[:500]}...")
        
        # Method 4: Try to extract just the response field if JSON structure is malformed
        try:
            import re
            # Look for "response": "..." pattern
            response_pattern = r'"response"\s*:\s*"([^"]*(?:\\.[^"]*)*)"'
            response_match = re.search(response_pattern, text_response)
            if response_match:
                response_text = response_match.group(1).replace('\\"', '"').replace('\\n', '\n')
                logger.info(f"Extracted response using pattern matching: {response_text}")
                return {
                    "response": response_text,
                    "thinking": "",
                    "image": []
                }
        except Exception as e:
            logger.debug(f"Method 4 failed: {e}")
        
        # Method 5: Fallback - return the raw text
        logger.warning("JSON parsing failed. Using fallback method.")
        return {
            "response": text_response,
            "thinking": "",
            "image": []
        }

class JibAI:
    def __init__(self, global_storage):
        """
        Initialize the JibAI assistant with necessary components and prompts.
        
        Args:
            global_storage: Storage for conversation history and context
        """
        self.client = AsyncAnthropicBedrock(
            aws_access_key=Config.AWS_ACCESS_KEY,
            aws_secret_key=Config.AWS_SECRET_KEY,
            aws_region=Config.REGION
        )
        #self.client = AsyncAnthropicVertex(region=Config.LOCATION, project_id=Config.PROJECT_ID)
        self.prompt_generator = PromptGenerator()
        self.rag = RAG(global_storage=global_storage)
        self.google_searcher = GoogleSearcher(global_storage)
        self.tools = Tools()
        self.global_storage = global_storage
        
        # Load prompt templates
        self._load_prompt_templates()
        
        # Prepare cached system prompt and tools
        self._prepare_cached_components()

    def _load_prompt_templates(self):
        """Load all prompt templates from files."""
        self.misc = self._read_prompt_file('services/web_agent/prompts/misc.txt')
        self.system_prompt_interpret = self._read_prompt_file('services/web_agent/prompts/one_jib_system.txt')
        self.user_persona = self._read_prompt_file('services/web_agent/prompts/user_persona.txt')
        self.system_prompt_parse_xml = self._read_prompt_file('services/web_agent/prompts/parse_xml.txt')
        # Healthcare-specific prompts
        # Get the directory of this file and navigate to hl_prompts
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))
        category_tag_path = os.path.join(project_root, "hl_prompts", "category_tag.txt")
        self.category_tag_prompt = self._read_prompt_file(category_tag_path)
    
    def _prepare_cached_components(self):
        """Prepare cached system prompt and tools for better performance."""
        # Cache the main system prompt - this is the largest component
        self.cached_system_prompt = [
            {
                "type": "text",
                "text": self.system_prompt_interpret,
                "cache_control": {"type": "ephemeral"}
            }
        ]
        
        # Cache the tools array since retrieval tool is frequently used
        self.cached_tools = [
            self.tools.retrieval, 
            self.tools.cart,
            self.tools.ask_hospital
        ]
        
        # Cache just the retrieval tool for category tag calls
        self.cached_category_tools = []
    
    def _update_cached_system_prompt(self):
        """Update the cached system prompt with current date/time and user persona."""
        # Get current date and time
        current_date_time = datetime.now().strftime("%A, %d %B %Y, %I:%M %p")
        
        # Update system prompt with dynamic content
        #updated_prompt = self.system_prompt_interpret.replace("{CURRENT_DATE_TIME}", current_date_time)
        #updated_prompt = updated_prompt.replace("{USER_PERSONA}", self.user_persona)
        
        # Update cached system prompt
        self.cached_system_prompt = [
            {
                "type": "text", 
                "text": self.system_prompt_interpret,
                "cache_control": {"type": "ephemeral"}
            }
        ]
        
        return self.cached_system_prompt

    def _read_prompt_file(self, file_path: str) -> str:
        """
        Read the content of a prompt file.
        
        Args:
            file_path: Path to the prompt file
            
        Returns:
            Content of the file as a string
        """
        try:
            with open(file_path, 'r') as file:
                return file.read()
        except Exception as e:
            logger.error(f"Error reading prompt file {file_path}: {e}")
            return ""

    @retry(
        wait=wait_random_exponential(min=1, max=30), #300
        stop=stop_after_attempt(10)) # 10
    async def tell_claude(self, *args, **kwargs):
        """Send a request to Claude model with retry logic."""
        response = await self.client.messages.create(*args, **kwargs)
        # Log usage information
        if hasattr(response, 'usage'):
            logger.info(f"Claude API Usage - Input tokens: {response.usage.input_tokens}, Output tokens: {response.usage.output_tokens}")
            if hasattr(response.usage, 'cache_creation_input_tokens'):
                logger.info(f"Claude Cache Usage - Creation: {response.usage.cache_creation_input_tokens}, Read: {response.usage.cache_read_input_tokens}")
        return response
    
    @retry(
        wait=wait_random_exponential(min=1, max=30),
        stop=stop_after_attempt(3))
    async def tell_claude_to_ocr(self, *args, **kwargs):
        """Send a request to Claude for OCR with more limited retries."""
        response = await self.client.messages.create(*args, **kwargs)
        # Log usage information for OCR
        if hasattr(response, 'usage'):
            logger.info(f"Claude OCR Usage - Input tokens: {response.usage.input_tokens}, Output tokens: {response.usage.output_tokens}")
        return response

    @retry(
        wait=wait_random_exponential(min=1, max=30),
        stop=stop_after_attempt(3))
    async def tell_claude_cached(self, model, max_tokens, temperature, messages, tools=None, tool_choice=None, **kwargs):
        """Send a cached request to Claude model with retry logic."""
        response = await self.client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=self._update_cached_system_prompt(),
            messages=messages,
            tools=tools or self.cached_tools,
            tool_choice=tool_choice,
            **kwargs
        )
        # Log usage information for cached calls
        if hasattr(response, 'usage'):
            logger.info(f"Claude Cached Usage - Input tokens: {response.usage.input_tokens}, Output tokens: {response.usage.output_tokens}")
            if hasattr(response.usage, 'cache_creation_input_tokens'):
                logger.info(f"Claude Cache Metrics - Creation: {response.usage.cache_creation_input_tokens}, Read: {response.usage.cache_read_input_tokens}")
        return response
        
    async def _preprocessing(self, input_list: list) -> list:
        """
        Preprocess the input messages, extracting text from images via OCR.
        
        Args:
            input_list: List of input messages
            
        Returns:
            Processed list of messages
        """
        for message in input_list:
            # Handle case where content might be a string instead of a list
            if isinstance(message.get('content'), str):
                continue  # Skip string content, no preprocessing needed
            
            # Check if content is a list and has at least one item
            if (isinstance(message.get('content'), list) and 
                len(message['content']) > 0 and 
                isinstance(message['content'][0], dict) and
                message['content'][0].get('type') == 'image_url'):
                
                url = message['content'][0]['image_url']['url']
                text_ocr = await self.ocr(url)
                if text_ocr is not None:
                    message['content'] = [{'type': 'text', 'text': text_ocr}]
        return input_list

    async def ocr(self, url: str) -> Optional[str]:
        """
        Perform OCR on an image URL using Claude.
        
        Args:
            url: URL of the image
            
        Returns:
            OCR extracted text or None if an error occurred
        """
        try:
            # Get image type and encode to base64 # this one is not robust, need to improve
            response = requests.get(url)
            image_type = response.headers.get('content-type', 'image/png')
            image_data = base64.standard_b64encode(response.content).decode("utf-8")
            #check image type, assuming url won't tell the image type
            print(image_type)
            message = await self.tell_claude_to_ocr(
                model=Config.MODEL['haiku'],
                max_tokens=Config.MAX_TOKENS,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": image_type,
                                    "data": image_data,
                                },
                            },
                            {
                                "type": "text",
                                "text": "อธิบายรูปนี้แหละสินค้าหรือบริการที่พบ"
                            }
                        ],
                    }
                ],
            )
            ocr_text = '<IMAGE_DESCRIPTION>' + message.content[0].text + '</IMAGE_DESCRIPTION>'
            return ocr_text
        except Exception as e:
            logger.error(f"Error at OCR: {e}")
            return '<IMAGE_DESCRIPTION>URLs is expired, skip this image</IMAGE_DESCRIPTION>'
    
    async def extract_xml(self, text_resp, tag):
        """Extract content from XML-like tags in text."""
        pattern = f"<{tag}>(.*?)</{tag}>"
        match = re.search(pattern, text_resp, re.DOTALL)
        match_text = match.group(1).strip() if match else None
        if match_text is None:
            logger.info("Jib Agent : fixing XML extraction...")
            fixed_resp = await self.tell_claude(
                model=Config.MODEL['haiku'],
                max_tokens=Config.MAX_TOKENS,
                temperature=Config.TEMP,
                system=self.system_prompt_parse_xml,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": text_resp
                        }
                    ]
                }]
            )
            # Log XML fixing usage
            logger.info(f"XML Fix Usage - Input: {fixed_resp.usage.input_tokens}, Output: {fixed_resp.usage.output_tokens}")
            
            fixed_resp = fixed_resp.content[0].text
            return fixed_resp
        else:
            return match_text

    async def _handle_retrieval(self, chat_resp, chats, last_query, routing_layer_usage, thought_block, tool_use_block, room_id):
        """
        Handle the retrieval tool flow.
        
        Args:
            chat_resp: Response from the first layer
            chats: Chat history
            last_query: The last user query
            routing_layer_usage: Token usage from routing layer
            thought_block: The thought process block (can be None)
            tool_use_block: The tool use block
            
        Returns:
            Response, token usage, and thought dictionary
        """
        search_query = tool_use_block.input['search_keyword']
        preferred_area = tool_use_block.input['preferred_area']
        radius = tool_use_block.input['radius']
        category_tag = tool_use_block.input['category_tag']
        package_url = tool_use_block.input['package_url']
        action_choice = tool_use_block.input['reason']
        logger.info(f"RAG-ing for {search_query} in {preferred_area} with radius {radius} and category {category_tag} and action {action_choice} and package_url {package_url}")

        # Handle case where thought_block might be None
        if thought_block and hasattr(thought_block, 'text'):
            agent_thought_step = thought_block.text
        else:
            agent_thought_step = "I need to search for relevant information."
            
        tool_use_id = tool_use_block.id
        tool_use_name = tool_use_block.name
        tool_use_inputs = tool_use_block.input
        condition1 = 'hdAd=1' in str(last_query)
        condition2 = ('สวัสดี/สอบถาม' in str(last_query) and 'highlight' in str(search_query))
        final_result = condition1 or condition2
        if final_result:
            quality_tag = 'Junk'
        else:
            quality_tag = 'Quality'
        print(category_tag)
        print(category_tag +" "+quality_tag)
        final_tag = category_tag +" "+quality_tag
        if action_choice == '<GET_PACKAGE_METADATA>' or action_choice == 'GET_PACKAGE_METADATA':
            logger.info("Jib Agent : Retrieving package url...")
            package_url_context = self.rag._get_package_url(search_query, preferred_area, radius, category_tag)
            agent_scratchpad = {
                "role":"assistant", 
                "content":[
                    {
                        "type": "text",
                        "text": agent_thought_step
                    },
                    {
                        "type": "tool_use",
                        "id": tool_use_id,
                        "name": tool_use_name,
                        "input": tool_use_inputs
                    }
                ]
            }
            tool_result = {
                "role":"user",
                "content":[
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": package_url_context
                    }
                ]
            }
            chats.append(agent_scratchpad)
            chats.append(tool_result)
            logger.info("Jib Agent : I'm done with retrieving package url... I should decide what to do next")
            return await self.forward(chats, room_id) # Agent Jump
        elif action_choice == '<PROVIDE_PACKAGE_INFO>' or action_choice == 'PROVIDE_PACKAGE_INFO':
            logger.info("Jib Agent : Retrieving package info from URL...")
            package_context = self.rag.get_package_info_from_url(package_url)
            agent_scratchpad = {
                "role":"assistant", 
                "content":[
                    {
                        "type": "text",
                        "text": agent_thought_step
                    },
                    {
                        "type": "tool_use",
                        "id": tool_use_id,
                        "name": tool_use_name,
                        "input": tool_use_inputs
                    }
                ]
            }
            tool_result = {
                "role":"user",
                "content":[
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": package_context
                    }
                ]
            }
            chats.append(agent_scratchpad)
            chats.append(tool_result)
            logger.info("Jib Agent : I'm done with retrieving package info... I should decide what to do next")
            return await self.forward(chats, room_id) # Agent Jump
        else:
            agent_scratchpad = {
                "role":"assistant", 
                "content":[
                    {
                        "type": "text",
                        "text": agent_thought_step
                    },
                    {
                        "type": "tool_use",
                        "id": tool_use_id,
                        "name": tool_use_name,
                        "input": tool_use_inputs
                    }
                ]
            }
            tool_result = {
                "role":"user",
                "content":[
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": """ Some parameters are not correct, please check your action again. it's supposed to be either <GET_PACKAGE_METADATA> or <PROVIDE_PACKAGE_INFO> ONLY"""
                    }
                ]
            }

            return await self.forward(chats, room_id)
          

    async def _handle_handover(self, chat_resp, tool_name, last_query, routing_layer_usage):
        """
        Handle handover to human agents.
        
        Args:
            chat_resp: Response from the first layer
            tool_name: Name of the handover tool
            last_query: The last user query
            routing_layer_usage: Token usage from routing layer
            
        Returns:
            Handover instruction, token usage, and thought dictionary
        """
        time_stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.info(f"Handling {tool_name}")
        
        # Default handover note
        handover_note = ""
        
        # Extract package info if available
        if tool_name in ['handover_to_cx', 'handover_asap']:
            try:
                handover_note = chat_resp.content[1].input.get("package_name", "")
            except Exception:
                handover_note = ""
        
        token_dict = {
            "date": time_stamp,
            "layer_routing_input": routing_layer_usage.input_tokens,
            "layer_routing_output": routing_layer_usage.output_tokens,
            "layer_0_input": 0,
            "layer_0_output": 0,
            "layer_1_input": 0,
            "layer_1_output": 0,
            "layer_2_input": 0,
            "layer_2_output": 0,
            "total_input_sonnet": routing_layer_usage.input_tokens,
            "total_output_sonnet": routing_layer_usage.output_tokens,
            "total_input_haiku": 0,
            "total_output_haiku": 0
        }
        
        thought_dict = {
            "response_text": "น้องจิ๊บขออนุญาตประสานงานกับฝ่ายบริการลูกค้าให้นะคะ กรุณารอสักครู่ค่ะ",
            "date": time_stamp,
            "last_q": last_query,
            "router_thought": str(chat_resp),
            "haiku_thought": "-",
            "sonnet_1_thought": "-",
            "sonnet_2_thought": "-"
        }
        
        # Determine the handover instruction based on tool name
        if tool_name == 'handover_to_cx':
            return f"QISCUS_INTEGRATION_TO_CX: {handover_note}", token_dict, thought_dict
        elif tool_name == 'handover_to_bk':
            return "QISCUS_INTEGRATION_TO_BK", token_dict, thought_dict
        elif tool_name == 'handover_asap':
            return f"QISCUS_INTEGRATION_TO_IMMEDIATE_CX: {handover_note}", token_dict, thought_dict
        else:
            return "QISCUS_INTEGRATION_TO_CX", token_dict, thought_dict

         

    async def _get_tag(self, chats):
        """
        Handle the influenza vaccine specialized agent.
        
        Args:
            chats: Chat history
            
        Returns:
            Response text and empty dictionaries for token usage and thoughts
        """
        # Create cached system prompt for category tagging
        cached_category_system = [
            {
                "type": "text",
                "text": self.category_tag_prompt,
                "cache_control": {"type": "ephemeral"}
            }
        ]
        
        category_resp = await self.tell_claude(
            model=Config.MODEL['haiku'], 
            max_tokens=Config.MAX_TOKENS, 
            temperature=0,
            system=cached_category_system,
            messages=chats
        )
        # Log category tag usage
        logger.info(f"Category Tag Usage - Input: {category_resp.usage.input_tokens}, Output: {category_resp.usage.output_tokens}")
        
        category_text = category_resp.content[0].text
        category_tag = re.search(r"<category_tag>(.*?)</category_tag>", category_text, re.DOTALL)
        if category_tag:
            category_tag = category_tag.group(1).strip()
        else:
            category_tag = "<UNKNOWN>"
        last_query = str(chats[-1])
        if 'hdAd=1' in str(last_query):
            quality_tag = 'Junk'
        else:
            quality_tag = 'Quality'
        print(category_tag)
        print(category_tag +" "+quality_tag)
        final_tag = category_tag +" "+quality_tag

        return str(final_tag)


    
    async def _handle_cart(self,chats,tool_use_block,thought_block, room_id):
        """
        Handle the cart agent.
        
        Args:
            chats: Chat history
            tool_use_block: Tool use block
            thought_block: The thought process block (can be None)
        Returns:
            A tuple containing the response, token usage information, and thought process
        """
        # Handle case where thought_block might be None
        if thought_block and hasattr(thought_block, 'text'):
            agent_thought_step = thought_block.text
        else:
            agent_thought_step = "I need to handle the cart operation."
            
        tool_use_id = tool_use_block.id
        tool_use_name = tool_use_block.name
        tool_use_inputs = tool_use_block.input
        action = tool_use_block.input['action']
        package_url = tool_use_block.input['package_url']
        cart_id = tool_use_block.input['cart_id']
        logger.info(f"Cart tool called with action {action}")
        logger.info(f"tool_use_inputs: {tool_use_inputs}")
        agent_scratchpad = {
            "role":"assistant", 
            "content":[
            {
                "type": "text",
                "text": agent_thought_step
            },
            {
                "type": "tool_use",
                "id": tool_use_id,
                "name": tool_use_name,
                "input": tool_use_inputs
            }
                    ]
                            }
        chats.append(agent_scratchpad)
        if action == "create_cart":
            cart_response = create_cart_curl(room_id)

        elif action == "delete_cart":
            cart_response = delete_cart_curl(cart_id, room_id)
        elif action == "add_item_to_cart":
            cart_response = add_package_to_cart(cart_id, package_url, room_id)
        elif action == "delete_item_from_cart":
            cart_response = delete_package_curl(package_url, room_id, cart_id)    
        elif action == "view_cart":
            cart_response = list_cart_packages_curl(cart_id, room_id)
        elif action == "create_order":
            cart_response = create_order_curl(cart_id, room_id)
        

        tool_result = {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": str(cart_response)
                }
                        ]
            }
        print(f"tool_result: {tool_result}")
        chats.append(tool_result)
        return await self.forward(chats, room_id)
    
    async def _call_hospital_api(self, room_id: str, question: str, package_url: str, brand: str) -> str:
        """
        Make an API call to the hospital with the question, package URL, and brand.
        
        Args:
            room_id: Room identifier
            question: The question to ask the hospital
            package_url: The URL of the package
            brand: The brand/hospital name
            
        Returns:
            Response from the hospital API
        """
        try:
            endpoint_url = "https://jib-second-brain-dot-omnichannel-ai-integration.et.r.appspot.com/ask"
            
            input_data = {
                "room_id": room_id,
                "question": question,
                "package_url": package_url,
                "brand": brand,
            }
            
            logger.info(f"Calling hospital API for brand: {brand}")
            logger.info(f"Question: {question}")
            logger.info(f"Package URL: {package_url}")
            logger.info(f"Room ID: {room_id}")
            
            # Use httpx for async HTTP requests
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(endpoint_url, json=input_data)
                response.raise_for_status()
                
                # Parse the response
                response_data = response.json()
                logger.info(f"Hospital API response: {response_data}")
                
                # Extract the answer from the response
                # Adjust this based on the actual response format from your API
                if isinstance(response_data, dict):
                    return response_data.get("answer", response_data.get("response", str(response_data)))
                else:
                    return str(response_data)
                    
        except httpx.TimeoutException:
            logger.error(f"Timeout calling hospital API for brand: {brand}")
            return f"Sorry, the request to {brand} timed out. Please try again later."
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error calling hospital API: {e.response.status_code} - {e.response.text}")
            return f"Sorry, I couldn't get a response from {brand} at the moment (HTTP {e.response.status_code}). Please try again later."
            
        except Exception as e:
            logger.error(f"Error calling hospital API: {e}")
            return f"Sorry, I couldn't get a response from {brand} at the moment. Please try again later or contact them directly."

    async def _handle_ask_hospital(self, room_id, tool_use_block, thought_block, chats):
        """
        Handle the ask_hospital tool.
        
        Args:
            room_id: Room identifier
            tool_use_block: Tool use block containing the question and package_url
            thought_block: The thought process block (can be None)
            chats: Chat history
            
        Returns:
            Result from forward method continuing the agentic loop
        """
        # Handle case where thought_block might be None
        if thought_block and hasattr(thought_block, 'text'):
            agent_thought_step = thought_block.text
        else:
            agent_thought_step = "I need to ask the hospital for more information."
            
        tool_use_id = tool_use_block.id
        tool_use_name = tool_use_block.name
        tool_use_inputs = tool_use_block.input
        question = tool_use_block.input['question']
        package_url = tool_use_block.input['package_url']
        
        logger.info(f"Ask hospital tool called with question: {question}")
        logger.info(f"Package URL: {package_url}")
        logger.info(f"tool_use_inputs: {tool_use_inputs}")
        
        # Create agent scratchpad
        agent_scratchpad = {
            "role": "assistant", 
            "content": [
                {
                    "type": "text",
                    "text": agent_thought_step
                },
                {
                    "type": "tool_use",
                    "id": tool_use_id,
                    "name": tool_use_name,
                    "input": tool_use_inputs
                }
            ]
        }
        chats.append(agent_scratchpad)
        
        # Fetch brand from package.csv using package_url
        brand = None
        hospital_response = ""
        
        try:
            knowledge_base = self.global_storage.knowledge_base
            matching_rows = knowledge_base[knowledge_base['URL'] == package_url]
            
            if not matching_rows.empty:
                brand = matching_rows.iloc[0]['Brand']
                logger.info(f"Found brand: {brand} for package URL: {package_url}")
                
                # Call hospital API
                hospital_response = await self._call_hospital_api(room_id, question, package_url, brand)
                
            else:
                logger.warning(f"No matching package found for URL: {package_url}")
                hospital_response = f"Brand not found for package URL: {package_url}. Please verify the package URL is correct or use the retrieval tool to get the correct package information first."
                
        except Exception as e:
            logger.error(f"Error fetching brand from package.csv: {e}")
            hospital_response = f"Error occurred while looking up package information for URL: {package_url}. Please try again or use the retrieval tool to get the correct package information."
        
        # Create tool result
        tool_result = {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": str(hospital_response)
                }
            ]
        }
        
        logger.info(f"Hospital response: {hospital_response}")
        chats.append(tool_result)
        
        # Continue the agentic loop by calling forward
        return await self.forward(chats, room_id)

    async def _handle_web_recommendation(self, chat_resp, chats, last_query, routing_layer_usage, thought_block, tool_use_block, room_id):
        """
        Handle the web_recommendation tool.
        
        Args:
            chat_resp: Response from the first layer
            chats: Chat history
            last_query: The last user query
            routing_layer_usage: Token usage from routing layer
            thought_block: The thought process block (can be None)
            tool_use_block: The tool use block
            room_id: Room identifier
            
        Returns:
            Result from forward method continuing the agentic loop
        """
        # Handle case where thought_block might be None
        if thought_block and hasattr(thought_block, 'text'):
            agent_thought_step = thought_block.text
        else:
            agent_thought_step = "I need to get web recommendations for this query."
            
        tool_use_id = tool_use_block.id
        tool_use_name = tool_use_block.name
        tool_use_inputs = tool_use_block.input
        query = tool_use_block.input['query']
        recommendation_type = tool_use_block.input['type']
        
        logger.info(f"Web recommendation tool called with query: {query}")
        logger.info(f"Recommendation type: {recommendation_type}")
        logger.info(f"tool_use_inputs: {tool_use_inputs}")
        
        # Create agent scratchpad
        agent_scratchpad = {
            "role": "assistant", 
            "content": [
                {
                    "type": "text",
                    "text": agent_thought_step
                },
                {
                    "type": "tool_use",
                    "id": tool_use_id,
                    "name": tool_use_name,
                    "input": tool_use_inputs
                }
            ]
        }
        chats.append(agent_scratchpad)
        
        # Call the RAG web_recommendation method
        try:
            web_recommendation_context = self.rag.web_recommendation(query, recommendation_type)
            logger.info(f"Web recommendation context retrieved successfully")
        except Exception as e:
            logger.error(f"Error calling RAG web_recommendation: {e}")
            web_recommendation_context = f"Error occurred while getting web recommendations: {str(e)}"
        
        # Create tool result
        tool_result = {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": str(web_recommendation_context)
                }
            ]
        }
        
        logger.info(f"Web recommendation result: {web_recommendation_context}")
        chats.append(tool_result)
        
        # Continue the agentic loop by calling forward
        return await self.forward(chats, room_id)

    async def forward(self, chats, room_id, json_retry_count=0):
        """
        Main function to process user input and generate responses.
        
        Args:
            chats: List of chat messages
            room_id: Room identifier
            json_retry_count: Number of times we've retried due to JSON parsing failures
            
        Returns:
            A tuple containing the response, token usage information, and thought process
            
        """
        # Prevent infinite loops - max 2 retries for JSON parsing
        MAX_JSON_RETRIES = 2
        
        last_query = str(chats[-1])  # for CoT log
        
        # Preprocess images if any
        chats = await self._preprocessing(chats)
        logger.info('OCR. . .')
        
        # Initial agent layer to determine how to handle the request
        prompt_layer_0 = chats
         
        logger.info('Jib is thinking...')
        chat_resp = await self.tell_claude_cached(
            model=Config.MODEL['sonnet_4'],
            max_tokens=Config.MAX_TOKENS,
            temperature=Config.TEMP,
            messages=prompt_layer_0,
            tools=[
                self.tools.web_recommendation,
                #self.tools.retrieval
            ],
            tool_choice={'type': 'auto'}
        )
        
        # Log main routing usage
        logger.info(f"Main Routing Usage - Input: {chat_resp.usage.input_tokens}, Output: {chat_resp.usage.output_tokens}")
        if hasattr(chat_resp.usage, 'cache_read_input_tokens'):
            logger.info(f"Main Routing Cache - Read: {chat_resp.usage.cache_read_input_tokens}, Creation: {chat_resp.usage.cache_creation_input_tokens}")
        
        router_thought = str(chat_resp)
        print(f"Router thought: {router_thought}")
        routing_layer_usage = chat_resp.usage

        # Safely print thought - find the first text block from all content blocks
        try:
            text_block = next((block for block in chat_resp.content if hasattr(block, 'text')), None)
            if text_block:
                print(f"Thought: {text_block.text}")
            else:
                print("Thought: No text block found in response")
        except Exception as e:
            print(f"Could not extract thought: {e}")
        
        if chat_resp.stop_reason == 'tool_use':
            # Find the text block and tool use block
            text_block = None
            tool_use_block = None
            
            for block in chat_resp.content:
                if hasattr(block, 'text'):
                    text_block = block
                elif hasattr(block, 'name'):  # ToolUseBlock has 'name' attribute
                    tool_use_block = block
            
            if tool_use_block is None:
                logger.error("Tool use expected but no tool use block found")
                return {"text": "เกิดข้อผิดพลาดในระบบ กรุณาลองใหม่อีกครั้ง", "image": []}
                
            logger.info(f'Tool calling: {tool_use_block.name}')
            
            # Handle different tools
            if tool_use_block.name == 'retrieval':
                return await self._handle_retrieval(chat_resp, chats, last_query, routing_layer_usage, text_block, tool_use_block, room_id)
            
            elif tool_use_block.name == 'web_recommendation':
                return await self._handle_web_recommendation(chat_resp, chats, last_query, routing_layer_usage, text_block, tool_use_block, room_id)
            
            elif tool_use_block.name in ['handover_to_cx', 'handover_to_bk', 'handover_asap']:
                return await self._handle_handover(
                    chat_resp, 
                    tool_use_block.name, 
                    last_query, 
                    routing_layer_usage
                )

            elif tool_use_block.name == "cart":
                return await self._handle_cart(chats, tool_use_block, text_block, room_id)
            
            elif tool_use_block.name == "ask_hospital":
                return await self._handle_ask_hospital(room_id, tool_use_block, text_block, chats)
            
        else:
            # Generic response handling with JSON parser
            logger.info(f"Parsing JSON response...")
            
            # Safely extract text from the first content block
            try:
                if hasattr(chat_resp.content[0], 'text'):
                    text_resp = chat_resp.content[0].text
                else:
                    logger.error(f"First content block is not a text block: {type(chat_resp.content[0])}")
                    return {"text": "เกิดข้อผิดพลาดในระบบ กรุณาลองใหม่อีกครั้ง", "image": []}
            except (IndexError, AttributeError) as e:
                logger.error(f"Error accessing content: {e}")
                return {"text": "เกิดข้อผิดพลาดในระบบ กรุณาลองใหม่อีกครั้ง", "image": []}
                
            logger.info(f"Original response: {text_resp}")
            
            # Parse JSON response
            parsed_response = ResponseParser.parse_response(text_resp)
            
            # Check if we got a valid response (our new parser always returns something)
            if not parsed_response.get("response"):
                # Check if we've exceeded retry limit
                if json_retry_count >= MAX_JSON_RETRIES:
                    logger.error(f"JSON parsing failed after {MAX_JSON_RETRIES} retries. Returning fallback response.")
                    return {
                        "text": "ขออภัยค่ะ เกิดข้อผิดพลาดในระบบ กรุณาลองถามใหม่อีกครั้งค่ะ", 
                        "image": []
                    }
                
                # If parsing failed, send error back to JibAI to fix
                logger.warning(f"JSON parsing failed (attempt {json_retry_count + 1}/{MAX_JSON_RETRIES + 1}): No valid response found")
                error_message = {
                    "role": "user",
                    "content": f"Parser (do not reply to parser) : Please fix the JSON format: {parsed_response['response']}"
                }
                chats.append(error_message)
                # Recursively call forward to let JibAI fix the format, with incremented retry count
                return await self.forward(chats, room_id, json_retry_count + 1)
            
            logger.info(f"Parsed response: {parsed_response['response']}")
            logger.info(f"Images: {parsed_response['image']}")
            
            return {
                "text": parsed_response["response"], 
                "image": parsed_response["image"]
            }