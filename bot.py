from src.RAG import RAG
from src.google_searcher import GoogleSearcher
from tools import Tools
from cart import create_cart_curl, add_package_to_cart,delete_package_curl, list_cart_packages_curl, delete_cart_curl, create_order_curl
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
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional, Union
import asyncio
from anthropic import AsyncAnthropicVertex

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
        "sonnet_4" :"us.anthropic.claude-sonnet-4-20250514-v1:0",
        "sonnet_3_7":"us.anthropic.claude-3-7-sonnet-20250219-v1:0",
        #"sonnet_3_7":"claude-3-7-sonnet@20250219",
        #'sonnet': "anthropic.claude-3-5-sonnet-20240620-v1:0",
        'sonnet': "claude-3-5-sonnet-v2@20241022",
        #'sonnet': "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
        'haiku': "anthropic.claude-3-haiku-20240307-v1:0",
        #'haiku': "us.anthropic.claude-3-5-haiku-20241022-v1:0",
        'sonnet_3_6': 'us.anthropic.claude-3-5-sonnet-20241022-v2:0'
    }
    MAX_TOKENS = 8000
    TEMP = 0.0
    MAX_REASONING_TOKENS = 4000

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
        
        # Load prompt templates
        self._load_prompt_templates()

    def _load_prompt_templates(self):
        """Load all prompt templates from files."""
        self.misc = self._read_prompt_file('src/prompts/misc.txt')
        self.system_prompt_layer_1 = self._read_prompt_file('src/prompts/first_layer.txt')
        self.system_prompt_layer_2 = self._read_prompt_file('src/prompts/middle_layer.txt')
        self.system_prompt_layer_3 = self._read_prompt_file('src/prompts/last_layer.txt')
        self.system_prompt_interpret = self._read_prompt_file('src/prompts/interpret.txt')
        self.user_persona = self._read_prompt_file('src/prompts/user_persona.txt')
        self.system_prompt_parse_xml = self._read_prompt_file('src/prompts/parse_xml.txt')
        # Healthcare-specific prompts
        self.category_tag_prompt = self._read_prompt_file('hl_prompts/category_tag.txt')
    
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
        wait=wait_random_exponential(min=1, max=2), #300
        stop=stop_after_attempt(10)) # 10
    async def tell_claude(self, *args, **kwargs):
        """Send a request to Claude model with retry logic."""
        return await self.client.messages.create(*args, **kwargs) 
    
    @retry(
        wait=wait_random_exponential(min=1, max=30),
        stop=stop_after_attempt(3))
    async def tell_claude_to_ocr(self, *args, **kwargs):
        """Send a request to Claude for OCR with more limited retries."""
        return await self.client.messages.create(*args, **kwargs)
        
    async def _preprocessing(self, input_list: list) -> list:
        """
        Preprocess the input messages, extracting text from images via OCR.
        
        Args:
            input_list: List of input messages
            
        Returns:
            Processed list of messages
        """
        for message in input_list:
            if message['content'][0]['type'] == 'image_url':
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
                model=Config.MODEL['sonnet_3_7'],
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
                model=Config.MODEL['sonnet_3_7'],
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
            
        Returns:
            Response, token usage, and thought dictionary
        """
        search_query = chat_resp.content[1].input['search_keyword']
        preferred_area = chat_resp.content[1].input['preferred_area']
        radius = chat_resp.content[1].input['radius']
        category_tag = chat_resp.content[1].input['category_tag']
        package_url = chat_resp.content[1].input['package_url']
        action_choice = chat_resp.content[1].input['reason']
        logger.info(f"RAG-ing for {search_query} in {preferred_area} with radius {radius} and category {category_tag} and action {action_choice} and package_url {package_url}")

        agent_thought_step = thought_block.text
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
            return await self.forward(chats, room_id, last_query) # Agent Jump
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
            return await self.forward(chats, room_id, last_query) # Agent Jump
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

            return await self.forward(chats, room_id, last_query)
          

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
        category_resp = await self.tell_claude(
            model=Config.MODEL['sonnet_3_7'], 
            max_tokens=Config.MAX_TOKENS, 
            temperature=0,
            system=self.category_tag_prompt,
            messages=chats
        )
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


    
    async def _handle_cart(self,chats,tool_use_block,thought_block, room_id,last_query):
        """
        Handle the cart agent.
        
        Args:
            chats: Chat history
            tool_use_block: Tool use block
        Returns:
            A tuple containing the response, token usage information, and thought process
        """
        agent_thought_step = thought_block.text
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
        return await self.forward(chats, room_id, last_query)
    
    async def forward(self, chats,room_id, last_query):
        """
        Main function to process user input and generate responses.
        
        Args:
            chats: List of chat messages
            
        Returns:
            A tuple containing the response, token usage information, and thought process
            
        """
        #MCP fetching things into system prompt
        #get current date and time for example : Wednesday, 30 April 2025, 10:00 AM
        current_date_time = datetime.now().strftime("%A, %d %B %Y, %I:%M %p")
        #replace {CURRENT_DATE_TIME} in system prompt with current date and time
        #self.system_prompt_interpret = self.system_prompt_interpret.replace("{CURRENT_DATE_TIME}", current_date_time)
        #self.system_prompt_interpret = self.system_prompt_interpret.replace("{USER_PERSONA}", self.user_persona)
        #check for hdexpress keyword in last_query
 
        # Preprocess images if any
        chats = await self._preprocessing(chats)
        logger.info('OCR. . .')
            
        # Initial agent layer to determine how to handle the request
        prompt_layer_0 = chats
         
        logger.info('Jib is thinking...')
        chat_resp = await self.tell_claude(
            model=Config.MODEL['sonnet_3_7'],
            max_tokens=Config.MAX_TOKENS,
            temperature=Config.TEMP,
            system=[
                {
                    "type": "text",
                    "text": self.system_prompt_interpret,
                    "cache_control": {"type": "ephemeral"}
                }
            ],
            messages=prompt_layer_0,
            tools=[
                self.tools.retrieval, 
                self.tools.handover_to_cx,
                self.tools.handover_to_bk,
                self.tools.handover_asap,
                self.tools.cart
            ],
            tool_choice={'type': 'auto'}
        )
        
        router_thought = str(chat_resp)
        routing_layer_usage = chat_resp.usage

        
        if chat_resp.stop_reason == 'tool_use':
            logger.info(f'Tool calling: {chat_resp.content[1].name}')
            thought_block = next(block for block in chat_resp.content if block.type == 'text')
            tool_use_block = next(block for block in chat_resp.content if block.type == 'tool_use')
            
            # Handle different tools
            if chat_resp.content[1].name == 'retrieval':
                return await self._handle_retrieval(chat_resp, chats, last_query, routing_layer_usage, thought_block, tool_use_block, room_id)
            
            elif chat_resp.content[1].name in ['handover_to_cx', 'handover_to_bk', 'handover_asap']:
                return await self._handle_handover(
                    chat_resp, 
                    chat_resp.content[1].name, 
                    last_query, 
                    routing_layer_usage
                )

            elif chat_resp.content[1].name == "cart":
                return await self._handle_cart(chats, tool_use_block, thought_block, room_id,last_query)
            
        else:
            # Generic response handling
            logger.info(f"Parsing response. . .")
            text_resp = chat_resp.content[0].text
            logger.info(f"Original response: {text_resp}")
            xml_resp = await self.extract_xml(text_resp, 'response')
            logger.info(f"Parsed response: {xml_resp}")
            return {"text":xml_resp, "image":[]}, {}, {}
            #return await self._handle_generic_response(chat_resp, chats, last_query, routing_layer_usage)
    
    async def claude_reason(self, chats):

        resp = await self.tell_claude(
            model=Config.MODEL['sonnet_3_7'],
            max_tokens=Config.MAX_REASONING_TOKENS,
            system="""
            language and tone:
            <langauge_style>
            -begining of response : do not say "hello" or "thank you for asking" or "I understand that you want to....." in the beginning of sentences when previous turn already said it, beginning of response should be answer of the question and straight to the point
            - answer in user's language. 
            - if user speaks in Thai then your name will be "จิ๊บ" and call user as "คุณลูกค้า" and use "ค่ะ"OR"คะ"OR"ค่า" to end the sentences ad your age is 22 years old  
            - พิมลากตัวอักษรสุดท้ายก่อนจะเปลี่ยนเรื่องคุยหรือทอปปิคเช่น "ค่ะะ" "ค่าา" "คะะ" 
            - เรียกแทนตัวเองว่า "จิ๊บ" หรือ "เรา" เสมอ ห้ามเรียกตัวเองว่า "ดิฉัน" หรือ "ฉัน"
            - do not provide any mobile phone numbers, ONLY ending the response with kind question to continue the conversation flow
            - do not use formal vocabs but instead use casual vocabs but in formal tone instead. tone is what makes conversation polite, vocabs are just medium.
            - use emojis about Summer Month to make it feels warm and comfortable like Pop City vibe 80s japanese summer,  and also use hands+face emojis to convey emotions like human
            - you provide full google map url along side with actual address
            - you answer only what user is asking for, do not provide any other information, let them ask you back.
            - always provide package url when you recommend a package. and a full google map url when you provide address.
            - always put your answer in <response> tag and <selected_image> tag if there's an image to show. please always put <selected_image> after <response> section.
            </language_style>


            """,
            messages=chats,
            thinking={
                "type": "enabled",
                "budget_tokens": 1300
            },
            tools=[
                self.kid_tools.cart
            ],
            tool_choice={'type': 'auto'}
        )
        print(resp)
        print(resp.content[0].thinking)
        try:
            print(resp.content[1].text)
            out = resp.content[1].text
        except:
            print(resp.content[2].text)
            out = resp.content[2].text

        # Extract response using non-greedy match
        response = re.search(r"<response>(.*?)</response>", out, re.DOTALL)
        if response:
            response = response.group(1).strip()
        else:
            response = "เกิดความผิดพลาดในระบบตอบอัตโนมัติ น้องจิ๊บรบกวนคุณลูกค้าช่วยพิมข้อความมาอีกทีได้มั้ยคะ"

        # Extract image URLs separately
        image_url = re.search(r"<selected_image>(.*?)</selected_image>", out, re.DOTALL)
        if image_url:
            image_url = image_url.group(1).strip()
            url_pattern = r"https?://[^\s<]+"
            image_url_list = re.findall(url_pattern, image_url)
        else:
            image_url_list = []

        print(image_url_list)
        return response, image_url_list