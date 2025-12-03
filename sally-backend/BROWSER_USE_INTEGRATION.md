# 🌐 راهنمای یکپارچه‌سازی Browser-Use با SallyBot

این راهنما نحوه استفاده از کتابخانه `browser-use` در پروژه SallyBot و اتصال آن به OpenRouter API را توضیح می‌دهد.

## 📋 فهرست مطالب

- [معرفی](#معرفی)
- [نصب و راه‌اندازی](#نصب-و-راه‌اندازی)
- [پیکربندی OpenRouter](#پیکربندی-openrouter)
- [استفاده از سرویس](#استفاده-از-سرویس)
- [API Endpoints](#api-endpoints)
- [مثال‌های کاربردی](#مثال‌های-کاربردی)
- [نکات مهم](#نکات-مهم)

---

## 🎯 معرفی

`browser-use` یک کتابخانه قدرتمند برای خودکارسازی وظایف مرورگر با استفاده از AI است. این کتابخانه به شما امکان می‌دهد:

- ✅ وظایف مرورگر را با دستورات طبیعی انجام دهید
- ✅ فرم‌ها را پر کنید
- ✅ اطلاعات را از وب‌سایت‌ها استخراج کنید
- ✅ جستجو و خرید آنلاین را خودکار کنید
- ✅ و خیلی بیشتر...

در SallyBot، این کتابخانه با استفاده از **OpenAI API** (اولویت اول) یا **OpenRouter API** (fallback) کار می‌کند. به صورت پیش‌فرض از `gpt-4o-mini` استفاده می‌شود که سریع و ارزان است.

---

## 🚀 نصب و راه‌اندازی

### 1. نصب کتابخانه browser-use

```bash
# نصب از PyPI
pip install browser-use

# یا اگر از requirements.txt استفاده می‌کنید
pip install -r sally-backend/release/requirements.txt
```

### 2. نصب Chromium

`browser-use` نیاز به Chromium دارد. برای نصب:

```bash
# با استفاده از uvx (توصیه می‌شود)
uvx browser-use install

# یا با استفاده از playwright (از طریق Python)
python -m playwright install chromium
# یا
uvx playwright install chromium
```

### 3. پیکربندی LLM (OpenAI یا OpenRouter)

سرویس browser automation به ترتیب اولویت زیر از LLM استفاده می‌کند:

**اولویت 1: OpenAI API (پیش‌فرض و توصیه می‌شود)**

```bash
# در فایل .env
Embedder_API_KEY=sk-proj-xxxxxxxxxxxxx  # OpenAI API Key
# پیش‌فرض: از gpt-4o-mini استفاده می‌شود
```

**اولویت 2: OpenRouter API (fallback)**

```bash
# در فایل .env
OPENAI_API_KEY=sk-or-v1-xxxxxxxxxxxxx  # OpenRouter API Key
OPENAI_BASE_URL=https://openrouter.ai/api/v1
CHAT_MODEL=google/gemini-2.5-flash  # یا هر مدل دیگری
```

**نکات مهم:**
- اگر `Embedder_API_KEY` تنظیم شده باشد، از OpenAI `gpt-4o-mini` استفاده می‌شود (بهترین سازگاری با browser-use)
- اگر فقط `OPENAI_API_KEY` تنظیم شده باشد، از OpenRouter استفاده می‌شود
- سرویس به صورت خودکار از `ChatBrowserUse` (از browser-use) استفاده می‌کند که بهترین سازگاری را دارد
- در صورت عدم دسترسی به `ChatBrowserUse`، از `ChatOpenAI` با wrapper استفاده می‌شود

### 4. پیکربندی Browser Use Cloud (اختیاری)

اگر می‌خواهید از Browser Use Cloud استفاده کنید (برای سرعت بیشتر یا اگر راه‌حل محلی کار نکرد):

```bash
# در فایل .env
BROWSER_USE_CLOUD_ENABLED=true
BROWSER_USE_API_KEY=your-browser-use-api-key
```

**نکته:** می‌توانید API key را از [browser-use.com](https://browser-use.com) دریافت کنید. کاربران جدید $10 اعتبار رایگان دریافت می‌کنند.

**⚠️ مهم:** به صورت پیش‌فرض، همه داده‌ها به صورت محلی پردازش می‌شوند و نیازی به Browser Use Cloud نیست. کد به صورت خودکار مشکل Windows را حل می‌کند.

### 5. استفاده از مرورگر موجود (اختیاری)

اگر می‌خواهید از مرورگر موجود استفاده کنید (به جای باز کردن مرورگر جدید):

**مرحله 1: اجرای Chrome/Edge با Remote Debugging**

```bash
# Windows (Chrome)
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\temp\chrome-debug"

# Windows (Edge)
"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --remote-debugging-port=9222 --user-data-dir="C:\temp\edge-debug"

# Linux/Mac (Chrome)
google-chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-debug

# Linux/Mac (Chrome via command)
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-debug
```

**مرحله 2: تنظیم در .env**

```bash
# در فایل .env
BROWSER_USE_EXISTING=true
BROWSER_CDP_URL=http://127.0.0.1:9222
# یا
BROWSER_CDP_URL=ws://127.0.0.1:9222
# هر دو فرمت پشتیبانی می‌شود
```

**نکات مهم:**
- Port 9222 پیش‌فرض است، می‌توانید تغییر دهید
- `--user-data-dir` برای جلوگیری از تداخل با profile اصلی است
- مرورگر باید قبل از اجرای agent باز باشد
- CDP URL می‌تواند `http://` یا `ws://` باشد (هر دو پشتیبانی می‌شود)
- پس از تنظیم، agent از همان مرورگر موجود استفاده می‌کند و صفحه جدید باز نمی‌کند

**مثال کامل:**

1. Chrome را با remote debugging اجرا کنید:
```bash
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\temp\chrome-debug"
```

2. در `.env` تنظیم کنید:
```bash
BROWSER_USE_EXISTING=true
BROWSER_CDP_URL=http://127.0.0.1:9222
```

3. حالا agent از همان مرورگر Chrome که باز است استفاده می‌کند!

---

## ⚙️ پیکربندی LLM

### گزینه 1: استفاده از OpenAI (توصیه می‌شود)

1. به [OpenAI Platform](https://platform.openai.com) بروید
2. یک حساب کاربری ایجاد کنید
3. از بخش API Keys، یک کلید جدید ایجاد کنید
4. کلید را در فایل `.env` قرار دهید:

```env
Embedder_API_KEY=sk-proj-xxxxxxxxxxxxx
```

**مزایا:**
- بهترین سازگاری با browser-use
- استفاده از `ChatBrowserUse` که بهینه‌تر است
- مدل پیش‌فرض: `gpt-4o-mini` (سریع و ارزان)

### گزینه 2: استفاده از OpenRouter

1. به [OpenRouter.ai](https://openrouter.ai) بروید
2. یک حساب کاربری ایجاد کنید
3. از بخش API Keys، یک کلید جدید ایجاد کنید
4. کلید را در فایل `.env` قرار دهید:

```env
OPENAI_API_KEY=sk-or-v1-xxxxxxxxxxxxx
OPENAI_BASE_URL=https://openrouter.ai/api/v1
CHAT_MODEL=google/gemini-2.5-flash
```

### انتخاب مدل مناسب

برای browser automation، مدل‌های زیر توصیه می‌شوند:

- `gpt-4o-mini` (OpenAI) - سریع و ارزان، بهترین سازگاری
- `deepseek/deepseek-chat` (OpenRouter) - سریع و ارزان
- `google/gemini-pro` (OpenRouter) - قدرتمند و دقیق
- `anthropic/claude-3-haiku` (OpenRouter) - تعادل خوب بین سرعت و دقت

می‌توانید مدل را در هنگام فراخوانی API با پارامتر `model_name` مشخص کنید.

---

## 💻 استفاده از سرویس

### استفاده مستقیم از سرویس

```python
from app.services.browser_automation_service import browser_automation_service

# اجرای یک وظیفه ساده
result = await browser_automation_service.execute_task(
    task_description="Find the price of iPhone 15 on Amazon",
    url="https://www.amazon.com"
)

if result.success:
    print(f"نتیجه: {result.result}")
    print(f"زمان اجرا: {result.execution_time:.2f} ثانیه")
else:
    print(f"خطا: {result.error}")
```

### استفاده با مدل خاص

```python
# استفاده از یک مدل خاص از model_factory
result = await browser_automation_service.execute_task_with_custom_llm(
    task_description="Search for Python tutorials on YouTube",
    model_name="deepseek/deepseek-chat",  # یا هر مدل دیگری از model_factory
    url="https://www.youtube.com"
)
```

### استفاده با صفحه فعلی (بدون navigate)

```python
# استفاده از صفحه فعلی مرورگر (مثلاً بعد از لاگین)
result = await browser_automation_service.execute_task(
    task_description="Fill out the form on the current page",
    use_current_page=True,  # از صفحه فعلی استفاده کن
    max_steps=15
)
```

### استفاده با مرورگر موجود (CDP)

```python
# اتصال به مرورگر موجود با CDP
result = await browser_automation_service.execute_task(
    task_description="Click on the submit button",
    cdp_url="http://127.0.0.1:9222",  # CDP endpoint
    use_current_page=True  # از صفحه فعلی استفاده کن
)
```

### استفاده با لاگین خودکار

```python
# اجرای لاگین قبل از انجام task
result = await browser_automation_service.execute_task(
    task_description="Create a new user in admin panel",
    url="http://localhost:3000/super-admin",
    login_email="admin@example.com",
    login_password="password123",
    max_steps=30
)
```

---

## 🔌 API Endpoints

### 1. اجرای وظیفه مرورگر

**Endpoint:** `POST /api/browser/execute`

**درخواست:**
```json
{
  "task": "Find the price of iPhone 15 on Amazon",
  "url": "https://www.amazon.com",
  "model_name": "deepseek/deepseek-chat",  // اختیاری
  "max_steps": 20,  // اختیاری، پیش‌فرض: 20
  "cdp_url": "http://127.0.0.1:9222",  // اختیاری - برای اتصال به مرورگر موجود
  "use_current_page": false  // اختیاری - استفاده از صفحه فعلی بدون navigate
}
```

**پاسخ:**
```json
{
  "success": true,
  "result": "The iPhone 15 is priced at $799 on Amazon...",
  "execution_time": 12.5,
  "metadata": {
    "task": "Find the price of iPhone 15 on Amazon",
    "url": "https://www.amazon.com",
    "steps": 8,
    "max_steps": 20,
    "used_cdp": false,
    "use_current_page": false
  }
}
```

**پارامترهای جدید:**
- `cdp_url`: آدرس CDP برای اتصال به مرورگر موجود (مثلاً: `http://127.0.0.1:9222`)
- `use_current_page`: اگر `true` باشد، agent در صفحه فعلی کار می‌کند و navigate نمی‌کند

### 2. اجرای غیرهمزمان (برای وظایف طولانی)

**Endpoint:** `POST /api/browser/execute-async`

این endpoint وظیفه را در background اجرا می‌کند و فوراً پاسخ می‌دهد.

### 3. بررسی وضعیت سلامت

**Endpoint:** `GET /api/browser/health`

**پاسخ:**
```json
{
  "status": "healthy",
  "browser_initialized": true,
  "llm_initialized": true,
  "openrouter_configured": true
}
```

### 4. دریافت لیست مدل‌های موجود

**Endpoint:** `GET /api/browser/available-models`

این endpoint لیست تمام مدل‌های موجود در `model_factory` را که مناسب browser automation هستند برمی‌گرداند.

**پاسخ:**
```json
{
  "models": [
    {
      "name": "deepseek/deepseek-chat",
      "type": "chat",
      "streaming": true
    }
  ],
  "total": 1,
  "recommended": "deepseek/deepseek-chat"
}
```

### 5. اجرای دستور Agent (برای پنل ادمین)

**Endpoint:** `POST /api/browser/agent-execute`

این endpoint برای اجرای دستورات پیچیده‌تر مانند ساخت کاربر، مدیریت مقالات و غیره در پنل ادمین استفاده می‌شود. Agent به صورت خودکار لاگین می‌کند و سپس task را انجام می‌دهد.

**درخواست:**
```json
{
  "task": "Create a new admin user with email: test@example.com, name: Test User",
  "url": "http://localhost:3000/super-admin",
  "max_steps": 30
}
```

**نکات:**
- این endpoint فقط برای Admin و SuperAdmin قابل دسترسی است
- Agent به صورت خودکار با credentials پیش‌فرض لاگین می‌کند
- برای استفاده از مرورگر موجود، `cdp_url` را ارسال کنید

---

## 📝 مثال‌های کاربردی

### مثال 1: جستجوی قیمت محصول

```python
import requests

response = requests.post(
    "http://localhost:8000/api/browser/execute",
    json={
        "task": "Find the current price of MacBook Pro M3 on Apple website",
        "url": "https://www.apple.com"
    },
    headers={"Authorization": "Bearer YOUR_TOKEN"}
)

result = response.json()
print(result["result"])
```

### مثال 2: پر کردن فرم

```python
response = requests.post(
    "http://localhost:8000/api/browser/execute",
    json={
        "task": "Fill out the contact form on example.com with name: John Doe, email: john@example.com, message: Hello",
        "url": "https://example.com/contact"
    },
    headers={"Authorization": "Bearer YOUR_TOKEN"}
)
```

### مثال 3: استخراج اطلاعات

```python
response = requests.post(
    "http://localhost:8000/api/browser/execute",
    json={
        "task": "Extract the top 5 news headlines from BBC News homepage",
        "url": "https://www.bbc.com/news"
    },
    headers={"Authorization": "Bearer YOUR_TOKEN"}
)
```

### مثال 4: استفاده در کد Python

```python
from app.services.browser_automation_service import browser_automation_service

async def search_product(product_name: str):
    """جستجوی محصول در آمازون"""
    result = await browser_automation_service.execute_task(
        task_description=f"Find the price and rating of {product_name} on Amazon",
        url="https://www.amazon.com"
    )
    
    if result.success:
        return {
            "product": product_name,
            "info": result.result,
            "execution_time": result.execution_time
        }
    else:
        raise Exception(f"Browser automation failed: {result.error}")

# استفاده
product_info = await search_product("iPhone 15")
print(product_info)
```

### مثال 5: استفاده با مرورگر موجود و صفحه فعلی

```python
import requests

# 1. Chrome را با remote debugging باز کنید:
# chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\temp\chrome-debug"

# 2. به صفحه مورد نظر بروید (مثلاً پنل ادمین)

# 3. درخواست را با cdp_url و use_current_page ارسال کنید
response = requests.post(
    "http://localhost:8000/api/browser/execute",
    json={
        "task": "Fill out the user creation form",
        "cdp_url": "http://127.0.0.1:9222",
        "use_current_page": True,
        "max_steps": 20
    },
    headers={"Authorization": "Bearer YOUR_TOKEN"}
)

result = response.json()
print(result["result"])
```

### مثال 6: استفاده از Agent برای پنل ادمین

```python
import requests

response = requests.post(
    "http://localhost:8000/api/browser/agent-execute",
    json={
        "task": "Create a new article with title: 'Test Article', content: 'This is a test'",
        "url": "http://localhost:3000/super-admin",
        "max_steps": 30
    },
    headers={"Authorization": "Bearer YOUR_ADMIN_TOKEN"}
)

result = response.json()
print(result["result"])
```

---

## ⚠️ نکات مهم

### 1. محدودیت‌های امنیتی

- ✅ همیشه URLهای مورد اعتماد را استفاده کنید
- ✅ از اجرای وظایف روی سایت‌های حساس (بانک، ایمیل) خودداری کنید
- ✅ API key OpenRouter را در محیط production محافظت کنید

### 2. عملکرد و هزینه

- ⏱️ وظایف browser automation ممکن است چند ثانیه تا چند دقیقه طول بکشد
- 💰 هر درخواست به OpenRouter هزینه دارد (بر اساس تعداد tokens)
- 📊 برای وظایف طولانی، از endpoint `/execute-async` استفاده کنید

### 3. مدیریت خطا

```python
try:
    result = await browser_automation_service.execute_task(
        task_description="Your task here"
    )
    
    if not result.success:
        logger.error(f"Task failed: {result.error}")
        # مدیریت خطا
        
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    # مدیریت خطای غیرمنتظره
```

### 4. بهینه‌سازی

- 🎯 وظایف را تا حد امکان مشخص و واضح تعریف کنید
- 🔢 `max_steps` را بر اساس پیچیدگی وظیفه تنظیم کنید
- 🚀 برای وظایف ساده، از مدل‌های سریع‌تر استفاده کنید

---

## 🔧 عیب‌یابی

### مشکل: browser-use نصب نشده

```bash
pip install browser-use
```

### مشکل: Chromium نصب نشده

```bash
# روش 1: با استفاده از uvx (توصیه می‌شود)
uvx browser-use install

# روش 2: با استفاده از playwright از طریق Python
python -m playwright install chromium

# روش 3: با استفاده از uvx playwright
uvx playwright install chromium
```

**نکته:** در Windows PowerShell، اگر `playwright` به عنوان دستور مستقیم شناخته نمی‌شود، از `python -m playwright` استفاده کنید.

### مشکل: LLM API key تنظیم نشده

مطمئن شوید که یکی از متغیرهای محیطی زیر تنظیم شده‌اند:

**گزینه 1: OpenAI (توصیه می‌شود)**
```bash
export Embedder_API_KEY=sk-proj-xxxxxxxxxxxxx
```

**گزینه 2: OpenRouter**
```bash
export OPENAI_API_KEY=sk-or-v1-xxxxxxxxxxxxx
export OPENAI_BASE_URL=https://openrouter.ai/api/v1
export CHAT_MODEL=google/gemini-2.5-flash
```

### مشکل: خطای `NotImplementedError` در Windows

این خطا به دلیل محدودیت‌های `asyncio` در Windows رخ می‌دهد. راه‌حل:

**راه‌حل 1: استفاده از مرورگر محلی (پیش‌فرض - بدون نیاز به API key)**

کد به صورت خودکار از `ProactorEventLoop` در Windows استفاده می‌کند و browser automation را در یک thread جداگانه اجرا می‌کند. **نیازی به تنظیمات اضافی نیست** و همه داده‌ها به صورت محلی پردازش می‌شوند.

```bash
# در فایل .env - هیچ تنظیماتی نیاز نیست!
# فقط مطمئن شوید که browser-use نصب شده است:
# pip install browser-use
# uvx browser-use install
```

**راه‌حل 2: استفاده از Browser Use Cloud (اختیاری)**

اگر می‌خواهید از Browser Use Cloud استفاده کنید (برای سرعت بیشتر یا اگر راه‌حل 1 کار نکرد):

```bash
# در فایل .env
BROWSER_USE_CLOUD_ENABLED=true
BROWSER_USE_API_KEY=your-browser-use-api-key
```

**راه‌حل 3: استفاده از WSL (Windows Subsystem for Linux)**

اگر راه‌حل 1 کار نکرد، می‌توانید از WSL استفاده کنید:

```bash
# در WSL
pip install browser-use
uvx browser-use install
```

**راه‌حل 4: استفاده از Docker**

می‌توانید از Docker برای اجرای browser automation استفاده کنید.

### مشکل: خطای timeout

اگر وظایف timeout می‌شوند، `max_steps` را افزایش دهید یا از endpoint async استفاده کنید.

### مشکل: خطای `'ChatOpenAI' object has no attribute 'model'`

این مشکل با `BrowserUseLLMWrapper` حل شده است. اگر هنوز رخ می‌دهد:

1. مطمئن شوید که از آخرین نسخه کد استفاده می‌کنید
2. سرویس به صورت خودکار از `ChatBrowserUse` استفاده می‌کند که بهترین سازگاری را دارد
3. در صورت عدم دسترسی به `ChatBrowserUse`، از wrapper استفاده می‌شود

### مشکل: Agent نمی‌تواند با صفحه تعامل کند

اگر agent نمی‌تواند با عناصر صفحه تعامل کند:

1. **صبر کنید**: صفحات React ممکن است چند ثانیه طول بکشد تا کاملاً بارگذاری شوند
   - سرویس به صورت خودکار 5 ثانیه صبر می‌کند
   - `wait_for_network_idle_page_load_time` به 10 ثانیه تنظیم شده است

2. **از `use_current_page` استفاده کنید**: اگر قبلاً در صفحه مورد نظر هستید
   ```json
   {
     "task": "Your task",
     "use_current_page": true
   }
   ```

3. **`max_steps` را افزایش دهید**: برای وظایف پیچیده‌تر
   ```json
   {
     "task": "Your task",
     "max_steps": 30
   }
   ```

4. **از مرورگر موجود استفاده کنید**: اگر می‌خواهید مرورگر را خودتان کنترل کنید
   ```bash
   # Chrome را با remote debugging باز کنید
   chrome.exe --remote-debugging-port=9222
   ```
   سپس در درخواست:
   ```json
   {
     "task": "Your task",
     "cdp_url": "http://127.0.0.1:9222",
     "use_current_page": true
   }
   ```

---

## 🔍 جزئیات فنی

### معماری سرویس

سرویس browser automation از معماری زیر استفاده می‌کند:

1. **BrowserUseLLMWrapper**: یک wrapper class برای `ChatOpenAI` که با browser-use سازگار است
   - تبدیل پیام‌های browser-use به فرمت langchain
   - پشتیبانی از `model` و `model_name` attributes
   - Forward کردن method calls به ChatOpenAI

2. **ChatBrowserUse**: استفاده از `ChatBrowserUse` از browser-use (اولویت اول)
   - بهترین سازگاری با browser-use
   - پشتیبانی کامل از structured output

3. **Fallback**: در صورت عدم دسترسی به `ChatBrowserUse`، از `ChatOpenAI` با wrapper استفاده می‌شود

### اولویت LLM

سرویس به ترتیب زیر از LLM استفاده می‌کند:

1. **OpenAI GPT-4o-mini** (اگر `Embedder_API_KEY` تنظیم شده باشد)
   - استفاده از `ChatBrowserUse` با OpenAI
   - بهترین سازگاری و عملکرد

2. **OpenRouter** (اگر فقط `OPENAI_API_KEY` تنظیم شده باشد)
   - استفاده از مدل مشخص شده در `CHAT_MODEL`
   - پشتیبانی از تمام مدل‌های OpenRouter

### مدیریت Windows

در Windows، سرویس به صورت خودکار:
- از `ProactorEventLoop` استفاده می‌کند
- browser automation را در یک thread جداگانه اجرا می‌کند
- مشکل `NotImplementedError` را حل می‌کند

### Login Agent

سرویس از یک login agent جداگانه استفاده می‌کند که:
- قبل از انجام task اصلی، لاگین را انجام می‌دهد
- از credentials ارائه شده استفاده می‌کند
- موفقیت لاگین را بررسی می‌کند

## 📚 منابع بیشتر

- [مستندات browser-use](https://github.com/browser-use/browser-use)
- [مستندات OpenRouter](https://openrouter.ai/docs)
- [مستندات OpenAI](https://platform.openai.com/docs)
- [مستندات SallyBot](../README.md)

---

## 🤝 پشتیبانی

اگر سوالی دارید یا مشکلی پیش آمد:

1. بررسی کنید که تمام پیش‌نیازها نصب شده‌اند
2. لاگ‌ها را بررسی کنید (`logs/` directory)
3. وضعیت سلامت را بررسی کنید: `GET /api/browser/health`

---

**نوشته شده برای SallyBot v2.0** 🚀

