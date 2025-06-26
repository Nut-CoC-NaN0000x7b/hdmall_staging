import os
import sys
import asyncio
import json
import re
import logging
from dotenv import load_dotenv
from datetime import datetime
from typing import Dict, List, Any, Optional
from anthropic import AsyncAnthropicBedrock

# Add parent directory to path to import from main codebase
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging with timestamps
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

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

class TestTools:
    """Collection of test tools for Sonnet 4 agent"""
    
    @staticmethod
    def get_calculator_tool():
        """Calculator tool for mathematical operations"""
        return {
            "name": "calculator",
            "description": "Perform mathematical calculations. Supports basic arithmetic, advanced math functions, and scientific calculations.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Mathematical expression to evaluate (e.g., '2 + 3 * 4', 'sqrt(16)', 'sin(pi/2)')"
                    },
                    "reasoning": {
                        "type": "string", 
                        "description": "Your reasoning for why you need this calculation"
                    }
                },
                "required": ["expression", "reasoning"]
            }
        }
    
    @staticmethod
    def get_weather_tool():
        """Weather checking tool (dummy implementation)"""
        return {
            "name": "weather_check",
            "description": "Get current weather information for a specified location.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City name or location to check weather for"
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Your reasoning for checking the weather"
                    }
                },
                "required": ["location", "reasoning"]
            }
        }
    
    @staticmethod
    def get_sql_search_tool():
        """Text-to-SQL search tool for the knowledge base"""
        return {
            "name": "sql_search",
            "description": """Search the knowledge base using pandas queries with automatic category masking.
            
            Use this tool when users ask for:
            - Specific filtering criteria (e.g., "cheapest packages", "most expensive")
            - Sorting packages by attributes (e.g., "sort by price", "sort by rating")
            - Limiting results (e.g., "top 5", "first 10")
            - Category-specific searches (e.g., "HPV vaccines under 15000 baht")
            
            Query Syntax (use pandas syntax, NOT raw SQL):
            - `kb[kb['Cash Price'] < 5000].head(10)` - Find packages under 5000 baht
            - `kb.sort_values('Cash Price').head(5)` - Find 5 cheapest packages
            - `kb[kb['Brand'].str.contains('Bangkok', case=False, na=False)]` - Find packages from Bangkok hospitals
            """,
            "input_schema": {
                "type": "object",
                "properties": {
                    "sql_query": {
                        "type": "string",
                        "description": "The pandas query to search the knowledge base. Use pandas syntax (e.g., kb[kb['Cash Price'] < 5000]) NOT raw SQL."
                    },
                    "category_tag": {
                        "type": "string",
                        "description": "Category to filter by. Choose from categories like 'ฉีดวัคซีน HPV (HPV Vaccine)', 'โปรแกรมตรวจสุขภาพ (Health Checkup)', etc. Leave empty if not specific."
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Your reasoning for this search query and what you expect to find"
                    }
                },
                "required": ["sql_query", "reasoning"]
            }
        }
    
    @staticmethod
    def get_dummy_retrieval_tool():
        """Dummy retrieval tool for testing"""
        return {
            "name": "retrieval",
            "description": "Search for healthcare packages and services in the HDmall database.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "search_keyword": {
                        "type": "string",
                        "description": "Search keyword for packages (e.g., 'HPV vaccine', 'health checkup')"
                    },
                    "preferred_area": {
                        "type": "string", 
                        "description": "Preferred location/area (e.g., 'Bangkok', 'Chiang Mai')"
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Your reasoning for this search"
                    }
                },
                "required": ["search_keyword", "reasoning"]
            }
        }

class Sonnet4Agent:
    def __init__(self):
        """Initialize Sonnet 4 agent with extended thinking capabilities"""
        self.client = AsyncAnthropicBedrock(
            aws_access_key=Config.AWS_ACCESS_KEY,
            aws_secret_key=Config.AWS_SECRET_KEY,
            aws_region=Config.REGION
        )
        
        # Load test tools
        self.test_tools = TestTools()
        
        # System prompt for testing
        self.system_prompt = self._create_system_prompt()
    
    def _create_system_prompt(self):
        """Create system prompt for testing Sonnet 4 capabilities"""
        return """You are an intelligent AI assistant with extended thinking capabilities, including interleaved thinking that allows you to reason between tool calls. You have access to several tools to help users with various tasks.

IMPORTANT INSTRUCTIONS:
1. Think through problems step by step using your built-in reasoning
2. Use tools when necessary to gather information or perform calculations
3. For maximum efficiency, whenever you need to perform multiple independent operations, invoke all relevant tools simultaneously rather than sequentially
4. With interleaved thinking, you can reason about tool results before deciding on next actions
5. After receiving tool results, carefully reflect on their quality and determine optimal next steps before proceeding. Use your thinking to plan and iterate based on this new information, and then take the best next action
6. Always explain your reasoning when using tools
7. Provide clear, helpful responses based on the information gathered

Available tools:
- calculator: For mathematical operations
- weather_check: For weather information
- sql_search: For searching the healthcare package database (dummy data)
- retrieval: For finding specific healthcare packages (dummy data)

Your goal is to be helpful, accurate, and demonstrate sophisticated reasoning capabilities, including the ability to think between tool calls when using interleaved thinking and to maximize efficiency through parallel tool execution when appropriate.

Current date and time: {current_time}
"""

    async def _call_claude(self, messages: List[Dict], tools: List[Dict] = None, use_thinking: bool = True, use_interleaved_thinking: bool = True):
        """Make a call to Claude with optional thinking and tools"""
        kwargs = {
            "model": Config.MODEL["sonnet_4"],
            "max_tokens": Config.MAX_TOKENS,
            "temperature": 1.0 if use_thinking else Config.TEMP,  # Temperature must be 1 when thinking is enabled
            "system": self.system_prompt.format(current_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            "messages": messages
        }
        
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = {"type": "auto"}
        
        if use_thinking:
            kwargs["thinking"] = {
                "type": "enabled",
                "budget_tokens": Config.MAX_REASONING_TOKENS
            }
        
        # Add interleaved thinking beta header
        if use_interleaved_thinking:
            kwargs["extra_headers"] = {
                "anthropic-beta": "interleaved-thinking-2025-05-14"
            }
        
        return await self.client.messages.create(**kwargs)
    
    def _execute_tool(self, tool_name: str, tool_input: Dict) -> str:
        """Execute a tool and return the result"""
        try:
            if tool_name == "calculator":
                return self._execute_calculator(tool_input)
            elif tool_name == "weather_check":
                return self._execute_weather(tool_input)
            elif tool_name == "sql_search":
                return self._execute_sql_search(tool_input)
            elif tool_name == "retrieval":
                return self._execute_retrieval(tool_input)
            else:
                return f"Unknown tool: {tool_name}"
        except Exception as e:
            return f"Error executing {tool_name}: {str(e)}"
    
    
    def _execute_calculator(self, tool_input: Dict) -> str:
        """Execute calculator tool"""
        import math
        
        expression = tool_input["expression"]
        reasoning = tool_input["reasoning"]
        
        try:
            # Safe evaluation with math functions
            allowed_names = {
                k: v for k, v in math.__dict__.items() if not k.startswith("__")
            }
            allowed_names.update({
                "abs": abs, "round": round, "min": min, "max": max,
                "sum": sum, "len": len, "sqrt": math.sqrt, "pi": math.pi,
                "e": math.e, "sin": math.sin, "cos": math.cos, "tan": math.tan,
                "log": math.log, "log10": math.log10, "exp": math.exp
            })
            
            result = eval(expression, {"__builtins__": {}}, allowed_names)
            return f"Calculation: {expression} = {result}\nReasoning: {reasoning}"
        except Exception as e:
            return f"Error in calculation '{expression}': {str(e)}\nReasoning: {reasoning}"
    
    def _execute_weather(self, tool_input: Dict) -> str:
        """Execute weather tool (dummy implementation)"""
        location = tool_input["location"]
        reasoning = tool_input["reasoning"]
        
        # Dummy weather data
        weather_data = {
            "Bangkok": {"temp": "32°C", "condition": "Sunny", "humidity": "65%"},
            "Chiang Mai": {"temp": "28°C", "condition": "Partly Cloudy", "humidity": "70%"},
            "Phuket": {"temp": "30°C", "condition": "Rainy", "humidity": "80%"}
        }
        
        weather = weather_data.get(location, {"temp": "25°C", "condition": "Clear", "humidity": "60%"})
        
        return f"Weather in {location}:\nTemperature: {weather['temp']}\nCondition: {weather['condition']}\nHumidity: {weather['humidity']}\nReasoning: {reasoning}"
    
    def _execute_sql_search(self, tool_input: Dict) -> str:
        """Execute SQL search tool (dummy implementation)"""
        sql_query = tool_input["sql_query"]
        category_tag = tool_input.get("category_tag", "")
        reasoning = tool_input["reasoning"]
        
        # Dummy SQL search results
        dummy_results = """
Package Name                    | Brand           | Cash Price | Location
HPV Vaccine (4 doses)          | Bangkok Hospital| 12,000     | Bangkok
HPV Vaccine (3 doses)          | Bumrungrad      | 15,000     | Bangkok  
Health Checkup Premium         | BAAC Hospital   | 4,500      | Bangkok
Basic Health Screening         | Samitivej       | 2,800      | Bangkok
Dental Checkup Package         | Dent Hospital   | 1,500      | Bangkok
"""
        
        return f"SQL Search Results for query: {sql_query}\nCategory: {category_tag}\n{dummy_results}\nReasoning: {reasoning}"
    
    def _execute_retrieval(self, tool_input: Dict) -> str:
        """Execute retrieval tool (dummy implementation)"""
        search_keyword = tool_input["search_keyword"]
        preferred_area = tool_input.get("preferred_area", "")
        reasoning = tool_input["reasoning"]
        
        # Dummy retrieval results
        dummy_packages = [
            f"Package: HPV Vaccine Premium - {search_keyword} related service",
            f"Location: {preferred_area if preferred_area else 'Bangkok'}",
            f"Price: 12,000 - 18,000 THB",
            f"Provider: Bangkok Hospital, Bumrungrad",
            f"Description: Comprehensive {search_keyword} package with consultation"
        ]
        
        return f"Retrieval Results:\n" + "\n".join(dummy_packages) + f"\nReasoning: {reasoning}"
    
    async def chat(self, user_message: str, conversation_history: List[Dict] = None, use_interleaved_thinking: bool = True) -> Dict:
        """Main chat interface with extended thinking"""
        if conversation_history is None:
            conversation_history = []
        
        # Add user message
        conversation_history.append({
            "role": "user",
            "content": user_message
        })
        
        # Get available tools
        available_tools = [
            self.test_tools.get_calculator_tool(),
            self.test_tools.get_weather_tool(),
            self.test_tools.get_sql_search_tool(),
            self.test_tools.get_dummy_retrieval_tool(),
        ]
        
        max_iterations = 5
        iteration = 0
        tools_used = []
        all_thinking_blocks = []
        
        while iteration < max_iterations:
            iteration += 1
            if iteration > 1:
                logger.info("─" * 80)
            logger.info(f"🚀 [ITERATION-{iteration}] Invoking Sonnet-4 with {'Interleaved' if use_interleaved_thinking else 'Extended'} Thinking Mode")
            
            # Call Claude with thinking enabled
            response = await self._call_claude(
                messages=conversation_history,
                tools=available_tools,
                use_thinking=True,
                use_interleaved_thinking=use_interleaved_thinking
            )
            
            # Extract thinking content and collect all thinking blocks
            thinking_blocks_this_turn = []
            text_content = None
            tool_use_blocks = []
            
            for content_block in response.content:
                if content_block.type == "thinking":
                    thinking_blocks_this_turn.append(content_block)
                    all_thinking_blocks.append(content_block.thinking)
                    logger.info(f"💭 [THINKING-{iteration}] {'Interleaved' if use_interleaved_thinking else 'Extended'} Reasoning:")
                    logger.info(f"   {content_block.thinking}")
                elif content_block.type == "text":
                    text_content = content_block.text
                elif content_block.type == "tool_use":
                    tool_use_blocks.append(content_block)
            
            # Check stop reason
            if response.stop_reason == "end_turn":
                # No tools used, return response - preserve the full response structure
                conversation_history.append({
                    "role": "assistant",
                    "content": response.content
                })
                
                logger.info(f"✅ [COMPLETION] Task completed in {iteration} iterations with {len(tools_used)} tool calls")
                return {
                    "response": text_content,
                    "thinking": all_thinking_blocks,
                    "iterations": iteration,
                    "tools_used": tools_used,
                    "conversation_history": conversation_history,
                    "stop_reason": response.stop_reason
                }
            
            elif response.stop_reason == "tool_use":
                # Tools were used - handle with interleaved thinking support
                if use_interleaved_thinking:
                    # Log tool execution strategy
                    tool_count = len(tool_use_blocks)
                    if tool_count > 1:
                        logger.info(f"⚡ [PARALLEL-EXECUTION] Executing {tool_count} tools simultaneously")
                    else:
                        logger.info(f"🔄 [SEQUENTIAL-EXECUTION] Executing single tool")
                    
                    # For interleaved thinking, we need to preserve the exact structure
                    # including thinking blocks that may appear before tool calls
                    assistant_content = []
                    for idx, content in enumerate(response.content):
                        if content.type == "thinking":
                            assistant_content.append(content)
                        elif content.type == "tool_use":
                            assistant_content.append(content)
                            # Execute tool for tracking
                            tool_result = self._execute_tool(content.name, content.input)
                            tools_used.append({
                                "name": content.name,
                                "input": content.input,
                                "result": tool_result
                            })
                            logger.info(f"🛠️  [TOOL-{idx+1}/{tool_count}] {content.name}")
                            logger.info(f"📥 [INPUT] {content.input}")
                            logger.info(f"📤 [OUTPUT] {tool_result[:150]}{'...' if len(tool_result) > 150 else ''}")
                        elif content.type == "text":
                            assistant_content.append(content)
                    
                    # Add assistant message with thinking and tool calls
                    conversation_history.append({
                        "role": "assistant",
                        "content": assistant_content
                    })
                    
                    # Add tool results for each tool used
                    for content in response.content:
                        if content.type == "tool_use":
                            tool_result = self._execute_tool(content.name, content.input)
                            conversation_history.append({
                                "role": "user",
                                "content": [{
                                    "type": "tool_result",
                                    "tool_use_id": content.id,
                                    "content": tool_result
                                }]
                            })
                else:
                    # Original non-interleaved handling
                    assistant_message = {"role": "assistant", "content": response.content}
                    
                    tool_count = len(tool_use_blocks)
                    if tool_count > 1:
                        logger.info(f"⚡ [PARALLEL-EXECUTION] Executing {tool_count} tools simultaneously")
                    else:
                        logger.info(f"🔄 [SEQUENTIAL-EXECUTION] Executing single tool")
                    
                    for idx, content in enumerate(response.content):
                        if content.type == "tool_use":
                            # Execute tool
                            tool_result = self._execute_tool(content.name, content.input)
                            tools_used.append({
                                "name": content.name,
                                "input": content.input,
                                "result": tool_result
                            })
                            
                            logger.info(f"🛠️  [TOOL-{idx+1}/{tool_count}] {content.name}")
                            logger.info(f"📥 [INPUT] {content.input}")
                            logger.info(f"📤 [OUTPUT] {tool_result[:150]}{'...' if len(tool_result) > 150 else ''}")
                    
                    # Add assistant message with tool calls
                    conversation_history.append(assistant_message)
                    
                    # Add tool results
                    for content in response.content:
                        if content.type == "tool_use":
                            tool_result = self._execute_tool(content.name, content.input)
                            conversation_history.append({
                                "role": "user",
                                "content": [
                                    {
                                        "type": "tool_result",
                                        "tool_use_id": content.id,
                                        "content": tool_result
                                    }
                                ]
                            })
                
                # Continue the conversation
                continue
            
            else:
                # Unexpected stop reason
                logger.warning(f"Unexpected stop reason: {response.stop_reason}")
                break
        
        return {
            "response": "Maximum iterations reached",
            "thinking": all_thinking_blocks,
            "iterations": iteration,
            "tools_used": tools_used,
            "conversation_history": conversation_history,
            "stop_reason": "max_iterations"
        }

# Test queries for experimentation
TEST_QUERIES = [
    "What's the weather like in Bangkok and calculate the average temperature if it's been 32°C, 30°C, and 35°C for the past 3 days?",
    "Find me the cheapest HPV vaccines under 15,000 baht in Bangkok area",
    "I need health checkup packages under 5000 baht. Can you search for the top 5 cheapest ones?",
    "Calculate the compound interest on 100,000 baht at 5% annual rate for 3 years, then find health packages in that price range",
    "What's the weather in Chiang Mai? Also, find dental services there under 3000 baht"
]

async def run_tests(use_interleaved_thinking: bool = True):
    """Run test queries to understand Sonnet 4 response structure"""
    thinking_type = "Interleaved Thinking" if use_interleaved_thinking else "Extended Thinking"
    print(f"🚀 Starting Sonnet 4 {thinking_type} Tests\n")
    
    # Initialize agent
    agent = Sonnet4Agent()
    
    for i, query in enumerate(TEST_QUERIES, 1):
        print(f"\n{'='*60}")
        print(f"🧪 TEST {i} ({thinking_type}): {query}")
        print('='*60)
        
        try:
            result = await agent.chat(query, use_interleaved_thinking=use_interleaved_thinking)
            
            print(f"✅ Response: {result['response']}")
            print(f"🔄 Iterations: {result['iterations']}")
            print(f"🔧 Tools Used: {len(result['tools_used'])}")
            print(f"🛑 Stop Reason: {result['stop_reason']}")
            
            if result['thinking']:
                if isinstance(result['thinking'], list):
                    print(f"🧠 Thinking Blocks: {len(result['thinking'])}")
                    for idx, thinking in enumerate(result['thinking'][:2]):  # Show first 2 blocks
                        print(f"   Block {idx+1}: {thinking[:200]}...")
                        if idx >= 1:  # Limit to 2 blocks for readability
                            remaining = len(result['thinking']) - 2
                            if remaining > 0:
                                print(f"   ... and {remaining} more thinking blocks")
                            break
                else:
                    print(f"🧠 Thinking Process:\n{result['thinking'][:300]}...")
            
            for tool in result['tools_used']:
                print(f"   - {tool['name']}: {tool['input']}")
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            logger.error(f"Test {i} failed: {e}")
        
        print("\n" + "-"*40)
    
    print(f"\n{'='*60}")
    print("🏁 Tests completed!")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Sonnet 4 Extended/Interleaved Thinking")
    parser.add_argument(
        "--thinking-mode", 
        choices=["interleaved", "extended"], 
        default="interleaved",
        help="Choose thinking mode: 'interleaved' for interleaved thinking, 'extended' for basic extended thinking"
    )
    args = parser.parse_args()
    
    use_interleaved = args.thinking_mode == "interleaved"
    asyncio.run(run_tests(use_interleaved_thinking=use_interleaved)) 