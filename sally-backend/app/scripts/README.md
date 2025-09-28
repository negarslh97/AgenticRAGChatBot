# Weaviate-MongoDB Connection Script

این اسکریپت اتصال بین پروژه SallyBot، Weaviate vector database و MongoDB را برقرار کرده و عملیات انتقال داده‌ها را انجام می‌دهد.

## پیش‌نیازها

1. **Docker و Docker Compose**: برای اجرای Weaviate
2. **Python 3.11+**: با تمام وابستگی‌های پروژه
3. **متغیرهای محیطی**: تنظیم API key های مورد نیاز

## تنظیمات اولیه

### ۱. اجرای Weaviate با Docker Compose

```bash
cd sally-backend
docker-compose up -d
```

### ۲. تنظیم متغیرهای محیطی

در فایل `.env` یا environment variables:

```bash
# OpenAI API Key برای embedder
Embedder_API_KEY=your-openai-api-key-here

# تنظیمات Weaviate (اختیاری - پیش‌فرض localhost:8080)
WEAVIATE_URL=http://localhost:8080
WEAVIATE_API_KEY=your-weaviate-api-key-if-needed

# MongoDB URL
MONGODB_URL=mongodb://localhost:27017/SallyChatBot
```

## نحوه استفاده

### تست اتصال

```bash
python app/scripts/weaviate_mongodb_connector.py --test-connection
```

### راه‌اندازی اولیه سیستم

```bash
python app/scripts/weaviate_mongodb_connector.py --setup
```

این دستور:
- اتصال به MongoDB و Weaviate را بررسی می‌کند
- Schema های Weaviate را ایجاد می‌کند
- تنظیمات را بررسی می‌کند

### انتقال داده‌ها

```bash
python app/scripts/weaviate_mongodb_connector.py --migrate
```

این دستور:
- مقالات پایگاه دانش را از MongoDB به Weaviate منتقل می‌کند
- تیکت‌های پشتیبانی را منتقل می‌کند
- داده‌ها را برای جستجوی برداری آماده می‌کند

### بررسی وضعیت سیستم

```bash
python app/scripts/weaviate_mongodb_connector.py --verify
```

این دستور وضعیت اتصالات و داده‌ها را نمایش می‌دهد.

## ساختار داده‌ها در Weaviate

### کلاس KnowledgeBaseArticle

- **title**: عنوان مقاله
- **content**: محتوای مقاله
- **summary**: خلاصه مقاله
- **tags**: تگ‌های مقاله
- **category**: دسته‌بندی
- **visibility**: سطح دسترسی
- **status**: وضعیت مقاله
- **created_at/updated_at**: تاریخ‌ها
- **article_id**: شناسه در MongoDB

### کلاس SupportTicket

- **title**: عنوان تیکت
- **description**: توضیحات
- **status**: وضعیت
- **priority**: اولویت
- **created_at/updated_at**: تاریخ‌ها
- **ticket_id**: شناسه در MongoDB
- **customer_id**: شناسه مشتری

## ویژگی‌ها

- **اتصال امن**: استفاده از API key های امن
- **error handling**: مدیریت خطاها با لاگ‌گیری کامل
- **انتقال تدریجی**: انتقال داده‌ها به صورت batch
- **بررسی صحت**: validation داده‌ها قبل از انتقال
- **لاگ‌گیری**: ذخیره لاگ‌ها در فایل `weaviate_mongodb_connector.log`

## عیب‌یابی

### خطای اتصال به Weaviate

```
❌ خطا در اتصال به Weaviate: Connection refused
```

**راه‌حل:**
- بررسی اجرای Docker container: `docker-compose ps`
- بررسی پورت‌ها: `docker-compose logs weaviate`
- تنظیم متغیر `WEAVIATE_URL`

### خطای اتصال به MongoDB

```
❌ خطا در اتصال به MongoDB: Authentication failed
```

**راه‌حل:**
- بررسی اجرای MongoDB
- بررسی URL اتصال در `settings.database_url`
- بررسی credentials

### خطای API Key

```
❌ خطا در تولید embeddings: Invalid API key
```

**راه‌حل:**
- تنظیم صحیح `Embedder_API_KEY`
- بررسی اعتبار API key در OpenAI

## لاگ‌ها

تمام عملیات در فایل `weaviate_mongodb_connector.log` ذخیره می‌شود. برای دیدن لاگ‌های زنده:

```bash
tail -f weaviate_mongodb_connector.log
```

## مثال خروجی موفق

```
🔌 اتصال به Weaviate...
📍 Weaviate URL: http://localhost:8080
🔑 API Key تنظیم شده: بله
✅ اتصال به Weaviate موفق - نسخه: 1.24.2
🔌 اتصال به MongoDB...
📍 MongoDB URL: mongodb://localhost:27017/SallyChatBot
✅ اتصال به MongoDB موفق
🏗️ ایجاد schema های Weaviate...
✅ کلاس KnowledgeBaseArticle ایجاد شد
✅ کلاس SupportTicket ایجاد شد
✅ راه‌اندازی با موفقیت تکمیل شد!
🎉 سیستم آماده استفاده است!
```
