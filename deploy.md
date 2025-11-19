# 🚀 راهنمای کامل دیپلوی پروژه SallyBot

این راهنما مراحل کامل دیپلوی پروژه SallyBot (React Frontend + FastAPI Backend) روی سرور Ubuntu را توضیح می‌دهد.

## 📋 پیش‌نیازها

### روی لوکال (سیستم توسعه):
- Node.js 16+
- Python 3.8+
- Git
- دسترسی SSH به سرور

### روی سرور:
- Ubuntu 18.04+ یا Debian
- sudo access
- SSH server
- Python 3.8+
- Node.js (اختیاری، چون frontend build می‌شود)
- MongoDB (در حال اجرا)
- Redis (در حال اجرا)
- Weaviate (در حال اجرا)
- Nginx

## 🔧 مرحله ۱: آماده‌سازی تغییرات روی لوکال

### ۱.۱ چک کردن وضعیت Git
```bash
# وضعیت تغییرات
git status

# اگر تغییرات unstaged داری
git add .

# commit تغییرات
git commit -m "Deploy: Update features and fixes"

# push به repository
git push origin dev
```

### ۱.۲ Build کردن Frontend
```bash
# رفتن به دایرکتوری frontend
cd sally-frontend

# نصب dependencies (اگر نیاز باشه)
npm install

# build برای production
npm run build

# چک کردن فایل‌های build شده
ls -la build/
```

### ۱.۳ آماده‌سازی Backend (اختیاری)
اگر تغییرات backend نیاز به build یا کامپایل داشته باشه، در اینجا انجام دهید.

## 📤 مرحله ۲: انتقال فایل‌ها به سرور

### ۲.۱ تنظیم دسترسی‌های SSH
```bash
# تست اتصال SSH
ssh aiuser@192.168.10.221

# اگر اولین باره، کلید SSH اضافه کن
ssh-copy-id aiuser@192.168.10.221
```

### ۲.۲ انتقال فایل‌های Frontend
```bash
# انتقال فایل‌های build شده frontend
scp -r sally-frontend/build/* aiuser@192.168.10.221:/var/www/sally-frontend/
```

### ۲.۳ انتقال فایل‌های Backend (اگر نیاز به آپدیت باشه)
```bash
# انتقال کل دایرکتوری backend
scp -r sally-backend/* aiuser@192.168.10.221:~/apps/SallyChatBot/sally-backend/
```

## 🔧 مرحله ۳: تنظیم دسترسی‌ها روی سرور

### ۳.۱ اضافه کردن کاربر به گروه www-data (اگر لازم باشه)
```bash
# روی سرور
sudo usermod -a -G www-data aiuser

# logout و login مجدد
exit
ssh aiuser@192.168.10.221

# چک کردن عضویت در گروه
groups aiuser
```

### ۳.۲ تنظیم permissions برای frontend
```bash
# تنظیم ownership و permissions
sudo chown -R www-data:www-data /var/www/sally-frontend/
sudo chmod -R 755 /var/www/sally-frontend/
```

## 🔄 مرحله ۴: ری‌استارت و آپدیت سرویس‌ها

### ۴.۱ آپدیت Backend Dependencies (اگر فایل‌ها تغییر کرده)
```bash
# رفتن به دایرکتوری backend
cd ~/apps/SallyChatBot/sally-backend

# فعال کردن virtual environment
source venv/bin/activate

# آپدیت dependencies
pip install -r requirements.txt

# غیرفعال کردن virtual environment
deactivate
```

### ۴.۲ ری‌استارت سرویس‌های سیستم

#### استاپ سرویس‌ها:
```bash
# استاپ backend
sudo systemctl stop sally-backend

# استاپ nginx
sudo systemctl stop nginx
```

#### استارت سرویس‌ها:
```bash
# استارت backend
sudo systemctl start sally-backend

# استارت nginx
sudo systemctl start nginx
```

#### چک کردن وضعیت:
```bash
# وضعیت backend
sudo systemctl status sally-backend

# وضعیت nginx
sudo systemctl status nginx
```

## 🔍 مرحله ۵: تست و بررسی عملکرد

### ۵.۱ تست دسترسی به Frontend
```bash
# تست HTTP access
curl -I http://192.168.10.221/

# تست HTTPS (اگر تنظیم شده)
curl -I https://your-domain.com/

# چک کردن محتوای صفحه
curl -s http://192.168.10.221/ | head -20
```

### ۵.۲ تست Backend API
```bash
# تست health check
curl http://localhost:8000/api/system/health

# تست API documentation
curl -I http://localhost:8000/docs
```

### ۵.۳ تست Database Connections
```bash
# اگر از Docker استفاده می‌کنی
sudo docker ps | grep -E "(mongo|redis|weaviate)"

# یا چک کردن سرویس‌ها
sudo systemctl status mongod
sudo systemctl status redis-server
```

### ۵.۴ چک کردن لاگ‌ها
```bash
# لاگ‌های backend
sudo journalctl -u sally-backend.service -f

# لاگ‌های nginx
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log

# لاگ‌های application
tail -f ~/apps/SallyChatBot/sally-backend/logs/app.log
```

## 🚨 مرحله ۶: عیب‌یابی مشکلات رایج

### ۶.۱ Permission Denied
```bash
# اضافه کردن کاربر به گروه
sudo usermod -a -G www-data aiuser
newgrp www-data

# یا تغییر ownership
sudo chown -R aiuser:aiuser /var/www/sally-frontend/

# یا تنظیم permissions
sudo chmod -R 775 /var/www/sally-frontend/
```

### ۶.۲ Backend Start نمی‌شود
```bash
# چک کردن خطاها
sudo journalctl -u sally-backend.service --no-pager | tail -50

# تست manual اجرا
cd ~/apps/SallyChatBot/sally-backend
source venv/bin/activate
python main.py

# چک کردن syntax
python -m py_compile main.py
```

### ۶.۳ Nginx Error
```bash
# چک کردن configuration
sudo nginx -t

# ری‌استارت nginx
sudo systemctl restart nginx

# چک کردن error logs
sudo tail -f /var/log/nginx/error.log
```

### ۶.۴ Port Conflicts
```bash
# چک کردن پورت‌های باز
sudo netstat -tlnp | grep -E "(8000|80|443)"

# kill کردن process‌های conflicting
sudo kill -9 <PID>
```

### ۶.۵ Database Connection Issues
```bash
# تست اتصال MongoDB
mongosh --eval "db.adminCommand('ping')"

# تست Redis
redis-cli ping

# تست Weaviate
curl http://localhost:8080/v1/.well-known/ready
```

### ۶.۶ Memory Pressure Warnings
اگر warning هایی مثل "Memory pressure detected: 87.7%" می‌بینید:
```bash
# چک کردن استفاده از حافظه
free -h
htop

# تنظیمات cache رو تغییر دهید در model_factory.py:
cache_config = CacheConfig(
    max_size=100,
    ttl=300,
    memory_threshold_percent=90.0,  # افزایش از 80 به 90%
    memory_cleanup_ratio=0.5  # افزایش از 0.3 به 0.5
)

# یا غیرفعال کردن memory pressure monitoring:
cache_config = CacheConfig(
    max_size=100,
    ttl=300,
    memory_pressure_enabled=False  # غیرفعال کردن monitoring
)

# ری‌استارت سرویس بعد از تغییرات
sudo systemctl restart sally-backend
```

## 📊 مرحله ۷: مانیتورینگ و نگهداری

### ۷.۱ تنظیم Log Rotation
```bash
# چک کردن logrotate برای nginx
sudo cat /etc/logrotate.d/nginx

# برای backend logs
sudo logrotate -f /etc/logrotate.conf
```

### ۷.۲ Backup Strategy
```bash
# backup از database
mongodump --db SallyChatBot --out /backup/mongodb_$(date +%Y%m%d)

# backup از فایل‌ها
tar -czf /backup/sallybot_$(date +%Y%m%d).tar.gz ~/apps/SallyChatBot/
```

### ۷.۳ Monitoring Commands
```bash
# چک کردن استفاده منابع
htop
df -h
free -h

# چک کردن سرویس‌ها
sudo systemctl status sally-backend nginx mongod redis-server

# چک کردن پورت‌ها
sudo netstat -tlnp
```

## 🔒 مرحله ۸: امنیت

### ۸.۱ تنظیم Firewall
```bash
# اگر UFW استفاده می‌کنی
sudo ufw status
sudo ufw allow 80
sudo ufw allow 443
sudo ufw allow 22
```

### ۸.۲ SSL Certificate (Let's Encrypt)
```bash
# نصب certbot
sudo apt install certbot python3-certbot-nginx

# دریافت certificate
sudo certbot --nginx -d your-domain.com

# تست renewal
sudo certbot renew --dry-run
```

## 🎯 چک لیست نهایی دیپلوی

- [ ] تغییرات git commit و push شده
- [ ] Frontend build شده
- [ ] فایل‌ها به سرور منتقل شده
- [ ] Permissions تنظیم شده
- [ ] Dependencies آپدیت شده
- [ ] سرویس‌ها ری‌استارت شده
- [ ] Frontend از طریق HTTP قابل دسترسی
- [ ] Backend API کار می‌کنه
- [ ] Database connections برقرار
- [ ] لاگ‌ها خطا ندارند
- [ ] SSL تنظیم شده (اختیاری)

## 🆘 تماس برای کمک

اگر در هر مرحله‌ای مشکل داشتی:
1. لاگ‌های مربوط رو چک کن
2. وضعیت سرویس‌ها رو بررسی کن
3. جزئیات خطا رو کپی کن
4. با تیم پشتیبانی تماس بگیر

**موفق باشید! 🚀**