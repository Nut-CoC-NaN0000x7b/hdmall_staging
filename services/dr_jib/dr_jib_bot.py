from shared.rag import RAG
from shared.rag import GoogleSearcher
from .tools import Tools
from .dummy_tools import KidTools
# Cart functionality removed - only JibAI should use cart
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
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional, Union
import asyncio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configuration constants
class Config:
    AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY')
    AWS_SECRET_KEY = os.getenv('AWS_SECRET_KEY')
    REGION = 'us-east-1' #east-1, east-2, us-west-2
    MODEL = {
        "sonnet_3_7":"us.anthropic.claude-3-7-sonnet-20250219-v1:0",
        'sonnet': "anthropic.claude-3-5-sonnet-20240620-v1:0",
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
        self.prompt_generator = PromptGenerator()
        self.rag = RAG(global_storage=global_storage)
        self.google_searcher = GoogleSearcher(global_storage)
        self.tools = Tools()
        self.kid_tools = KidTools()
        
        # Load prompt templates
        self._load_prompt_templates()

    def _load_prompt_templates(self):
        """Load all prompt templates from files."""
        self.misc = self._read_prompt_file('shared/rag/prompts/misc.txt')
        self.system_prompt_layer_1 = self._read_prompt_file('shared/rag/prompts/first_layer.txt')
        self.system_prompt_layer_2 = self._read_prompt_file('shared/rag/prompts/middle_layer.txt')
        self.system_prompt_layer_3 = self._read_prompt_file('shared/rag/prompts/last_layer.txt')
        self.system_prompt_interpret = self._read_prompt_file('shared/rag/prompts/interpret.txt')
        
        # Healthcare-specific prompts
        # Get the directory of this file and navigate to hl_prompts
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))
        category_tag_path = os.path.join(project_root, "hl_prompts", "category_tag.txt")
        self.category_tag_prompt = self._read_prompt_file(category_tag_path)
    
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
                model=Config.MODEL['sonnet'],
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
    
    def extract_xml(self, text_resp, tag):
        """Extract content from XML-like tags in text."""
        pattern = f"<{tag}>(.*?)</{tag}>"
        match = re.search(pattern, text_resp, re.DOTALL)
        return match.group(1).strip() if match else None

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
        action_choice = chat_resp.content[1].input['reason']
        logger.info(f"RAG-ing for {search_query} in {preferred_area} with radius {radius} and category {category_tag} and action {action_choice}")

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
        if action_choice == '<GET_PACKAGE_METADATA>':
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
            
        logger.info(f"Search query: {search_query}")
        context_rag, context_rag_non_filtered, image_context = self.rag.forward(search_query, preferred_area, radius, category_tag)
        context_misc = self.misc    
        context = '\n'.join(["<DATA>", context_rag, context_misc, "</DATA>"])
        context_non_filtered = '\n'.join(["<DATA>", context_rag_non_filtered, context_misc, "</DATA>"])
        


        # Layer 0 processing with Haiku
        instruction_layer_0 = self.prompt_generator.get_template_layer_0(search_query)
        prompt_layer_0 = [{"role": "user", "content": [{"type": "text", "text": context},
                                                       {"type": "text", "text": instruction_layer_0}]}
                          ]
        prompt_layer_0_non_filtered = [{"role": "user", "content": [{"type": "text", "text": context_non_filtered},
                                                       {"type": "text", "text": instruction_layer_0}]}
                ]
        
        # Run both API calls concurrently using asyncio.gather
        layer_0_resp, layer_0_resp_non_filtered = await asyncio.gather(
            self.tell_claude(
                model=Config.MODEL['haiku'], 
                max_tokens=Config.MAX_TOKENS, 
                temperature=Config.TEMP,
                system="You're experienced Data analyst working with large scale data. You're an expert in identify corelated and relevant data for downstream analysis tasks",
                messages=prompt_layer_0
            ),
            self.tell_claude(
                model=Config.MODEL['haiku'], 
                max_tokens=Config.MAX_TOKENS, 
                temperature=Config.TEMP,
                system="You're experienced Data analyst working with large scale data. You're an expert in identify corelated and relevant data for downstream analysis tasks",
                messages=prompt_layer_0_non_filtered
            )
        )

        # Get usages and reports from both responses
        layer_0_usage = layer_0_resp.usage
        layer_0_report = layer_0_resp.content[0].text

        layer_0_usage_non_filtered = layer_0_resp_non_filtered.usage
        layer_0_report_non_filtered = layer_0_resp_non_filtered.content[0].text

        print(f"layer_0_usage: {layer_0_usage}")
        print(f"layer_0_usage_non_filtered: {layer_0_usage_non_filtered}")

        print(f"layer_0_report: {layer_0_report}")
        print(f"layer_0_report_non_filtered: {layer_0_report_non_filtered}")

        #remove trailing spaces
        layer_0_report = layer_0_report
        layer_0_report_non_filtered = layer_0_report_non_filtered
        

        #Layer 1 reasoning
        dense_context = ("<DATA>" + "<PREFERENCE_FILTERED>" +layer_0_report + "</PREFERENCE_FILTERED>" + "<PREFERENCE_NON_FILTERED>" + layer_0_report_non_filtered + "</PREFERENCE_NON_FILTERED>" + "<MISC>" + context_misc + "</MISC>" "</DATA>")
        instruction_layer_1 = self.prompt_generator.get_reasoner_instruction()
        prompt_layer_1 = image_context + [{"role": "user", "content": [{"type": "text", "text": dense_context}]}] + chats + [instruction_layer_1]
        layer_1_resp, image_url_list = await self.claude_reason(prompt_layer_1)

        return {"text": layer_1_resp, "image": image_url_list, "tag":final_tag}, {}, {}
          

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
            model=Config.MODEL['sonnet'], 
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

    async def _handle_generic_response(self, chat_resp, chats, last_query, routing_layer_usage):
        """
        Handle generic responses when no tool is selected.
        
        Args:
            chat_resp: Response from the first layer
            chats: Chat history
            last_query: The last user query
            routing_layer_usage: Token usage from routing layer
            
        Returns:
            Response, token usage, and thought dictionary
        """
        generic_prompt = f"""
        Please take a look at this thought, and use them provide response. do not say anything about this thought and keep it as internal thought, provide response based on chat conversation and lanuage style provided.
        <thought>
        {chat_resp.content[0].text}

        we should probe back only important informations. 
        <For booking queue>
        Also, If above chat conversation is not showing any confirmation of booking queue yet then we should not comfirm the booking queue and kindly inform them that we don't have the information yet we have to contact hospital/clinic first
        If above chat conversation is showing confirmation message then inform user if they need help or anything
        </For booking queue>
        </thoght>
        """
        
        system_prompt = """
        <langauge_style>
        -begining of response : do not say "hello" or "thank you for" in the beginning of sentences when previous turn already said it, beginning of response should be answer of the question and straight to the point
        - answer in user's language. 
        - if user speaks in Thai then your name will be "จิ๊บ" and call user as "คุณลูกค้า" and use "ค่ะ"OR"คะ"OR"ค่า" to end the sentences
        - เรียกแทนตัวเองว่า "จิ๊บ" หรือ "เรา" เสมอ 
        - พิมลากตัวอักษรสุดท้ายก่อนจะเปลี่ยนเรื่องคุยหรือทอปปิคเช่น "ค่ะะ" "ค่าา" "คะะ" 
        - do not provide any mobile phone numbers, ONLY ending the response with kind question to continue the conversation flow
        - do not use formal vocabs but instead use casual vocabs but in formal tone instead. tone is what makes conversation polite, vocabs are just medium.
        - use emojis about Summer Month to make it feels warm and comfortable like Pop City vibe 80s japanese summer,  and also use hands+face emojis to convey emotions like human
        </language_style> 

        You will recieve <thought> as a internal monologue.
        """
        
        generic_resp = await self.tell_claude(
            model=Config.MODEL['sonnet'],
            max_tokens=Config.MAX_TOKENS,
            #temperature=Config.TEMP,
            system=system_prompt,
            messages=chats + [{"role": "user", "content": generic_prompt}]
        )

        tag = await self._get_tag(chats)
        
        generic_text = generic_resp.content[0].text
        time_stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        

        
 
        print(tag)
        return {"text": generic_text, "image": [], "tag":tag}, {}, {}
    
# Cart handling removed - only JibAI should handle cart functionality
    
    async def forward(self, chats,room_id):
        """
        Main function to process user input and generate responses.
        
        Args:
            chats: List of chat messages
            
        Returns:
            A tuple containing the response, token usage information, and thought process
            
        """
        last_query = str(chats[-1])  # for CoT log
        
        # Preprocess images if any
        chats = await self._preprocessing(chats)
        logger.info('OCR. . .')
        
        # Initial agent layer to determine how to handle the request
        prompt_layer_0 = chats + [
            {
                "role": "user", 
                "content": """
                
                ALWAYS 
                Think step by step in <thinking> tag then select tools, when provide response, always put your response in <response> tag."""
            }
        ]
         
        logger.info('Jib is thinking...')
        chat_resp = await self.tell_claude(
            model=Config.MODEL['sonnet'],
            max_tokens=Config.MAX_TOKENS,
            temperature=Config.TEMP,
            system=self.system_prompt_interpret,
            messages=prompt_layer_0,
            tools=[
                self.tools.retrieval
            ],
            tool_choice={'type': 'auto'}
        )
        
        router_thought = str(chat_resp)
        routing_layer_usage = chat_resp.usage

        print(f"Thought: {chat_resp.content[0].text}")
        
        if chat_resp.stop_reason == 'tool_use':
            logger.info(f'Tool calling: {chat_resp.content[1].name}')
            thought_block = chat_resp.content[0]
            tool_use_block = chat_resp.content[1]
            
            # Handle different tools
            if chat_resp.content[1].name == 'retrieval':
                return await self._handle_retrieval(chat_resp, chats, last_query, routing_layer_usage, thought_block, tool_use_block, room_id)
            
# Handover tools removed - dr_jib only handles retrieval

# Cart tool removed - only JibAI should handle cart functionality
            
        else:
            # Generic response handling
            xml_resp = self.extract_xml(chat_resp.content[0].text, 'response')
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