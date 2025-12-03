# 🤖 راهنمای Browser Automation با CDP

## مقدمه

این راهنما نحوه استفاده از **Chrome DevTools Protocol (CDP)** برای اجرای دستورات Agent در **همان صفحه مرورگر فعلی** (بدون باز کردن پنجره جدید) را توضیح می‌دهد.

---

## 🚀 راه‌اندازی سریع

### قدم ۱: بستن همه پنجره‌های Chrome

```powershell
taskkill /F /IM chrome.exe
```

### قدم ۲: باز کردن Chrome با CDP فعال

```powershell
# Windows
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --remote-allow-origins=* --user-data-dir=C:\temp\chrome-debug-profile "http://localhost:3000/super-admin"
```

```bash
# Linux/Mac
google-chrome --remote-debugging-port=9222 --remote-allow-origins=* --user-data-dir=/tmp/chrome-debug-profile "http://localhost:3000/super-admin"
```

### قدم ۳: بررسی فعال بودن CDP

```powershell
curl http://127.0.0.1:9222/json/version
```

اگر پاسخی شبیه این دریافت کردید، CDP فعال است:

```json
{
  "Browser": "Chrome/142.0.7444.176",
  "Protocol-Version": "1.3",
  "webSocketDebuggerUrl": "ws://127.0.0.1:9222/devtools/browser/..."
}
```

### قدم ۴: اجرای سرورها

```powershell
# Backend
cd sally-backend
.\venv\Scripts\activate
uvicorn main:app --reload

# Frontend (در terminal جداگانه)
cd sally-frontend
npm start
```

### قدم ۵: استفاده از Agent

1. در Chrome (که با CDP باز شده)، به `http://localhost:3000` بروید
2. لاگین کنید
3. از **دستیار سالی** استفاده کنید
4. Agent در **همان صفحه** کار می‌کند!

---

## 📋 پارامترهای API

### Endpoint: `POST /api/browser/agent-execute`

```json
{
  "task": "ایجاد ادمین جدید با ایمیل test@example.com",
  "max_steps": 30,
  "url": "http://localhost:3000/super-admin",
  "cdp_url": "http://127.0.0.1:9222",
  "use_current_page": true
}
```

| پارامتر | نوع | پیش‌فرض | توضیحات |
|---------|-----|---------|---------|
| `task` | string | **الزامی** | دستور زبان طبیعی |
| `max_steps` | number | `30` | حداکثر تعداد مراحل |
| `url` | string | `http://localhost:3000/super-admin` | URL پنل ادمین |
| `cdp_url` | string | `null` | آدرس CDP (مثلاً `http://127.0.0.1:9222`) |
| `use_current_page` | boolean | `false` | استفاده از صفحه فعلی |

---

## 🔄 حالت‌های مختلف

| `cdp_url` | `use_current_page` | رفتار |
|-----------|-------------------|-------|
| `null` | `false` | ✨ Browser جدید باز می‌شود و لاگین می‌کند |
| `"http://127.0.0.1:9222"` | `false` | 🔗 به browser موجود وصل می‌شود، **tab جدید** باز می‌کند |
| `"http://127.0.0.1:9222"` | `true` | 🎯 از **همان صفحه فعلی** استفاده می‌کند (بهترین حالت) |

---

## ⚠️ نکات مهم

### ۱. Chrome باید با CDP باز شود

اگر Chrome را به صورت عادی باز کنید، CDP فعال نیست و Agent **نمی‌تواند** به آن متصل شود.

### ۲. پورت ۹۲۲۲ پیش‌فرض است

می‌توانید پورت دیگری استفاده کنید:

```powershell
chrome.exe --remote-debugging-port=9333
```

و در API:

```json
{
  "cdp_url": "http://127.0.0.1:9333"
}
```

### ۳. Profile جداگانه

پارامتر `--user-data-dir` یک profile جداگانه برای Chrome ایجاد می‌کند. این کار باعث می‌شود:
- تنظیمات Chrome اصلی شما دست نخورد
- مشکلات احتمالی با extensionها رفع شود

### ۴. Fallback به Browser جدید

اگر CDP در دسترس نباشد، Agent به صورت خودکار به روش قبلی (باز کردن browser جدید) **fallback** می‌کند.

---

## 🔧 عیب‌یابی

### مشکل: "CDP not responding"

**علت:** Chrome با CDP باز نشده

**راه‌حل:**
```powershell
# بستن همه Chrome ها
taskkill /F /IM chrome.exe

# باز کردن با CDP
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --remote-allow-origins=*
```

### مشکل: "Could not connect to existing browser"

**علت:** پورت اشتباه یا CDP غیرفعال

**راه‌حل:**
```powershell
# بررسی پورت
netstat -an | findstr "9222"

# باید این را ببینید:
# TCP    127.0.0.1:9222    LISTENING
```

### مشکل: Browser جدید باز می‌شود

**علت:** `use_current_page` تنظیم نشده

**راه‌حل:** مطمئن شوید که هر دو پارامتر تنظیم شده‌اند:
```json
{
  "cdp_url": "http://127.0.0.1:9222",
  "use_current_page": true
}
```

---

## 📝 مثال‌های کاربردی

### ایجاد ادمین جدید

```json
{
  "task": "ایجاد ادمین جدید با ایمیل test@example.com و رمز 123456 و نام Test Admin و نقش Admin",
  "cdp_url": "http://127.0.0.1:9222",
  "use_current_page": true
}
```

### جستجو در لیست ادمین‌ها

```json
{
  "task": "جستجوی ادمین با نام Xtra",
  "cdp_url": "http://127.0.0.1:9222",
  "use_current_page": true
}
```

### تغییر وضعیت ادمین

```json
{
  "task": "غیرفعال کردن ادمین test@example.com",
  "cdp_url": "http://127.0.0.1:9222",
  "use_current_page": true
}
```

---

## 🛠️ اسکریپت راه‌اندازی سریع

فایل `start-with-cdp.ps1`:

```powershell
# بستن Chrome های قبلی
Write-Host "🔄 Closing existing Chrome instances..."
taskkill /F /IM chrome.exe 2>$null

Start-Sleep -Seconds 2

# باز کردن Chrome با CDP
Write-Host "🚀 Starting Chrome with CDP..."
Start-Process "C:\Program Files\Google\Chrome\Application\chrome.exe" -ArgumentList @(
    "--remote-debugging-port=9222",
    "--remote-allow-origins=*",
    "--user-data-dir=C:\temp\chrome-debug-profile",
    "http://localhost:3000/super-admin"
)

Start-Sleep -Seconds 3

# بررسی CDP
Write-Host "🔍 Checking CDP..."
try {
    $response = Invoke-RestMethod -Uri "http://127.0.0.1:9222/json/version" -TimeoutSec 5
    Write-Host "✅ CDP is active!"
    Write-Host "   Browser: $($response.Browser)"
} catch {
    Write-Host "❌ CDP not responding. Please try again."
}
```

---

## 📚 منابع

- [Chrome DevTools Protocol Documentation](https://chromedevtools.github.io/devtools-protocol/)
- [Playwright CDP Connection](https://playwright.dev/docs/api/class-browsertype#browser-type-connect-over-cdp)

---

## تاریخچه تغییرات

| تاریخ | تغییرات |
|-------|---------|
| 2025-12-03 | اضافه شدن پشتیبانی CDP به `agentic_playwright_service.py` |
| 2025-12-03 | آپدیت `SallyFloatingAgent.tsx` برای استفاده از CDP |
| 2025-12-03 | اضافه شدن پارامترهای `cdp_url` و `use_current_page` به API |

