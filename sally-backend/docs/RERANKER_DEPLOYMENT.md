# راهنمای استقرار Reranker به عنوان سرویس داخلی

## چرا Reranker مهم است؟

Reranker یکی از مهم‌ترین مراحل پایپ‌لاین RAG است که کیفیت نتایج را به شدت بهبود می‌بخشد. استفاده از یک Reranker API خارجی (مثل Colab) برای محیط پروداکشن بسیار پرریسک است.

### مشکلات استفاده از Reranker خارجی:
- ❌ در دسترس نبودن (Availability)
- ❌ Latency بالا
- ❌ مشکلات امنیتی
- ❌ هزینه‌های غیرقابل پیش‌بینی

## راه‌حل پیشنهادی: Self-Hosted Reranker

### گزینه 1: استقرار با FastAPI (توصیه می‌شود)

#### 1. نصب Dependencies

```bash
pip install fastapi uvicorn transformers torch sentence-transformers
```

#### 2. ایجاد سرویس Reranker

فایل `reranker_service.py`:

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import torch
from sentence_transformers import CrossEncoder

app = FastAPI(title="Reranker Service")

# بارگذاری مدل (یکبار در startup)
MODEL_NAME = "BAAI/bge-reranker-v2-m3"
model = None

@app.on_event("startup")
async def load_model():
    global model
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Loading model {MODEL_NAME} on {device}...")
    model = CrossEncoder(MODEL_NAME, device=device, max_length=512)
    print("✅ Model loaded successfully!")

class RerankRequest(BaseModel):
    query: str
    documents: List[str]

class RerankResponse(BaseModel):
    scores: List[float]

@app.post("/rerank", response_model=RerankResponse)
async def rerank(request: RerankRequest):
    """
    Rerank documents based on relevance to query.
    """
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        # ساخت pairs برای reranking
        pairs = [[request.query, doc] for doc in request.documents]
        
        # محاسبه scores
        scores = model.predict(pairs, show_progress_bar=False)
        
        # تبدیل به لیست
        scores_list = scores.tolist()
        
        return RerankResponse(scores=scores_list)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "model": MODEL_NAME,
        "device": "cuda" if torch.cuda.is_available() else "cpu"
    }
```

#### 3. اجرای سرویس

```bash
# اجرا با uvicorn
uvicorn reranker_service:app --host 0.0.0.0 --port 8001

# یا با GPU
CUDA_VISIBLE_DEVICES=0 uvicorn reranker_service:app --host 0.0.0.0 --port 8001
```

#### 4. تست سرویس

```bash
curl -X POST "http://localhost:8001/rerank" \
     -H "Content-Type: application/json" \
     -d '{
       "query": "چطور محصول را نصب کنم؟",
       "documents": [
         "راهنمای نصب محصول شامل مراحل زیر است...",
         "برای خرید محصول به سایت مراجعه کنید...",
         "نصب نرم‌افزار به این صورت انجام می‌شود..."
       ]
     }'
```

#### 5. پیکربندی در SallyBot

در فایل `.env`:

```bash
RERANKER_API_URL=http://localhost:8001/rerank
RERANKER_TIMEOUT=60
```

### گزینه 2: استفاده از Docker

#### Dockerfile

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# نصب dependencies
RUN pip install --no-cache-dir fastapi uvicorn transformers torch sentence-transformers

# کپی کد
COPY reranker_service.py .

# دانلود مدل در build time (اختیاری - برای سرعت بالاتر)
RUN python -c "from sentence_transformers import CrossEncoder; CrossEncoder('BAAI/bge-reranker-v2-m3')"

EXPOSE 8001

CMD ["uvicorn", "reranker_service:app", "--host", "0.0.0.0", "--port", "8001"]
```

#### اجرا با Docker

```bash
# Build
docker build -t sallybot-reranker .

# Run (CPU)
docker run -p 8001:8001 sallybot-reranker

# Run (با GPU)
docker run --gpus all -p 8001:8001 sallybot-reranker
```

#### Docker Compose

```yaml
version: '3.8'

services:
  reranker:
    build: ./reranker
    ports:
      - "8001:8001"
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    environment:
      - CUDA_VISIBLE_DEVICES=0
    restart: unless-stopped
```

### گزینه 3: استفاده از Managed Services

#### 3.1 Cohere Rerank API

```python
# در rag_service.py
import cohere

co = cohere.Client(api_key="YOUR_API_KEY")

def rerank_with_cohere(query: str, documents: List[str]) -> List[float]:
    results = co.rerank(
        model="rerank-english-v2.0",
        query=query,
        documents=documents,
        top_n=20
    )
    
    # استخراج scores
    scores = [result.relevance_score for result in results.results]
    return scores
```

پیکربندی `.env`:
```bash
COHERE_API_KEY=your_cohere_api_key
USE_COHERE_RERANK=true
```

#### 3.2 Jina Rerank API

```python
import requests

def rerank_with_jina(query: str, documents: List[str]) -> List[float]:
    response = requests.post(
        "https://api.jina.ai/v1/rerank",
        headers={
            "Authorization": f"Bearer {JINA_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "jina-reranker-v1-base-en",
            "query": query,
            "documents": documents,
            "top_n": 20
        }
    )
    
    return response.json()["results"]
```

## نیازمندی‌های سخت‌افزاری

### حداقل (CPU):
- CPU: 4 cores
- RAM: 8GB
- Latency: ~500-1000ms per request

### توصیه شده (GPU):
- GPU: NVIDIA T4 یا بالاتر
- VRAM: 4GB+
- RAM: 8GB
- Latency: ~50-100ms per request

### پروداکشن (GPU):
- GPU: NVIDIA A10 یا بالاتر
- VRAM: 8GB+
- RAM: 16GB
- Latency: ~30-50ms per request

## مانیتورینگ و Scaling

### لاگ‌گذاری

```python
import logging
from prometheus_client import Counter, Histogram

# Metrics
rerank_requests = Counter('rerank_requests_total', 'Total rerank requests')
rerank_latency = Histogram('rerank_latency_seconds', 'Rerank latency')

@app.post("/rerank")
async def rerank(request: RerankRequest):
    rerank_requests.inc()
    
    with rerank_latency.time():
        # ... reranking logic ...
        pass
```

### Health Check

```bash
# ساده
curl http://localhost:8001/health

# با Kubernetes
kubectl create deployment reranker --image=sallybot-reranker:latest
kubectl expose deployment reranker --port=8001 --type=LoadBalancer
```

## بهترین پرکتیس‌ها

1. **Caching**: برای queries تکراری از cache استفاده کنید
2. **Batching**: چندین request را با هم پردازش کنید
3. **Load Balancing**: برای traffic بالا، چندین instance راه‌اندازی کنید
4. **Monitoring**: metrics مهم را track کنید (latency, throughput, errors)
5. **Fallback**: همیشه یک fallback strategy داشته باشید

## مقایسه گزینه‌ها

| گزینه | هزینه | Latency | کنترل | پیچیدگی |
|-------|------|---------|-------|---------|
| Self-hosted (CPU) | کم | متوسط | بالا | کم |
| Self-hosted (GPU) | متوسط | کم | بالا | متوسط |
| Cohere API | متغیر | کم | کم | خیلی کم |
| Jina API | متغیر | کم | کم | خیلی کم |
| Colab (تست) | رایگان | بالا | خیلی کم | کم |

## نتیجه‌گیری

برای محیط پروداکشن:
- ✅ **توصیه اول**: Self-hosted با GPU (کنترل کامل + performance بالا)
- ✅ **توصیه دوم**: Managed Service (Cohere/Jina) برای سادگی
- ❌ **توصیه نمی‌شود**: External API (Colab) - فقط برای تست

