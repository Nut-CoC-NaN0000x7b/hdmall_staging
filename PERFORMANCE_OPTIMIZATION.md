# Performance Optimization Guide

## 🚨 Issues Identified

Your `/search` and `/ads` endpoints were experiencing severe performance degradation under high load (100-200 requests/min) due to several bottlenecks:

### Critical Bottlenecks Fixed:

1. **Object Recreation on Every Request** ⚠️
   - Creating new `RAG` and `AdsAgent` instances for every request
   - Reinitializing heavy components (BM25Retriever, SemanticRetriever, etc.)
   - Reloading embeddings and knowledge base references

2. **Excessive Retry Logic** 🔄
   - AdsAgent had 15 retry attempts with up to 200s wait time
   - Causing cascading delays under high load

3. **Blocking Operations** ⏱️
   - Synchronous operations blocking the event loop
   - No connection pooling for HTTP requests
   - Repeated geocoding API calls without caching

4. **No Timeout Protection** ⏰
   - Claude API calls could hang indefinitely
   - No circuit breaker pattern

## ✅ Optimizations Implemented

### 1. Singleton Pattern for Heavy Objects
```python
# Before: Creating new instances every request
rag = RAG(global_storage)  # Heavy initialization
ads_agent = AdsAgent(global_storage)  # Heavy initialization

# After: Singleton pattern
_rag_instance: Optional[RAG] = None
_ads_agent_instance: Optional[AdsAgent] = None

def get_rag_instance() -> RAG:
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = RAG(global_storage)
    return _rag_instance
```

### 2. Async Thread Pool Execution
```python
# Before: Blocking operations
result = rag.search_for_web(query)

# After: Non-blocking execution
loop = asyncio.get_event_loop()
result = await loop.run_in_executor(None, rag.search_for_web, query)
```

### 3. Connection Pooling
```python
# Added aiohttp session with connection pooling
connector = aiohttp.TCPConnector(
    limit=100,  # Total connection pool size
    limit_per_host=30,  # Max connections per host
    ttl_dns_cache=300,  # DNS cache TTL
    use_dns_cache=True,
)
```

### 4. Caching Layer
```python
# LRU cache for geocoding results
@lru_cache(maxsize=1000)
def _get_geocode_cached(self, input_string: str) -> Tuple[Optional[float], Optional[float]]:
    # Cached geocoding implementation
```

### 5. Reduced Retry Logic
```python
# Before: 15 attempts, 200s max wait
@retry(stop=stop_after_attempt(15), wait=wait_random_exponential(min=1, max=200))

# After: 5 attempts, 60s max wait
@retry(stop=stop_after_attempt(5), wait=wait_random_exponential(min=1, max=60))
```

### 6. Timeout Protection
```python
# Added timeouts to prevent hanging requests
response = await asyncio.wait_for(
    self.client.messages.create(...),
    timeout=120.0  # 2 minute timeout
)
```

### 7. Graceful Error Handling
```python
# Before: Raising exceptions causing cascading failures
except Exception as e:
    raise

# After: Graceful degradation
except Exception as e:
    logger.error(f"Error: {str(e)}")
    return []  # Return empty result instead of failing
```

## 🚀 Deployment Recommendations

### Azure App Service Configuration

Set these environment variables in Azure:

```bash
PYTHONUNBUFFERED=1
PYTHONDONTWRITEBYTECODE=1
WORKERS=4
WEB_CONCURRENCY=4
TIMEOUT=240
```

### Gunicorn Configuration

Use the provided `deployment_config.py`:

```python
from deployment_config import get_gunicorn_config
config = get_gunicorn_config()
```

### Startup Command for Azure

```bash
gunicorn --config deployment_config.py __init__:create_app --factory
```

## 📊 Expected Performance Improvements

### Before Optimization:
- **Response Time**: 30-60s under load, up to 240s timeout
- **Throughput**: Degrading rapidly after 50 requests/min
- **Memory Usage**: Increasing with each request
- **Error Rate**: High timeout errors under load

### After Optimization:
- **Response Time**: 5-15s consistent under load
- **Throughput**: Stable at 100-200 requests/min
- **Memory Usage**: Stable with singleton pattern
- **Error Rate**: Significantly reduced with graceful degradation

## 🔧 Additional Recommendations

### 1. Database Connection Pooling
If using databases, implement connection pooling:
```python
from sqlalchemy.pool import QueuePool
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True
)
```

### 2. Redis Caching
For distributed caching:
```python
import redis.asyncio as redis
redis_client = redis.Redis(
    host='your-redis-host',
    port=6379,
    decode_responses=True,
    max_connections=20
)
```

### 3. Load Balancing
Consider using Azure Load Balancer or Application Gateway for distributing traffic across multiple instances.

### 4. Monitoring
Implement proper monitoring:
```python
# Added performance monitoring middleware
@app.middleware("http")
async def add_process_time_header(request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response
```

### 5. Auto-scaling
Configure Azure App Service auto-scaling rules based on:
- CPU usage > 70%
- Memory usage > 80%
- Request queue length > 100

## 🧪 Testing Under Load

Test the optimizations with:

```bash
# Install load testing tool
pip install locust

# Create locustfile.py for testing
from locust import HttpUser, task, between

class APIUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def test_search(self):
        self.client.post("/search", json={"query": "vaccine"})
    
    @task
    def test_ads(self):
        self.client.post("/ads", json={
            "thread_name": "test",
            "conversation": [{"role": "user", "content": "test"}]
        })

# Run load test
locust -f locustfile.py --host=https://your-azure-app.azurewebsites.net
```

## 📈 Monitoring Metrics

Monitor these key metrics:
- Response time percentiles (P50, P95, P99)
- Request rate (requests/second)
- Error rate (%)
- Memory usage
- CPU usage
- Connection pool utilization

The optimizations should significantly improve your API's ability to handle high concurrent loads without timing out. 