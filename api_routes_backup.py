# api_routes.py
from utils import remove_markdown_elements, update_urls_with_utm, post_data, shorten_url
from fastapi import APIRouter, HTTPException
from api_models import ChatRequest
from src.RAG import RAG
from ads_handler.ads_agent import AdsAgent
#from jib_reasoner import JibAI
from bot import JibAI
from pydantic import BaseModel
from globals import global_storage
from dotenv import load_dotenv
import os
import time
import re
import json
import asyncio
from typing import Optional
input = [{'content': [{'type': 'image_url', 'image_url': {'url': 'https://dnlbo7fgjcc7f.cloudfront.net/daki-fq9mhonubqarcuy6/docs/upload/0ROZm2PVCK/ด.ญ.-พิณเพียงอินทร์-ทวีผลจรูญ.pdf', 'detail': 'auto'}}], 'role': 'assistant'}, {'content': [{'text': 'เวลาถ้าเปลี่ยนต้องโทรแจ้งไหมคะ', 'type': 'text'}], 'role': 'user'}, {'content': [{'text': 'อาจจะเลทค่ะ', 'type': 'text'}], 'role': 'user'}, {'content': [{'text': 'เวลาถ้าเปลี่ยนต้องโทรแจ้งไหมคะ', 'type': 'text'}], 'role': 'user'}, {'content': [{'text': 'อาจจะเลทค่ะ', 'type': 'text'}], 'role': 'user'}, {'content': [{'text': 'ลูกค้าสามารถโทรแจ้งทางโรงพยาบาลได้ตามข้อมูลนี้เลยนะคะ กรณีฉุกเฉิน หรือไม่สามารถมาตามนัดหมาย กรุณาติดต่อ 1507 หรือ 02-483-9999', 'type': 'text'}], 'role': 'assistant'}, {'content': [{'text': 'ขอบคุณค่า', 'type': 'text'}], 'role': 'user'}, {'content': [{'text': '😊🙏', 'type': 'text'}], 'role': 'assistant'}, {'content': [{'type': 'image_url', 'image_url': {'url': 'https://dnlbo7fgjcc7f.cloudfront.net/daki-fq9mhonubqarcuy6/image/upload/0RMVMgOpLu/image.jpg', 'detail': 'auto'}}], 'role': 'user'}, {'content': [{'text': 'ซื้อวัคซีนไข้หวัดใหญ่เพิ่ม 1 เข็มค่ะ', 'type': 'text'}], 'role': 'user'}, {'content': [{'text': 'ผู้เข้ารับบริการ \nนายกฤติน ทวีผลจรูญ\n0811572929\nannepkm29@gmail.com \nเกิด 16 กันยายน 2524\nโรงพยาบาลนวเวชค่ะ', 'type': 'text'}], 'role': 'user'}, {'content': [{'text': 'รบกวนออกคูปองให้ด้วยค่า', 'type': 'text'}], 'role': 'user'}, {'content': [{'text': 'แอดมินประสานงานออกคูปองให้สักครู่ค่ะ', 'type': 'text'}], 'role': 'assistant'}, {'content': [{'text': '[ข้อความอัตโนมัติ 🤖]\n\nการจองแพ็กเกจ ฉีดวัคซีนป้องกันไข้หวัดใหญ่ 2024/2025 4 สายพันธุ์ 1 เข็ม (แพ็กเกจ HDmall+) ที่  โรงพยาบาลนวเวช ของคุณ กฤติน ทวีผลจรูญ สำเร็จแล้วค่ะ 😃\n\nเจ้าหน้าที่ได้ทำการส่งคูปองสำหรับเข้ารับบริการไปที่อีเมลของคุณแล้ว หากไม่พบ รบกวนตรวจสอบในกล่องสแปมหรือถังขยะ และอย่าลืมนัดหมายล่วงหน้าอย่างน้อย 24-48 ชม. ก่อนเข้าใช้บริการนะคะ', 'type': 'text'}], 'role': 'assistant'}, {'content': [{'text': 'ต้องแจ้งวันเข้ารับบริการมั้ยคะ', 'type': 'text'}], 'role': 'user'}, {'content': [{'text': 'หรือเข้าไปเมื่อไหร่ก็ได้คะ ก่อนคูปองหมดอายุ', 'type': 'text'}], 'role': 'user'}, {'content': [{'text': 'เวลาถ้าเปลี่ยนต้องโทรแจ้งไหมคะ', 'type': 'text'}], 'role': 'user'}, {'content': [{'text': 'อาจจะเลทค่ะ', 'type': 'text'}], 'role': 'user'}, {'content': [{'text': 'ต้องแจ้งวันเข้ารับบริการมั้ยคะ', 'type': 'text'}], 'role': 'user'}, {'content': [{'text': 'หรือเข้าไปเมื่อไหร่ก็ได้คะ ก่อนคูปองหมดอายุ', 'type': 'text'}], 'role': 'user'}]


class SearchRequest(BaseModel):
    query: str

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
    return {"message": "Hello Jawad"}

@router.post("/chat")
async def chat_handler(chat_request:ChatRequest):
    """API to chat with the RAG model."""
    room_id = chat_request.room_id
    #mesaure time take for bot to respond
    start_time = time.time()
    messages = [message.model_dump() for message in chat_request.messages]
    last_query = str(messages[-1])
    if 'hdexpress' in last_query.lower() or 'hd express' in last_query.lower():
        return {"text":"QISCUS_INTEGRATION_TO_BK", "image":[]}
    print(f"rountes : {global_storage}")
    bot = JibAI(global_storage)
    raw_response = await bot.forward(messages, room_id, last_query)
    chat_resp, token_dict, thought_dict = raw_response
    end_time = time.time()
    print(f"Time taken: {end_time - start_time} seconds")
    #in minute
    print(f"Time taken: {(end_time - start_time)/60} minutes")



    # create this on the fly
    LOG_TYPE_USAGE = "ProductionTokenUsage"  
    LOG_TYPE_COT = "ProductionCoTLog"
    post_data(WORKSPACE_ID, PRIMARY_KEY, LOG_TYPE_USAGE, [token_dict])
    post_data(WORKSPACE_ID, PRIMARY_KEY, LOG_TYPE_COT, [thought_dict])
    

    #for local, return out
    #for deploy, return chat_resp
    try : 
        out = chat_resp['text']
        print(out)
    except:
        out = chat_resp


    # Define the regex pattern for matching HDmall package URLs specifically
    url_pattern = r'\(?https?://(?:www\.)?hdmall\.co\.th/[^\s<>"\']+\)?'

    # Function to append parameters to URLs, handling existing query params
    def append_utm(match):
        url = match.group(0)
        # Remove wrapping parentheses if URL is wrapped like (URL)
        if url.startswith('(') and url.endswith(')'):
            url = url[1:-1]
        # Remove any remaining single parentheses just in case
        url = url.replace('(', '').replace(')', '')
        
        if "cart" in url:
            params = "?openExternalBrowser=1&ai-id=hdmall-jibai&hdAd=1"
        else:
            params = "?openExternalBrowser=1&ai-id=hdmall-jibai&hdAd=1&branch=1"
        
        # Check if URL already has query parameters
        if '?' in url:
            print(f"URL already has query parameters: {url}")
            print(f"Appending parameters: {params}")
            params = params.replace('?', '&')
            extened_url = url + params
            try:
                shortened_url = shorten_url(SHORT_IO_API_KEY, extened_url)
                return shortened_url
            except:
                return extened_url
        else:
            print(f"URL does not have query parameters: {url}")
            print(f"Appending parameters: {params}")
            extened_url = url + params
            try:
                shortened_url = shorten_url(SHORT_IO_API_KEY, extened_url)
                return shortened_url
            except:
                return extened_url


    # Use re.sub to find HDmall URLs and append parameters
    updated_out = re.sub(url_pattern, append_utm, out)
    updated_out = remove_markdown_elements(updated_out)
    
    try:
        chat_resp['text'] = updated_out
    except:
        chat_resp = updated_out
    
    
    print(f"Updated out: {updated_out}")
    return updated_out



@router.post("/search")
async def search_handler(search_request: SearchRequest):
    """API to search for web - optimized version."""
    try:
        query = search_request.query
        
        # Use singleton instance instead of creating new one
        rag = get_rag_instance()
        
        # Run the search in a thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, rag.search_for_web, query)
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.post("/ads")
async def ads_handler(ads_request: AdsRequest):
    """API to get ads - optimized version."""
    try:
        # Use singleton instance instead of creating new one
        ads_agent = get_ads_agent_instance()
        
        # The forward method is already async, so we can await it directly
        ads_response = await ads_agent.forward(ads_request.model_dump())
        
        return {"result": ads_response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ads generation failed: {str(e)}")