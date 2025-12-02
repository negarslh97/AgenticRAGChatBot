# 🚀 SallyBot - Hugging Face Spaces Deployment Guide

این راهنما نحوه استقرار پروژه SallyBot در Hugging Face Spaces را توضیح می‌دهد.

## 📋 پیش‌نیازها

1. **حساب Hugging Face**: یک حساب کاربری در [Hugging Face](https://huggingface.co) داشته باشید
2. **MongoDB Atlas**: برای دیتابیس (رایگان)
3. **Weaviate Cloud**: برای vector database (اختیاری - می‌توانید از سرویس رایگان استفاده کنید)

## 🔧 مراحل استقرار

### مرحله 1: ایجاد Space جدید در Hugging Face

1. به [Hugging Face Spaces](https://huggingface.co/spaces) بروید
2. روی "Create new Space" کلیک کنید
3. تنظیمات زیر را وارد کنید:
   - **Name**: `sallybot` (یا نام دلخواه)
   - **SDK**: `Docker`
   - **Hardware**: `CPU basic` (یا `GPU` اگر نیاز دارید)
   - **Visibility**: `Public` یا `Private`

### مرحله 2: آپلود کد

دو روش دارید:

#### روش 1: از طریق Git (توصیه می‌شود)

```bash
# کلون کردن repository
git clone https://huggingface.co/spaces/YOUR_USERNAME/sallybot
cd sallybot

# کپی کردن فایل‌های پروژه
cp -r /path/to/SallyBot/* .

# Commit و Push
git add .
git commit -m "Initial deployment"
git push
```

#### روش 2: آپلود مستقیم

فایل‌های زیر را در Hugging Face Space آپلود کنید:
- `Dockerfile`
- `app.py`
- `sally-backend/` (کل دایرکتوری)
- `sally-frontend/` (کل دایرکتوری)
- `sally-backend/release/requirements.txt`

### مرحله 3: تنظیم Environment Variables

در صفحه Space خود، به بخش **Settings** > **Repository secrets** بروید و متغیرهای زیر را اضافه کنید:

#### متغیرهای ضروری:

```env
# MongoDB (از MongoDB Atlas استفاده کنید)
MONGODB_URL=mongodb+srv://username:password@cluster.mongodb.net/SallyChatBot

# JWT Secret
jwt_secret_key=your-super-secret-key-change-this-in-production

# CORS (URL Space شما)
cors_origins=["https://YOUR_USERNAME-sallybot.hf.space"]

# Default Admin
default_SuperAdmin_email=admin@sally.com
default_SuperAdmin_password=admin123
```

#### متغیرهای اختیاری (برای AI):

```env
# OpenAI / OpenRouter
OPENAI_API_KEY=your-openai-api-key
OPENAI_BASE_URL=https://api.openai.com/v1

# یا برای OpenRouter
OPENAI_BASE_URL=https://openrouter.ai/api/v1

# Weaviate (اختیاری)
WEAVIATE_URL=https://your-cluster.weaviate.network
WEAVIATE_API_KEY=your-weaviate-api-key

# Models
RAG_MODEL=gpt-3.5-turbo
CHAT_MODEL=gpt-3.5-turbo
METADATA_MODEL=gpt-3.5-turbo
```

### مرحله 4: تنظیم MongoDB Atlas

1. به [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) بروید
2. یک cluster رایگان ایجاد کنید
3. یک database user ایجاد کنید
4. Network Access را تنظیم کنید (Allow access from anywhere برای تست)
5. Connection string را کپی کنید و در `MONGODB_URL` قرار دهید

### مرحله 5: Build و Deploy

Hugging Face Spaces به صورت خودکار:
1. Dockerfile را می‌خواند
2. Image را build می‌کند
3. Container را اجرا می‌کند
4. App را در `https://YOUR_USERNAME-sallybot.hf.space` در دسترس قرار می‌دهد

## 🔍 بررسی و عیب‌یابی

### چک کردن Logs

در صفحه Space خود:
1. به بخش **Logs** بروید
2. Logs را بررسی کنید

### تست Health Check

```bash
curl https://YOUR_USERNAME-sallybot.hf.space/api/system/health
```

### مشکلات رایج

#### 1. Port Error
- Hugging Face Spaces از متغیر `PORT` استفاده می‌کند
- در Dockerfile پورت 7860 استفاده شده که پیش‌فرض Hugging Face است

#### 2. MongoDB Connection Error
- مطمئن شوید `MONGODB_URL` صحیح است
- Network Access در MongoDB Atlas را چک کنید

#### 3. Frontend Not Loading
- مطمئن شوید `npm run build` در Dockerfile اجرا شده
- فایل‌های build در مسیر صحیح هستند

## 📝 ساختار فایل‌های مورد نیاز

```
.
├── Dockerfile              # Docker configuration
├── app.py                 # Entry point for HF Spaces
├── sally-backend/         # Backend code
│   ├── app/
│   ├── main.py
│   └── release/
│       └── requirements.txt
└── sally-frontend/        # Frontend code
    ├── src/
    ├── package.json
    └── public/
```

## 🎯 نکات مهم

1. **حجم Space**: Hugging Face Spaces محدودیت حجم دارد (معمولاً 50GB)
2. **Timeout**: درخواست‌ها نباید بیشتر از 60 ثانیه طول بکشند
3. **Environment Variables**: حتماً از Repository secrets استفاده کنید (نه hardcode)
4. **CORS**: URL Space خود را در `cors_origins` اضافه کنید

## 🔒 امنیت

- هرگز API keys را در کد commit نکنید
- از Repository secrets استفاده کنید
- JWT secret را تغییر دهید
- Password پیش‌فرض admin را تغییر دهید

## 📚 منابع بیشتر

- [Hugging Face Spaces Documentation](https://huggingface.co/docs/hub/spaces)
- [Docker on Hugging Face Spaces](https://huggingface.co/docs/hub/spaces-sdks-docker)
- [MongoDB Atlas Setup](https://www.mongodb.com/docs/atlas/getting-started/)

## 🆘 پشتیبانی

اگر مشکلی داشتید:
1. Logs را بررسی کنید
2. Environment variables را چک کنید
3. Health check endpoint را تست کنید
4. Issue در repository ایجاد کنید

---

**موفق باشید! 🚀**

