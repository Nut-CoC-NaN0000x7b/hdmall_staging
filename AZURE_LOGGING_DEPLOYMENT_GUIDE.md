# 🚀 Azure Logging Deployment Guide for HDmall JibAI Bot

## 📋 Overview

This guide covers the complete setup for Azure-optimized logging that provides:
- **Structured JSON logging** for Azure Log Analytics
- **Application Insights integration** for monitoring and alerting
- **Thailand timezone support** for business hours tracking
- **Tool execution tracking** with performance metrics
- **Business hours monitoring** for after-hours support
- **Local development friendly** with colored console output

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Azure Logging Stack                      │
├─────────────────────────────────────────────────────────────┤
│  Local Development          │  Azure Production            │
│  ┌─────────────────────┐    │  ┌─────────────────────────┐  │
│  │ Colored Console     │    │  │ JSON Structured Logs   │  │
│  │ Human Readable      │    │  │ Azure Log Analytics    │  │
│  │ DEBUG Level         │    │  │ Application Insights   │  │
│  └─────────────────────┘    │  └─────────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│               Common Features                               │
│  • Thailand timezone tracking                              │
│  • Business hours detection                                │
│  • Tool execution metrics                                  │
│  • Emoji-based categorization                             │
│  • Room ID tracking                                        │
│  • Performance monitoring                                  │
└─────────────────────────────────────────────────────────────┘
```

## 🛠️ Implementation Steps

### 1. Install Dependencies

Add to your `requirements.txt`:

```bash
# Copy from requirements-azure-logging.txt
azure-monitor-opentelemetry>=1.6.0
opentelemetry-api>=1.20.0
opentelemetry-sdk>=1.20.0
opentelemetry-instrumentation>=0.41b0
opentelemetry-instrumentation-logging>=0.41b0
opentelemetry-instrumentation-fastapi>=0.41b0
opentelemetry-instrumentation-httpx>=0.41b0
azure-storage-blob>=12.24.0
azure-identity>=1.16.0
pytz>=2024.1
```

### 2. Environment Variables

Set these environment variables in Azure App Service:

```bash
# Logging Configuration
LOG_LEVEL=INFO                           # DEBUG, INFO, WARNING, ERROR, CRITICAL
ENVIRONMENT=production                   # development, staging, production
APP_VERSION=1.0.0                       # Your app version

# Azure Application Insights (required for monitoring)
APPLICATIONINSIGHTS_CONNECTION_STRING=InstrumentationKey=your-key;IngestionEndpoint=https://your-region.in.applicationinsights.azure.com/;LiveEndpoint=https://your-region.livediagnostics.monitor.azure.com/

# Azure App Service (automatically set by Azure)
WEBSITE_SITE_NAME=your-app-name         # Auto-set by Azure
```

### 3. Azure Resources Setup

#### A. Create Application Insights Resource

```bash
# Using Azure CLI
az monitor app-insights component create \
  --app hdmall-jibai-insights \
  --location eastus \
  --resource-group your-resource-group \
  --application-type web
```

#### B. Get Connection String

```bash
# Get the connection string
az monitor app-insights component show \
  --app hdmall-jibai-insights \
  --resource-group your-resource-group \
  --query connectionString -o tsv
```

### 4. Code Integration

The logging is already integrated into your codebase:

- ✅ `azure_logging_config.py` - Main logging configuration
- ✅ `sonnet4_bot.py` - Updated to use Azure logging
- ✅ `__init__.py` - Logging initialization during app startup

## 📊 Log Structure

### Local Development Format (Human Readable)
```
[17:43:24] INFO     sonnet4_bot.get_tool_definitions:67 - 🕒 [BUSINESS-HOURS] Human agents available (Hour: 14:00) [room=room123, tool=retrieval, time=500.0ms]
```

### Azure Production Format (JSON)
```json
{
  "timestamp": "2024-12-26T17:43:24+07:00",
  "level": "INFO",
  "logger": "sonnet4_bot",
  "message": "🕒 [BUSINESS-HOURS] Human agents available (Hour: 14:00)",
  "module": "sonnet4_bot",
  "function": "get_tool_definitions",
  "line": 67,
  "thailand_hour": 17,
  "category": "time_tracking",
  "business_hours": true,
  "room_id": "room123",
  "tool_name": "retrieval",
  "processing_time_ms": 500.0
}
```

## 🎯 Log Categories

The system automatically categorizes logs based on emoji prefixes:

| Emoji | Category | Description | Azure Query |
|-------|----------|-------------|-------------|
| 🕒 | `time_tracking` | Business hours, timezone info | `category == "time_tracking"` |
| 🔧 | `tools` | Tool execution, availability | `category == "tools"` |
| 🤖 | `ai_processing` | AI responses, thinking | `category == "ai_processing"` |
| 👥 | `human_handover` | Agent handovers | `category == "human_handover"` |
| 🖼️ | `image_processing` | Image analysis, URLs | `category == "image_processing"` |
| 💬 | `chat` | Chat interactions | `category == "chat"` |
| ⚠️❌ | `error` | Errors, warnings | `category == "error"` |
| ✅ | `success` | Successful operations | `category == "success"` |
| 🌙 | `after_hours` | After-hours operations | `category == "after_hours"` |

## 📈 Azure Log Analytics Queries

### Monitor Business Hours Status
```kql
traces
| where category == "time_tracking"
| summarize count() by business_hours, bin(timestamp, 1h)
| render timechart
```

### Tool Performance Monitoring
```kql
traces
| where category == "tools"
| where isnotnull(processing_time_ms)
| summarize avg(processing_time_ms), max(processing_time_ms) by tool_name
| order by avg_processing_time_ms desc
```

### After-Hours Activity
```kql
traces
| where category == "after_hours" or thailand_hour between (1 .. 8)
| summarize count() by bin(timestamp, 1h)
| render timechart
```

### Error Tracking
```kql
traces
| where category == "error" or level in ("ERROR", "CRITICAL")
| summarize count() by tostring(message), bin(timestamp, 15m)
| order by timestamp desc
```

### Room Activity Monitoring
```kql
traces
| where isnotnull(room_id)
| summarize 
    message_count = count(),
    unique_tools = dcount(tool_name),
    avg_processing_time = avg(processing_time_ms)
    by room_id
| order by message_count desc
```

## 🚨 Alerting Rules

### 1. High Error Rate Alert
```kql
traces
| where category == "error"
| summarize error_count = count() by bin(timestamp, 5m)
| where error_count > 10
```

### 2. Tool Performance Degradation
```kql
traces
| where category == "tools" and isnotnull(processing_time_ms)
| summarize avg_time = avg(processing_time_ms) by tool_name, bin(timestamp, 10m)
| where avg_time > 5000  // Alert if tools take > 5 seconds
```

### 3. After-Hours Human Agent Requests
```kql
traces
| where category == "human_handover" and thailand_hour between (1 .. 8)
| summarize count() by bin(timestamp, 1h)
```

## 🔧 Deployment Checklist

### Pre-Deployment
- [ ] Add dependencies to `requirements.txt`
- [ ] Set environment variables in Azure App Service
- [ ] Create Application Insights resource
- [ ] Test logging configuration locally

### Azure App Service Configuration
- [ ] Set `LOG_LEVEL=INFO` (or `DEBUG` for troubleshooting)
- [ ] Set `APPLICATIONINSIGHTS_CONNECTION_STRING`
- [ ] Set `ENVIRONMENT=production`
- [ ] Verify `WEBSITE_SITE_NAME` is auto-set

### Post-Deployment Verification
- [ ] Check Application Insights for incoming telemetry
- [ ] Verify JSON log format in Azure Log Analytics
- [ ] Test business hours detection
- [ ] Confirm tool execution logging
- [ ] Set up alerting rules

## 🔍 Troubleshooting

### Common Issues

1. **No logs in Application Insights**
   - Check `APPLICATIONINSIGHTS_CONNECTION_STRING` is set correctly
   - Verify Application Insights resource exists
   - Check if logs appear in container logs first

2. **Logs not structured properly**
   - Ensure `WEBSITE_SITE_NAME` environment variable is set (Azure auto-sets this)
   - Check if Azure environment detection is working

3. **Missing business hours data**
   - Verify Thailand timezone is working: `python -c "import pytz; print(pytz.timezone('Asia/Bangkok'))"`
   - Check if `thailand_hour` field appears in logs

4. **Tool execution not logged**
   - Ensure tools are using the helper functions: `log_tool_execution()`
   - Check if `tool_name` and `processing_time` fields are present

### Debug Commands

```bash
# Test logging configuration
python azure_logging_config.py

# Check Azure environment detection
python -c "import os; print('Azure:', os.getenv('WEBSITE_SITE_NAME') is not None)"

# Verify Thailand time
python -c "import pytz; from datetime import datetime; print(datetime.now(pytz.timezone('Asia/Bangkok')))"
```

## 📚 Best Practices

1. **Use Helper Functions**: Always use `log_business_hours_status()`, `log_tool_execution()`, etc.
2. **Include Context**: Add `room_id`, `tool_name`, and timing info to logs
3. **Structured Messages**: Keep emoji prefixes for automatic categorization
4. **Performance Tracking**: Log execution times for all operations
5. **Error Handling**: Include exception details and context
6. **Monitor Regularly**: Set up dashboards and alerts in Azure

## 🎉 Benefits

✅ **Automatic Environment Detection** - Works seamlessly in local and Azure  
✅ **Thailand Business Hours Tracking** - Perfect for your after-hours workflow  
✅ **Tool Performance Monitoring** - Track slow operations  
✅ **Rich Context** - Room IDs, user context, tool execution details  
✅ **Azure Integration** - Direct integration with Log Analytics and Application Insights  
✅ **Developer Friendly** - Beautiful colored logs for local development  
✅ **Production Ready** - Structured JSON logs for Azure monitoring  

Your HDmall JibAI Bot will now have enterprise-grade logging! 🚀 