# Test Moving Cache Implementation for Sonnet4 Bot
# This shows how the cache breakpoint moves through conversations

def simulate_moving_cache():
    """Simulate how the moving cache works in practice"""
    
    # Simulated conversation history
    conversation_turns = [
        # Turn 1
        [
            {"role": "user", "content": [{"type": "text", "text": "Hello, what is HDmall?"}]}
        ],
        
        # Turn 2 (after assistant response)
        [
            {"role": "user", "content": [{"type": "text", "text": "Hello, what is HDmall?"}]},
            {"role": "assistant", "content": [{"type": "text", "text": "HDmall is a health platform..."}]},
            {"role": "user", "content": [{"type": "text", "text": "Tell me about health checkups"}]}
        ],
        
        # Turn 3 (after agentic tool use)
        [
            {"role": "user", "content": [{"type": "text", "text": "Hello, what is HDmall?"}]},
            {"role": "assistant", "content": [{"type": "text", "text": "HDmall is a health platform..."}]},
            {"role": "user", "content": [{"type": "text", "text": "Tell me about health checkups"}]},
            {"role": "assistant", "content": [
                {"type": "thinking", "content": "I should search for health checkup packages..."},
                {"type": "tool_use", "id": "tool_1", "name": "retrieval", "input": {"search_keyword": "health checkup"}}
            ]},
            {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "tool_1", "content": "Found 5 packages..."}]},
            {"role": "assistant", "content": [{"type": "text", "text": "Here are some great health checkup options..."}]},
            {"role": "user", "content": [{"type": "text", "text": "What about the prices?"}]}
        ]
    ]
    
    print("🚀 Simulating Moving Cache Implementation\n")
    
    for turn, messages in enumerate(conversation_turns, 1):
        print(f"{'='*60}")
        print(f"TURN {turn}: Processing {len(messages)} messages")
        print(f"{'='*60}")
        
        # Simulate _apply_conversation_caching
        cached_messages = apply_conversation_caching_demo(messages)
        
        # Show the result
        for i, msg in enumerate(cached_messages, 1):
            role = msg.get("role", "unknown")
            content = msg.get("content", [])
            
            # Check if any content has cache_control
            has_cache = False
            for content_block in content:
                if isinstance(content_block, dict) and content_block.get("cache_control"):
                    has_cache = True
                    break
            
            cache_indicator = "💾 [CACHED]" if has_cache else "        "
            content_preview = str(content)[:50] + "..." if len(str(content)) > 50 else str(content)
            print(f"  {cache_indicator} Message {i} ({role}): {content_preview}")
        
        # Show token economics
        total_messages = len(messages)
        estimated_tokens = total_messages * 100  # Rough estimate
        
        if turn == 1:
            cache_read_tokens = 0
            cache_write_tokens = estimated_tokens
        else:
            cache_read_tokens = (total_messages - 2) * 100  # Previous messages cached
            cache_write_tokens = 200  # New assistant + user turn
        
        cost_savings = (cache_read_tokens * 0.9) if cache_read_tokens > 0 else 0  # 90% savings on cached tokens
        
        print(f"\n📊 Estimated Token Economics:")
        print(f"   Total tokens: ~{estimated_tokens}")
        if cache_read_tokens > 0:
            print(f"   Cache read: ~{cache_read_tokens} tokens (10x cheaper!)")
            print(f"   Cache write: ~{cache_write_tokens} tokens")
            print(f"   💰 Cost savings: ~{cost_savings:.0f} tokens worth")
        else:
            print(f"   Cache write: ~{cache_write_tokens} tokens (first turn)")
        
        print()

def apply_conversation_caching_demo(messages):
    """Demo version of _apply_conversation_caching"""
    if not messages:
        return messages
    
    # Remove existing cache controls (simulate _remove_existing_cache_controls)
    cleaned_messages = []
    removed_count = 0
    
    for msg in messages:
        cleaned_msg = msg.copy()
        if "content" in cleaned_msg and isinstance(cleaned_msg["content"], list):
            cleaned_content = []
            for content_block in cleaned_msg["content"]:
                clean_block = content_block.copy()
                if clean_block.pop("cache_control", None):
                    removed_count += 1
                cleaned_content.append(clean_block)
            cleaned_msg["content"] = cleaned_content
        cleaned_messages.append(cleaned_msg)
    
    if removed_count > 0:
        print(f"🔄 [CACHE-CLEANUP] Removed {removed_count} old cache_control markers")
    
    # Add cache_control to the last user message
    last_user_idx = -1
    for i in range(len(cleaned_messages) - 1, -1, -1):
        if cleaned_messages[i].get("role") == "user":
            last_user_idx = i
            break
    
    if last_user_idx >= 0:
        msg = cleaned_messages[last_user_idx]
        content = msg.get("content", [])
        
        if content and isinstance(content, list):
            last_content_block = content[-1]
            if isinstance(last_content_block, dict) and last_content_block.get("type") == "text":
                last_content_block["cache_control"] = {"type": "ephemeral"}
                print(f"💾 [CACHE-APPLIED] Added moving cache breakpoint to message {last_user_idx + 1}")
    
    return cleaned_messages

if __name__ == "__main__":
    simulate_moving_cache() 