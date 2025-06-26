#!/usr/bin/env python3
"""
Test script for Sonnet 4 Bot with Centralized Tools System
==========================================================
This script tests the new centralized tools handling, interleaved thinking,
and parallel tool execution capabilities.
"""

import asyncio
import logging
import json
from datetime import datetime
from sonnet4_bot import JibAI

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

class MockGlobalStorage:
    """Mock global storage for testing"""
    def __init__(self):
        # Mock data structures similar to the real global storage
        self.data = {
            'packages': [],
            'categories': [],
            'brands': []
        }

async def test_centralized_tools():
    """Test the centralized tools system with various query types"""
    
    print("🚀 Testing Sonnet 4 Bot with Centralized Tools System")
    print("=" * 80)
    
    # Initialize JibAI with mock storage
    mock_storage = MockGlobalStorage()
    jib_ai = JibAI(mock_storage)
    
    # Test queries covering different tool usage scenarios
    test_cases = [
        {
            "name": "Simple Greeting",
            "query": "สวัสดีครับ",
            "room_id": "test_room_001",
            "expected_tools": [],  # Should use initial RAG context
            "description": "Basic greeting that should get initial RAG context but no tools"
        },
        {
            "name": "Vaccine Search",
            "query": "ฉีดวัคซีน HPV ราคาถูกที่สุด 3 อันดับแรก",
            "room_id": "test_room_002", 
            "expected_tools": ["retrieval", "sql_search"],
            "description": "Should use retrieval tool and SQL search for filtering by price"
        },
        {
            "name": "Health Checkup Comparison",
            "query": "อยากเปรียบเทียบโปรแกรมตรวจสุขภาพในกรุงเทพ ราคาระหว่าง 3000-8000 บาท",
            "room_id": "test_room_003",
            "expected_tools": ["sql_search", "retrieval"],
            "description": "Should use SQL search for price filtering and retrieval for details"
        },
        {
            "name": "Cart Creation",
            "query": "ผมต้องการใส่แพ็กเกจตรวจสุขภาพลงในตะกร้าสินค้า",
            "room_id": "test_room_004",
            "expected_tools": ["cart", "retrieval"],
            "description": "Should use cart tool to create cart and retrieval to find packages"
        },
        {
            "name": "Booking Request",
            "query": "ผมชื่อ สมชาย โทร 081-234-5678 อยากจองวัคซีน HPV วันจันทร์หน้า เวลา 10:00",
            "room_id": "test_room_005",
            "expected_tools": ["retrieval", "handover_to_bk"],
            "description": "Should search for vaccine and handover to booking specialist"
        },
        {
            "name": "Technical Issue",
            "query": "เว็บไซต์พัง เข้าไม่ได้ รบกวนช่วยด่วน",
            "room_id": "test_room_006",
            "expected_tools": ["handover_asap"],
            "description": "Should immediately handover for technical issues"
        },
        {
            "name": "Complex Multi-tool Query",
            "query": "หาแพ็กเกจฟันราคาถูกที่สุด 5 อันดับ แล้วสร้างตะกร้าใส่อันดับ 1 และจองเลย",
            "room_id": "test_room_007",
            "expected_tools": ["sql_search", "cart", "handover_to_bk"],
            "description": "Should use multiple tools in sequence: search, cart, and booking"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"🧪 TEST {i}: {test_case['name']}")
        print(f"📝 Query: {test_case['query']}")
        print(f"💡 Expected: {test_case['description']}")
        print('='*60)
        
        try:
            # Prepare mock chat history
            chats = [
                {"role": "user", "content": test_case['query']}
            ]
            
            # Run the test
            start_time = datetime.now()
            result = await jib_ai.forward(chats, test_case['room_id'], test_case['query'])
            end_time = datetime.now()
            
            processing_time = (end_time - start_time).total_seconds()
            
            # Extract results
            chat_resp, token_dict, thought_dict = result
            response_text = chat_resp.get('text', 'No response')
            tools_used = thought_dict.get('tools_used', [])
            tool_count = thought_dict.get('tool_count', 0)
            thinking_content = thought_dict.get('thinking_content', '')
            
            # Display results
            print(f"✅ RESPONSE: {response_text[:100]}...")
            print(f"⏱️  PROCESSING TIME: {processing_time:.2f} seconds")
            print(f"🔧 TOOLS USED: {tool_count}")
            
            if tools_used:
                for j, tool in enumerate(tools_used, 1):
                    print(f"  {j}. {tool['name']}")
                    print(f"     Input: {str(tool['input'])[:100]}...")
                    print(f"     Result: {str(tool['result'])[:100]}...")
            
            print(f"💭 THINKING BLOCKS: {len(thinking_content.split('\\n\\n')) if thinking_content else 0}")
            if thinking_content:
                # Show first thinking block preview
                first_block = thinking_content.split('\\n\\n')[0]
                print(f"💭 THINKING PREVIEW: {first_block[:150]}...")
            
            print(f"📊 TOKEN USAGE: {token_dict.get('total_tokens', 0)}")
            
            # Verify expected tools were used
            used_tool_names = [tool['name'] for tool in tools_used]
            expected_tools = test_case.get('expected_tools', [])
            
            if expected_tools:
                tools_match = all(tool in used_tool_names for tool in expected_tools)
                if tools_match:
                    print(f"✅ TOOL VERIFICATION: Expected tools were used")
                else:
                    print(f"⚠️  TOOL VERIFICATION: Expected {expected_tools}, got {used_tool_names}")
            else:
                print(f"ℹ️  TOOL VERIFICATION: No specific tools expected")
            
        except Exception as e:
            print(f"❌ ERROR in test {i}: {str(e)}")
            logger.error(f"Test {i} failed: {e}")
        
        print(f"\n{'-'*40}")
    
    print(f"\n{'='*60}")
    print("🏁 Centralized Tools Testing Completed!")
    print("Check the logs above for detailed agent step-by-step processing.")

async def test_parallel_tools():
    """Test parallel tool execution capabilities"""
    print(f"\n{'='*60}")
    print("🚀 Testing Parallel Tool Execution")
    print('='*60)
    
    mock_storage = MockGlobalStorage()
    jib_ai = JibAI(mock_storage)
    
    # Query that should trigger multiple parallel tools
    complex_query = "ค้นหาวัคซีน HPV ราคาถูกที่สุด และสร้างตะกร้าสินค้าพร้อมกันเลย"
    
    chats = [{"role": "user", "content": complex_query}]
    
    try:
        start_time = datetime.now()
        result = await jib_ai.forward(chats, "parallel_test", complex_query)
        end_time = datetime.now()
        
        processing_time = (end_time - start_time).total_seconds()
        
        chat_resp, token_dict, thought_dict = result
        tools_used = thought_dict.get('tools_used', [])
        
        print(f"✅ PARALLEL TEST COMPLETED")
        print(f"⏱️  PROCESSING TIME: {processing_time:.2f} seconds")
        print(f"🔧 TOOLS EXECUTED: {len(tools_used)}")
        
        # Check if multiple tools were used (indicating parallel execution capability)
        if len(tools_used) > 1:
            print(f"⚡ PARALLEL EXECUTION: Successfully executed {len(tools_used)} tools")
        else:
            print(f"🔄 SEQUENTIAL EXECUTION: {len(tools_used)} tool(s) executed")
            
    except Exception as e:
        print(f"❌ ERROR in parallel test: {str(e)}")

if __name__ == "__main__":
    print("🎯 Starting Comprehensive Centralized Tools Testing")
    print(f"📅 Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Run main tests
    asyncio.run(test_centralized_tools())
    
    # Run parallel execution test
    asyncio.run(test_parallel_tools())
    
    print(f"\n📅 Testing completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("💡 Review the detailed logs above to see the agent's step-by-step reasoning and tool usage!") 