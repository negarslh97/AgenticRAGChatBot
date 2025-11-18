# 🤖 SallyBot Backend

Backend API برای سیستم چت‌بات هوشمند SallyBot با قابلیت RAG (Retrieval-Augmented Generation)

## 📋 فهرست مطالب

- [معماری](#-معماری)
- [ویژگی‌های کلیدی](#-ویژگیهای-کلیدی)
- [Confidence Score System](#-confidence-score-system)
- [نصب و راه‌اندازی](#-نصب-و-راهاندازی)
- [مستندات](#-مستندات)

---

## 🏗️ معماری

```
sally-backend/
├── app/
│   ├── api/                    # API routes & middleware
│   ├── core/                   # Core configs & security
│   ├── domain/                 # Domain entities
│   ├── infrastructure/         # RAG, DB, integrations
│   ├── use_cases/              # Business logic
│   └── services/               # Application services
├── tests/                      # Test suite
├── uploads/                    # Uploaded files
└── main.py                     # Application entry point
```

---

## ✨ ویژگی‌های کلیدی

### 🧠 RAG (Retrieval-Augmented Generation)

- **Hybrid Search**: ترکیب Weaviate (vector) + MongoDB (metadata)
- **Reranking**: استفاده از reranker API برای دقت بالاتر
- **Query Analysis**: تشخیص خودکار نوع سوال (specific/general/explanation)
- **Context Enrichment**: غنی‌سازی نتایج با metadata

### 🎯 Confidence Score System v2.0

سیستم پیشرفته محاسبه اطمینان بر اساس 5 فاکتور:

| فاکتور | توضیح | وزن (General) | وزن (Specific) |
|--------|-------|---------------|----------------|
| **Retrieval Quality** | کیفیت documents بازیابی شده | 18% | 28% |
| **Source Diversity** | تنوع منابع | 12% | 10% |
| **Semantic Match** | تطابق معنایی با سوال | 25% ⭐ | 30% ⭐ |
| **Context Richness** | غنای context | 22% | 14% |
| **Answer Quality** | کیفیت پاسخ تولید شده | 23% | 18% |

**سطوح Confidence:**
- `≥ 0.90` → 🟢 بسیار بالا
- `0.80-0.89` → 🟢 بالا
- `0.65-0.79` → 🟡 خوب
- `0.50-0.64` → 🟠 متوسط
- `0.35-0.49` → 🔴 پایین
- `< 0.35` → 🔴 بسیار پایین

📚 **مستندات کامل:** [CONFIDENCE_SCORE_GUIDE.md](./CONFIDENCE_SCORE_GUIDE.md)

### 🔐 Authentication & Authorization

- JWT-based authentication
- Role-based access control (RBAC)
- Multiple user types: SuperAdmin, Admin, Customer, Guest

### 💬 Chat System

- **Streaming responses** برای تجربه کاربری بهتر
- **Conversation management** با MongoDB
- **Message history** و tracking
- **Admin panel** برای مدیریت چت‌ها

### 📚 Knowledge Base

- **Document upload** (PDF, TXT, DOCX, etc.)
- **Automatic chunking** و embedding
- **Vector storage** در Weaviate
- **Metadata storage** در MongoDB
- **Version control** برای documents

### 🎫 Ticket System

- ایجاد و مدیریت تیکت‌ها
- نظام اولویت‌بندی
- تخصیص به Admin
- پیگیری وضعیت

---

## 🚀 نصب و راه‌اندازی

### پیش‌نیازها

- Python 3.11+
- MongoDB
- Weaviate
- Reranker API (optional)

### نصب

```bash
# ایجاد virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# نصب dependencies
pip install -r requirements.txt

# تنظیم environment variables
cp .env.example .env
# ویرایش .env و تنظیم API keys
```

### اجرا

```bash
# حالت development
uvicorn main:app --reload

# حالت production
uvicorn main:app --host 0.0.0.0 --port 8000
```

### تست

```bash
# اجرای همه تست‌ها
pytest

# اجرای تست‌های خاص
pytest tests/test_rag_service.py

# با coverage
pytest --cov=app tests/
```

---

## 📖 مستندات

### Core Documentation

- **[CONFIDENCE_SCORE_GUIDE.md](./CONFIDENCE_SCORE_GUIDE.md)** - راهنمای کامل Confidence Score System
- **[CONFIDENCE_CALIBRATION.md](./CONFIDENCE_CALIBRATION.md)** - جزئیات calibration v2.0

### API Documentation

بعد از اجرای سرور، به آدرس‌های زیر مراجعه کنید:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Test Documentation

- [tests/README.md](./tests/README.md) - راهنمای تست‌ها

---

## 🔧 تنظیمات

### Environment Variables

```env
# MongoDB
MONGO_URI=mongodb://localhost:27017
MONGO_DB_NAME=sallybot

# Weaviate
WEAVIATE_URL=http://localhost:8080
WEAVIATE_API_KEY=optional

# OpenAI
OPENAI_API_KEY=your_api_key

# Reranker (optional)
RERANKER_API_URL=http://192.168.10.222:5000/rerank

# JWT
SECRET_KEY=your_secret_key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=525600

# RAG Settings
RAG_MODEL=deepseek/deepseek-chat-v3.1:free
TEMPERATURE=0.2
MAX_TOKENS=4000
```

---

## 📊 معماری RAG

```
User Query
    ↓
Query Analysis (نوع سوال: specific/general/explanation)
    ↓
Weaviate Vector Search (30 documents)
    ↓
Reranker API (top 20 documents)
    ↓
MongoDB Metadata Enrichment
    ↓
Context Building (20 chunks)
    ↓
LLM Generation (with streaming)
    ↓
Confidence Calculation (5 factors)
    ↓
Response to User (با confidence score)
```

---

## 🎯 Query Types

سیستم سه نوع سوال را تشخیص می‌دهد:

### 1. Specific (خاص)
- سوالات کوتاه و مستقیم
- مثال: "مدل فروش چیه؟"
- Max tokens: 800
- Weights: Semantic (30%) + Retrieval (28%)

### 2. General (عمومی)
- سوالات جامع و کلی
- مثال: "در مورد مدل های فروش چی میدونی؟"
- Max tokens: 4000
- Weights: Semantic (25%) + Answer Quality (23%)

### 3. Explanation (توضیحی)
- سوالات نیازمند توضیح تفصیلی
- مثال: "فرآیند استقرار نرم افزار را توضیح بده"
- Max tokens: 6000
- Weights: Context (25%) + Answer Quality (25%)

---

## 📈 تاریخچه تغییرات

### v2.0 - 2025-10-06

🎯 **Confidence Score Calibration**
- ✅ Recalibration کامل سیستم confidence
- ✅ افزایش 15-20% در accuracy confidence scores
- ✅ سطح جدید "خوب" (0.65-0.79)
- ✅ بهبود retrieval quality calculation
- ✅ Semantic match thresholds واقع‌بینانه‌تر

📚 **مستندات**:
- راهنمای کامل Confidence Score
- مستندات calibration v2.0

### v1.0 - 2024

- 🎉 نسخه اولیه
- RAG system با Weaviate + MongoDB
- Chat system با streaming
- Authentication & Authorization
- Ticket system

---

## 🤝 مشارکت

برای مشارکت در پروژه:

1. Fork کنید
2. یک branch جدید بسازید
3. تغییرات را commit کنید
4. Pull request ارسال کنید

---

## 📝 License

این پروژه تحت لایسنس MIT منتشر شده است.

---

## 🐛 گزارش مشکلات

اگر مشکلی پیدا کردید:

1. ✅ Check existing issues
2. ✅ Open new issue با جزئیات کامل
3. ✅ در صورت امکان، logs ارسال کنید

---

## 📞 تماس

- Website: [صدگان سامانه هوشمند](https://sadegan.com)
- Support: support@sadegan.com

---

*ساخته شده با ❤️ توسط تیم صدگان*

