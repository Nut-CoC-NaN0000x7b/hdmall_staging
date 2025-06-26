#!/usr/bin/env python3
"""
Test script for enhanced logging in Sonnet 4 bot
"""

import asyncio
import logging
from datetime import datetime
from sonnet4_bot import JibAI

# Configure logging to see all details
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_enhanced_logging():
    """Test the enhanced logging functionality"""
    print("🧪 Testing Enhanced Logging for Sonnet 4 Bot")
    print("=" * 60)
    
    # Mock global storage for testing
    class MockGlobalStorage:
        def __init__(self):
            self.web_recommendation_json = None
            self.hl_embed = None
            self.brand_embed = None
            self.cat_embed = None
            self.tag_embed = None
            self.hl_docs = None
            self.brand_docs = None
            self.cat_docs = None
            self.tag_docs = None
    
    try:
        # Initialize JibAI with mock storage
        global_storage = MockGlobalStorage()
        jib_ai = JibAI(global_storage)
        
        # Test queries
        test_queries = [
            "หาวัคซีนโควิดให้หน่อย",
            "ต้องการตรวจสุขภาพประจำปี",
            "ฟันคุดผ่าตัดที่ไหนดี",
            "สวัสดีครับ"
        ]
        
        # Test each query
        for i, query in enumerate(test_queries, 1):
            print(f"\n🔍 TEST {i}: {query}")
            print("-" * 40)
            
            # Test category extraction
            category = jib_ai._extract_category_from_query(query)
            print(f"Detected Category: {category}")
            
            # Mock chat history
            mock_chats = [
                {"role": "user", "content": "สวัสดีครับ"},
                {"role": "assistant", "content": "สวัสดีค่ะ มีอะไรให้ช่วยไหม"},
                {"role": "user", "content": query}
            ]
            
            # Test the full forward method (will fail at Claude call, but we can see logging)
            try:
                await jib_ai.forward(mock_chats, f"test_room_{i}", query)
            except Exception as e:
                print(f"Expected error (no real Claude call): {e}")
            
            print("-" * 40)
        
        print("\n✅ Enhanced logging test completed!")
        print("Check the logs above to see all the detailed agent steps.")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_enhanced_logging()) 