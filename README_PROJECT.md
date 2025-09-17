# 🚀 راهنمای اجرای پروژه SallyChatBot

## 📋 پیش‌نیازها

- **Python 3.8 یا بالاتر**
- **Node.js 16 یا بالاتر**
- **MongoDB** (در حال اجرا)
- **PowerShell یا Command Prompt**

## 🔧 راه‌اندازی سریع

### روش ۱: استفاده از فایل Batch (سریع‌ترین روش)
```bash
# در دایرکتوری پروژه اجرا کنید
start_project.bat
```

### روش ۲: اجرای دستی

#### مرحله ۱: تنظیم Backend
```bash
cd sally-backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

#### مرحله ۲: تنظیم Frontend
```bash
cd sally-frontend
npm install
```

#### مرحله ۳: اجرای سرورها
```bash
# ترمینال ۱ - Backend
cd sally-backend
venv\Scripts\activate
python main.py

# ترمینال ۲ - Frontend
cd sally-frontend
npm start
```

## 🌐 دسترسی به برنامه

| سرویس | آدرس | توضیح |
|-------|------|-------|
| **Frontend** | http://localhost:3000 | رابط کاربری برنامه |
| **Backend API** | http://127.0.0.1:8000 | API سرور FastAPI |
| **API Docs** | http://127.0.0.1:8000/docs | مستندات Swagger UI |
| **MongoDB** | mongodb://localhost:27017 | دیتابیس |

## 👤 حساب کاربری پیش‌فرض

- **ایمیل**: `admin@sally.com`
- **رمز عبور**: `admin123`
- **نقش**: Super Admin

## 📁 ساختار پروژه

```
SallyBot/
├── sally-backend/          # سرور FastAPI
│   ├── venv/              # محیط مجازی Python
│   ├── main.py            # نقطه ورود برنامه
│   ├── requirements.txt   # وابستگی‌های Python
│   ├── app/               # کدهای Backend
│   │   ├── api/           # API Routes
│   │   ├── core/          # تنظیمات و امنیت
│   │   ├── domain/        # مدل‌های داده
│   │   └── infrastructure/# سرویس‌های زیرساختی
│   └── tests/             # تست‌ها
├── sally-frontend/        # برنامه React
│   ├── node_modules/      # وابستگی‌های Node.js
│   ├── package.json       # تنظیمات Frontend
│   ├── src/               # کدهای React
│   │   ├── components/    # کامپوننت‌ها
│   │   ├── pages/         # صفحات
│   │   ├── services/      # سرویس‌های API
│   │   └── types/         # تایپ‌های TypeScript
│   └── public/            # فایل‌های استاتیک
└── start_project.bat      # فایل راه‌انداز سریع
```

## 🛠️ دستورات مفید

### Backend
```bash
# فعال کردن محیط مجازی
venv\Scripts\activate

# اجرای سرور با auto-reload
uvicorn main:app --reload --host 127.0.0.1 --port 8000

# نصب مجدد وابستگی‌ها
pip install -r requirements.txt
```

### Frontend
```bash
# نصب وابستگی‌ها
npm install

# اجرای سرور توسعه
npm start

# ساخت برای production
npm run build

# اجرای تست‌ها
npm test
```

### MongoDB
```bash
# بررسی وضعیت MongoDB
mongod --version

# اجرای MongoDB به صورت دستی
mongod --dbpath "C:\data\db"

# یا با Docker
docker run -d --name mongodb -p 27017:27017 mongo:latest
```

## 🔧 عیب‌یابی

### مشکل اتصال به MongoDB
```bash
# بررسی پورت MongoDB
netstat -ano | findstr :27017

# ری‌استارت MongoDB
docker restart mongodb
```

### مشکل پورت‌های اشغال شده
```bash
# بررسی پورت‌های در حال استفاده
netstat -ano | findstr :8000
netstat -ano | findstr :3000

# کشتن پروسس (PID را پیدا کنید)
taskkill /PID <PID> /F
```

### پاک کردن و نصب مجدد
```bash
# پاک کردن node_modules
rm -rf node_modules && npm install

# پاک کردن venv و نصب مجدد
rm -rf venv
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## 📊 مانیتورینگ

### Backend Logs
لاگ‌های backend در ترمینالی که سرور اجرا می‌شود نمایش داده می‌شود.

### Frontend DevTools
از Developer Tools مرورگر برای مشاهده خطاهای JavaScript استفاده کنید.

### MongoDB Logs
```bash
# مشاهده لاگ‌های Docker
docker logs mongodb

# یا اتصال به MongoDB Compass
```

## 🚀 ویژگی‌های کلیدی

- ✅ **Real-time Development**: تغییرات کد به صورت خودکار اعمال می‌شود
- ✅ **Hot Reload**: سرورها به صورت خودکار ری‌استارت می‌شوند
- ✅ **API Documentation**: مستندات کامل API با Swagger UI
- ✅ **Environment Variables**: تنظیمات از طریق متغیرهای محیطی
- ✅ **CORS Configured**: تنظیمات CORS برای توسعه محلی
- ✅ **Error Handling**: مدیریت خطای مناسب در هر دو سمت

## 📞 پشتیبانی

اگر با مشکل مواجه شدید:

1. لاگ‌های سرور را چک کنید
2. پورت‌های در حال استفاده را بررسی کنید
3. وابستگی‌ها را بروزرسانی کنید
4. فایل‌های `.env` را بررسی کنید

---

**موفق باشید! 🎉**
