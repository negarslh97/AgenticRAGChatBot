# 🚀 راهنمای استقرار SallyBot در Hugging Face Spaces

## ✅ فایل‌های ایجاد شده

برای استقرار پروژه در Hugging Face Spaces، فایل‌های زیر ایجاد شده‌اند:

1. **`Dockerfile`** - فایل Docker برای build و اجرای پروژه
2. **`app.py`** - Entry point برای Hugging Face Spaces
3. **`start.sh`** - اسکریپت راه‌اندازی
4. **`.dockerignore`** - فایل‌های غیرضروری برای Docker
5. **`README_HF_SPACES.md`** - راهنمای کامل انگلیسی

## 📝 مراحل استقرار

### 1. ایجاد Space در Hugging Face

1. به [huggingface.co/spaces](https://huggingface.co/spaces) بروید
2. روی **"Create new Space"** کلیک کنید
3. تنظیمات:
   - **Name**: `sallybot` (یا نام دلخواه)
   - **SDK**: `Docker` ⚠️ مهم!
   - **Hardware**: `CPU basic` (یا `GPU` برای مدل‌های بزرگتر)
   - **Visibility**: `Public` یا `Private`

### 2. آپلود فایل‌ها

#### روش 1: از طریق Git (توصیه می‌شود)

```bash
# کلون کردن Space
git clone https://huggingface.co/spaces/YOUR_USERNAME/sallybot
cd sallybot

# کپی کردن فایل‌های پروژه
# Windows PowerShell:
Copy-Item -Path "D:\Project\SallyBot\*" -Destination "." -Recurse -Force

# Linux/Mac:
cp -r /path/to/SallyBot/* .

# Commit و Push
git add .
git commit -m "Deploy SallyBot to HF Spaces"
git push
```

#### روش 2: آپلود مستقیم

در صفحه Space خود، فایل‌های زیر را آپلود کنید:
- `Dockerfile`
- `app.py`
- `start.sh`
- `.dockerignore`
- کل دایرکتوری `sally-backend/`
- کل دایرکتوری `sally-frontend/`

### 3. تنظیم Environment Variables

در صفحه Space، به **Settings** > **Repository secrets** بروید و متغیرهای زیر را اضافه کنید:

#### متغیرهای ضروری:

```env
MONGODB_URL=mongodb+srv://username:password@cluster.mongodb.net/SallyChatBot
jwt_secret_key=your-super-secret-key-change-this
cors_origins=["https://YOUR_USERNAME-sallybot.hf.space"]
default_SuperAdmin_email=admin@sally.com
default_SuperAdmin_password=admin123
```

#### متغیرهای اختیاری (برای AI):

```env
OPENAI_API_KEY=your-openai-api-key
OPENAI_BASE_URL=https://api.openai.com/v1
RAG_MODEL=gpt-3.5-turbo
CHAT_MODEL=gpt-3.5-turbo
```

### 4. راه‌اندازی MongoDB Atlas

1. به [mongodb.com/cloud/atlas](https://www.mongodb.com/cloud/atlas) بروید
2. یک حساب رایگان ایجاد کنید
3. یک Cluster رایگان بسازید
4. Database User ایجاد کنید
5. Network Access را تنظیم کنید (Allow from anywhere)
6. Connection String را کپی کنید

### 5. Build خودکار

Hugging Face Spaces به صورت خودکار:
- ✅ Dockerfile را می‌خواند
- ✅ Image را build می‌کند
- ✅ Container را اجرا می‌کند
- ✅ App را در دسترس قرار می‌دهد

## 🔍 بررسی و تست

### چک کردن Logs

در صفحه Space:
1. به بخش **Logs** بروید
2. Logs را بررسی کنید

### تست Health Check

```bash
curl https://YOUR_USERNAME-sallybot.hf.space/api/system/health
```

### دسترسی به App

بعد از build موفق، App شما در این آدرس در دسترس است:
```
https://YOUR_USERNAME-sallybot.hf.space
```

## ⚠️ نکات مهم

1. **حجم**: Hugging Face Spaces محدودیت حجم دارد (معمولاً 50GB)
2. **Timeout**: درخواست‌ها نباید بیشتر از 60 ثانیه طول بکشند
3. **Environment Variables**: از Repository secrets استفاده کنید (نه hardcode)
4. **CORS**: URL Space خود را در `cors_origins` اضافه کنید
5. **Port**: Hugging Face Spaces از متغیر `PORT` استفاده می‌کند (پیش‌فرض: 7860)

## 🐛 عیب‌یابی مشکلات رایج

### مشکل: Build فیل می‌شود
- ✅ Logs را بررسی کنید
- ✅ `requirements.txt` را چک کنید
- ✅ فایل‌های مورد نیاز را آپلود کنید

### مشکل: MongoDB Connection Error
- ✅ `MONGODB_URL` را بررسی کنید
- ✅ Network Access در MongoDB Atlas را چک کنید
- ✅ Username و Password را بررسی کنید

### مشکل: Frontend لود نمی‌شود
- ✅ مطمئن شوید `npm run build` اجرا شده
- ✅ فایل‌های build در مسیر صحیح هستند
- ✅ CORS را بررسی کنید

### مشکل: Port Error
- ✅ Hugging Face Spaces از `PORT` env var استفاده می‌کند
- ✅ در `start.sh` این متغیر استفاده شده است

## 📚 فایل‌های مهم

```
.
├── Dockerfile              # Docker configuration
├── app.py                 # Entry point
├── start.sh               # Startup script
├── .dockerignore          # Ignore files
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

## 🔒 امنیت

- ⚠️ هرگز API keys را در کد commit نکنید
- ✅ از Repository secrets استفاده کنید
- ✅ JWT secret را تغییر دهید
- ✅ Password پیش‌فرض admin را تغییر دهید

## 📞 پشتیبانی

اگر مشکلی داشتید:
1. Logs را بررسی کنید
2. Environment variables را چک کنید
3. Health check endpoint را تست کنید
4. Issue در repository ایجاد کنید

---

**موفق باشید! 🚀**

برای اطلاعات بیشتر، فایل `README_HF_SPACES.md` را مطالعه کنید.

