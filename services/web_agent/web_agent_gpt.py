import os
from dotenv import load_dotenv
from openai import AsyncAzureOpenAI
import asyncio
from shared.rag import RAG
from .gpt_tools import GPTTools
from tenacity import retry, stop_after_attempt, wait_random_exponential
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import json
import logging
import re
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

load_dotenv()

# Temporarily use Azure OpenAI credentials for testing
api_key = os.getenv('GPT_MINI_API_KEY')
endpoint = os.getenv('GPT_MINI_ENDPOINT') 
MODEL = "gpt-4.1-mini"  # Use deployment name for Azure OpenAI




class BranchLocation(BaseModel):
    """Pydantic model for branch location information."""
    branch_name: str
    coordinates: List[float]  # [lat, lng]
    address: Optional[str] = None
    map_url: Optional[str] = None
    package_url: Optional[str] = None
    original_index: Optional[int] = None

class recommended_urls(BaseModel):
    """Pydantic model for recommended urls."""
    url: str
    url_type: str

class EnhancedRecommendedUrl(BaseModel):
    """Enhanced Pydantic model for recommended urls with branch locations."""
    url: str
    type: str  # e.g., 'package_page', 'brand_page', 'category_page'
    branch_locations: Optional[List[BranchLocation]] = None
    # Keep backward compatibility
    url_type: Optional[str] = None

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
        self.system_prompt = open("services/web_agent/prompts/gpt.txt", "r").read()
        self.global_storage = global_storage
    
    def find_package_indices_by_url(self, url: str) -> List[int]:
        """
        Find package indices in package.csv that match the given URL
        """
        try:
            # Access package dataframe from global storage
            package_df = self.global_storage.knowledge_base
            if package_df is None:
                logger.warning("Package dataframe not found in global storage")
                return []
            
            # Look for matching URLs in the URL column
            matching_rows = package_df[package_df['URL'] == url]
            
            if len(matching_rows) > 0:
                # Return the dataframe indices
                indices = matching_rows.index.tolist()
                logger.info(f"Found {len(indices)} matching packages for URL: {url}")
                return indices
            else:
                logger.debug(f"No matching packages found for URL: {url}")
                return []
                
        except Exception as e:
            logger.error(f"Error finding packages for URL {url}: {e}")
            return []
    
    def find_branch_locations_by_indices(self, package_indices: List[int]) -> List[BranchLocation]:
        """
        Find all branch locations using package indices.
        Gets branch names from location column in CSV and coordinates from index_list.npy
        """
        if not package_indices:
            return []
        
        branch_locations = []
        
        try:
            # Access index_list from RAG object (for coordinates)
            index_list = self.rag.index_list
            if index_list is None:
                logger.warning("Index list not found in RAG object")
                return []
            
            # Access package CSV from global storage (for branch names)
            package_df = self.global_storage.knowledge_base
            if package_df is None:
                logger.warning("Package dataframe not found in global storage")
                return []
            
            # For each package index, get branch names and coordinates
            for package_index in package_indices:
                # Get branch names from location column
                package_row = package_df[package_df.index == package_index]
                if package_row.empty:
                    continue
                
                location_text = package_row['location'].iloc[0]
                branch_names = self.extract_branch_names_from_location(location_text)
                
                # Get coordinates from index_list for this package
                coordinates_list = []
                for entry in index_list:
                    if entry.get('index') == package_index:
                        coordinates_list.append({
                            'coordinates': entry.get('coor', []),
                            'address': entry.get('address', ''),
                            'map_url': entry.get('map_url', ''),
                            'package_url': entry.get('package_url', ''),
                        })
                
                # Combine branch names with coordinates (they should be aligned)
                for i in range(min(len(branch_names), len(coordinates_list))):
                    branch_location = BranchLocation(
                        branch_name=branch_names[i],
                        coordinates=coordinates_list[i]['coordinates'],
                        address=coordinates_list[i]['address'],
                        map_url=coordinates_list[i]['map_url'],
                        package_url=coordinates_list[i]['package_url'],
                        original_index=package_index
                    )
                    branch_locations.append(branch_location)
            
            # Remove duplicates based on branch_name and coordinates
            unique_branches = []
            seen = set()
            for branch in branch_locations:
                key = (branch.branch_name, tuple(branch.coordinates))
                if key not in seen:
                    seen.add(key)
                    unique_branches.append(branch)
            
            logger.info(f"Found {len(unique_branches)} unique branch locations for indices: {package_indices}")
            return unique_branches[:20]  # Limit to top 20 branches for performance
            
        except Exception as e:
            logger.error(f"Error finding branch locations: {e}")
            return []
    
    def extract_branch_names_from_location(self, location_text: str) -> List[str]:
        """
        Extract clean branch names from location column
        """
        if pd.isna(location_text):
            return []
        
        branch_names = []
        
        try:
            # Split by numbered entries (1. 2. 3. etc.)
            entries = re.split(r'\n\d+\.\s*', location_text)
            
            for entry in entries:
                if not entry.strip():
                    continue
                    
                # Extract the first line which contains the branch name
                lines = entry.strip().split('\n')
                if lines:
                    branch_name = lines[0].strip()
                    # Remove numbering if it exists at the start
                    branch_name = re.sub(r'^\d+\.\s*', '', branch_name)
                    if branch_name:
                        branch_names.append(branch_name)
            
            logger.debug(f"Extracted {len(branch_names)} branch names from location text")
            return branch_names
            
        except Exception as e:
            logger.warning(f"Failed to extract branch names from location: {str(e)}")
            return []
    
    def enrich_recommended_urls(self, recommended_urls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Post-process recommended URLs to add branch location information.
        This method enriches URLs with branch data without requiring LLM calls.
        """
        enriched_urls = []
        
        logger.info("Starting URL enrichment process...")
        
        for i, url_item in enumerate(recommended_urls):
            logger.debug(f"Processing URL {i+1}: {url_item.get('url', 'Unknown')}")
            
            # Create enhanced URL item
            enriched_item = {
                'url': url_item.get('url', ''),
                'type': url_item.get('url_type', 'package_page'),
                'branch_locations': [],
                'url_type': url_item.get('url_type', 'package_page')  # Keep backward compatibility
            }
            
            try:
                # Only enrich package URLs (not category or brand pages)
                if 'hdmall.co.th' in enriched_item['url'] and enriched_item['type'] == 'package_page':
                    # Step 1: Find package indices in CSV
                    package_indices = self.find_package_indices_by_url(enriched_item['url'])
                    
                    if package_indices:
                        # Step 2: Find branch locations using those indices
                        branch_locations = self.find_branch_locations_by_indices(package_indices)
                        enriched_item['branch_locations'] = [branch.model_dump() for branch in branch_locations]
                        
                        logger.info(f"✅ Enriched URL {i+1} with {len(branch_locations)} branch locations")
                    else:
                        logger.debug(f"❌ No branch locations found for URL {i+1}")
                else:
                    logger.debug(f"⏭️ Skipping enrichment for non-package URL {i+1}")
                    
            except Exception as e:
                logger.warning(f"Failed to enrich URL {enriched_item['url']}: {e}")
                # Keep original URL if enrichment fails
                pass
            
            enriched_urls.append(enriched_item)
        
        logger.info(f"URL enrichment complete. Processed {len(enriched_urls)} URLs")
        return enriched_urls
    
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
            
            # Post-process recommended URLs to add branch location information
            if output.get('recommended_urls'):
                try:
                    logger.info("Applying URL enrichment post-processing...")
                    enriched_urls = self.enrich_recommended_urls(output['recommended_urls'])
                    output['recommended_urls'] = enriched_urls
                    logger.info("URL enrichment completed successfully")
                except Exception as e:
                    logger.error(f"URL enrichment failed: {e}")
                    # Continue with original URLs if enrichment fails
                    logger.info("Continuing with original URLs")
            
            #delete "thinking" key
            output.pop("thinking")

            #response = output.response
            #logger.info(f"Providing Response. . . \n Response: {response} \n Recommended Prompts: {output.recommended_prompts_for_users} \n Recommended Urls: {output.recommended_urls}")
            return output
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
            return {"error": str(response.choices[0].finish_reason)}







