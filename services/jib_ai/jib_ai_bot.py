"""
Sonnet 4 Bot - Drop-in Replacement for JibAI
============================================
Advanced Sonnet 4 agent with centralized tool handling, interleaved thinking,
and parallel tool execution capabilities.
"""

import asyncio
import anthropic
import logging
import json
import os
import re
import base64
import httpx
import pytz
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional
from shared.rag import RAG

from .cart import create_cart_curl, add_package_to_cart, delete_package_curl, list_cart_packages_curl, delete_cart_curl, create_order_curl
from anthropic import AsyncAnthropicBedrock
from dotenv import load_dotenv
from .memory_monitor import memory_monitor, memory_check_decorator

# Load environment variables
load_dotenv()

# Configure Azure-optimized logging
from .azure_logging_config import setup_azure_logging, get_logger, log_business_hours_status, log_tool_execution

# Initialize Azure logging (will be called once during app startup)
# This is set up in __init__.py or api_routes.py
logger = get_logger(__name__)

# Configuration constants (matching extended_thinking_test/sonnet4_agent.py)
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

class CentralizedTools:
    """Centralized tool definitions and execution for JibAI Sonnet 4 agent"""
    
    def __init__(self, rag: RAG):
        """Initialize with RAG instance"""
        self.rag = rag
        logger.info("🔧 [TOOLS-INIT] Centralized tools system initialized")
    
    def get_tool_definitions(self) -> List[Dict]:
        """Get available tool definitions based on Thailand business hours"""
        import pytz
        from datetime import datetime
        
        # Get Thailand time
        thailand_tz = pytz.timezone('Asia/Bangkok')
        current_time = datetime.now(thailand_tz)
        current_hour = current_time.hour
        
        # Base tools always available
        tools = [
            self._get_retrieval_tool(),
            self._get_cart_tool(),
            self._get_sql_search_tool(),
            self._get_package_images_tool(),
        ]
        
        # Business hours: 9:00 AM - 1:00 AM (next day)
        # After hours: 1:00 AM - 9:00 AM (no human agents)
        is_business_hours = current_hour >= 9 or current_hour < 1
        
        if is_business_hours:
            # Add handover tools during business hours
            tools.extend([
                self._get_handover_cx_tool(),
                self._get_handover_bk_tool(),
                self._get_handover_asap_tool(),  # Emergency handover for sensitive packages
            ])
            log_business_hours_status(logger, current_hour, True)
            logger.info(f"🔧 [TOOLS-AVAILABLE] {len(tools)} tools loaded: {[t['name'] for t in tools]}")
        else:
            # After hours - no handover tools
            log_business_hours_status(logger, current_hour, False)
            logger.info(f"🔧 [TOOLS-AVAILABLE] {len(tools)} tools loaded: {[t['name'] for t in tools]}")
            logger.info(f"🤖 [AFTER-HOURS] JibAI will handle all inquiries until 9:00 AM")
        
        return tools
    
    def _get_retrieval_tool(self) -> Dict:
        """Retrieval tool for searching healthcare packages"""
        return {
            "name": "retrieval",
            "description": "Search for healthcare packages and services in the HDmall database. Use for finding packages, getting detailed package information, and package metadata.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "search_keyword": {
                        "type": "string",
                        "description": "Search keyword for packages (e.g., 'HPV vaccine', 'health checkup', 'dental')"
                    },
                    "preferred_area": {
                        "type": "string", 
                        "description": "Preferred location/area (e.g., 'Bangkok', 'Chiang Mai') or leave empty for all areas"
                    },
                    "radius": {
                        "type": "integer",
                        "description": "Search radius in kilometers from preferred_area (default: 10). Use higher values for broader search."
                    },
                    "package_url": {
                        "type": "string",
                        "description": "Specific package URL for detailed information (when using PROVIDE_PACKAGE_INFO mode)"
                    },
                    "category_tag": {
                        "type": "string",
                        "description": """Package category to filter results. Select from the following specific categories based on user query:
                        
                        Available categories:
                        - ตรวจกระดูก
                        - กายภาพบำบัดออฟฟิศซินโดรม (Physical Therapy Office Syndrome)
                        - ฟอกสีฟัน (Teeth Whitening)
                        - ตรวจตับ (Liver Function Test)
                        - ตรวจภูมิแพ้และภาวะแพ้ (Allergy Test)
                        - จี้ไฝ กระ และรอยปาน
                        - กำจัดขนรักแร้ (Armpit Hair Removal)
                        - ตรวจ รักษาไทรอยด์
                        - อุดฟัน (Dental Filling)
                        - รักษารอยแตกลาย รอยคล้ำ (Stretch Marks Treatment)
                        - ตรวจภูมิแพ้อาหารแฝง (Food Intolerance Test)
                        - ตรวจการนอน (Sleep Test)
                        - ทำรีเทนเนอร์แบบลวด (Hawley Retainer)
                        - ฉีดวัคซีนไข้หวัดใหญ่ (Influenza Vaccine)
                        - Pico Laser
                        - โปรแกรมตรวจสุขภาพ (Health Checkup)
                        - ทำรีเทนเนอร์ใส (Clear Retainer)
                        - ตรวจก่อนแต่งงาน (Pre-Marriage Checkup)
                        - ตรวจระดับฮอร์โมน (Hormone Test)
                        - ทำ Morpheus 8
                        - ทำอัลเทอร์รา (Ulthera)
                        - รักษาหลุมสิว ลดรอยสิว
                        - ฉีดวัคซีน HPV (HPV Vaccine)
                        - ตรวจโรคติดต่อทางเพศสัมพันธ์ (STD)
                        - รักษาแผลเป็นคีลอยด์ (keloid treatment)
                        - ตรวจมะเร็งสำหรับผู้หญิง
                        - ถอนหรือผ่าฟันคุด
                        - ลดเหงื่อ ลดกลิ่นตัว
                        - รักษาสิว (Acne Treatment)
                        
                        Use '<UNKNOWN>' if no specific category matches the query."""
                    },
                    "mode": {
                        "type": "string",
                        "description": "Search mode: 'GET_PACKAGE_METADATA' for finding packages, 'PROVIDE_PACKAGE_INFO' for detailed package info",
                        "enum": ["GET_PACKAGE_METADATA", "PROVIDE_PACKAGE_INFO"]
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Your reasoning for this search and what you expect to find"
                    }
                },
                "required": ["search_keyword", "category_tag", "mode", "reasoning"]
            }
        }
    
    def _get_cart_tool(self) -> Dict:
        """Cart management tool with real implementation"""
        return {
            "name": "cart",
            "description": """
            <instruction>
            This is a cart function with 6 available actions:
            1. create_cart : create a new shopping cart
            2. delete_cart : delete a shopping cart
            3. add_item_to_cart : add an item to the shopping cart
            4. delete_item_from_cart : delete an item from the shopping cart
            5. view_cart : view the items in the shopping cart
            6. create_order : create an order from the shopping cart for payment url

            where each action has different parameters.
            1. create_cart has no parameters.
            2. delete_cart has 1 parameter :
            - cart_id
            3. add_item_to_cart has 2 parameters:
            - package_url
            - cart_id
            4. delete_item_from_cart has 2 parameters:
            - package_url
            - cart_id
            5. view_cart has 1 parameter:
            - cart_id
            6. create_order has 1 parameter:
            - cart_id
            </instruction>
            """,
            "input_schema": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": """The action to perform. please select only from the following actions:
                        - "create_cart"
                        - "delete_cart"
                        - "add_item_to_cart"
                        - "delete_item_from_cart"
                        - "view_cart"
                        - "create_order"
                        """
                    },
                    "cart_id": {
                        "type": "string",
                        "description": "The id of the cart to perform the action on. if the action you selected doesn't require a cart id, please leave this as <NULL>."
                    },
                    "package_url": {
                        "type": "string",
                        "description": "The url of the package to perform the action on. if the action you selected doesn't require a package url, please leave this as <NULL>."
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Your reasoning for this cart operation"
                    }
                },
                "required": ["action", "cart_id", "package_url", "reasoning"]
            }
        }
    
    def _get_sql_search_tool(self) -> Dict:
        """SQL search tool for advanced filtering"""
        return {
            "name": "sql_search",
            "description": "Advanced search using pandas queries for filtering, sorting, and finding specific packages with price/location/category criteria.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "sql_query": {
                        "type": "string",
                        "description": "Pandas query string (e.g., \"kb[kb['Cash Price'] < 5000].head(10)\")"
                    },
                    "category_tag": {
                        "type": "string",
                        "description": """Category filter to apply before running the SQL query. Select from the following specific categories:
                        
                        Available categories:
                        - ตรวจกระดูก
                        - กายภาพบำบัดออฟฟิศซินโดรม (Physical Therapy Office Syndrome)
                        - ฟอกสีฟัน (Teeth Whitening)
                        - ตรวจตับ (Liver Function Test)
                        - ตรวจภูมิแพ้และภาวะแพ้ (Allergy Test)
                        - จี้ไฝ กระ และรอยปาน
                        - กำจัดขนรักแร้ (Armpit Hair Removal)
                        - ตรวจ รักษาไทรอยด์
                        - อุดฟัน (Dental Filling)
                        - รักษารอยแตกลาย รอยคล้ำ (Stretch Marks Treatment)
                        - ตรวจภูมิแพ้อาหารแฝง (Food Intolerance Test)
                        - ตรวจการนอน (Sleep Test)
                        - ทำรีเทนเนอร์แบบลวด (Hawley Retainer)
                        - ฉีดวัคซีนไข้หวัดใหญ่ (Influenza Vaccine)
                        - Pico Laser
                        - โปรแกรมตรวจสุขภาพ (Health Checkup)
                        - ทำรีเทนเนอร์ใส (Clear Retainer)
                        - ตรวจก่อนแต่งงาน (Pre-Marriage Checkup)
                        - ตรวจระดับฮอร์โมน (Hormone Test)
                        - ทำ Morpheus 8
                        - ทำอัลเทอร์รา (Ulthera)
                        - รักษาหลุมสิว ลดรอยสิว
                        - ฉีดวัคซีน HPV (HPV Vaccine)
                        - ตรวจโรคติดต่อทางเพศสัมพันธ์ (STD)
                        - รักษาแผลเป็นคีลอยด์ (keloid treatment)
                        - ตรวจมะเร็งสำหรับผู้หญิง
                        - ถอนหรือผ่าฟันคุด
                        - ลดเหงื่อ ลดกลิ่นตัว
                        - รักษาสิว (Acne Treatment)
                        
                        Use '<UNKNOWN>' to search all categories."""
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Your reasoning for this search query and expected results"
                    }
                },
                "required": ["sql_query", "category_tag", "reasoning"]
            }
        }
    
    def _get_handover_cx_tool(self) -> Dict:
        """Customer service handover tool"""
        return {
            "name": "handover_to_cx",
            "description": """
    ALWAYS call this function when the <LIST_OF_INFORMATIONS_YOU_WILL_GET> in 'retrieval' tool doesn't seem to be able to answer user's query. OR ALWAYS call this function when last couple turns of 'assistant' role seems to not be able to handle user query with good UX.
    <instruction>This function is used to seamlessly transfer the current conversation to a live
                customer support agent/human/someone when the user's message indicates the following :
                    1. If the user wants to talk to a salesperson or human agent specifically
                    2. If the user wants something that you cannot provide, call the 'handover_to_cx' function like "อยากคุยกับหมอได้มั้ยคะ" since you're not doctor
                    3. If you cannot handle their technical issues or complex queries
                Caution : There is a nuance when the user says "I want..."/"Im looking for..". 
                If they are simply curious and say something like "I want/looking for a health checkup/treatment", 
                DO NOT call this as its still too general and you can still gather more information.
                For purchase intent: Use 'cart' tool to help them buy packages, NOT this handover function.
                </instruction>
                """,
            "input_schema": {
                "type": "object",
                "properties": {
                    "package_name": {
                        "type": "string",
                        "description": "answer this part with just the package_name that user wants to buy, no need other response just the full name of package as you see on RETRIEVED_PACKAGE or chat history of users"
                    },
                    "package_category": {
                        "type": "string",
                        "description": ""
                    },
                    "package_location": {
                        "type": "string",
                        "description": "answer this part with just the package_location that user wants to buy, no need other response just the full name of package location/places as you see on RETRIEVED_PACKAGE or chat history of users"
                    },
                    "price_and_budget": {
                        "type": "string",
                        "description": "answer this part with just the prices or budget that user/assitant were discussed OR agreed during the chat history or the one from RETRIEVED_PACKAGE for example : 1890.0 Baht"
                    }
                },
                "required": ["package_name", "package_category", "package_location", "price_and_budget"]
            }
        }
    
    def _get_handover_bk_tool(self) -> Dict:
        """Booking specialist handover tool"""
        return {
            "name": "handover_to_bk",
            "description": """
    <information_needed_to_call_this_tool>
    1.full name and last name
    2.prefer booking date
    3.mobile phone
    </information_needed_to_call_this_tool>
    1.This function will handover to booking agent who can take care of scheduling and also re-scheduling. when user ask for booking/schedule/reschedule, ALWAYS kindly ask them back the first and last name,date they prefer, and mobile phone number first before calling this function. 
    2.when all 3 of informations needed to call this tool are present then call this tool.
    
    <SPECIAL_CASE_HDEXPRESS>
    For HDExpress cases (when user mentions "hdexpress", "hd express", "เอชดีเอ็กซ์เพreส" or similar), you can call this tool even if you only have the full name. For missing information, use the default value "<UNKNOWN>".
    </SPECIAL_CASE_HDEXPRESS>
                """,
            "input_schema": {
                "type": "object",
                "properties": {
                    "full_name_last_name": {
                        "type": "string",
                        "description": "Full name and last name that provided by user."
                    },
                    "booking_date": {
                        "type": "string",
                        "description": "booking date or rescehdule date provided by user. For HDExpress cases where this information is not available, use \"<UNKNOWN>\"."
                    },
                    "mobile_phone": {
                        "type": "string",
                        "description": "mobile phone number provided by either user themselves or mobile app template message. For HDExpress cases where this information is not available, use \"<UNKNOWN>\"."
                    }
                },
                "required": ["full_name_last_name", "booking_date", "mobile_phone"]
            }
        }
    
    def _get_handover_asap_tool(self) -> Dict:
        """Emergency handover tool"""
        return {
            "name": "handover_asap",
            "description": """
    <Instruction>We will give you set of topics/subjects that are very sensitive and we want you to call this function right away when user starts to ask about that
    topic or subject</Instruction>
                 <set_of_topics/subjects>
                    <subject_1>Lasik for eyes</subject_1>
                    <subject_2>ReLEx for eyes</subject_2>
                    <subject_3>HPV vaccines</subject_3>
                    <subject_4>Food Intolerance / Hidden Food allergy Testing</subject_4>
                    <subject_6>Veneer for teeth</subject_6>
                    <subject_7>General Health Checkup / ตรวจสุขภาพ</subject_7>
                </set_of_topics/subjects>
    
    * Only call this functions when user query falls into these specific packages, DO NOT call this functions when user query is about similar packages like for example clear retainer might be similar to veneer but they're aren't exactly the same so don't call this. *
    - Do not make any guess, if user is unclear about what they want, just say you don't know and ask them to be more specific.
    
                """,
            "input_schema": {
                "type": "object",
                "properties": {
                    "package_name": {
                        "type": "string",
                        "description": """
                            One of the package names that triggered this function. 
                            if the package name is/about either Lasik/ReLEx, return "Lasik"
                            if the package name is/about HPV vaccines, return "HPV Vaccine"
                            if the package name is/about Food Intolerance, return "Food Intolerance"
                            if the package name is/about Veneer, return "Veneer"
                            if the package name is/about Health Checkup, return "Health Checkup"
                """
                    }
                },
                "required": ["package_name"],
                "cache_control": {"type": "ephemeral"}
            }
        }
    
    def _get_package_images_tool(self) -> Dict:
        """Package images tool for fetching and analyzing infographics"""
        return {
            "name": "get_package_images",
            "description": "Fetch visual infographics for healthcare packages. Use this tool AFTER retrieval when you want to provide users with helpful visual content like package overviews, location maps, or detailed infographics that enhance understanding of the packages. ONLY use this tool in conversation states 1 or 2 (asking for packages or package details).",
            "input_schema": {
                "type": "object",
                "properties": {
                    "package_url": {
                        "type": "string",
                        "description": "The specific package URL to fetch images for (obtained from retrieval tool results)"
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Why you think visual content would be helpful for this user query (e.g., 'User asked about locations', 'User wants package overview', 'Visual aid would clarify options')"
                    }
                },
                "required": ["package_url", "reasoning"]
            }
        }
    
    async def execute_tool(self, tool_name: str, tool_input: Dict, room_id: str = None) -> str:
        """Execute a tool and return the result with streamlined logging"""
        try:
            logger.info(f"🔧 [TOOL-EXECUTE] Starting execution of '{tool_name}'")
            
            if tool_name == "retrieval":
                result = await self._execute_retrieval(tool_input)
            elif tool_name == "cart":
                # Cart operations need room_id for API calls
                if not room_id:
                    result = "❌ Room ID is required for cart operations"
                else:
                    result = await self._execute_cart(tool_input, room_id)
            elif tool_name == "sql_search":
                result = await self._execute_sql_search(tool_input)
            elif tool_name == "get_package_images":
                result = await self._execute_package_images(tool_input)
            elif tool_name == "handover_to_cx":
                result = await self._execute_handover_cx(tool_input)
            elif tool_name == "handover_to_bk":
                result = await self._execute_handover_bk(tool_input)
            elif tool_name == "handover_asap":
                result = await self._execute_handover_asap(tool_input)
            else:
                result = f"❌ Unknown tool: {tool_name}"
                logger.error(f"🔧 [TOOL-ERROR] Unknown tool: {tool_name}")
            
            logger.info(f"✅ [TOOL-SUCCESS] '{tool_name}' completed successfully")
            
            return result
            
        except Exception as e:
            error_msg = f"❌ Error executing {tool_name}: {str(e)}"
            logger.error(f"🔧 [TOOL-ERROR] {error_msg}")
            if tool_name == "handover_to_bk":
                return "QISCUS_INTEGRATION_TO_BK"
            else:
                return "QISCUS_INTEGRATION_TO_CX"
    
    async def _execute_retrieval(self, tool_input: Dict) -> str:
        """Execute retrieval tool"""
        search_keyword = tool_input["search_keyword"]
        preferred_area = tool_input.get("preferred_area", "")
        package_url = tool_input.get("package_url", "")
        mode = tool_input["mode"]
        reasoning = tool_input["reasoning"]
        
        # Handle radius parameter - convert from string/None to int
        radius_input = tool_input.get("radius", 10)
        try:
            if radius_input is None or radius_input == "<UNKNOWN>" or radius_input == "":
                radius = 10  # Default radius
            else:
                radius = int(radius_input)
        except (ValueError, TypeError):
            radius = 10  # Fallback to default
        
        logger.info(f"🔍 [RETRIEVAL] Mode: {mode}, Keyword: '{search_keyword}', Area: '{preferred_area}', Radius: {radius}")
        
        # Check if RAG is available
        if not self.rag:
            return f"❌ RAG system not available. Mock result for '{search_keyword}' in {preferred_area if preferred_area else 'all areas'}.\nReasoning: {reasoning}"
        
        try:
            if mode == "GET_PACKAGE_METADATA":
                # Get category tag from LLM (now required parameter)
                category_tag = tool_input.get("category_tag", "<UNKNOWN>")
                if category_tag == "<UNKNOWN>":
                    logger.info(f"🏷️  [CATEGORY-NONE] Sonnet selected '<UNKNOWN>' - no specific category filtering")
                else:
                    logger.info(f"🏷️  [CATEGORY-PROVIDED] Sonnet selected category: '{category_tag}'")
                
                result = self.rag._get_package_url(
                    query=search_keyword,
                    preferred_area=preferred_area,
                    radius=radius,
                    category_tag=category_tag
                )
            elif mode == "PROVIDE_PACKAGE_INFO" and package_url:
                result = self.rag.get_package_info_from_url(package_url)
            else:
                result = "❌ Invalid retrieval mode or missing package_url for PROVIDE_PACKAGE_INFO"
        except Exception as e:
            result = f"❌ Error in retrieval: {str(e)}"
            logger.error(f"🔍 [RETRIEVAL-ERROR] {result}")
        
        return f"Retrieval Results ({mode}):\n{result}\nReasoning: {reasoning}"
    
    async def _execute_cart(self, tool_input: Dict, room_id: str) -> str:
        """Execute cart operations using real cart API functions"""
        action = tool_input["action"]
        cart_id = tool_input.get("cart_id", "")
        package_url = tool_input.get("package_url", "")
        reasoning = tool_input["reasoning"]
        
        logger.info(f"🛒 [CART] Action: {action}, Cart ID: {cart_id}, Room ID: {room_id}")
        
        try:
            if action == "create_cart":
                cart_response = create_cart_curl(room_id)
                
            elif action == "delete_cart":
                if cart_id == "<NULL>" or not cart_id:
                    return f"❌ Cart ID is required for delete_cart action\nReasoning: {reasoning}"
                cart_response = delete_cart_curl(cart_id, room_id)
                
            elif action == "add_item_to_cart":
                if cart_id == "<NULL>" or not cart_id or package_url == "<NULL>" or not package_url:
                    return f"❌ Both cart_id and package_url are required for add_item_to_cart action\nReasoning: {reasoning}"
                cart_response = add_package_to_cart(cart_id, package_url, room_id)
                
            elif action == "delete_item_from_cart":
                if cart_id == "<NULL>" or not cart_id or package_url == "<NULL>" or not package_url:
                    return f"❌ Both cart_id and package_url are required for delete_item_from_cart action\nReasoning: {reasoning}"
                cart_response = delete_package_curl(package_url, room_id, cart_id)
                
            elif action == "view_cart":
                if cart_id == "<NULL>" or not cart_id:
                    return f"❌ Cart ID is required for view_cart action\nReasoning: {reasoning}"
                cart_response = list_cart_packages_curl(cart_id, room_id)
                
            elif action == "create_order":
                if cart_id == "<NULL>" or not cart_id:
                    return f"❌ Cart ID is required for create_order action\nReasoning: {reasoning}"
                cart_response = create_order_curl(cart_id, room_id)
                
            else:
                return f"❌ Invalid cart action: {action}\nReasoning: {reasoning}"
            
            # Format the response
            if cart_response:
                return f"Cart Operation ({action}):\n{json.dumps(cart_response, indent=2, ensure_ascii=False)}\nReasoning: {reasoning}"
            else:
                return f"❌ Cart operation failed - no response received\nReasoning: {reasoning}"
                
        except Exception as e:
            error_msg = f"❌ Error executing cart action '{action}': {str(e)}"
            logger.error(f"🛒 [CART-ERROR] {error_msg}")
            return f"{error_msg}\nReasoning: {reasoning}"
    
    async def _execute_sql_search(self, tool_input: Dict) -> str:
        """Execute SQL search"""
        sql_query = tool_input["sql_query"]
        category_tag = tool_input.get("category_tag", "<UNKNOWN>")
        reasoning = tool_input["reasoning"]
        
        if category_tag == "<UNKNOWN>":
            logger.info(f"📊 [SQL-SEARCH] Query: {sql_query[:100]}..., No category filter")
            logger.info(f"🏷️  [CATEGORY-SQL] Sonnet selected '<UNKNOWN>' - searching all categories")
        else:
            logger.info(f"📊 [SQL-SEARCH] Query: {sql_query[:100]}..., Category: '{category_tag}'")
            logger.info(f"🏷️  [CATEGORY-SQL] Sonnet selected category: '{category_tag}' for SQL filtering")
        
        # Check if RAG is available
        if not self.rag:
            return f"❌ RAG system not available. Mock SQL search for query: {sql_query[:50]}...\nReasoning: {reasoning}"
        
        try:
            result = self.rag.sql_search(query=sql_query, category_tag=category_tag)
        except Exception as e:
            result = f"❌ Error in SQL search: {str(e)}"
            logger.error(f"📊 [SQL-ERROR] {result}")
            
        return f"SQL Search Results:\n{result}\nReasoning: {reasoning}"
    
    async def _execute_handover_cx(self, tool_input: Dict) -> str:
        """Execute customer service handover"""
        package_name = tool_input["package_name"]
        package_category = tool_input["package_category"]
        package_location = tool_input["package_location"]
        price_and_budget = tool_input["price_and_budget"]
        
        logger.info(f"👥 [HANDOVER-CX] Package: {package_name}, Location: {package_location}, Price: {price_and_budget}")
        
        return "QISCUS_INTEGRATION_TO_CX"
    
    async def _execute_handover_bk(self, tool_input: Dict) -> str:
        """Execute booking specialist handover"""
        full_name_last_name = tool_input["full_name_last_name"]
        booking_date = tool_input["booking_date"]
        mobile_phone = tool_input["mobile_phone"]
        
        logger.info(f"📅 [HANDOVER-BK] Customer: {full_name_last_name}, Date: {booking_date}, Phone: {mobile_phone}")
        return "QISCUS_INTEGRATION_TO_BK"

    
    async def _execute_handover_asap(self, tool_input: Dict) -> str:
        """Execute emergency handover"""
        package_name = tool_input["package_name"]
        
        logger.info(f"🚨 [HANDOVER-ASAP] Sensitive Package: {package_name}")
        
        return f"QISCUS_INTEGRATION_TO_IMMEDIATE_CX: {package_name}"
    
    async def _execute_package_images(self, tool_input: Dict) -> str:
        """Execute package images fetching with base64 and URL data"""
        package_url = tool_input["package_url"]
        reasoning = tool_input["reasoning"]
        
        logger.info(f"🖼️ [PACKAGE-IMAGES] Fetching images for: {package_url}")
        
        try:
            # Import the functions from airtable_fetching
            from .airtable_fetching import fetch_and_decode, _url_to_base64_content
            
            # Get the Airtable record
            decoded_result = fetch_and_decode(package_url)
            
            if 'records' not in decoded_result or not decoded_result['records']:
                return "No images found for this package."
            
            record = decoded_result['records'][0]
            images_data = []
            
            # Look for Campaign Name artwork only
            campaign_artwork_field = 'Artwork (from Campaign Name)_urls'
            if campaign_artwork_field in record['fields']:
                campaign_images = record['fields'][campaign_artwork_field]
                if isinstance(campaign_images, list) and campaign_images:
                    for img_url in campaign_images:
                        try:
                            # Convert URL to base64
                            base64_content = await _url_to_base64_content(img_url)
                            if base64_content:
                                base64_string = f"data:{base64_content['source']['media_type']};base64,{base64_content['source']['data']}"
                                images_data.append({
                                    "image_url": img_url,
                                    "base64_data": base64_string
                                })
                        except Exception as e:
                            logger.warning(f"⚠️ [PACKAGE-IMAGES] Failed to process image {img_url}: {e}")
                            continue
            
            if not images_data:
                return "No Campaign Name artwork images found for this package."
            
            logger.info(f"✅ [PACKAGE-IMAGES] Successfully fetched {len(images_data)} image(s)")
            
            # Return content blocks format: text block + image blocks
            # This allows Claude to analyze images and bot to extract URLs for response
            content_blocks = [
                {
                    "type": "text",
                    "text": f"Found {len(images_data)} Campaign Name artwork images for analysis. Image URLs: {', '.join([img['image_url'] for img in images_data])}"
                }
            ]
            
            # Add each image as a separate image block for Claude's vision analysis
            valid_images_count = 0
            total_images_count = len(images_data)
            
            for img_data in images_data:
                try:
                    # Parse the data URL to extract media type and base64 data
                    base64_parts = img_data["base64_data"].split(",")
                    if len(base64_parts) == 2:
                        header = base64_parts[0]  # "data:image/jpeg;base64"
                        data = base64_parts[1]    # actual base64 string
                        
                        # Extract media type from header
                        media_type = header.split(";")[0].split(":")[1] if ":" in header else "image/jpeg"
                        
                        # Validate image size before adding to content blocks
                        try:
                            import base64
                            decoded_data = base64.b64decode(data, validate=True)
                            size_bytes = len(decoded_data)
                            size_mb = size_bytes / (1024 * 1024)
                            
                            if size_bytes > 5 * 1024 * 1024:  # 5MB limit
                                logger.warning(f"❌ [IMAGE-SIZE] Skipping oversized image: {size_mb:.2f}MB (limit: 5MB) from {img_data['image_url']}")
                                continue  # Skip this image
                            else:
                                logger.info(f"✅ [IMAGE-SIZE] Image size validation passed: {size_mb:.2f}MB")
                        except Exception as size_error:
                            logger.warning(f"⚠️ [IMAGE-SIZE] Failed to validate image size: {size_error}, skipping image")
                            continue  # Skip this image if size validation fails
                        
                        content_blocks.append({
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": data
                            }
                        })
                        valid_images_count += 1
                except Exception as e:
                    logger.warning(f"⚠️ [IMAGE-BLOCK] Failed to format image block: {e}")
                    continue
            
            # Log summary of image processing
            logger.info(f"🖼️ [IMAGE-SUMMARY] Included {valid_images_count}/{total_images_count} images after size validation")
            
            # Return as JSON string that will be parsed by the tool result handler
            import json
            return json.dumps(content_blocks, ensure_ascii=False)
            
        except Exception as e:
            error_msg = f"❌ Error fetching package images: {str(e)}"
            logger.error(f"🖼️ [PACKAGE-IMAGES-ERROR] {error_msg}")
            return error_msg


class JibAI:
    """
    Sonnet 4 version of JibAI with interleaved thinking
    Drop-in replacement for the existing JibAI class
    """
    
    def __init__(self, global_storage, device):
        """Initialize with global storage like the original JibAI"""
        self.global_storage = global_storage
        self.device = device
        # Fix missing attributes in global_storage FIRST
        self._fix_global_storage_attributes(global_storage)
        
        # Use AWS Bedrock client for Sonnet 4 (async)
        self.client = AsyncAnthropicBedrock(
            aws_access_key=Config.AWS_ACCESS_KEY,
            aws_secret_key=Config.AWS_SECRET_KEY,
            aws_region=Config.REGION
        )
        
        # Initialize RAG with the fixed global_storage
        try:
            self.rag = RAG(global_storage)
            logger.info("✅ RAG initialized successfully")
        except Exception as e:
            logger.warning(f"RAG initialization issue: {e}. Using fallback mode.")
            self.rag = None
            
        # Initialize centralized tools system
        self.centralized_tools = CentralizedTools(self.rag)
        
        # System prompts for Thai context - Load from the new file
        self.system_prompt = self._load_system_prompt(device)
        
        logger.info("🚀 Sonnet 4 JibAI initialized with centralized tools and interleaved thinking")
    
    def _fix_global_storage_attributes(self, global_storage):
        """Fix missing attributes in global_storage that RAG might need"""
        missing_attrs = [
            'web_recommendation_json', 'hl_embed', 'brand_embed', 'cat_embed', 'tag_embed',
            'hl_docs', 'brand_docs', 'cat_docs', 'tag_docs'
        ]
        
        for attr in missing_attrs:
            if not hasattr(global_storage, attr):
                setattr(global_storage, attr, None)
                logger.info(f"Added missing attribute: {attr}")
    
    def _load_system_prompt(self, device='social'):
        """Load system prompt from the interpret.txt file"""
        if device == 'social':
            prompt_file = 'services/jib_ai/prompts/interpret.txt'
        elif device == 'app':
            prompt_file = 'services/jib_ai/prompts/interpret_app.txt'
        else:
            prompt_file = 'services/jib_ai/prompts/interpret.txt'
            
        try:
            with open(prompt_file, 'r', encoding='utf-8') as f:
                prompt_template = f.read()
            
            # The interpret.txt template uses placeholders that will be replaced at runtime
            return prompt_template
            
        except Exception as e:
            logger.warning(f"Failed to load interpret.txt system prompt: {e}. Using fallback.")
            return self._create_fallback_system_prompt()
    
    def _create_fallback_system_prompt(self):
        """Fallback system prompt if file loading fails"""
        return """คุณคือ JibAI ผู้ช่วยอัจฉริยะด้านสุขภาพของ HDmall ที่มีความสามารถในการคิดวิเคราะห์แบบขั้นสูง

บทบาทหลัก:
1. 🏥 **ผู้เชี่ยวชาญด้านสุขภาพ**: ให้คำแนะนำเกี่ยวกับแพ็กเกจสุขภาพ วัคซีน การตรวจสุขภาพ และบริการทางการแพทย์
2. 🔍 **ผู้ช่วยค้นหา**: ช่วยหาแพ็กเกจสุขภาพที่เหมาะสมตามความต้องการและงบประมาณของลูกค้า
3. 💰 **ที่ปรึกษาการเงิน**: แนะนำตัวเลือกที่คุ้มค่าและเหมาะสมกับงบประมาณ
4. 🎯 **ผู้ให้บริการส่วนบุคคล**: ปรับคำแนะนำให้เหมาะกับแต่ละบุคคล

หลักการสำคัญ:
- ใช้ภาษาไทยที่เป็นกันเองและเข้าใจง่าย
- ให้ข้อมูลที่ถูกต้องและทันสมัย
- แนะนำแพ็กเกจที่เหมาะสมที่สุดตามความต้องการ
- เน้นความปลอดภัยและประสิทธิภาพของการรักษา
- ใช้ข้อมูลจาก HDmall database ในการแนะนำ

วัน/เวลาปัจจุบัน: {current_time}
"""

    async def _validate_image(self, image_content: Dict) -> Tuple[bool, str]:
        """
        Validate image content before sending to Claude
        Returns: (is_valid, reason)
        """
        try:
            # Check basic structure
            if not isinstance(image_content, dict):
                return False, "Image content is not a dictionary"
            
            if image_content.get('type') != 'image':
                return False, "Content type is not 'image'"
            
            source = image_content.get('source')
            if not source:
                return False, "Missing 'source' field"
            
            source_type = source.get('type')
            
            if source_type == 'url':
                return await self._validate_image_url(source)
            elif source_type == 'base64':
                return self._validate_base64_image(source)
            else:
                return False, f"Unknown source type: {source_type}"
                
        except Exception as e:
            return False, f"Validation error: {str(e)}"
    
    async def _validate_image_url(self, source: Dict) -> Tuple[bool, str]:
        """Validate image URL accessibility, format, and size"""
        url = source.get('url')
        if not url:
            return False, "Missing URL"
        
        # Basic URL format check
        if not url.startswith(('http://', 'https://')):
            return False, "Invalid URL format"
        
        try:
            # Quick HEAD request to check if URL is accessible
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.head(url)
                
                if response.status_code >= 400:
                    return False, f"URL returned {response.status_code}"
                
                # Check content type
                content_type = response.headers.get('content-type', '').lower()
                valid_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp']
                
                if content_type and not any(vtype in content_type for vtype in valid_types):
                    logger.warning(f"⚠️ [IMAGE-VALIDATION] URL content-type: {content_type}")
                    # Don't fail here - some servers don't return correct content-type in HEAD
                
                # Check content-length if available
                content_length = response.headers.get('content-length')
                if content_length:
                    try:
                        size_bytes = int(content_length)
                        size_mb = size_bytes / (1024 * 1024)
                        if size_bytes > 5 * 1024 * 1024:  # 5MB limit
                            return False, f"Image too large: {size_mb:.2f}MB (limit: 5MB)"
                        logger.info(f"✅ [IMAGE-VALIDATION] URL size check: {size_mb:.2f}MB")
                    except ValueError:
                        logger.warning(f"⚠️ [IMAGE-VALIDATION] Invalid content-length: {content_length}")
                
                return True, "Valid URL"
                
        except httpx.TimeoutException:
            return False, "URL timeout"
        except Exception as e:
            return False, f"URL validation error: {str(e)}"
    
    def _validate_base64_image(self, source: Dict) -> Tuple[bool, str]:
        """Validate base64 image data and format"""
        data = source.get('data')
        media_type = source.get('media_type')
        
        if not data:
            return False, "Missing base64 data"
        
        if not media_type:
            return False, "Missing media_type"
        
        # Check supported media types
        valid_media_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp']
        if media_type not in valid_media_types:
            return False, f"Unsupported media_type: {media_type}"
        
        try:
            # Validate base64 format
            decoded = base64.b64decode(data, validate=True)
            
            # Check basic size limits (Claude has limits around 5MB per image)
            if len(decoded) > 5 * 1024 * 1024:  # 5MB
                return False, "Image too large (>5MB)"
            
            # Basic image header validation
            image_headers = {
                'image/jpeg': [b'\xff\xd8\xff'],
                'image/jpg': [b'\xff\xd8\xff'],
                'image/png': [b'\x89PNG\r\n\x1a\n'],
                'image/gif': [b'GIF87a', b'GIF89a'],
                'image/webp': [b'RIFF']
            }
            
            expected_headers = image_headers.get(media_type, [])
            if expected_headers:
                if not any(decoded.startswith(header) for header in expected_headers):
                    return False, f"Invalid {media_type} format"
            
            return True, "Valid base64 image"
            
        except Exception as e:
            return False, f"Base64 validation error: {str(e)}"
    
    async def _url_to_base64(self, url: str) -> Tuple[bool, str, str]:
        """
        Convert image URL to base64 for Bedrock compatibility with size validation
        Returns: (success, base64_data, media_type)
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # First, do a HEAD request to check content-length
                try:
                    head_response = await client.head(url)
                    content_length = head_response.headers.get('content-length')
                    if content_length:
                        size_bytes = int(content_length)
                        size_mb = size_bytes / (1024 * 1024)
                        if size_bytes > 5 * 1024 * 1024:  # 5MB limit
                            logger.warning(f"❌ [IMAGE-SIZE] Image too large: {size_mb:.2f}MB (limit: 5MB)")
                            return False, "", ""
                        logger.info(f"✅ [IMAGE-SIZE] Image size check passed: {size_mb:.2f}MB")
                except Exception as e:
                    # If HEAD request fails, continue with GET but add streaming validation
                    logger.info(f"⚠️ [IMAGE-SIZE] HEAD request failed, will validate during download: {e}")
                
                # Download the image
                response = await client.get(url)
                
                if response.status_code >= 400:
                    return False, "", ""
                
                # Get content type
                content_type = response.headers.get('content-type', 'image/jpeg').lower()
                
                # Validate content type
                valid_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp']
                if not any(vtype in content_type for vtype in valid_types):
                    logger.warning(f"❌ [IMAGE-TYPE] Invalid content type: {content_type}")
                    return False, "", ""
                
                # Check actual downloaded size
                image_data = response.content
                size_bytes = len(image_data)
                size_mb = size_bytes / (1024 * 1024)
                
                if size_bytes > 5 * 1024 * 1024:  # 5MB limit
                    logger.warning(f"❌ [IMAGE-SIZE] Downloaded image too large: {size_mb:.2f}MB (limit: 5MB)")
                    return False, "", ""
                
                # Convert to base64
                base64_data = base64.b64encode(image_data).decode('utf-8')
                
                logger.info(f"✅ [URL-TO-BASE64] Converted image: {size_mb:.2f}MB, {len(base64_data)} chars, type: {content_type}")
                return True, base64_data, content_type
                
        except Exception as e:
            logger.error(f"❌ [URL-TO-BASE64] Failed to convert {url}: {e}")
            return False, "", ""

    async def _filter_valid_images(self, content_list: List[Dict]) -> List[Dict]:
        """Filter content list to keep only valid images and text, converting URLs to base64 for Bedrock"""
        if not content_list:
            return content_list
        
        filtered_content = []
        image_count = 0
        valid_image_count = 0
        
        for item in content_list:
            if item.get('type') == 'image':
                image_count += 1
                
                # Check if this is a URL image that needs conversion for Bedrock
                source = item.get('source', {})
                if source.get('type') == 'url':
                    url = source.get('url')
                    logger.info(f"🔄 [BEDROCK-CONVERT] Converting URL image to base64 for Bedrock compatibility")
                    success, base64_data, media_type = await self._url_to_base64(url)
                    
                    if success:
                        # Create base64 image for Bedrock
                        converted_item = {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": base64_data
                            }
                        }
                        filtered_content.append(converted_item)
                        valid_image_count += 1
                        logger.info(f"✅ [IMAGE-VALID] Image {image_count} converted URL→base64 for Bedrock")
                    else:
                        logger.warning(f"❌ [IMAGE-INVALID] Skipping image {image_count}: Failed URL conversion")
                else:
                    # Base64 image - validate normally
                    is_valid, reason = await self._validate_image(item)
                    
                    if is_valid:
                        filtered_content.append(item)
                        valid_image_count += 1
                        logger.info(f"✅ [IMAGE-VALID] Image {valid_image_count} passed validation")
                    else:
                        logger.warning(f"❌ [IMAGE-INVALID] Skipping image {image_count}: {reason}")
            else:
                # Keep non-image content (text, etc.)
                filtered_content.append(item)
        
        # Log summary
        if image_count > 0:
            logger.info(f"🖼️ [IMAGE-SUMMARY] {valid_image_count}/{image_count} images passed validation")
        
        return filtered_content
    
    async def _call_claude(self, messages: List[Dict], use_tools: bool = True, max_iterations: int = 10):
        """Call Claude with interleaved thinking, tools, and streamlined logging"""
        try:
            # Format dynamic values with Thailand timezone (UTC+7)
            thailand_tz = pytz.timezone('Asia/Bangkok')
            current_time = datetime.now(thailand_tz).strftime("%A, %d %B %Y, %I:%M %p")
            user_persona = "Customer seeking health packages and services"  # Default persona
            
            # Split system prompt into cacheable and dynamic parts
            # Remove dynamic placeholders from the main prompt for caching
            static_system_prompt = self.system_prompt.replace(
                '{CURRENT_DATE_TIME}', '[DYNAMIC_TIME_PLACEHOLDER]'
            ).replace(
                '{USER_PERSONA}', '[DYNAMIC_PERSONA_PLACEHOLDER]'
            )
            
            # Create system message array with caching
            system_messages = [
                {
                    "type": "text",
                    "text": static_system_prompt,
                    "cache_control": {"type": "ephemeral"}  # Cache the large static part (breakpoint 1)
                },
                {
                    "type": "text", 
                    "text": f"\n# Dynamic Context (Updated per conversation):\n- Current date and time: {current_time}\n- User persona: {user_persona}"
                }
            ]
            
            # Apply moving cache to conversation history (breakpoint 4)
            cached_messages = self._apply_conversation_caching(messages)
            logger.info(f"💾 [CACHE-STRATEGY] Using moving cache breakpoint for {len(cached_messages)} messages")
            
            # Validate messages for empty content before sending to API
            validated_messages = []
            for i, msg in enumerate(cached_messages):
                content = msg.get('content')
                if isinstance(content, str) and not content.strip():
                    logger.warning(f"⚠️ [MESSAGE-VALIDATION] Empty string content in message {i}, skipping")
                    continue
                elif isinstance(content, list) and len(content) == 0:
                    logger.warning(f"⚠️ [MESSAGE-VALIDATION] Empty list content in message {i}, skipping")
                    continue
                elif content is None or content == "":
                    logger.warning(f"⚠️ [MESSAGE-VALIDATION] Null/empty content in message {i}, skipping")
                    continue
                validated_messages.append(msg)
            
            # Use validated messages
            cached_messages = validated_messages
            logger.info(f"✅ [MESSAGE-VALIDATION] {len(cached_messages)} validated messages ready for API")
            
            # Debug: Count cache breakpoints in the final request
            system_cache_count = sum(1 for msg in system_messages if isinstance(msg, dict) and msg.get("cache_control"))
            message_cache_count = 0
            for msg in cached_messages:
                if isinstance(msg.get("content"), list):
                    message_cache_count += sum(1 for block in msg["content"] if isinstance(block, dict) and block.get("cache_control"))
            
            total_cache_breakpoints = system_cache_count + message_cache_count
            logger.info(f"🔍 [CACHE-BREAKPOINTS] System: {system_cache_count}, Messages: {message_cache_count}, Total: {total_cache_breakpoints}/4")
            
            if total_cache_breakpoints > 4:
                logger.error(f"❌ [CACHE-ERROR] Exceeding 4 cache breakpoint limit! Total: {total_cache_breakpoints}")
            
            kwargs = {
                "model": Config.MODEL["sonnet_4"],
                "max_tokens": Config.MAX_TOKENS,
                "temperature": 1.0,  # Required for thinking mode
                "system": system_messages,  # Use the new system message array
                "messages": cached_messages,  # Use cached messages with content blocks
                "thinking": {
                    "type": "enabled",
                    "budget_tokens": Config.MAX_REASONING_TOKENS
                },
                "extra_headers": {
                    "anthropic-beta": "interleaved-thinking-2025-05-14"
                }
            }
            
            # Add tools if requested
            if use_tools and self.centralized_tools:
                tools = self.centralized_tools.get_tool_definitions()
                kwargs["tools"] = tools
                kwargs["tool_choice"] = {"type": "auto"}
                logger.info(f"🔧 [TOOLS-AVAILABLE] {len(tools)} tools loaded: {[t['name'] for t in tools]}")
            
            logger.info("🚀 [AGENT-STEP] Invoking Sonnet-4 with Interleaved Thinking + Prompt Caching")
            
            response = await self.client.messages.create(**kwargs)
            
            # Log basic response details including cache info
            if response:
                thinking_blocks = sum(1 for block in response.content if hasattr(block, 'type') and block.type == 'thinking')
                tool_use_blocks = sum(1 for block in response.content if hasattr(block, 'type') and block.type == 'tool_use')
                
                logger.info(f"✅ [RESPONSE-RECEIVED] Content blocks: {len(response.content)}, Stop reason: {response.stop_reason}")
                if thinking_blocks > 0:
                    logger.info(f"🧠 [CONTENT-ANALYSIS] Thinking: {thinking_blocks}, Tool calls: {tool_use_blocks}")
                
                # Log token usage with cache information if available
                if hasattr(response, 'usage'):
                    usage = response.usage
                    cache_creation = getattr(usage, 'cache_creation_input_tokens', 0) or 0
                    cache_read = getattr(usage, 'cache_read_input_tokens', 0) or 0
                    total_input = usage.input_tokens + cache_read
                    
                    logger.info(f"📈 [TOKEN-USAGE] Input: {usage.input_tokens}, Output: {usage.output_tokens}")
                    
                    if cache_creation > 0:
                        logger.info(f"💾 [CACHE-CREATION] {cache_creation} tokens cached for future use")
                        logger.info(f"🔍 [CACHE-DEBUG] New cache entry created - this should grow over iterations")
                    else:
                        logger.info(f"🔍 [CACHE-DEBUG] No new cache creation - using existing cache")
                    
                    if cache_read > 0:
                        cache_efficiency = (cache_read / total_input) * 100 if total_input > 0 else 0
                        logger.info(f"⚡ [CACHE-HIT] {cache_read} tokens loaded from cache ({cache_efficiency:.1f}% cache efficiency - saved cost!)")
                        logger.info(f"🔍 [CACHE-DEBUG] Cache read amount should grow with conversation length")
                    else:
                        logger.info(f"🔍 [CACHE-DEBUG] No cache hits - this might indicate caching issues")
                    
                    # Expected vs actual cache behavior
                    logger.info(f"🔍 [CACHE-ANALYSIS] Total input tokens: {total_input} (fresh: {usage.input_tokens}, cached: {cache_read})")
            
            return response
            
        except Exception as e:
            logger.error(f"❌ [CLAUDE-ERROR] Failed to call Claude: {e}")
            return None
    
    async def _process_with_tools(self, messages: List[Dict], room_id: str, max_iterations: int = None) -> Tuple[str, List[str], List[Dict], Dict]:
        """Process query with tool calling support and interleaved thinking"""
        conversation_history = messages.copy()
        all_thinking_blocks = []
        tools_used = []
        iteration = 0
        
        # Use global threshold if max_iterations not provided
        if max_iterations is None:
            from globals import global_storage
            max_iterations = global_storage.AGENTIC_LOOP_THRESHOLD
        
        # Token tracking
        total_tokens = {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "cache_creation_tokens": 0,
            "cache_read_tokens": 0,
            "iterations": 0,
            "api_calls": 0
        }
        
        while iteration < max_iterations:
            iteration += 1
            total_tokens["iterations"] = iteration
            logger.info(f"🔄 [ITERATION-{iteration}] Processing with tools support")
            
            # Call Claude with tools
            response = await self._call_claude(conversation_history, use_tools=True)
            
            if not response:
                # Generate handover instead of generic error message
                logger.critical(f"🚨 [AGENT-FALLBACK] Claude API failure triggered handover fallback")
                logger.critical(f"🔧 [FALLBACK-TRIGGER] Claude API response failure in iteration {iteration}")
                handover_message = await self._generate_handover_fallback("Claude API response failure")
                return handover_message, all_thinking_blocks, tools_used, total_tokens
            
            # Track tokens from this API call
            if hasattr(response, 'usage'):
                total_tokens["api_calls"] += 1
                total_tokens["input_tokens"] += response.usage.input_tokens
                total_tokens["output_tokens"] += response.usage.output_tokens
                total_tokens["total_tokens"] = total_tokens["input_tokens"] + total_tokens["output_tokens"]
                
                # Track cache metrics
                cache_creation = getattr(response.usage, 'cache_creation_input_tokens', 0) or 0
                cache_read = getattr(response.usage, 'cache_read_input_tokens', 0) or 0
                total_tokens["cache_creation_tokens"] += cache_creation
                total_tokens["cache_read_tokens"] += cache_read
                
                logger.info(f"📊 [ITERATION-{iteration}-TOKENS] Input: {response.usage.input_tokens}, Output: {response.usage.output_tokens}")
                if cache_creation > 0:
                    logger.info(f"💾 [ITERATION-{iteration}-CACHE] Created: {cache_creation} tokens")
                if cache_read > 0:
                    logger.info(f"⚡ [ITERATION-{iteration}-CACHE] Read: {cache_read} tokens")
                logger.info(f"📈 [CUMULATIVE-TOKENS] Total Input: {total_tokens['input_tokens']}, Total Output: {total_tokens['output_tokens']}, Grand Total: {total_tokens['total_tokens']}")
            
            # Extract thinking content
            thinking_blocks_this_turn = []
            text_content = ""
            tool_use_blocks = []
            
            for content_block in response.content:
                if content_block.type == "thinking":
                    thinking_blocks_this_turn.append(content_block.thinking)
                    all_thinking_blocks.append(content_block.thinking)
                elif content_block.type == "text":
                    text_content = content_block.text
                elif content_block.type == "tool_use":
                    tool_use_blocks.append(content_block)
            
            # Log thinking for this iteration with detailed content
            if thinking_blocks_this_turn:
                logger.info(f"🧠 [JIB-THINKING] Reasoning through {len(thinking_blocks_this_turn)} thinking blocks")
                for i, thinking_content in enumerate(thinking_blocks_this_turn, 1):
                    logger.info(f"💭 [THINKING-BLOCK-{i}] {'-'*50}")
                    # Split thinking content into lines for better readability
                    thinking_lines = thinking_content.strip().split('\n')
                    for line in thinking_lines:
                        if line.strip():  # Only log non-empty lines
                            logger.info(f"💭 [THINKING] {line.strip()}")
                    logger.info(f"💭 [THINKING-END-{i}] {'-'*50}")
            
            # Check stop reason and handle accordingly
            if response.stop_reason == "end_turn":
                # No tools used, return final response
                conversation_history.append({
                    "role": "assistant",
                    "content": response.content
                })
                
                logger.info(f"✅ [COMPLETION] Task completed in {iteration} iterations with {len(tools_used)} tool calls")
                return text_content, all_thinking_blocks, tools_used, total_tokens
            
            elif response.stop_reason == "tool_use":
                # Tools were used - handle with streamlined logging
                tool_count = len(tool_use_blocks)
                
                if tool_count > 1:
                    logger.info(f"⚡ [PARALLEL-EXECUTION] Executing {tool_count} tools simultaneously")
                else:
                    logger.info(f"🔄 [SEQUENTIAL-EXECUTION] Executing single tool")
                
                # Add assistant message with thinking and tool calls
                conversation_history.append({
                    "role": "assistant",
                    "content": response.content
                })
                
                # Execute tools and add results
                handover_detected = False
                handover_result = None
                
                for idx, tool_block in enumerate(tool_use_blocks, 1):
                    logger.info(f"🛠️  [TOOL-{idx}/{tool_count}] {tool_block.name}: {list(tool_block.input.keys())}")
                    
                    # Execute tool with room_id
                    tool_result = await self.centralized_tools.execute_tool(tool_block.name, tool_block.input, room_id)
                    
                    # Track tool usage
                    tools_used.append({
                        "name": tool_block.name,
                        "input": tool_block.input,
                        "result": tool_result
                    })
                    
                    # Check for handover tools - immediately return handover message like bot.py
                    if tool_block.name in ["handover_to_cx", "handover_to_bk", "handover_asap"]:
                        handover_detected = True
                        handover_result = tool_result
                        logger.info(f"🚨 [IMMEDIATE-HANDOVER] {tool_block.name} detected - returning handover message immediately")
                        break
                    
                    # Add tool result to conversation
                    # Special handling for image tools that return content blocks
                    tool_result_content = self._parse_tool_result_content(tool_block.name, tool_result)
                    
                    conversation_history.append({
                        "role": "user",
                        "content": [{
                            "type": "tool_result",
                            "tool_use_id": tool_block.id,
                            "content": tool_result_content
                        }]
                    })
                    
                    # Concise completion message
                    logger.info(f"✅ [{tool_block.name.upper()}] Tool execution complete, back to agentic main loop")
                
                # If handover was detected, return immediately without further LLM processing
                if handover_detected:
                    logger.info(f"🔄 [HANDOVER-BYPASS] Skipping LLM continuation, returning: {handover_result}")
                    return handover_result, all_thinking_blocks, tools_used, total_tokens
                
                # Continue message for next iteration
                logger.info("🧠 [JIB-THINKING] Jib is processing tool results...")
                continue
            
            else:
                logger.warning(f"⚠️ [UNEXPECTED-STOP] Unexpected stop reason: {response.stop_reason}")
                break
        
        # Generate handover for max iterations reached
        logger.critical(f"🚨 [AGENT-FALLBACK] Max iterations ({max_iterations}) reached - triggering handover fallback")
        logger.critical(f"🔧 [FALLBACK-TRIGGER] Complex query requiring human assistance after {max_iterations} iterations")
        handover_message = await self._generate_handover_fallback(f"Maximum iterations ({max_iterations}) reached - complex query requiring human assistance")
        return handover_message, all_thinking_blocks, tools_used, total_tokens

    async def forward(self, chats, room_id, last_query) -> Tuple[Dict, Dict, Dict]:
        """
        Main forward method to match original JibAI interface (now async)
        Returns: (chat_resp, token_dict, thought_dict)
        """
        start_time = datetime.now()
        logger.info("="*80)
        logger.info(f"🚀 [AGENT-START] JibAI Sonnet-4 Agent Processing New Query")
        logger.info(f"⏰ [TIMESTAMP] {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"🏠 [ROOM-ID] {room_id}")
        logger.info(f"💬 [USER-QUERY] {last_query}")
        logger.info(f"📜 [CHAT-HISTORY] {len(chats)} previous messages")
        
        try:
            # Call the async method directly (no asyncio.run needed)
            result = await self._process_query_async(chats, room_id, last_query)
            
            # Log completion timing
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            logger.info(f"⏱️ [PROCESSING-TIME] {duration:.2f} seconds")
            logger.info(f"🎉 [AGENT-SUCCESS] Processing completed successfully")
            logger.info("="*80)
            
            return result
            
        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            logger.error(f"❌ [AGENT-ERROR] Error in forward method after {duration:.2f}s: {e}")
            logger.error("="*80)
            
            # Log critical agent failure for monitoring
            logger.critical(f"🚨 [AGENT-FALLBACK] System error triggered handover fallback: {str(e)}")
            logger.critical(f"🔧 [FALLBACK-TRIGGER] Forward method error context: {str(e)}")
            
            # Generate handover instead of generic error
            try:
                handover_response = await self._generate_handover_fallback(f"Forward method error: {str(e)}")
            except:
                # Ultimate fallback - ensure we ALWAYS return QISCUS integration format
                logger.critical(f"🚨 [ULTIMATE-FALLBACK] Handover generation failed, using emergency handover")
                handover_response = "QISCUS_INTEGRATION_TO_CX: System Error"
            
            return (
                {"text": handover_response, "image": []}, 
                {"total_tokens": 0}, 
                {"thinking_content": f"Error occurred: {str(e)}"}
            )
    
    async def _process_query_async(self, chats, room_id, last_query):
        """Process the query asynchronously with centralized tools support"""
        try:
            # Prepare conversation context with image validation
            messages = await self._prepare_messages(chats, last_query)
            
            logger.info("🧠 [AGENT-DECISION] Letting Claude analyze and decide if RAG/tools are needed")
            
            # Debug: Log the exact message structure being sent to Claude
            logger.info(f"🔍 [DEBUG-MESSAGES] Processing {len(messages)} messages")
            for i, msg in enumerate(messages):
                content = msg.get('content')
                if isinstance(content, list):
                    logger.info(f"📝 [DEBUG-MSG-{i}] Has {len(content)} content items")
                    for j, content_item in enumerate(content):
                        if content_item.get('type') == 'image':
                            source = content_item.get('source', {})
                            logger.info(f"🖼️ [DEBUG-IMAGE-{i}-{j}] Type: {source.get('type')}, Keys: {list(source.keys())}")
                            # Log source details but truncate base64 data to avoid terminal spam
                            if source.get('type') == 'base64' and 'data' in source:
                                truncated_source = source.copy()
                                data_length = len(source['data']) if source['data'] else 0
                                truncated_source['data'] = f"<BASE64_DATA_{data_length}_CHARS>"
                                logger.info(f"🖼️ [DEBUG-IMAGE-{i}-{j}] Source: {truncated_source}")
                            else:
                                logger.info(f"🖼️ [DEBUG-IMAGE-{i}-{j}] Full source: {source}")
                else:
                    logger.info(f"📝 [DEBUG-MSG-{i}] Text content: {str(content)[:100]}...")
            
            # Process with centralized tools system - Claude will decide what it needs
            # No pre-RAG injection - let Claude think first and use tools if needed
            text_response, thinking_blocks, tools_used, total_tokens = await self._process_with_tools(messages, room_id)
            
            # Compile thinking content
            thinking_content = "\n\n".join(thinking_blocks) if thinking_blocks else ""
            
            # Log tool usage summary
            if tools_used:
                logger.info(f"🔧 [TOOLS-SUMMARY] Used {len(tools_used)} tools:")
                for tool in tools_used:
                    logger.info(f"🔧   - {tool['name']}: {str(tool['input'])[:100]}...")
            
            # Create response structure matching original bot
            # Parse image URLs from response text and clean the text
            image_urls = self._extract_image_urls_from_response(text_response)
            cleaned_text = self._remove_image_urls_from_text(text_response)
            
            chat_resp = {"text": cleaned_text, "image": image_urls}
            token_dict = {
                "total_tokens": total_tokens["total_tokens"],
                "input_tokens": total_tokens["input_tokens"],
                "output_tokens": total_tokens["output_tokens"],
                "cache_creation_tokens": total_tokens["cache_creation_tokens"],
                "cache_read_tokens": total_tokens["cache_read_tokens"],
                "api_calls": total_tokens["api_calls"],
                "iterations": total_tokens["iterations"]
            }
            thought_dict = {
                "thinking_content": thinking_content,
                "tools_used": tools_used,
                "tool_count": len(tools_used)
            }
            
            # Enhanced final summary with comprehensive token information
            if thinking_blocks:
                logger.info(f"🧠 [FINAL-THINKING-SUMMARY] Total thinking blocks: {len(thinking_blocks)}")
                logger.info(f"💭 [THINKING-TOTAL-LENGTH] {len(thinking_content)} characters of reasoning")
            
            # Comprehensive token usage summary
            logger.info(f"💰 [TOKEN-SUMMARY] ===== CONVERSATION TOKEN USAGE =====")
            logger.info(f"💰 [INPUT-TOKENS] {total_tokens['input_tokens']:,} tokens")
            logger.info(f"💰 [OUTPUT-TOKENS] {total_tokens['output_tokens']:,} tokens")
            logger.info(f"💰 [TOTAL-TOKENS] {total_tokens['total_tokens']:,} tokens")
            logger.info(f"💰 [API-CALLS] {total_tokens['api_calls']} Claude API calls")
            logger.info(f"💰 [ITERATIONS] {total_tokens['iterations']} agentic iterations")
            logger.info(f"💰 [TOOLS-USED] {len(tools_used)} tool executions")
            
            # Cache usage summary
            if total_tokens["cache_creation_tokens"] > 0 or total_tokens["cache_read_tokens"] > 0:
                logger.info(f"💾 [CACHE-SUMMARY] ===== PROMPT CACHING METRICS =====")
                logger.info(f"💾 [CACHE-CREATED] {total_tokens['cache_creation_tokens']:,} tokens cached")
                logger.info(f"⚡ [CACHE-READ] {total_tokens['cache_read_tokens']:,} tokens from cache") 
                
                # Calculate cache efficiency
                total_cache_tokens = total_tokens["cache_creation_tokens"] + total_tokens["cache_read_tokens"]
                cache_hit_rate = (total_tokens["cache_read_tokens"] / total_cache_tokens * 100) if total_cache_tokens > 0 else 0
                logger.info(f"📊 [CACHE-EFFICIENCY] Hit rate: {cache_hit_rate:.1f}% ({total_tokens['cache_read_tokens']:,}/{total_cache_tokens:,})")
            
            # Cost estimation (based on Sonnet 4 official pricing)
            # Sonnet 4: $3/1M input, $15/1M output, $3.75/1M cache write, $0.30/1M cache read
            estimated_cost_input = (total_tokens['input_tokens'] / 1_000_000) * 3
            estimated_cost_output = (total_tokens['output_tokens'] / 1_000_000) * 15
            estimated_cost_cache_creation = (total_tokens['cache_creation_tokens'] / 1_000_000) * 3.75
            estimated_cost_cache_read = (total_tokens['cache_read_tokens'] / 1_000_000) * 0.30
            
            estimated_total_cost = estimated_cost_input + estimated_cost_output + estimated_cost_cache_creation + estimated_cost_cache_read
            
            # Calculate potential savings from caching
            potential_cost_without_cache = (total_tokens['cache_read_tokens'] / 1_000_000) * 3  # If cache reads were regular input tokens
            cache_savings = potential_cost_without_cache - estimated_cost_cache_read
            
            logger.info(f"💲 [COST-BREAKDOWN] Input: ${estimated_cost_input:.4f}, Output: ${estimated_cost_output:.4f}")
            if total_tokens["cache_creation_tokens"] > 0:
                logger.info(f"💲 [CACHE-COSTS] Creation: ${estimated_cost_cache_creation:.4f}, Read: ${estimated_cost_cache_read:.4f}")
            logger.info(f"💲 [TOTAL-COST] ${estimated_total_cost:.4f}")
            if cache_savings > 0:
                logger.info(f"💰 [CACHE-SAVINGS] ${cache_savings:.4f} saved from prompt caching!")
            logger.info(f"💰 [TOKEN-SUMMARY] ========================================")
            
            logger.info(f"✅ [AGENT-COMPLETE] Response ready - Text: {len(text_response)} chars, Tools: {len(tools_used)}, Thinking blocks: {len(thinking_blocks)}")
            
            return (chat_resp, token_dict, thought_dict)
                
        except Exception as e:
            logger.error(f"❌ [ASYNC-ERROR] Error in async processing: {e}")
            
            # Log critical agent failure for monitoring
            logger.critical(f"🚨 [AGENT-FALLBACK] System error triggered handover fallback: {str(e)}")
            logger.critical(f"🔧 [FALLBACK-TRIGGER] Async processing error context: {str(e)}")
            
            # Generate handover instead of generic error
            try:
                handover_response = await self._generate_handover_fallback(f"Async processing error: {str(e)}")
            except:
                # Ultimate fallback - ensure we ALWAYS return QISCUS integration format
                logger.critical(f"🚨 [ULTIMATE-FALLBACK] Handover generation failed, using emergency handover")
                handover_response = "QISCUS_INTEGRATION_TO_CX: System Error"
            
            return (
                {"text": handover_response, "image": []}, 
                {"total_tokens": 0}, 
                {"thinking_content": f"Error: {str(e)}"}
            )
    
    # Removed hardcoded decision functions - Claude now decides when to use RAG via tools
    
    async def _prepare_messages(self, chats, last_query):
        """Prepare message history for Claude with proper content handling, format conversion, and image validation"""
        messages = []
        
        def convert_content_format(content, role="user"):
            """Convert and clean image formats for Claude - ensure strict format compliance
            Remove images from assistant messages (Claude API constraint)"""
            if isinstance(content, list):
                converted_content = []
                for item in content:
                    if isinstance(item, dict):
                        if item.get('type') == 'image_url' and 'image_url' in item:
                            # Skip images for assistant messages
                            if role == 'assistant':
                                logger.info(f"🔄 [IMAGE-FILTER] Removing image from assistant message (Claude constraint)")
                                continue
                            # Convert from OpenAI format to Claude format with base64 for Bedrock
                            url = item['image_url']['url']
                            converted_content.append({
                                "type": "image",
                                "source": {
                                    "type": "url",
                                    "url": url
                                }
                            })
                        elif item.get('type') == 'image' and 'source' in item:
                            # Skip images for assistant messages
                            if role == 'assistant':
                                logger.info(f"🔄 [IMAGE-FILTER] Removing image from assistant message (Claude constraint)")
                                continue
                            # Clean Claude format - ensure strict field separation
                            source = item['source']
                            if source.get('type') == 'url':
                                # URL format: only include url
                                converted_content.append({
                                    "type": "image",
                                    "source": {
                                        "type": "url",
                                        "url": source['url']
                                    }
                                })
                            elif source.get('type') == 'base64':
                                # Base64 format: only include media_type and data
                                converted_content.append({
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": source.get('media_type', 'image/jpeg'),
                                        "data": source['data']
                                    }
                                })
                            else:
                                # Keep as is if format is unknown
                                converted_content.append(item)
                        else:
                            # Keep as is (text, etc.)
                            converted_content.append(item)
                    else:
                        converted_content.append(item)
                return converted_content
            return content
        
        def is_content_empty(content):
            """Check if content is empty - handles both string and list formats"""
            if isinstance(content, str):
                return not content.strip()
            elif isinstance(content, list):
                return len(content) == 0
            else:
                return content is None or content == ""
        
        # Add conversation history (last few messages)
        if chats:
            for chat in chats[-5:]:  # Last 5 messages for context
                if isinstance(chat, dict):
                    role = chat.get('role')
                    content = chat.get('content', '')
                    
                    if role in ['user', 'assistant']:
                        # Handle both string content and structured content
                        if isinstance(content, str):
                            # Only add if content is not empty
                            if not is_content_empty(content):
                                messages.append({"role": role, "content": content})
                            else:
                                logger.warning(f"⚠️ [EMPTY-CONTENT] Skipping empty {role} message")
                        elif isinstance(content, list):
                            # Convert format and validate images, filter assistant images
                            converted_content = convert_content_format(content, role)
                            validated_content = await self._filter_valid_images(converted_content)
                            # Only add if content is not empty after processing
                            if not is_content_empty(validated_content):
                                messages.append({"role": role, "content": validated_content})
                            else:
                                logger.warning(f"⚠️ [EMPTY-CONTENT] Skipping empty {role} message after processing")
                        else:
                            # Only add if content is not empty
                            if not is_content_empty(content):
                                messages.append({"role": role, "content": content})
                            else:
                                logger.warning(f"⚠️ [EMPTY-CONTENT] Skipping empty {role} message")
        
        # Add current query - handle both string and structured format
        if isinstance(last_query, str):
            # Only add if not empty
            if not is_content_empty(last_query):
                messages.append({"role": "user", "content": last_query})
            else:
                logger.warning(f"⚠️ [EMPTY-QUERY] Current query is empty, adding fallback message")
                messages.append({"role": "user", "content": "สวัสดีค่ะ"})  # Fallback greeting
        elif isinstance(last_query, dict) and last_query.get('content'):
            # Structured query with images/text - convert format
            content = last_query.get('content')
            if isinstance(content, list):
                converted_content = convert_content_format(content, "user")
                validated_content = await self._filter_valid_images(converted_content)
                # Only add if not empty after processing
                if not is_content_empty(validated_content):
                    messages.append({"role": "user", "content": validated_content})
                else:
                    logger.warning(f"⚠️ [EMPTY-QUERY] Structured query is empty after processing, adding fallback message")
                    messages.append({"role": "user", "content": "สวัสดีค่ะ"})  # Fallback greeting
            else:
                # Only add if not empty
                if not is_content_empty(content):
                    messages.append({"role": "user", "content": content})
                else:
                    logger.warning(f"⚠️ [EMPTY-QUERY] Query content is empty, adding fallback message")
                    messages.append({"role": "user", "content": "สวัสดีค่ะ"})  # Fallback greeting
        else:
            # No valid query found, add fallback
            logger.warning(f"⚠️ [NO-QUERY] No valid query found, adding fallback message")
            messages.append({"role": "user", "content": "สวัสดีค่ะ"})  # Fallback greeting
        
        return messages

    async def _generate_handover_fallback(self, error_context: str = "") -> str:
        """Generate a handover message when errors occur"""
        try:
            # Use the centralized handover tool - normal CX handover for system errors
            handover_result = await self.centralized_tools.execute_tool(
                "handover_to_cx",
                {
                    "package_name": "System Error",
                    "package_category": "Technical Support",
                    "package_location": "System",
                    "price_and_budget": f"Error: {error_context[:100]}..."
                }
            )
            return handover_result
        except Exception as e:
            logger.error(f"❌ [HANDOVER-FALLBACK] Failed to generate handover: {e}")
            logger.critical(f"🚨 [HANDOVER-GENERATION-FAILED] Error context: {error_context[:100]}...")
            # Ultimate fallback - ensure we ALWAYS return QISCUS integration format
            return "QISCUS_INTEGRATION_TO_CX: System Error"
    
    def _remove_existing_cache_controls(self, messages):
        """Remove cache_control from all message content blocks to avoid exceeding cache breakpoint limits"""
        cleaned = []
        removed_count = 0
        removed_details = []
        
        logger.info(f"🔍 [CACHE-CLEANUP-DEBUG] Starting cleanup for {len(messages)} messages")
        
        for msg_idx, msg in enumerate(messages):
            cleaned_msg = msg.copy()
            if "content" in cleaned_msg and isinstance(cleaned_msg["content"], list):
                cleaned_content = []
                for block_idx, content_block in enumerate(cleaned_msg["content"]):
                    # Handle different content block types (dict vs special objects like ThinkingBlock)
                    if isinstance(content_block, dict):
                        clean_block = content_block.copy()
                        if clean_block.pop("cache_control", None):  # Remove if exists
                            removed_count += 1
                            block_preview = clean_block.get('text', str(clean_block))[:50] + "..."
                            removed_details.append(f"msg{msg_idx+1}:block{block_idx+1}({block_preview})")
                            logger.info(f"🔄 [CACHE-CLEANUP-DEBUG] Removed cache_control from message {msg_idx+1}, block {block_idx+1}")
                        cleaned_content.append(clean_block)
                    else:
                        # For non-dict objects (like ThinkingBlock), just pass through as-is
                        # These don't have cache_control anyway
                        logger.info(f"🔍 [CACHE-CLEANUP-DEBUG] Skipping non-dict block: {type(content_block).__name__}")
                        cleaned_content.append(content_block)
                cleaned_msg["content"] = cleaned_content
            cleaned.append(cleaned_msg)
        
        if removed_count > 0:
            logger.info(f"🔄 [CACHE-CLEANUP] Removed {removed_count} old cache_control markers from: {', '.join(removed_details)}")
        else:
            logger.info(f"🔍 [CACHE-CLEANUP] No existing cache_control markers found")
        
        return cleaned
    
    def _parse_tool_result_content(self, tool_name: str, tool_result: str):
        """Parse tool result content, handling special cases like image tools"""
        if tool_name == "get_package_images":
            try:
                import json
                # Try to parse as content blocks (for image tools)
                content_blocks = json.loads(tool_result)
                
                # Validate that it's a list of content blocks
                if isinstance(content_blocks, list) and all(
                    isinstance(block, dict) and "type" in block 
                    for block in content_blocks
                ):
                    return content_blocks
                else:
                    # Fallback to string if not valid content blocks
                    return tool_result
                    
            except json.JSONDecodeError:
                # Not JSON, return as string
                return tool_result
        else:
            # For all other tools, return as string
            return tool_result
    

    def _apply_conversation_caching(self, messages):
        """Apply moving cache breakpoint to conversation history (4th cache breakpoint)"""
        if not messages:
            logger.info("🔍 [CACHE-DEBUG] No messages to cache")
            return messages
        
        logger.info(f"🔍 [CACHE-DEBUG] Starting conversation caching for {len(messages)} messages")
        
        # Remove any existing cache_control from all messages first
        cleaned_messages = self._remove_existing_cache_controls(messages)
        
        # Add cache_control to the last tool_result or user text message to create moving cache breakpoint
        last_cache_idx = -1
        cache_target_type = "none"
        
        for i in range(len(cleaned_messages) - 1, -1, -1):
            if cleaned_messages[i].get("role") == "user":
                content = cleaned_messages[i].get("content", [])
                if isinstance(content, list):
                    # Prioritize tool_result over text (tool results are "complete" interactions)
                    for block in content:
                        if isinstance(block, dict):
                            if block.get("type") == "tool_result":
                                last_cache_idx = i
                                cache_target_type = "tool_result"
                                break
                            elif block.get("type") == "text" and cache_target_type == "none":
                                last_cache_idx = i
                                cache_target_type = "text"
                if last_cache_idx >= 0 and cache_target_type == "tool_result":
                    break  # tool_result found, stop searching
        
        # If we found a cache target, use that index
        last_user_idx = last_cache_idx
        
        logger.info(f"🔍 [CACHE-DEBUG] Found cache target at index: {last_user_idx}, type: {cache_target_type}")
        
        if last_user_idx >= 0:
            msg = cleaned_messages[last_user_idx]
            content = msg.get("content", [])
            
            logger.info(f"🔍 [CACHE-DEBUG] Cache target message content type: {type(content)}, length: {len(content) if isinstance(content, list) else 'N/A'}")
            
            if content and isinstance(content, list):
                # Find the target block (tool_result or text) and add cache control
                cache_applied = False
                for content_block in content:
                    if isinstance(content_block, dict):
                        block_type = content_block.get("type")
                        if (cache_target_type == "tool_result" and block_type == "tool_result") or \
                           (cache_target_type == "text" and block_type == "text"):
                            content_block["cache_control"] = {"type": "ephemeral"}
                            logger.info(f"💾 [CACHE-APPLIED] ✅ Added moving cache breakpoint to {block_type} in message {last_user_idx + 1}")
                            if block_type == "text":
                                logger.info(f"🔍 [CACHE-DEBUG] Cache control added to text: {content_block.get('text', '')[:100]}...")
                            elif block_type == "tool_result":
                                logger.info(f"🔍 [CACHE-DEBUG] Cache control added to tool_result: {str(content_block.get('content', ''))[:100]}...")
                            cache_applied = True
                            break
                
                if not cache_applied:
                    logger.warning(f"⚠️ [CACHE-DEBUG] Could not find {cache_target_type} block to cache")
            else:
                logger.warning(f"⚠️ [CACHE-DEBUG] Cannot add cache control - content issue:")
                logger.warning(f"⚠️ [CACHE-DEBUG] Content exists: {bool(content)}, isinstance list: {isinstance(content, list)}")
                logger.warning(f"⚠️ [CACHE-DEBUG] Content type: {type(content)}")
                logger.warning(f"⚠️ [CACHE-DEBUG] Content value: {content}")
        else:
            logger.warning(f"⚠️ [CACHE-DEBUG] No user messages found in conversation")
        
        # Log final message structure for debugging
        logger.info(f"🔍 [CACHE-DEBUG] Final message structure:")
        for i, msg in enumerate(cleaned_messages):
            role = msg.get("role", "unknown")
            content = msg.get("content", [])
            has_cache = False
            cache_blocks = 0
            
            if isinstance(content, list):
                for content_block in content:
                    if isinstance(content_block, dict) and content_block.get("cache_control"):
                        has_cache = True
                        cache_blocks += 1
            
            cache_indicator = f"💾[{cache_blocks}]" if has_cache else "   [0]"
            logger.info(f"🔍 [CACHE-DEBUG]   {cache_indicator} Message {i+1} ({role}): {len(content) if isinstance(content, list) else 0} content blocks")
        
        return cleaned_messages

    def _extract_image_urls_from_response(self, response_text):
        """Extract image URLs from response text in format [url1, url2, ...] and remove them from text"""
        import re
        
        # Look for the specific format [url1, url2, ...] at the end of the response
        pattern = r'\[([^\]]+)\](?:\s*$)'
        match = re.search(pattern, response_text.strip())
        
        if match:
            urls_string = match.group(1)
            # Split by comma and clean up URLs
            urls = [url.strip() for url in urls_string.split(',')]
            # Filter to only include valid HTTP/HTTPS URLs
            valid_urls = [url for url in urls if re.match(r'https?://', url)]
            
            if valid_urls:
                logger.info(f"🖼️ [IMAGE-EXTRACTION] Found {len(valid_urls)} image URLs: {valid_urls}")
                return valid_urls
        
        logger.info(f"🖼️ [IMAGE-EXTRACTION] No image URLs found in response")
        return []
    
    def _remove_image_urls_from_text(self, response_text):
        """Remove the [url1, url2, ...] pattern from the response text"""
        import re
        
        # Remove the specific format [url1, url2, ...] at the end of the response
        pattern = r'\s*\[([^\]]+)\](?:\s*$)'
        cleaned_text = re.sub(pattern, '', response_text.strip())
        
        return cleaned_text