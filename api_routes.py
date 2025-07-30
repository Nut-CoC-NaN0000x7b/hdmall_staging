# api_routes.py - Centralized API Router for Jib's Brain Architecture
from shared.utils import remove_markdown_elements, update_urls_with_utm, post_data, shorten_url
from shared.models import ChatRequest
from shared.rag import RAG
from services.ads_handler.ads_agent import AdsAgent
from services.jib_ai.jib_ai_bot import JibAI  # Main Sonnet 4 service
from services.dr_jib.dr_jib_service import DrJib  # Medical RAG service
from services.web_agent.web_agent_gpt import GPTBot  # Web intelligence
#TODO import summarization bot
from services.summarization.summarization_service import process_slack_event
from services.co_pilot.co_pilot_service import co_pilot_run
from fastapi import FastAPI, APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from globals import global_storage
from dotenv import load_dotenv
import os
import time
import re
import asyncio
import logging
from typing import Optional
from memory_monitor import memory_monitor, memory_check_decorator

# Load environment variables
load_dotenv()

# Environment configuration
WORKSPACE_ID = os.getenv('WORKSPACE_ID')
PRIMARY_KEY = os.getenv('PRIMARY_KEY')
SHORT_IO_API_KEY = os.getenv('SHORT_IO_API_KEY')

logger = logging.getLogger(__name__)

# Legacy models for backward compatibility
class SearchRequest(BaseModel):
    query: str

class AdsRequest(BaseModel):
    thread_name: str
    conversation: list[dict]

# Summarization models
class SlackEvent(BaseModel):
    type: Optional[str] = None
    challenge: Optional[str] = None
    event: Optional[dict] = None

# Co-pilot models
class CoPilotRequest(BaseModel):
    messages: list[dict]

# Global instances to avoid recreation on every request
_rag_instance: Optional[RAG] = None
_ads_agent_instance: Optional[AdsAgent] = None
_gpt_bot_instance: Optional[GPTBot] = None
_dr_jib_instance: Optional[DrJib] = None

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

def get_gpt_bot_instance() -> GPTBot:
    """Get or create singleton GPTBot instance"""
    global _gpt_bot_instance
    if _gpt_bot_instance is None:
        _gpt_bot_instance = GPTBot(global_storage)
    return _gpt_bot_instance

def get_dr_jib_instance() -> DrJib:
    """Get or create singleton DrJib instance"""
    global _dr_jib_instance
    if _dr_jib_instance is None:
        _dr_jib_instance = DrJib(global_storage)
    return _dr_jib_instance

# Main router
router = APIRouter()

# =============================================================================
# MAIN SYSTEM ENDPOINTS
# =============================================================================

@router.get("/")
async def hello_world():
    return {"message": "🧠 Jib's Brain - Multi-Service AI Architecture 🚀"}

@router.get("/health")
async def health_check():
    """Overall system health check"""
    return {
        "status": "healthy",
        "architecture": "Jib's Brain v1.0",
        "services": ["jib_ai", "dr_jib", "web_agent", "co_pilot", "ads_handler", "summarization"],
        "components": ["shared_rag", "shared_tools", "shared_utils", "shared_models"]
    }

# =============================================================================
# LEGACY ENDPOINTS (Backward Compatibility)
# =============================================================================

@router.post("/chat")
@memory_check_decorator()
async def chat_handler(chat_request: ChatRequest):
    """Legacy chat endpoint - routes to main JibAI service for backward compatibility."""
    room_id = chat_request.room_id
    
    # Memory monitoring
    memory_stats = memory_monitor.get_memory_usage()
    print(f"🧠 [MEMORY] Starting chat request - Memory: {memory_stats['rss_mb']:.1f}MB")
    
    start_time = time.time()
    messages = [message.model_dump() for message in chat_request.messages]
    last_query = str(messages[-1])
    
    print(f"🚀 Using Main JibAI Service (Sonnet 4)")
    print(f"routes : {global_storage}")
    
    bot = JibAI(global_storage, 'social')
    raw_response = await bot.forward(messages, room_id, last_query)
    chat_resp, token_dict, thought_dict = raw_response
    
    end_time = time.time()
    print(f"Time taken: {end_time - start_time:.2f} seconds")

    # Log usage and chain-of-thought
    LOG_TYPE_USAGE = "ProductionTokenUsage"  
    LOG_TYPE_COT = "ProductionCoTLog"
    post_data(WORKSPACE_ID, PRIMARY_KEY, LOG_TYPE_USAGE, [token_dict])
    post_data(WORKSPACE_ID, PRIMARY_KEY, LOG_TYPE_COT, [thought_dict])

    # Extract response text
    try:
        out = chat_resp['text']
        print(out)
    except:
        out = chat_resp

    # URL processing for HDmall links
    url_pattern = r'\(?https?://(?:www\.)?hdmall\.co\.th/[^\s<>"\']+\)?'

    def append_utm(match):
        url = match.group(0)
        if url.startswith('(') and url.endswith(')'):
            url = url[1:-1]
        url = url.replace('(', '').replace(')', '')
        
        if "cart" in url:
            params = "?openExternalBrowser=1&ai-id=hdmall-jibai&hdAd=1"
        else:
            params = "?openExternalBrowser=1&ai-id=hdmall-jibai&hdAd=1&branch=1"
        
        if '?' in url:
            params = params.replace('?', '&')
            extended_url = url + params
        else:
            extended_url = url + params
            
        try:
            return shorten_url(SHORT_IO_API_KEY, extended_url)
        except:
            return extended_url

    # Process URLs and clean markdown
    updated_out = re.sub(url_pattern, append_utm, out)
    updated_out = remove_markdown_elements(updated_out)
    
    try:
        chat_resp['text'] = updated_out
        print(f"Updated response: {updated_out}")
        return chat_resp
    except:
        return {"text": updated_out, "image": []}

@router.post("/search")
async def search_handler(search_request: SearchRequest):
    """Legacy search endpoint - uses shared RAG."""
    try:
        query = search_request.query
        rag = get_rag_instance()
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, rag.search_for_web, query)
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.post("/ads")
async def ads_handler(ads_request: AdsRequest):
    """Legacy ads endpoint - uses shared ads agent."""
    try:
        ads_agent = get_ads_agent_instance()
        ads_response = await ads_agent.forward(ads_request.model_dump())
        
        return {"result": ads_response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ads generation failed: {str(e)}")

# =============================================================================
# JIB AI SERVICE ENDPOINTS
# =============================================================================

@router.post("/jib_ai/chat")
async def jib_ai_chat_handler(chat_request: ChatRequest):
    """Main JibAI conversation service with advanced RAG."""
    room_id = chat_request.room_id
    try:
        device = chat_request.device
    except:
        device = 'social'
    print(f"JibAI chat request for room: {room_id} with device: {device}")
    
    start_time = time.time()
    messages = [message.model_dump() for message in chat_request.messages]
    last_query = str(messages[-1])
    
    bot = JibAI(global_storage, device)
    raw_response = await bot.forward(messages, room_id, last_query)
    chat_resp, token_dict, thought_dict = raw_response
    
    end_time = time.time()
    print(f"JibAI response time: {end_time - start_time:.2f} seconds")

    # Extract response text
    try:
        out = chat_resp['text']
    except:
        out = chat_resp

    # URL processing for HDmall links
    url_pattern = r'\(?https?://(?:www\.)?hdmall\.co\.th/[^\s<>"\']+\)?'

    def append_utm(match):
        url = match.group(0)
        if url.startswith('(') and url.endswith(')'):
            url = url[1:-1]
        url = url.replace('(', '').replace(')', '')
        
        params = "?openExternalBrowser=1&ai-id=hdmall-jibai&hdAd=1"
        
        if '?' in url:
            params = params.replace('?', '&')
            extended_url = url + params
        else:
            extended_url = url + params
            
        try:
            return shorten_url(SHORT_IO_API_KEY, extended_url)
        except:
            return extended_url

    if device == 'app':
        updated_out = remove_markdown_elements(out)
        try:
            chat_resp['text'] = updated_out
        except:
            chat_resp = updated_out
        return chat_resp
    else:
        # Process URLs and clean markdown
        updated_out = re.sub(url_pattern, append_utm, out)
        updated_out = remove_markdown_elements(updated_out)
    
        try:
            chat_resp['text'] = updated_out
        except:
            chat_resp = updated_out

        return chat_resp

@router.get("/jib_ai/health")
async def jib_ai_health_check():
    """Health check endpoint for JibAI service."""
    return {"status": "healthy", "service": "jib_ai"}

# =============================================================================
# DR JIB SERVICE ENDPOINTS
# =============================================================================

@router.post("/dr_jib/chat")
async def dr_jib_chat_handler(chat_request: ChatRequest):
    """API to chat with Dr Jib medical RAG model."""
    room_id = chat_request.room_id
    print(f"Dr Jib chat request for room: {room_id}")
    
    start_time = time.time()
    messages = [message.model_dump() for message in chat_request.messages]
    
    bot = get_dr_jib_instance()
    chat_resp = await bot.forward(messages, room_id)
    
    end_time = time.time()
    print(f"Dr Jib response time: {end_time - start_time:.2f} seconds")

    # Extract response text
    try:
        out = chat_resp['text']
    except:
        out = chat_resp

    # URL processing for HDmall links
    url_pattern = r'\(?https?://(?:www\.)?hdmall\.co\.th/[^\s<>"\']+\)?'

    def append_utm(match):
        url = match.group(0)
        if url.startswith('(') and url.endswith(')'):
            url = url[1:-1]
        url = url.replace('(', '').replace(')', '')
        
        params = "?openExternalBrowser=1&ai-id=hdmall-dr-jib&hdAd=1"
        
        if '?' in url:
            params = params.replace('?', '&')
            extended_url = url + params
        else:
            extended_url = url + params
            
        try:
            return shorten_url(SHORT_IO_API_KEY, extended_url)
        except:
            return extended_url

    # Process URLs and clean markdown
    updated_out = re.sub(url_pattern, append_utm, out)
    updated_out = remove_markdown_elements(updated_out)
    
    try:
        chat_resp['text'] = updated_out
    except:
        chat_resp = updated_out

    return chat_resp

@router.get("/dr_jib/health")
async def dr_jib_health_check():
    """Health check endpoint for Dr Jib service."""
    return {"status": "healthy", "service": "dr_jib"}

# =============================================================================
# WEB AGENT SERVICE ENDPOINTS
# =============================================================================

@router.post("/web_agent/chat")
async def web_agent_chat_handler(chat_request: ChatRequest):
    """Advanced web agent chat with full RAG capabilities."""
    room_id = chat_request.room_id
    print(f"Web agent chat request for room: {room_id}")
    
    start_time = time.time()
    messages = [message.model_dump() for message in chat_request.messages]
    
    bot = get_gpt_bot_instance()
    chat_resp = await bot.forward(messages, room_id)
    
    end_time = time.time()
    print(f"Web agent response time: {end_time - start_time:.2f} seconds")

    # Web agent returns dict directly with response, recommended_prompts_for_users, recommended_urls
    return {'text':str(chat_resp), 'images':[]}

@router.post("/web_agent/search")
async def web_search_handler(search_request: SearchRequest):
    """Advanced web search with RAG."""
    try:
        query = search_request.query
        print(f"Web search query: {query}")
        
        rag = get_rag_instance()
        
        # Run search in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, rag.search_for_web, query)
        
        return result
    except Exception as e:
        print(f"Web search error: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.get("/web_agent/health")
async def web_agent_health_check():
    """Health check endpoint for web agent service."""
    return {"status": "healthy", "service": "web_agent"}

# =============================================================================
# SUMMARIZATION SERVICE ENDPOINTS
# =============================================================================

@router.post("/summarization/slack")
async def slack_webhook_handler(slack_event: SlackEvent, background_tasks: BackgroundTasks):
    """Handle Slack webhook events for summarization service."""
    try:
        data = slack_event.model_dump()
        logger.info("Received Slack event")
        
        # Handle Slack's URL verification
        if data.get('type') == 'url_verification':
            logger.info("Handling URL verification")
            return {"challenge": data.get('challenge')}

        # Get event data
        event = data.get('event')
        if not event:
            return {"message": "No event data"}

        # Process event in background
        logger.info("Starting background processing")
        background_tasks.add_task(process_slack_event, event)
        
        return {"message": "Got it, working on it!"}
        
    except Exception as e:
        logger.error(f"Error handling Slack event: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Slack event processing error: {str(e)}")

@router.get("/summarization/health")
async def summarization_health_check():
    """Health check endpoint for summarization service."""
    return {"status": "healthy", "service": "summarization"}

# =============================================================================
# CO-PILOT SERVICE ENDPOINTS
# =============================================================================

@router.post("/co_pilot/")
async def co_pilot_handler(request: CoPilotRequest):
    """GPT-4 proxy service for general AI completions."""
    try:
        data = request.model_dump()
        logger.info(f"Co-pilot request received with {len(data.get('messages', []))} messages")
        
        response = await co_pilot_run(data)
        logger.info("Co-pilot response generated successfully")
        
        return {"response": response}
        
    except Exception as e:
        logger.error(f"Error in co_pilot: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Co-pilot error: {str(e)}")

@router.get("/co_pilot/health")
async def co_pilot_health_check():
    """Health check endpoint for co-pilot service."""
    return {"status": "healthy", "service": "co_pilot"}

# =============================================================================
# ADS HANDLER SERVICE ENDPOINTS
# =============================================================================

@router.post("/ads_handler/chat")
async def ads_handler_chat_handler(ads_request: AdsRequest):
    """Generate contextual ads based on conversation thread."""
    try:
        thread_name = ads_request.thread_name
        conversation = ads_request.conversation
        
        print(f"🎯 Ads Handler request for thread: {thread_name}")
        print(f"🎯 Conversation has {len(conversation)} messages")
        
        start_time = time.time()
        
        # Get ads agent instance
        ads_agent = get_ads_agent_instance()
        
        # Prepare request data
        request_data = {
            "thread_name": thread_name,
            "conversation": conversation
        }
        
        # Generate contextual ads
        ads_result = await ads_agent.forward(request_data)
        logger.info(f"Ads result: {ads_result}")
        
        end_time = time.time()
        print(f"🎯 Ads Handler response time: {end_time - start_time:.2f} seconds")
        print(f"🎯 Generated {len(ads_result) if ads_result else 0} contextual ads")
        
        # Return ads_result directly for production compatibility
        return {"result": ads_result if ads_result else {"result": []}}
        
    except Exception as e:
        logger.error(f"Error in ads handler: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ads handler error: {str(e)}")

@router.get("/ads_handler/health")
async def ads_handler_health_check():
    """Health check endpoint for ads handler service."""
    return {"status": "healthy", "service": "ads_handler"}

# =============================================================================
# ROUTER EXPORT - App creation handled by __init__.py:create_app()
# =============================================================================