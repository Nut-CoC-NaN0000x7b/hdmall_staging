# Debug Script for Conversation Caching
# Tests the cache logic without making API calls

def debug_apply_conversation_caching(messages):
    """Simulate the conversation caching logic"""
    print(f"🔍 [DEBUG] Starting with {len(messages)} messages")
    
    # Show message structure
    for i, msg in enumerate(messages):
        role = msg.get("role", "unknown")
        content = msg.get("content", [])
        print(f"  Message {i+1} ({role}): {len(content) if isinstance(content, list) else 0} content blocks")
        
        if isinstance(content, list):
            for j, block in enumerate(content):
                if isinstance(block, dict):
                    block_type = block.get("type", "unknown")
                    has_cache = "cache_control" in block
                    cache_indicator = "💾" if has_cache else "  "
                    text_preview = block.get("text", str(block))[:30] + "..."
                    print(f"    {cache_indicator} Block {j+1} ({block_type}): {text_preview}")
                else:
                    print(f"      Block {j+1} (non-dict): {type(block).__name__}")
    
    # Find last user message
    last_user_idx = -1
    for i in range(len(messages) - 1, -1, -1):
        if messages[i].get("role") == "user":
            last_user_idx = i
            break
    
    print(f"🔍 [DEBUG] Last user message at index: {last_user_idx}")
    
    if last_user_idx >= 0:
        msg = messages[last_user_idx]
        content = msg.get("content", [])
        
        if content and isinstance(content, list):
            last_block = content[-1]
            if isinstance(last_block, dict) and last_block.get("type") == "text":
                last_block["cache_control"] = {"type": "ephemeral"}
                print(f"✅ [DEBUG] Added cache control to: {last_block.get('text', '')[:50]}...")
                return True
            else:
                print(f"❌ [DEBUG] Cannot add cache - last block: {last_block}")
                return False
        else:
            print(f"❌ [DEBUG] Content is not a list: {content}")
            return False
    else:
        print(f"❌ [DEBUG] No user messages found")
        return False

# Test cases
test_cases = [
    # Case 1: Simple conversation
    [
        {"role": "user", "content": [{"type": "text", "text": "Hello"}]},
        {"role": "assistant", "content": [{"type": "text", "text": "Hi there!"}]},
        {"role": "user", "content": [{"type": "text", "text": "How are you?"}]}
    ],
    
    # Case 2: With thinking blocks
    [
        {"role": "user", "content": [{"type": "text", "text": "Hello"}]},
        {"role": "assistant", "content": [
            {"type": "thinking", "content": "User said hello"},
            {"type": "text", "text": "Hi there!"}
        ]},
        {"role": "user", "content": [{"type": "text", "text": "How are you?"}]}
    ],
    
    # Case 3: With tool use
    [
        {"role": "user", "content": [{"type": "text", "text": "Search for something"}]},
        {"role": "assistant", "content": [
            {"type": "thinking", "content": "I should search"},
            {"type": "tool_use", "id": "tool_1", "name": "search", "input": {"query": "test"}}
        ]},
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "tool_1", "content": "Found results"}]},
        {"role": "user", "content": [{"type": "text", "text": "Tell me more"}]}
    ]
]

if __name__ == "__main__":
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"TEST CASE {i}")
        print(f"{'='*60}")
        success = debug_apply_conversation_caching(test_case)
        print(f"Result: {'✅ Success' if success else '❌ Failed'}") 