import os
from dotenv import load_dotenv
from openai import AsyncAzureOpenAI
import asyncio
from src.RAG import RAG
from gpt_tools import GPTTools
from tenacity import retry, stop_after_attempt, wait_random_exponential
from pydantic import BaseModel
from typing import List
import json
import logging
import re

logger = logging.getLogger(__name__)

load_dotenv()

api_key = os.getenv('GPT_MINI_API_KEY')
endpoint = os.getenv('GPT_MINI_ENDPOINT')
MODEL = "gpt-4.1-mini"




class recommended_urls(BaseModel):
    """Pydantic model for recommended urls."""
    url: str
    url_type: str

class OutputFormat(BaseModel):
    """Pydantic model for JibAI JSON response structure."""
    thinking: str
    response: str
    recommended_prompts_for_users: List[str]
    recommended_urls: List[recommended_urls]


class GPTBot:
    def __init__(self, global_storage):
        self.client = AsyncAzureOpenAI(
            api_version='2025-01-01-preview',
            azure_endpoint=endpoint,
            api_key=api_key,
        )
        self.rag = RAG(global_storage=global_storage)
        self.tools = GPTTools()
        self.system_prompt = open("src/prompts/gpt.txt", "r").read()
    
    @retry(
        wait=wait_random_exponential(min=1, max=30), #300
        stop=stop_after_attempt(3)) # Reduced from 10 to 3 for faster feedback
    async def invoke_gpt(self, *args, **kwargs) -> str:
        try:
            response = await self.client.beta.chat.completions.parse(*args, **kwargs)
            return response
        except Exception as e:
            # Handle the trailing characters error
            if "trailing characters" in str(e) or "Invalid JSON" in str(e):
                logger.warning(f"Structured parsing failed with error: {e}")
                logger.info("Attempting fallback parsing...")
                
                # Remove response_format from kwargs for fallback
                fallback_kwargs = kwargs.copy()
                fallback_kwargs.pop('response_format', None)
                
                # Get raw response without structured parsing
                raw_response = await self.client.chat.completions.create(*args, **fallback_kwargs)
                content = raw_response.choices[0].message.content
                
                logger.info(f"Raw response content: {content}")
                
                # Extract JSON part using regex
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    logger.info(f"Extracted JSON: {json_str}")
                    
                    # Clean up any potential trailing characters
                    json_str = json_str.strip()
                    
                    try:
                        # Validate with Pydantic
                        parsed_output = OutputFormat.model_validate_json(json_str)
                        
                        # Create a mock response object to maintain compatibility
                        class MockChoice:
                            def __init__(self, parsed_data):
                                self.message = type('obj', (object,), {'parsed': parsed_data})()
                                self.finish_reason = "stop"
                        
                        class MockResponse:
                            def __init__(self, parsed_data):
                                self.choices = [MockChoice(parsed_data)]
                        
                        logger.info("Successfully parsed JSON using fallback method")
                        return MockResponse(parsed_output)
                    except Exception as parse_error:
                        logger.error(f"Failed to parse extracted JSON: {parse_error}")
                        logger.error(f"Problematic JSON string (first 500 chars): {json_str[:500]}")
                        raise parse_error
                else:
                    logger.error("Could not extract JSON from response")
                    logger.error(f"Response content (first 500 chars): {content[:500]}")
                    raise e
            else:
                raise e
    
    def tools_calling(self, tool_name: str, args: dict) -> str:
        if tool_name == "search_package_database":
            #["thought", "package_name", "location", "price", "brand", "category_tag"]
            package_name = args["package_name"]
            location = args["location"]
            price = args["price"]
            brand = args["brand"]
            category_tag = args["category_tag"]
            
            # Normalize brand name
            if brand:
                normalized_brand = self.rag.normalize_brand_name(brand)
                if normalized_brand != brand:
                    print(f"Tool calling brand normalization: '{brand}' → '{normalized_brand}'")
                    brand = normalized_brand
            
            query = package_name + brand + location + price 
            result = self.rag._get_package_url(query=query, preferred_area=location, radius=None, category_tag=category_tag)
            return result
        elif tool_name == "fetch_package_details":
            package_url = args["package_url"]
            result = self.rag.get_package_info_from_url(package_url)
            return result
        elif tool_name == "browse_broad_pages":
            query = args["query"]
            page_type = args["page_type"]
            
            # Normalize brand names for brand page searches
            if page_type == "brand":
                normalized_query = self.rag.normalize_brand_name(query)
                if normalized_query != query:
                    print(f"Browse broad pages brand normalization: '{query}' → '{normalized_query}'")
                    query = normalized_query
            
            result = self.rag.web_recommendation(query=query, type=page_type)
            return result
        elif tool_name == "cart":
            pass
        elif tool_name == "sql_search":
            query = args["sql_query"]
            category_tag = args.get("category_tag", "")
            result = self.rag.sql_search(query=query, category_tag=category_tag)
            return result
        elif tool_name == "explore_data_structure":
            exploration_type = args["exploration_type"]
            result = self.rag.explore_data_structure(exploration_type=exploration_type)
            return result
        elif tool_name == "smart_search_suggestions":
            failed_query_type = args["failed_query_type"]
            original_search_term = args["original_search_term"]
            result = self.rag.smart_search_suggestions(failed_query_type=failed_query_type, original_search_term=original_search_term)
            return result

    async def forward(self, messages: list, room_id: str) -> str:
        logger.info(f"Jib is thinking. . . \n")
        messages.insert(0, {"role": "developer", "content": self.system_prompt})
        response = await self.invoke_gpt(
            model=MODEL,
            messages=messages,
            tools=[self.tools.search_package_database, self.tools.fetch_package_details, self.tools.browse_broad_pages, self.tools.cart, self.tools.sql_search, self.tools.explore_data_structure, self.tools.smart_search_suggestions],
            tool_choice="auto",
            temperature=0.0,
            response_format=OutputFormat,
            n=1,
            parallel_tool_calls=False
        )


        if response.choices[0].finish_reason == "stop":
            output = response.choices[0].message.parsed
            #Serialize the output to json
            output = output.model_dump()
            
            #delete "thinking" key
            output.pop("thinking")

            #response = output.response
            #logger.info(f"Providing Response. . . \n Response: {response} \n Recommended Prompts: {output.recommended_prompts_for_users} \n Recommended Urls: {output.recommended_urls}")
            return str(output), {} , {}
        elif response.choices[0].finish_reason == "tool_calls":
            tool_call = response.choices[0].message.tool_calls[0]
            args = json.loads(tool_call.function.arguments)
            thought = args["thought"]
            name = tool_call.function.name
            logger.info(f"Tools Calling. . . \n Thought: {thought} \n Tool: {name}")
            tool_result = self.tools_calling(name, args)

            #append tool message block
            messages.append(response.choices[0].message)

            #append tool result block
            messages.append(    
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_result
                }
            )
            #agentic loop
            return await self.forward(messages, room_id)
        else:
            return "Error: "+str(response.choices[0].finish_reason), {} , {}







