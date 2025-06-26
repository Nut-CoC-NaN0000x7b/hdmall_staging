# 🚀 HDmall Jib AI - Sonnet 4 Production Agent

This directory contains a production-ready implementation of HDmall's Jib AI chatbot powered by **Claude Sonnet 4** with **Interleaved Thinking** capabilities.

## 🌟 Key Features

### 🧠 Advanced Reasoning
- **Interleaved Thinking**: Reasons between tool calls for better decision making
- **Extended Thinking**: Deep reasoning capabilities for complex queries
- **Parallel Tool Execution**: Executes independent operations simultaneously for maximum efficiency

### 🔧 Real Tools Integration
- **Real RAG System**: Connected to production knowledge base and search
- **Smart SQL Search**: Advanced filtering with category masking and retry logic
- **Production Cart System**: Real shopping cart operations
- **Handover Systems**: Integrated customer service and booking handovers

### 📊 Enhanced Monitoring
- **Detailed Logging**: Production-style logs with timestamps and structured output
- **Performance Tracking**: Response times, thinking blocks, tool usage analytics
- **Debug Endpoints**: Comprehensive debugging and health check capabilities

## 📁 File Structure

```
extended_thinking_test/
├── production_sonnet4_agent.py    # Main Sonnet 4 agent with real tools
├── api_integration.py             # Drop-in replacement for existing bot
├── api_routes_sonnet4.py          # Modified API routes for Sonnet 4
├── app_sonnet4.py                 # FastAPI app initialization
├── sonnet4_agent.py               # Original test implementation
└── README_PRODUCTION.md           # This file
```

## 🚀 Quick Start

### 1. **Test the Agent Locally**
```bash
cd extended_thinking_test
python production_sonnet4_agent.py --thinking-mode interleaved
```

### 2. **Run the API Server**
```bash
# From the root directory
python3 -m uvicorn extended_thinking_test.app_sonnet4:app --reload --host 0.0.0.0 --port 8000

# Or using the factory method
python3 -m uvicorn extended_thinking_test.app_sonnet4:create_app --factory --reload
```

### 3. **Access the API**
- **Main Chat**: `POST http://localhost:8000/chat`
- **API Docs**: `http://localhost:8000/docs`
- **Health Check**: `GET http://localhost:8000/health`
- **Agent Info**: `GET http://localhost:8000/agent-info`

## 🔄 Migration from Existing Bot

To switch your existing `api_routes.py` to use Sonnet 4:

### Option 1: Simple Import Replacement
```python
# BEFORE:
from bot import JibAI

# AFTER:
from extended_thinking_test.api_integration import ProductionJibAI as JibAI
```

### Option 2: Use the Modified Routes
```python
# Replace api_routes.py with api_routes_sonnet4.py
# All endpoints remain the same, enhanced with Sonnet 4 capabilities
```

## 🛠️ Configuration

### Environment Variables
Ensure these are set in your `.env` file:
```env
ANTHROPIC_API_KEY=your_anthropic_api_key
WORKSPACE_ID=your_workspace_id
PRIMARY_KEY=your_primary_key
SHORT_IO_API_KEY=your_short_io_api_key
```

### Thinking Modes
- **Interleaved** (default): Full reasoning between tool calls
- **Extended**: Basic extended reasoning at the start

## 📡 API Endpoints

### Core Endpoints
- `POST /chat` - Main chat interface
- `POST /chat/debug` - Debug with detailed response info
- `GET /health` - Health check
- `GET /agent-info` - Agent information

### Monitoring Endpoints
- `GET /stats` - Performance statistics
- `POST /test-sonnet4` - Capability testing
- `GET /ping` - Simple ping endpoint

### Example Chat Request
```json
{
  "room_id": "test-room",
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": "สนใจวัคซีน HPV ราคาไม่เกิน 15,000 บาท ใกล้กรุงเทพ"
        }
      ]
    }
  ]
}
```

## 🧠 Understanding Interleaved Thinking

### How It Works
1. **User Query** → Initial thinking about the request
2. **Tool Call** → Execute relevant tools (possibly in parallel)
3. **Reflection** → Analyze tool results and plan next steps
4. **Next Action** → Make additional tool calls if needed
5. **Final Response** → Comprehensive answer based on all information

### Example Flow
```
User: "หาแพคเกจตรวจสุขภาพ ราคาถูกที่สุด 5 อันดับแรก"

🧠 Thinking 1: User wants health checkup packages, sorted by price, limited to top 5
⚡ Parallel Execution:
   🔧 Tool 1: sql_search - Query for health checkup packages
   🔧 Tool 2: retrieval - Get category information

🧠 Thinking 2: Got results, but need to sort by price and limit to 5
🔧 Tool 3: sql_search - Sort results by price and limit to 5

🧠 Thinking 3: Now I have the top 5 cheapest packages, ready to respond
✅ Final Response: [Comprehensive answer with top 5 packages]
```

## 🔧 Tools Available

### Primary Tools
- **`retrieval`**: Search packages database with comprehensive information
- **`sql_search`**: Advanced filtering, sorting, price comparisons with category masking
- **`cart`**: Shopping cart operations (create, add, view, order)

### Handover Tools
- **`handover_to_cx`**: Transfer to customer service for complex issues
- **`handover_to_bk`**: Transfer to booking agent (requires name, phone, date)
- **`handover_asap`**: Immediate handover for sensitive topics (Lasik, HPV, etc.)

## 📊 Monitoring & Debugging

### Production Logs
```
14:30:15 [INFO] 🚀 [ITERATION-1] Invoking Sonnet-4 with Interleaved Thinking Mode
14:30:16 [INFO] 💭 [THINKING-1] Interleaved Reasoning:
14:30:16 [INFO]     User is asking about HPV vaccines under 15,000 baht near Bangkok
14:30:16 [INFO]     I should search for HPV vaccine packages and filter by price and location
14:30:17 [INFO] ⚡ [PARALLEL-EXECUTION] Executing 2 tools simultaneously
14:30:17 [INFO] 🛠️ [TOOL-1/2] retrieval
14:30:17 [INFO] 🛠️ [TOOL-2/2] sql_search
14:30:18 [INFO] ✅ [COMPLETION] Task completed in 1 iterations with 2 tool calls
```

### Debug Endpoint Response
```json
{
  "response": {"text": "..."},
  "token_usage": {
    "model": "claude-sonnet-4-20250514",
    "input_tokens": 1234,
    "output_tokens": 567,
    "reasoning_tokens": 890
  },
  "thinking_info": {
    "thinking_blocks": 3,
    "tools_used": 2,
    "iterations": 1,
    "interleaved_thinking": true
  },
  "agent_info": {
    "agent_type": "ProductionSonnet4Agent",
    "features": ["interleaved_thinking", "parallel_tool_calling", ...]
  }
}
```

## 🎯 Best Practices

### When to Use Interleaved Thinking
- ✅ Complex queries requiring multiple steps
- ✅ Price comparisons and filtering
- ✅ Multi-step booking processes
- ✅ Information gathering with follow-up questions

### When Extended Thinking is Sufficient
- ✅ Simple greetings
- ✅ Single package inquiries
- ✅ Basic information requests

### Performance Optimization
- Use parallel tool calls for independent operations
- Leverage category filtering for focused searches
- Monitor thinking blocks and iterations for efficiency

## 🚀 Production Deployment

### Server Command
```bash
python3 -m uvicorn extended_thinking_test.app_sonnet4:create_app --factory --reload --host 0.0.0.0 --port 8000
```

### Docker Deployment (if needed)
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
EXPOSE 8000
CMD ["python3", "-m", "uvicorn", "extended_thinking_test.app_sonnet4:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
```

## 🔍 Troubleshooting

### Common Issues
1. **Import Errors**: Ensure all paths are correct and src/ is in PYTHONPATH
2. **API Key Issues**: Verify ANTHROPIC_API_KEY is set correctly
3. **Global Storage**: Ensure global_storage is properly initialized
4. **Tool Execution**: Check RAG system initialization

### Debug Mode
```python
# Enable detailed logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Test agent directly
from production_sonnet4_agent import ProductionSonnet4Agent
agent = ProductionSonnet4Agent()
result = await agent.chat("test query", use_interleaved_thinking=True)
```

## 📈 Performance Metrics

The agent tracks:
- Response times
- Number of thinking blocks per query
- Tool usage patterns
- Iteration counts
- Error rates

Access via `GET /stats` endpoint for real-time monitoring.

---

**Ready to experience the next generation of AI reasoning with Sonnet 4 Interleaved Thinking! 🚀🧠** 