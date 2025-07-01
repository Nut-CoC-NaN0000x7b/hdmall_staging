import contextlib
import logging
import os
from typing import AsyncGenerator
from azure_logging_config import setup_azure_logging
import azure.identity.aio
import fastapi
#from azure.monitor.opentelemetry import configure_azure_monitor
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from environs import Env
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from azure.storage.blob import BlobServiceClient
import pandas as pd
import numpy as np
import json
import io
from globals import global_storage
import asyncio
import uvloop  # For better async performance



load_dotenv()
CONNECTION_STRING = os.getenv('CONNECTION_STRING')
CONTAINER_NAME = os.getenv('CONTAINER_NAME')
DEVICE = os.getenv('DEVICE')

def load_from_azure_blob(connection_string, container_name, blob_path):
    """
    Load files from Azure Blob Storage based on file extension.
    Supports .json, .npy, and .csv files.
    """
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    container_client = blob_service_client.get_container_client(container_name)
    blob_client = container_client.get_blob_client(blob_path)
    blob_data = blob_client.download_blob()
    
    if blob_path.endswith('.json'):
        content = blob_data.readall()
        return json.loads(content)
    elif blob_path.endswith('.npy'):
        if blob_path.startswith('index'):
            content = io.BytesIO(blob_data.readall())
            return np.load(content, allow_pickle=True)
        elif blob_path =='image_database.npy':
            content = io.BytesIO(blob_data.readall())
            return np.load(content, allow_pickle=True)
            
        else:
            content = io.BytesIO(blob_data.readall())
            return np.load(content)
            
    elif blob_path.endswith('.csv'):
        content = blob_data.readall().decode('utf-8')
        return pd.read_csv(io.StringIO(content))
    else:
        raise ValueError(f"Unsupported file type: {blob_path}")

logger = logging.getLogger("hdbot")

@contextlib.asynccontextmanager
async def lifespan(app: fastapi.FastAPI) -> AsyncGenerator[None, None]:
    # Initialize Azure-optimized logging first
    logger = setup_azure_logging(
        app_name="hdmall-jibai-bot",
        log_level=os.getenv('LOG_LEVEL', 'INFO'),
        enable_azure_monitor=True  # Will auto-detect Azure environment
    )
    
    # Set uvloop as the event loop policy for better performance
    if hasattr(asyncio, 'set_event_loop_policy') and uvloop:
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        logger.info("⚡ uvloop event loop policy enabled for better performance")
    
    # Load different file types TODO : change before deploy

    if DEVICE == 'azure':
        knowledge_base = load_from_azure_blob(CONNECTION_STRING, CONTAINER_NAME, "package.csv")
        
        embed_matrix = load_from_azure_blob(CONNECTION_STRING, CONTAINER_NAME, "embed_matrix_19112024.npy")
        doc_json = load_from_azure_blob(CONNECTION_STRING, CONTAINER_NAME, "doc_tokens_19112024.json")
        index_list = load_from_azure_blob(CONNECTION_STRING, CONTAINER_NAME, "index_list.npy")
    
        embed_matrix_plus = load_from_azure_blob(CONNECTION_STRING, CONTAINER_NAME, "emb_matrix_plus.npy")
        doc_json_plus = load_from_azure_blob(CONNECTION_STRING, CONTAINER_NAME, "doc_tokens_19112024_plus.json")
        index_list_plus = load_from_azure_blob(CONNECTION_STRING, CONTAINER_NAME, "index_list_plus.npy")

        web_recommendation_json = load_from_azure_blob(CONNECTION_STRING, CONTAINER_NAME, "web_recommendation.json")
        hl_embed = load_from_azure_blob(CONNECTION_STRING, CONTAINER_NAME, "hl_emb.npy")
        hl_docs = load_from_azure_blob(CONNECTION_STRING, CONTAINER_NAME, "hl_docs.json")
        brand_embed = load_from_azure_blob(CONNECTION_STRING, CONTAINER_NAME, "brand_emb.npy")
        brand_docs = load_from_azure_blob(CONNECTION_STRING, CONTAINER_NAME, "brand_docs.json")
        cat_embed = load_from_azure_blob(CONNECTION_STRING, CONTAINER_NAME, "cat_emb.npy")
        cat_docs = load_from_azure_blob(CONNECTION_STRING, CONTAINER_NAME, "cat_docs.json")
        tag_embed = load_from_azure_blob(CONNECTION_STRING, CONTAINER_NAME, "tag_emb.npy")
        tag_docs = load_from_azure_blob(CONNECTION_STRING, CONTAINER_NAME, "tag_docs.json")
        

    
    # Load files locally
    if DEVICE == 'local':
        #knowledge base
        knowledge_base = pd.read_csv("shared/rag/data/package.csv")
        #doc json
        with open("shared/rag/data/doc_tokens_19112024.json", "r") as f:
            doc_json = json.load(f)
        #embed matrix
        embed_matrix = np.load("shared/rag/data/embed_matrix_19112024.npy")
        index_list = np.load("shared/rag/data/index_list.npy", allow_pickle=True)
    
        #doc json plus
        with open("shared/rag/data/doc_tokens_19112024_plus.json", "r") as f:
            doc_json_plus = json.load(f)
        #   embed matrix plus
        embed_matrix_plus = np.load("shared/rag/data/emb_matrix_plus.npy")
        index_list_plus = np.load("shared/rag/data/index_list_plus.npy", allow_pickle=True)

        #Web recommendation
        with open("shared/rag/data/web_recommendation.json", "r") as f:
            web_recommendation_json = json.load(f)
        #hl_embeddings_matrix named hl_emb.npy
        hl_embed = np.load("shared/rag/data/hl_emb.npy")
        with open("shared/rag/data/hl_docs.json", "r") as f:
            hl_docs = json.load(f)
        #brand_embed named brand_emb.npy
        brand_embed = np.load("shared/rag/data/brand_emb.npy")
        with open("shared/rag/data/brand_docs.json", "r") as f:
            brand_docs = json.load(f)
        #category_embed named cat_emb.npy
        cat_embed = np.load("shared/rag/data/cat_emb.npy")
        with open("shared/rag/data/cat_docs.json", "r") as f:
            cat_docs = json.load(f)
        #tag_embed named tag_emb.npy
        with open("shared/rag/data/tag_docs.json", "r") as f:
            tag_docs = json.load(f)
        tag_embed = np.load("shared/rag/data/tag_emb.npy")




    
    #assigning
    global_storage.knowledge_base = knowledge_base
    #global_storage.image_base = image_base 
    
    global_storage.doc_json = doc_json
    global_storage.embed_matrix = embed_matrix
    global_storage.index_list = index_list
    
    global_storage.embed_matrix_plus = embed_matrix_plus
    global_storage.doc_json_plus = doc_json_plus
    global_storage.index_list_plus = index_list_plus

    #Assigning
    global_storage.web_recommendation_json = web_recommendation_json
    global_storage.hl_embed = hl_embed
    global_storage.hl_docs = hl_docs
    global_storage.brand_embed = brand_embed
    global_storage.brand_docs = brand_docs
    global_storage.cat_embed = cat_embed
    global_storage.cat_docs = cat_docs
    global_storage.tag_embed = tag_embed
    global_storage.tag_docs = tag_docs
    
    #print(f"In LIFESPANE :{global_storage.embed_matrix.shape}")
    
    yield
    
    # Clean up the credentials file after the app shuts down
    #if os.path.exists(creds_path):
    #    os.remove(creds_path)
        
    # Clean up any remaining aiohttp sessions
    try:
        from api_routes import _rag_instance
        if _rag_instance:
            await _rag_instance.close_session()
    except:
        pass

def create_app(scope=None) -> fastapi.FastAPI:  # Add optional scope parameter
    env = Env()
    app = fastapi.FastAPI(
        title="JibAI Chat API",
        description="API for chatting with JibAI RAG model",
        docs_url="/docs",
        lifespan=lifespan
    )
    
    # Optimized CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add middleware for better performance monitoring
    @app.middleware("http")
    async def add_process_time_header(request, call_next):
        import time
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        return response
    
    import api_routes
    app.include_router(api_routes.router)
    return app

# For ASGI compatibility
#app = create_app()
