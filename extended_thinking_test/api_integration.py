"""
API Integration for Production Sonnet 4 Agent
============================================
This file provides a drop-in replacement for the existing bot in api_routes.py
to enable testing of Sonnet 4 with interleaved thinking in production.

Usage:
1. Import this class instead of the existing JibAI in api_routes.py
2. Replace the bot initialization line
3. All existing API routes will work seamlessly

Integration Example:
-------------------
# In api_routes.py, replace:
# from bot import JibAI
# with:
# from extended_thinking_test.api_integration import ProductionJibAI as JibAI

# Then use normally:
# bot = JibAI(global_storage)
# raw_response = await bot.forward(messages, room_id, last_query)
"""

import sys
import os
from typing import List, Dict, Tuple, Any
import logging

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from production_sonnet4_agent import ProductionSonnet4Agent

logger = logging.getLogger(__name__)

class ProductionJibAI:
    """
    Production Jib AI with Sonnet 4 Interleaved Thinking
    
    This class provides a drop-in replacement for the existing JibAI bot
    with enhanced Sonnet 4 capabilities including interleaved thinking.
    
    Features:
    - Sonnet 4 Extended/Interleaved Thinking
    - Real tools integration (retrieval, cart, handover_to_cx, etc.)
    - Smart SQL search with retry logic
    - Production-ready system prompt
    - Parallel tool calling
    - Full API compatibility with existing routes
    """
    
    def __init__(self, global_storage):
        """Initialize the Production Jib AI with Sonnet 4 agent"""
        self.global_storage = global_storage
        self.agent = ProductionSonnet4Agent(global_storage)
        logger.info("🎯 Production Jib AI with Sonnet 4 initialized")
    
    async def forward(self, messages: List[Dict], room_id: str, last_query: str = "") -> Tuple[Dict, Dict, Dict]:
        """
        Main forward method compatible with existing api_routes.py
        
        Args:
            messages: List of message dictionaries
            room_id: Room/conversation ID
            last_query: Last user query (optional)
            
        Returns:
            Tuple of (chat_response, token_dict, thought_dict)
        """
        try:
            # Use the agent's forward method which is designed for API compatibility
            return await self.agent.forward(messages, room_id, last_query)
            
        except Exception as e:
            logger.error(f"Error in ProductionJibAI.forward: {str(e)}")
            # Return error response in expected format
            error_response = {"text": f"Error: {str(e)}"}
            return error_response, {}, {}
    
    # Additional methods for backward compatibility if needed
    
    def get_agent_info(self) -> Dict[str, Any]:
        """Get information about the current agent"""
        return {
            "agent_type": "ProductionSonnet4Agent",
            "model": "claude-sonnet-4-20250514",
            "features": [
                "interleaved_thinking",
                "parallel_tool_calling", 
                "real_tools_integration",
                "smart_sql_search",
                "production_ready"
            ],
            "tools": [
                "retrieval",
                "sql_search", 
                "cart",
                "handover_to_cx",
                "handover_to_bk",
                "handover_asap"
            ]
        }
    
    async def health_check(self) -> Dict[str, str]:
        """Health check endpoint for the agent"""
        try:
            # Quick test of the agent
            test_result = await self.agent.chat(
                "สวัสดีค่ะ", 
                use_interleaved_thinking=True
            )
            
            return {
                "status": "healthy",
                "agent": "ProductionSonnet4Agent",
                "test_iterations": str(test_result.get("iterations", 0)),
                "thinking_blocks": str(len(test_result.get("thinking", []))),
                "tools_available": str(len(self.agent._get_real_tools()))
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }

# Alternative class name for easier migration
class JibAI(ProductionJibAI):
    """Alias for ProductionJibAI to enable seamless migration"""
    pass

# Utility function for API routes integration
def create_production_bot(global_storage) -> ProductionJibAI:
    """
    Factory function to create a production bot instance
    
    Usage in api_routes.py:
    from extended_thinking_test.api_integration import create_production_bot
    bot = create_production_bot(global_storage)
    """
    return ProductionJibAI(global_storage)

# Migration instructions
MIGRATION_INSTRUCTIONS = """
🔄 MIGRATION INSTRUCTIONS FOR api_routes.py
==========================================

To switch to the Production Sonnet 4 Agent, make this simple change:

BEFORE:
-------
from bot import JibAI

bot = JibAI(global_storage)
raw_response = await bot.forward(messages, room_id, last_query)

AFTER:
------
from extended_thinking_test.api_integration import ProductionJibAI as JibAI

bot = JibAI(global_storage)
raw_response = await bot.forward(messages, room_id, last_query)

That's it! All existing functionality will work seamlessly with enhanced Sonnet 4 capabilities.

🚀 NEW FEATURES ENABLED:
- Interleaved thinking between tool calls
- Parallel tool execution for independent operations
- Enhanced reasoning with extended thinking
- Real tools integration with smart retry logic
- Production-ready system prompts
- Advanced SQL search with category masking

🔧 DEBUGGING:
- Add --thinking-mode=extended for basic extended thinking
- Use --thinking-mode=interleaved for full interleaved thinking (default)
- Check logs for detailed thinking process and tool execution
"""

if __name__ == "__main__":
    print(MIGRATION_INSTRUCTIONS) 