#!/usr/bin/env python3

import asyncio
import logging
import pandas as pd
import numpy as np
from datetime import datetime
from sonnet4_bot import JibAI

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

# Mock classes to avoid BM25Retriever dependency issues
class MockBM25Retriever:
    def __init__(self, tokens_file):
        self.tokens_file = tokens_file
    
class MockSemanticRetriever:
    def __init__(self, embed_matrix):
        self.embed_matrix = embed_matrix

class MockGlobalStorage:
    def __init__(self):
        # Create mock data structures that RAG expects
        self.data = {}
        
        # Core RAG attributes
        self.knowledge_base = pd.DataFrame({
            'Package_Name': ['HPV Vaccine Package', 'Health Checkup Basic', 'Dental Package'],
            'Brand': ['Bangkok Hospital', 'Bumrungrad', 'Samitivej'],
            'Cash Price': [12000, 3500, 2500],
            'Location': ['Bangkok', 'Bangkok', 'Chiang Mai'],
            'Category': ['วัคซีน', 'ตรวจสุขภาพ', 'ทันตกรรม'],
            'Package_URL': ['https://hdmall.com/hpv1', 'https://hdmall.com/checkup1', 'https://hdmall.com/dental1']
        })
        
        # Mock embeddings and search data
        self.embed_matrix = np.random.rand(3, 384)  # 3 packages, 384-dim embeddings
        self.embed_matrix_plus = np.random.rand(3, 384)
        
        # Mock documents for BM25
        self.doc_json = [
            ['HPV', 'vaccine', 'bangkok', 'hospital'],
            ['health', 'checkup', 'basic', 'bumrungrad'],
            ['dental', 'package', 'samitivej', 'chiang', 'mai']
        ]
        self.doc_json_plus = self.doc_json.copy()
        
        # Index lists
        self.index_list = [0, 1, 2]
        self.index_list_plus = [0, 1, 2]
        
        # Web recommendation data
        self.web_recommendation_json = {
            'hospital': ['Bangkok Hospital', 'Bumrungrad', 'Samitivej'],
            'brand': ['Bangkok Hospital', 'Bumrungrad'],
            'category': ['วัคซีน', 'ตรวจสุขภาพ', 'ทันตกรรม'],
            'tag': ['HPV', 'checkup', 'dental']
        }
        
        # Additional embeddings for web recommendation
        self.hl_embed = np.random.rand(3, 384)
        self.brand_embed = np.random.rand(2, 384)
        self.cat_embed = np.random.rand(3, 384)
        self.tag_embed = np.random.rand(3, 384)
        
        # Additional documents for BM25
        self.hl_docs = [['hospital', 'medical'], ['clinic', 'health'], ['center', 'care']]
        self.brand_docs = [['bangkok', 'hospital'], ['bumrungrad', 'international']]
        self.cat_docs = [['vaccine', 'immunization'], ['checkup', 'screening'], ['dental', 'oral']]
        self.tag_docs = [['hpv', 'prevention'], ['health', 'wellness'], ['dental', 'teeth']]

async def test_tools():
    print("Testing Sonnet 4 Bot Centralized Tools")
    
    # Patch the imports to avoid dependency issues
    import sys
    sys.modules['src.bm25_searcher'] = type('MockModule', (), {'BM25Retriever': MockBM25Retriever})()
    sys.modules['src.semantic_searcher'] = type('MockModule', (), {'SemanticRetriever': MockSemanticRetriever})()
    
    mock_storage = MockGlobalStorage()
    jib_ai = JibAI(mock_storage)
    
    test_queries = [
        "สวัสดีครับ",
        "หาวัคซีน HPV ราคาถูก",
        "สร้างตะกร้าสินค้า",
        "จองแพ็กเกจตรวจสุขภาพ"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\nTest {i}: {query}")
        try:
            chats = [{"role": "user", "content": query}]
            result = await jib_ai.forward(chats, f"test_{i}", query)
            
            chat_resp, token_dict, thought_dict = result
            tools_used = thought_dict.get('tools_used', [])
            
            print(f"Response: {chat_resp.get('text', '')[:100]}...")
            print(f"Tools used: {len(tools_used)}")
            
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_tools()) 