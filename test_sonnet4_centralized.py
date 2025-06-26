#!/usr/bin/env python3
"""
Comprehensive Test Suite for Sonnet 4 Bot Centralized Tools System
================================================================
Tests the new centralized tools handling, interleaved thinking,
and parallel tool execution capabilities with enhanced logging.
"""

import asyncio
import logging
import json
from datetime import datetime
from sonnet4_bot import JibAI

# Configure detailed logging to see all agent steps
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

class MockGlobalStorage:
    """Mock global storage for testing"""
    def __init__(self):
        self.data = {
            'packages': [],
            'categories': [],
            'brands': []
        }

async def test_centralized_tools_comprehensive():
    """Comprehensive test of the centralized tools system"""
    
    print("🚀 Starting Comprehensive Centralized Tools Testing")
    print("=" * 80)
    
    # Initialize JibAI with mock storage
    mock_storage = MockGlobalStorage()
    jib_ai = JibAI(mock_storage)
    
    # Test cases covering different scenarios
    test_cases = [
        {
            "name": "Simple Greeting (RAG Context Only)",
            "query": "สวัสดีครับ",
            "room_id": "greeting_test",
            "description": "Should add initial RAG context but not use tools",
            "expected_no_tools": True
        },
        {
            "name": "Basic Vaccine Inquiry",
            "query": "มีวัคซีน HPV ไหม ราคาเท่าไหร่",
            "room_id": "vaccine_basic",
            "description": "Should use retrieval tool to search for HPV vaccines",
            "expected_tools": ["retrieval"]
        },
        {
            "name": "Price Filtering Query",
            "query": "หาแพ็กเกจตรวจสุขภาพราคาไม่เกิน 5000 บาท 10 อันดับแรก",
            "room_id": "price_filter",
            "description": "Should use SQL search for price filtering",
            "expected_tools": ["sql_search"]
        },
        {
            "name": "Shopping Cart Creation",
            "query": "ช่วยสร้างตะกร้าสินค้าใหม่ให้หน่อย",
            "room_id": "cart_create",
            "description": "Should use cart tool to create new cart",
            "expected_tools": ["cart"]
        },
        {
            "name": "Complex Multi-step Query",
            "query": "ค้นหาวัคซีน HPV ราคาถูกที่สุด 3 อันดับ แล้วใส่อันดับ 1 ลงตะกร้า",
            "room_id": "multi_step",
            "description": "Should use multiple tools: SQL search, then cart operations",
            "expected_tools": ["sql_search", "cart"]
        },
        {
            "name": "Booking with Complete Info",
            "query": "ผมชื่อ จอห์น สมิธ โทร 081-234-5678 อยากจองแพ็กเกจตรวจสุขภาพวันศุกร์หน้า เวลา 14:00",
            "room_id": "booking_complete",
            "description": "Should search for packages and handover to booking specialist",
            "expected_tools": ["retrieval", "handover_to_bk"]
        },
        {
            "name": "Technical Emergency",
            "query": "ระบบขัดข้อง เข้าไม่ได้ ช่วยด่วน",
            "room_id": "emergency",
            "description": "Should immediately handover for urgent technical issues",
            "expected_tools": ["handover_asap"]
        },
        {
            "name": "Complex Comparison Query",
            "query": "เปรียบเทียบแพ็กเกจทันตกรรมในกรุงเทพและเชียงใหม่ ราคา 2000-8000 บาท",
            "room_id": "comparison",
            "description": "Should use SQL search for filtering and retrieval for details",
            "expected_tools": ["sql_search", "retrieval"]
        }
    ]
    
    results_summary = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"🧪 TEST {i}/{len(test_cases)}: {test_case['name']}")
        print(f"📝 Query: {test_case['query']}")
        print(f"💡 Expected: {test_case['description']}")
        print('='*60)
        
        try:
            # Prepare mock chat history
            chats = [{"role": "user", "content": test_case['query']}]
            
            # Run the test with timing
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
            
            # Analyze results
            used_tool_names = [tool['name'] for tool in tools_used]
            expected_tools = test_case.get('expected_tools', [])
            expected_no_tools = test_case.get('expected_no_tools', False)
            
            # Determine test status
            if expected_no_tools:
                test_passed = len(tools_used) == 0
                status = "✅ PASSED" if test_passed else "❌ FAILED"
                reason = "No tools used as expected" if test_passed else f"Unexpected tools used: {used_tool_names}"
            elif expected_tools:
                tools_found = any(tool in used_tool_names for tool in expected_tools)
                test_passed = tools_found
                status = "✅ PASSED" if test_passed else "⚠️ PARTIAL"
                reason = f"Expected tools found: {expected_tools}" if test_passed else f"Expected {expected_tools}, got {used_tool_names}"
            else:
                test_passed = True
                status = "✅ COMPLETED"
                reason = "No specific tool expectations"
            
            # Display results
            print(f"\n{status}: {reason}")
            print(f"📱 RESPONSE: {response_text[:150]}...")
            print(f"⏱️  PROCESSING TIME: {processing_time:.2f}s")
            print(f"🔧 TOOLS USED ({tool_count}):")
            
            if tools_used:
                for j, tool in enumerate(tools_used, 1):
                    print(f"  {j}. {tool['name']}")
                    print(f"     📥 Input: {str(tool['input'])[:80]}...")
                    print(f"     📤 Result: {str(tool['result'])[:80]}...")
            else:
                print("  (No tools used)")
            
            # Thinking analysis
            thinking_blocks = thinking_content.split('\n\n') if thinking_content else []
            print(f"🧠 THINKING BLOCKS: {len(thinking_blocks)}")
            if thinking_blocks:
                print(f"🧠 FIRST BLOCK: {thinking_blocks[0][:100]}...")
            
            print(f"📊 ESTIMATED TOKENS: {token_dict.get('total_tokens', 0)}")
            
            # Store results for summary
            results_summary.append({
                'test_name': test_case['name'],
                'status': status,
                'processing_time': processing_time,
                'tools_used': len(tools_used),
                'thinking_blocks': len(thinking_blocks),
                'passed': test_passed
            })
            
        except Exception as e:
            print(f"❌ ERROR in test {i}: {str(e)}")
            logger.error(f"Test {i} ({test_case['name']}) failed: {e}")
            results_summary.append({
                'test_name': test_case['name'],
                'status': '❌ ERROR',
                'processing_time': 0,
                'tools_used': 0,
                'thinking_blocks': 0,
                'passed': False,
                'error': str(e)
            })
        
        print(f"\n{'-'*40}")
    
    # Final summary
    print(f"\n{'='*60}")
    print("📊 TESTING SUMMARY")
    print('='*60)
    
    passed_tests = sum(1 for r in results_summary if r['passed'])
    total_tests = len(results_summary)
    avg_processing_time = sum(r['processing_time'] for r in results_summary) / len(results_summary)
    total_tools_used = sum(r['tools_used'] for r in results_summary)
    total_thinking_blocks = sum(r['thinking_blocks'] for r in results_summary)
    
    print(f"✅ PASSED: {passed_tests}/{total_tests} tests")
    print(f"⏱️  AVERAGE PROCESSING TIME: {avg_processing_time:.2f}s")
    print(f"🔧 TOTAL TOOLS EXECUTED: {total_tools_used}")
    print(f"🧠 TOTAL THINKING BLOCKS: {total_thinking_blocks}")
    
    print(f"\n📋 DETAILED RESULTS:")
    for result in results_summary:
        print(f"  {result['status']} {result['test_name']} ({result['processing_time']:.2f}s, {result['tools_used']} tools)")
    
    print(f"\n🏁 Centralized Tools Testing Completed!")
    print("💡 Check the detailed logs above to see agent's step-by-step reasoning!")

async def test_parallel_execution():
    """Test parallel tool execution capabilities"""
    print(f"\n{'='*60}")
    print("⚡ TESTING PARALLEL TOOL EXECUTION")
    print('='*60)
    
    mock_storage = MockGlobalStorage()
    jib_ai = JibAI(mock_storage)
    
    # Query designed to potentially trigger multiple tools
    parallel_query = "ค้นหาวัคซีนราคาถูก สร้างตะกร้าใหม่ และเตรียมข้อมูลสำหรับจอง"
    
    print(f"📝 Parallel Test Query: {parallel_query}")
    
    try:
        chats = [{"role": "user", "content": parallel_query}]
        
        start_time = datetime.now()
        result = await jib_ai.forward(chats, "parallel_test", parallel_query)
        end_time = datetime.now()
        
        processing_time = (end_time - start_time).total_seconds()
        
        chat_resp, token_dict, thought_dict = result
        tools_used = thought_dict.get('tools_used', [])
        
        print(f"\n✅ PARALLEL TEST RESULTS:")
        print(f"⏱️  Processing Time: {processing_time:.2f}s")
        print(f"🔧 Tools Executed: {len(tools_used)}")
        
        if len(tools_used) > 1:
            print(f"⚡ Multiple tools executed - parallel capability demonstrated")
            for i, tool in enumerate(tools_used, 1):
                print(f"  {i}. {tool['name']}")
        elif len(tools_used) == 1:
            print(f"🔄 Single tool executed: {tools_used[0]['name']}")
        else:
            print(f"💬 No tools used - direct response provided")
            
        print(f"📱 Response: {chat_resp.get('text', '')[:100]}...")
        
    except Exception as e:
        print(f"❌ Parallel test error: {e}")

if __name__ == "__main__":
    print("🎯 SONNET 4 BOT - CENTRALIZED TOOLS TESTING SUITE")
    print(f"📅 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("🔍 Watch the logs for detailed agent reasoning and tool execution steps!\n")
    
    # Run comprehensive tests
    asyncio.run(test_centralized_tools_comprehensive())
    
    # Run parallel execution test
    asyncio.run(test_parallel_execution())
    
    print(f"\n📅 Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("✨ All tests completed! Review the detailed logs above for agent insights.") 