# api_routes.py
from utils import remove_markdown_elements, update_urls_with_utm, post_data, shorten_url
from fastapi import APIRouter, HTTPException
from api_models import ChatRequest
from src.RAG import RAG
from ads_handler.ads_agent import AdsAgent
#from jib_reasoner import JibAI
#from bot import JibAI  # Original bot
from sonnet4_bot import JibAI  # 🚀 Sonnet 4 with Interleaved Thinking
from pydantic import BaseModel
from globals import global_storage
from dotenv import load_dotenv
import os
import time
import re
import json
import asyncio
from typing import Optional
input = [{'content': [{'text': 'ฉีดซีน ไข้หวัดใหญ่', 'type': 'text'}], 'role': 'user'}, {'content': [{'text': '💉 วัคซีนไข้หวัดใหญ่ 2025 ที่แนะนำค่ะ\\n\\n🏥 สำหรับผู้ใหญ่ (15 ปีขึ้นไป)\\n💰 ราคา 600 บาท (จากราคาปกติ 900 บาท)\\n\\n📍 โรงพยาบาลวิชัยเวช แยกไฟฉาย\\nhttps://s.hdmall.co.th/VQDvbm\\n\\n📍 โรงพยาบาลวิชัยเวช หนองแขม \\nhttps://s.hdmall.co.th/enqRFv\\n\\n📍 โรงพยาบาลเกษมราษฎร์ บางแค\\nhttps://s.hdmall.co.th/mOJ8aC\\n\\n👶 สำหรับเด็ก (6 เดือนขึ้นไป)\\n💰 ราคา 600 บาท\\n📍 บางปะกอก-ปิยะเวท สหคลินิก ฟิวเจอร์พาร์ครังสิต\\nhttps://s.hdmall.co.th/XeZYEQ\\n\\n👵 สำหรับผู้สูงอายุ (65 ปีขึ้นไป) - High Dose\\n💰 ราคา 1,999 บาท (จากราคาปกติ 3,200 บาท)\\n📍 โรงพยาบาลวิชัยเวช แยกไฟฉาย\\nhttps://s.hdmall.co.th/UqX6IJ\\n\\nสนใจรับบริการที่ไหนดีคะ? หรือต้องการดูรายละเอียดเพิ่มเติมของแพ็กเกจไหนเป็นพิเศษมั้ย? 😊', 'type': 'text'}], 'role': 'assistant'}, {'content': [{'text': 'นวมินทร์9 ', 'type': 'text'}], 'role': 'user'}, {'content': [{'text': 'มีไหมครับ', 'type': 'text'}], 'role': 'user'}, {'content': [{'text': '🎯 มีครับ! โรงพยาบาลนวมินทร์ 9 มีวัคซีนไข้หวัดใหญ่ 2025\\n\\n💉 ฉีดวัคซีนป้องกันไข้หวัดใหญ่ 2025 \\n🏥 โรงพยาบาลนวมินทร์ 9\\n💰 ราคา 600 บาท (จากราคาปกติ 900 บาท)\\n👥 สำหรับอายุ 15-60 ปี\\n📍 96 ถ. สีหบุรานุกิจ แขวงมีนบุรี เขตมีนบุรี\\n\\nhttps://s.hdmall.co.th/WQ5Klt\\n\\n🏥 ตัวเลือกอื่นในย่านใกล้เคียง:\\n\\n📍 โรงพยาบาลเกษมราษฎร์ รามคำแหง\\n💰 ราคา 600 บาท (15 ปีขึ้นไป)\\nhttps://s.hdmall.co.th/AR9O95\\n\\n📍 PSK Clinic ลาดพร้าว 19 \\n💰 ราคา 600 บาท (6 เดือนขึ้นไป)\\nhttps://s.hdmall.co.th/B0UvbS\\n\\nสนใจจองคิวที่ไหนดีครับ? 😊', 'type': 'text'}], 'role': 'assistant'}, {'content': [{'text': 'นวมินทร์9 \\nไปฉีด2คน วันนี้ครับ ', 'type': 'text'}], 'role': 'user'}, {'content': [{'text': 'ต้องจองยังไง', 'type': 'text'}], 'role': 'user'}, {'content': [{'text': '🎯 ขั้นตอนการจองนวมินทร์ 9 สำหรับ 2 คนค่ะ\\n\\n💰 ซื้อแพ็กเกจก่อน:\\n- ราคา 600 บาท/คน รวม 1,200 บาท\\n- คูปองจะส่งให้ทางอีเมลภายใน 24 ชั่วโมง\\n- คูปองใช้ได้ 60 วัน\\n\\n📞 นัดหมายกับโรงพยาบาล:\\n- โทรนัดตามเบอร์ในคูปอง\\n- นัดล่วงหน้า 1-3 วันทำการ\\n- ใช้เวลารับบริการ 30 นาที-1 ชั่วโมง\\n\\n📍 วันนี้: เนื่องจากต้องซื้อคูปองก่อนแล้วค่อยนัด อาจไม่ทันวันนี้ครับ\\n\\n🛒 อยากให้จิ๊บช่วยสร้างตะกร้าสำหรับ 2 คนเลยมั้ยครับ?\\n\\nhttps://s.hdmall.co.th/WQ5Klt', 'type': 'text'}], 'role': 'assistant'}, {'content': [{'text': 'ไม่เป็นไรครับ ขอบคุณครับ พรุ่งนี้ต้องไป ตจว \\nจะไปฉีดวันนี้', 'type': 'text'}], 'role': 'user'}]


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
    return {"message": "Hello from Sonnet 4 with Interleaved Thinking! 🚀🧠"}

@router.post("/chat")
async def chat_handler(chat_request:ChatRequest):
    """API to chat with the RAG model."""
    room_id = chat_request.room_id
    #mesaure time take for bot to respond
    start_time = time.time()
    messages = [message.model_dump() for message in chat_request.messages]
    #### FOR TESTING ONLY , REPLACE MESSAGE WITH EXAMPLE INPUT
    #messages = input
    #messages = input['Messages']  # Fixed: input['Messages'] contains dicts, not Pydantic models
        
    last_query = str(messages[-1])
    #if 'hdexpress' in last_query.lower() or 'hd express' in last_query.lower():
        #return {"text":"QISCUS_INTEGRATION_TO_BK", "image":[]}
    print(f"🚀 Using Sonnet 4 with Interleaved Thinking")
    print(f"routes : {global_storage}")
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
        print(f"Updated out: {updated_out}")
        print(f"Final response structure: {chat_resp}")
        return chat_resp
    except:
        # Fallback if chat_resp is not a dict (shouldn't happen with new structure)
        print(f"Fallback - returning text only: {updated_out}")
        return {"text": updated_out, "image": []}



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