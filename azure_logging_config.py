#!/usr/bin/env python3
"""
Azure-optimized logging configuration for HDmall JibAI Bot
Supports both local development and Azure App Service deployment
"""

import logging
import json
import os
import sys
from datetime import datetime
from typing import Dict, Any
import pytz

class AzureJSONFormatter(logging.Formatter):
    """
    Custom JSON formatter optimized for Azure Log Analytics and Application Insights
    """
    
    def __init__(self):
        super().__init__()
        self.thailand_tz = pytz.timezone('Asia/Bangkok')
    
    def format(self, record: logging.LogRecord) -> str:
        # Get Thailand time
        thailand_time = datetime.now(self.thailand_tz)
        
        # Base log structure
        log_entry = {
            "timestamp": thailand_time.isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "thailand_hour": thailand_time.hour,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        if hasattr(record, 'room_id'):
            log_entry["room_id"] = record.room_id
        if hasattr(record, 'user_id'):
            log_entry["user_id"] = record.user_id
        if hasattr(record, 'tool_name'):
            log_entry["tool_name"] = record.tool_name
        if hasattr(record, 'business_hours'):
            log_entry["business_hours"] = record.business_hours
        if hasattr(record, 'token_count'):
            log_entry["token_count"] = record.token_count
        if hasattr(record, 'processing_time'):
            log_entry["processing_time_ms"] = record.processing_time
        
        # Parse structured log messages (emoji-based categories)
        message = record.getMessage()
        if message.startswith('🕒'):
            log_entry["category"] = "time_tracking"
        elif message.startswith('🔧'):
            log_entry["category"] = "tools"
        elif message.startswith('🤖'):
            log_entry["category"] = "ai_processing"
        elif message.startswith('👥'):
            log_entry["category"] = "human_handover"
        elif message.startswith('🖼️'):
            log_entry["category"] = "image_processing"
        elif message.startswith('💬'):
            log_entry["category"] = "chat"
        elif message.startswith('⚠️') or message.startswith('❌'):
            log_entry["category"] = "error"
        elif message.startswith('✅'):
            log_entry["category"] = "success"
        elif message.startswith('🌙'):
            log_entry["category"] = "after_hours"
        else:
            log_entry["category"] = "general"
        
        return json.dumps(log_entry, ensure_ascii=False)

class AzureConsoleFormatter(logging.Formatter):
    """
    Human-readable formatter for local development and console output
    """
    
    def __init__(self):
        super().__init__()
        self.thailand_tz = pytz.timezone('Asia/Bangkok')
    
    def format(self, record: logging.LogRecord) -> str:
        thailand_time = datetime.now(self.thailand_tz)
        timestamp = thailand_time.strftime('%H:%M:%S')
        
        # Color codes for different log levels
        colors = {
            'DEBUG': '\033[36m',    # Cyan
            'INFO': '\033[32m',     # Green
            'WARNING': '\033[33m',  # Yellow
            'ERROR': '\033[31m',    # Red
            'CRITICAL': '\033[35m', # Magenta
        }
        reset = '\033[0m'
        
        color = colors.get(record.levelname, '')
        
        # Format: [HH:MM:SS] LEVEL module.function:line - message
        formatted = f"[{timestamp}] {color}{record.levelname:8}{reset} {record.name}.{record.funcName}:{record.lineno} - {record.getMessage()}"
        
        # Add extra context if present
        extras = []
        if hasattr(record, 'room_id'):
            extras.append(f"room={record.room_id}")
        if hasattr(record, 'tool_name'):
            extras.append(f"tool={record.tool_name}")
        if hasattr(record, 'processing_time'):
            extras.append(f"time={record.processing_time}ms")
        
        if extras:
            formatted += f" [{', '.join(extras)}]"
        
        return formatted

def setup_azure_logging(
    app_name: str = "hdmall-jibai",
    log_level: str = None,
    enable_azure_monitor: bool = None
) -> logging.Logger:
    """
    Setup Azure-optimized logging configuration
    
    Args:
        app_name: Application name for logging context
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        enable_azure_monitor: Enable Azure Application Insights integration
    
    Returns:
        Configured root logger
    """
    
    # Determine environment and configuration
    is_azure = os.getenv('WEBSITE_SITE_NAME') is not None  # Azure App Service indicator
    is_local = not is_azure
    
    # Default configurations
    if log_level is None:
        log_level = os.getenv('LOG_LEVEL', 'DEBUG' if is_local else 'INFO')
    
    if enable_azure_monitor is None:
        enable_azure_monitor = is_azure and os.getenv('APPLICATIONINSIGHTS_CONNECTION_STRING') is not None
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler (always present)
    console_handler = logging.StreamHandler(sys.stdout)
    
    if is_azure:
        # Azure: Use JSON formatter for structured logging
        console_handler.setFormatter(AzureJSONFormatter())
        console_handler.setLevel(logging.INFO)
    else:
        # Local: Use human-readable formatter
        console_handler.setFormatter(AzureConsoleFormatter())
        console_handler.setLevel(logging.DEBUG)
    
    root_logger.addHandler(console_handler)
    
    # Azure Application Insights integration
    if enable_azure_monitor:
        try:
            from azure.monitor.opentelemetry import configure_azure_monitor
            from opentelemetry import trace
            from opentelemetry.instrumentation.logging import LoggingInstrumentor
            
            # Configure Azure Monitor
            configure_azure_monitor(
                connection_string=os.getenv('APPLICATIONINSIGHTS_CONNECTION_STRING'),
                resource_attributes={
                    "service.name": app_name,
                    "service.version": os.getenv('APP_VERSION', '1.0.0'),
                    "deployment.environment": os.getenv('ENVIRONMENT', 'production'),
                }
            )
            
            # Enable logging instrumentation
            LoggingInstrumentor().instrument(set_logging_format=True)
            
            # Get tracer for custom spans
            tracer = trace.get_tracer(__name__)
            
            root_logger.info("✅ Azure Application Insights integration enabled")
            
        except ImportError:
            root_logger.warning("⚠️ Azure Monitor packages not available - skipping Application Insights integration")
        except Exception as e:
            root_logger.error(f"❌ Failed to configure Azure Monitor: {e}")
    
    # Configure specific loggers
    configure_component_loggers(root_logger.level)
    
    # Log configuration summary
    root_logger.info(f"🚀 Logging configured for {app_name}")
    root_logger.info(f"📍 Environment: {'Azure' if is_azure else 'Local'}")
    root_logger.info(f"📊 Log Level: {log_level}")
    root_logger.info(f"🔍 Azure Monitor: {'Enabled' if enable_azure_monitor else 'Disabled'}")
    
    return root_logger

def configure_component_loggers(base_level: int):
    """Configure specific loggers for different components"""
    
    # JibAI specific loggers
    logging.getLogger('sonnet4_bot').setLevel(base_level)
    logging.getLogger('api_routes').setLevel(base_level)
    logging.getLogger('tools').setLevel(base_level)
    logging.getLogger('RAG').setLevel(base_level)
    logging.getLogger('cart').setLevel(base_level)
    
    # Third-party loggers (reduce verbosity)
    logging.getLogger('anthropic').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('azure').setLevel(logging.WARNING)
    logging.getLogger('opentelemetry').setLevel(logging.WARNING)
    logging.getLogger('uvicorn').setLevel(logging.INFO)

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with Azure-specific context
    
    Args:
        name: Logger name (usually __name__)
    
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)

def log_business_hours_status(logger: logging.Logger, current_hour: int, is_business_hours: bool):
    """Helper function to log business hours status consistently"""
    thailand_tz = pytz.timezone('Asia/Bangkok')
    current_time = datetime.now(thailand_tz)
    
    extra = {
        'business_hours': is_business_hours,
        'thailand_hour': current_hour
    }
    
    if is_business_hours:
        logger.info(f"🕒 [BUSINESS-HOURS] Human agents available (Hour: {current_hour}:00)", extra=extra)
    else:
        logger.info(f"🌙 [AFTER-HOURS] No human agents (Hour: {current_hour}:00)", extra=extra)

def log_tool_execution(logger: logging.Logger, tool_name: str, execution_time: float, success: bool, room_id: str = None):
    """Helper function to log tool execution consistently"""
    extra = {
        'tool_name': tool_name,
        'processing_time': round(execution_time * 1000, 2),  # Convert to milliseconds
        'room_id': room_id
    }
    
    if success:
        logger.info(f"🔧 [TOOL-SUCCESS] {tool_name} executed successfully", extra=extra)
    else:
        logger.error(f"❌ [TOOL-ERROR] {tool_name} execution failed", extra=extra)

def log_chat_interaction(logger: logging.Logger, room_id: str, message_count: int, token_count: int = None):
    """Helper function to log chat interactions consistently"""
    extra = {
        'room_id': room_id,
        'message_count': message_count
    }
    
    if token_count:
        extra['token_count'] = token_count
    
    logger.info(f"💬 [CHAT] Processing {message_count} messages", extra=extra)

# Environment-specific configurations
AZURE_LOG_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'azure_json': {
            '()': AzureJSONFormatter,
        },
        'console': {
            '()': AzureConsoleFormatter,
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'azure_json' if os.getenv('WEBSITE_SITE_NAME') else 'console',
            'stream': 'ext://sys.stdout'
        }
    },
    'root': {
        'level': os.getenv('LOG_LEVEL', 'INFO'),
        'handlers': ['console']
    }
}

if __name__ == "__main__":
    # Test the logging configuration
    logger = setup_azure_logging("test-app", "DEBUG", False)
    
    # Test different log types
    logger.debug("🔍 Debug message")
    logger.info("✅ Info message")
    logger.warning("⚠️ Warning message")
    logger.error("❌ Error message")
    
    # Test structured logging
    log_business_hours_status(logger, 14, True)
    log_tool_execution(logger, "retrieval", 0.5, True, "test-room-123")
    log_chat_interaction(logger, "test-room-123", 3, 1500) 