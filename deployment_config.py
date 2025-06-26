# deployment_config.py
"""
Production deployment configuration for Azure
Optimized for handling 100-200 requests per minute
"""

import os
from typing import Dict, Any

class ProductionConfig:
    """Production configuration optimized for high load"""
    
    # Uvicorn/Gunicorn settings
    UVICORN_CONFIG = {
        "host": "0.0.0.0",
        "port": int(os.getenv("PORT", 8000)),
        "workers": int(os.getenv("WORKERS", 4)),  # Adjust based on CPU cores
        "worker_class": "uvicorn.workers.UvicornWorker",
        "worker_connections": 1000,
        "max_requests": 1000,  # Restart workers after 1000 requests
        "max_requests_jitter": 100,
        "timeout": 240,  # Match Azure timeout
        "keepalive": 5,
        "preload_app": True,  # Important for sharing global_storage
    }
    
    # FastAPI settings
    FASTAPI_CONFIG = {
        "title": "JibAI Chat API - Production",
        "description": "Production API for chatting with JibAI RAG model",
        "docs_url": None,  # Disable docs in production
        "redoc_url": None,  # Disable redoc in production
    }
    
    # Connection pooling settings
    CONNECTION_LIMITS = {
        "max_connections": 100,
        "max_keepalive_connections": 20,
        "keepalive_expiry": 5.0,
    }
    
    # Timeout settings
    TIMEOUTS = {
        "claude_api": 120,  # 2 minutes for Claude API
        "geocoding_api": 10,  # 10 seconds for geocoding
        "http_client": 30,  # 30 seconds for HTTP clients
    }
    
    # Cache settings
    CACHE_CONFIG = {
        "geocoding_cache_size": 1000,
        "search_cache_ttl": 300,  # 5 minutes
    }
    
    # Retry settings
    RETRY_CONFIG = {
        "max_attempts": 3,  # Reduced from 15 to 3
        "max_wait_time": 60,  # Reduced from 200 to 60
        "exponential_base": 2,
    }

def get_gunicorn_config() -> Dict[str, Any]:
    """Get Gunicorn configuration for production deployment"""
    config = ProductionConfig()
    return {
        "bind": f"{config.UVICORN_CONFIG['host']}:{config.UVICORN_CONFIG['port']}",
        "workers": config.UVICORN_CONFIG["workers"],
        "worker_class": config.UVICORN_CONFIG["worker_class"],
        "worker_connections": config.UVICORN_CONFIG["worker_connections"],
        "max_requests": config.UVICORN_CONFIG["max_requests"],
        "max_requests_jitter": config.UVICORN_CONFIG["max_requests_jitter"],
        "timeout": config.UVICORN_CONFIG["timeout"],
        "keepalive": config.UVICORN_CONFIG["keepalive"],
        "preload_app": config.UVICORN_CONFIG["preload_app"],
        "access_log_format": '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s',
        "accesslog": "-",
        "errorlog": "-",
        "loglevel": "info",
    }

# Azure-specific environment variables to set
AZURE_ENV_VARS = {
    "PYTHONUNBUFFERED": "1",
    "PYTHONDONTWRITEBYTECODE": "1",
    "WORKERS": "4",  # Adjust based on your Azure plan
    "WEB_CONCURRENCY": "4",
    "MAX_WORKERS": "4",
    "TIMEOUT": "240",
} 