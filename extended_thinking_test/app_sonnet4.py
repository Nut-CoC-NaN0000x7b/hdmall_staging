"""
FastAPI App for Sonnet 4 Agent
===============================
This file creates a FastAPI application using the Production Sonnet 4 Agent.

Usage:
python3 -m uvicorn extended_thinking_test.app_sonnet4:app --reload --host 0.0.0.0 --port 8000

Or from the extended_thinking_test directory:
python3 -m uvicorn app_sonnet4:app --reload --host 0.0.0.0 --port 8000
"""

import sys
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the Sonnet 4 API routes
from api_routes_sonnet4 import router

def create_app() -> FastAPI:
    """
    Factory function to create FastAPI app with Sonnet 4 Agent
    
    This function can be used with uvicorn's --factory option:
    python3 -m uvicorn extended_thinking_test.app_sonnet4:create_app --factory --reload
    """
    
    # Create FastAPI app
    app = FastAPI(
        title="HDmall Jib AI - Sonnet 4 Edition",
        description="""
        🚀 **HDmall Jib AI powered by Claude Sonnet 4 with Interleaved Thinking**
        
        ## New Features:
        - 🧠 **Interleaved Thinking**: Reasons between tool calls for better decision making
        - ⚡ **Parallel Tool Execution**: Executes independent operations simultaneously  
        - 🔧 **Real Tools Integration**: Connected to production RAG, cart, and handover systems
        - 🎯 **Smart SQL Search**: Advanced filtering with category masking and retry logic
        - 📊 **Enhanced Monitoring**: Detailed performance and thinking analytics
        
        ## API Endpoints:
        - `POST /chat` - Main chat interface with Sonnet 4
        - `POST /chat/debug` - Debug endpoint with detailed response info
        - `GET /agent-info` - Get information about the current agent
        - `GET /health` - Health check endpoint
        - `GET /stats` - Performance statistics
        - `POST /test-sonnet4` - Test Sonnet 4 capabilities
        
        ## Thinking Modes:
        - **Interleaved Thinking** (default): Reasons between each tool call
        - **Extended Thinking**: Basic extended reasoning at the beginning
        
        ## Tools Available:
        - `retrieval`: Search packages database
        - `sql_search`: Advanced filtering and sorting
        - `cart`: Shopping cart operations
        - `handover_to_cx`: Customer service handover
        - `handover_to_bk`: Booking agent handover
        - `handover_asap`: Immediate handover for sensitive topics
        """,
        version="2.0.0-sonnet4",
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include the Sonnet 4 router
    app.include_router(router)
    
    # Add startup event
    @app.on_event("startup")
    async def startup_event():
        print("🚀 HDmall Jib AI - Sonnet 4 Edition starting up!")
        print("🧠 Interleaved thinking enabled")
        print("⚡ Parallel tool execution ready")
        print("🔧 Real tools integration active")
        print("📊 Enhanced monitoring enabled")
        print("🎯 Ready to serve requests!")
    
    # Add shutdown event
    @app.on_event("shutdown")
    async def shutdown_event():
        print("🛑 HDmall Jib AI - Sonnet 4 Edition shutting down")
    
    return app

# Create app instance for direct usage
app = create_app()

# Health check endpoint at root level
@app.get("/ping")
async def ping():
    """Simple ping endpoint"""
    return {"status": "ok", "agent": "sonnet4", "message": "Pong! 🚀🧠"}

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting HDmall Jib AI - Sonnet 4 Edition")
    print("🧠 Interleaved thinking enabled")
    print("📡 Server starting on http://localhost:8000")
    print("📖 API docs available at http://localhost:8000/docs")
    
    uvicorn.run(
        "app_sonnet4:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["extended_thinking_test", "src"],
        log_level="info"
    ) 