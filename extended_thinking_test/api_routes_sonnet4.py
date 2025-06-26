# api_routes_sonnet4.py - Modified for Sonnet 4 Integration
from utils import remove_markdown_elements, update_urls_with_utm, post_data, shorten_url
from fastapi import APIRouter, HTTPException
from api_models import ChatRequest
from src.RAG import RAG
from ads_handler.ads_agent import AdsAgent

# 🚀 SONNET 4 INTEGRATION - Replace the original bot import
# from bot import JibAI  # Original
from extended_thinking_test.api_integration import ProductionJibAI as JibAI  # Sonnet 4 Version

from pydantic import BaseModel
from globals import global_storage
from dotenv import load_dotenv
import os
import time
import re
import json
import asyncio
from typing import Optional

class AdsRequest(BaseModel):
    thread_name: str
    conversation: list[dict]

# Global instances to avoid recreation on every request
_rag_instance: Optional[RAG] = None
_ads_agent_instance: Optional[AdsAgent] = None

def get_rag_instance() -> RAG:
    """Get or create singleton RAG instance"""
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = RAG(global_storage)
    return _rag_instance

def get_ads_agent_instance() -> AdsAgent:
    """Get or create singleton AdsAgent instance"""
    global _ads_agent_instance
    if _ads_agent_instance is None:
        _ads_agent_instance = AdsAgent(global_storage)
    return _ads_agent_instance

router = APIRouter()
load_dotenv()
#python3 -m uvicorn __init__:create_app --factory --reload
WORKSPACE_ID = os.getenv('WORKSPACE_ID')
PRIMARY_KEY = os.getenv('PRIMARY_KEY')
SHORT_IO_API_KEY = os.getenv('SHORT_IO_API_KEY')

@router.get("/")
async def hello_world():
    return {"message": "Hello from Sonnet 4 Agent! 🚀🧠"}

@router.get("/agent-info")
async def get_agent_info():
    """Get information about the current agent"""
    try:
        bot = JibAI(global_storage)
        return bot.get_agent_info()
    except Exception as e:
        return {"error": str(e)}

@router.get("/health")
async def health_check():
    """Health check endpoint for the Sonnet 4 agent"""
    try:
        bot = JibAI(global_storage)
        return await bot.health_check()
    except Exception as e:
        return {"status": "error", "error": str(e)}

@router.post("/chat")
async def chat_handler(chat_request: ChatRequest):
    """API to chat with the Sonnet 4 Agent with interleaved thinking."""
    room_id = chat_request.room_id
    
    # Measure time for bot response
    start_time = time.time()
    messages = [message.model_dump() for message in chat_request.messages]
    last_query = str(messages[-1])
    
    # Check for HDExpress routing
    if 'hdexpress' in last_query.lower() or 'hd express' in last_query.lower():
        return {"text": "QISCUS_INTEGRATION_TO_BK", "image": []}
    
    print(f"🚀 Using Sonnet 4 Agent with Interleaved Thinking")
    print(f"Global storage: {global_storage}")
    
    # 🧠 Initialize Sonnet 4 Agent
    bot = JibAI(global_storage)
    
    # 🔄 Get response with interleaved thinking
    raw_response = await bot.forward(messages, room_id, last_query)
    chat_resp, token_dict, thought_dict = raw_response
    
    end_time = time.time()
    
    # Enhanced logging for Sonnet 4
    print(f"⏱️ Response time: {end_time - start_time:.2f} seconds ({(end_time - start_time)/60:.2f} minutes)")
    print(f"🧠 Thinking blocks: {thought_dict.get('thinking_blocks', 0)}")
    print(f"🔧 Tools used: {thought_dict.get('tools_used', 0)}")
    print(f"🔄 Iterations: {thought_dict.get('iterations', 0)}")
    
    # Create enhanced log entries for Sonnet 4
    LOG_TYPE_USAGE = "Sonnet4TokenUsage"  
    LOG_TYPE_COT = "Sonnet4InterleaveThinking"
    
    # Enhanced token tracking
    enhanced_token_dict = {
        **token_dict,
        "response_time_seconds": end_time - start_time,
        "agent_type": "ProductionSonnet4Agent",
        "interleaved_thinking": True
    }
    
    # Enhanced thought tracking  
    enhanced_thought_dict = {
        **thought_dict,
        "response_time_seconds": end_time - start_time,
        "room_id": room_id
    }
    
    # Log the usage and thoughts
    try:
        post_data(WORKSPACE_ID, PRIMARY_KEY, LOG_TYPE_USAGE, [enhanced_token_dict])
        post_data(WORKSPACE_ID, PRIMARY_KEY, LOG_TYPE_COT, [enhanced_thought_dict])
    except Exception as e:
        print(f"⚠️ Logging error: {e}")
    
    # Extract response text
    try:
        out = chat_resp['text']
        print(f"✅ Response: {out[:200]}{'...' if len(out) > 200 else ''}")
    except:
        out = chat_resp

    # URL processing with HDmall parameters
    url_pattern = r'\(?https?://(?:www\.)?hdmall\.co\.th/[^\s<>"\']+\)?'

    def append_utm(match):
        url = match.group(0)
        # Remove wrapping parentheses if URL is wrapped like (URL)
        if url.startswith('(') and url.endswith(')'):
            url = url[1:-1]
        # Remove any remaining single parentheses
        url = url.replace('(', '').replace(')', '')
        
        if "cart" in url:
            params = "?openExternalBrowser=1&ai-id=hdmall-sonnet4&hdAd=1"
        else:
            params = "?openExternalBrowser=1&ai-id=hdmall-sonnet4&hdAd=1&branch=1"
        
        # Check if URL already has query parameters
        if '?' in url:
            print(f"📎 URL already has query parameters: {url}")
            params = params.replace('?', '&')
            extended_url = url + params
            try:
                shortened_url = shorten_url(SHORT_IO_API_KEY, extended_url)
                return shortened_url
            except:
                return extended_url
        else:
            print(f"📎 URL processing: {url}")
            extended_url = url + params
            try:
                shortened_url = shorten_url(SHORT_IO_API_KEY, extended_url)
                return shortened_url
            except:
                return extended_url

    # Process URLs and clean markdown
    updated_out = re.sub(url_pattern, append_utm, out)
    updated_out = remove_markdown_elements(updated_out)
    
    try:
        chat_resp['text'] = updated_out
        print(f"📤 Final response: {updated_out[:200]}{'...' if len(updated_out) > 200 else ''}")
        print(f"📤 Final response structure: {chat_resp}")
        return chat_resp
    except:
        # Fallback if chat_resp is not a dict (shouldn't happen with new structure)
        print(f"📤 Fallback - returning text only: {updated_out[:200]}{'...' if len(updated_out) > 200 else ''}")
        return {"text": updated_out, "image": []}

# Additional Sonnet 4 specific endpoints

@router.post("/chat/debug")
async def chat_debug_handler(chat_request: ChatRequest):
    """Debug endpoint that returns detailed information about the Sonnet 4 response"""
    room_id = chat_request.room_id
    messages = [message.model_dump() for message in chat_request.messages]
    last_query = str(messages[-1])
    
    bot = JibAI(global_storage)
    raw_response = await bot.forward(messages, room_id, last_query)
    chat_resp, token_dict, thought_dict = raw_response
    
    return {
        "response": chat_resp,
        "token_usage": token_dict,
        "thinking_info": thought_dict,
        "agent_info": bot.get_agent_info()
    }

@router.post("/ads")
async def ads_handler(ads_request: AdsRequest):
    """Handle ads requests (unchanged from original)"""
    thread_name = ads_request.thread_name
    conversation = ads_request.conversation
    
    ads_agent = get_ads_agent_instance()
    ad_resp = ads_agent.forward(conversation, thread_name)
    
    return {"text": ad_resp}

# 🚀 Sonnet 4 Performance Monitoring
_performance_stats = {
    "total_requests": 0,
    "total_thinking_blocks": 0,
    "total_tools_used": 0,
    "average_response_time": 0.0
}

@router.get("/stats")
async def get_performance_stats():
    """Get performance statistics for the Sonnet 4 agent"""
    return _performance_stats

# Test endpoint for Sonnet 4 capabilities
@router.post("/test-sonnet4")
async def test_sonnet4_capabilities():
    """Test endpoint to validate Sonnet 4 capabilities"""
    test_queries = [
        "สวัสดีค่ะ",
        "สนใจวัคซีน HPV ราคาไม่เกิน 15,000 บาท",
        "หาแพคเกจตรวจสุขภาพ ราคาถูกที่สุด 5 อันดับแรก"
    ]
    
    results = []
    bot = JibAI(global_storage)
    
    for query in test_queries:
        try:
            start_time = time.time()
            result = await bot.agent.chat(query, use_interleaved_thinking=True)
            end_time = time.time()
            
            results.append({
                "query": query,
                "success": True,
                "response_time": end_time - start_time,
                "iterations": result.get("iterations", 0),
                "thinking_blocks": len(result.get("thinking", [])),
                "tools_used": len(result.get("tools_used", [])),
                "response_preview": result.get("response", "")[:100]
            })
        except Exception as e:
            results.append({
                "query": query,
                "success": False,
                "error": str(e)
            })
    
    return {
        "test_results": results,
        "agent_info": bot.get_agent_info()
    } 