#!/usr/bin/env python3
"""
تست عملکرد AI در آپلود فایل به پایگاه دانش
این اسکریپت یک فایل تستی را آپلود می‌کند تا بررسی کند آیا واقعاً از AI استفاده می‌شود
"""

import requests
import json
import os

# اطلاعات احراز هویت
ADMIN_EMAIL = "xtra_admin@sally.com"
ADMIN_PASSWORD = "123456"

# آدرس سرور
BASE_URL = "http://localhost:8000"

def login_and_get_token():
    """ورود به سیستم و دریافت توکن"""
    login_data = {
        "username": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/auth/login", data=login_data)
        if response.status_code == 200:
            token = response.json().get("access_token")
            print(f"✅ ورود موفق - توکن دریافت شد")
            return token
        else:
            print(f"❌ خطا در ورود: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ خطا در اتصال به سرور: {e}")
        return None

def upload_file_with_ai_test(token):
    """آپلود فایل تستی برای بررسی عملکرد AI"""
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    # آپلود فایل تستی
    try:
        with open("test_ai_upload.txt", "rb") as f:
            files = {"file": ("test_ai_upload.txt", f, "text/plain")}
            
            print("📤 در حال آپلود فایل تستی...")
            response = requests.post(f"{BASE_URL}/api/super-admin/upload", files=files, headers=headers)
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ آپلود موفق!")
                print(f"📄 File ID: {result.get('file_id')}")
                print(f"📝 Article ID: {result.get('article_id')}")
                print(f"📊 Message: {result.get('message')}")
                
                # بررسی اینکه آیا مقاله ایجاد شده است
                article_id = result.get('article_id')
                if article_id:
                    check_article_content(token, article_id)
                
                return True
            else:
                print(f"❌ خطا در آپلود: {response.status_code} - {response.text}")
                return False
                
    except FileNotFoundError:
        print("❌ فایل تستی یافت نشد")
        return False
    except Exception as e:
        print(f"❌ خطا در آپلود: {e}")
        return False

def check_article_content(token, article_id):
    """بررسی محتوای مقاله ایجاد شده برای دیدن نتیجه AI"""
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    try:
        response = requests.get(f"{BASE_URL}/api/super-admin/kb/articles/{article_id}", headers=headers)
        
        if response.status_code == 200:
            article = response.json()
            print("\n" + "="*50)
            print("📋 نتیجه بررسی AI:")
            print("="*50)
            print(f"📝 عنوان: {article.get('title', 'N/A')}")
            print(f"📋 خلاصه: {article.get('summary', 'N/A')}")
            print(f"🏷️  تگ‌ها: {article.get('tags', [])}")
            print(f"📁 دسته‌بندی: {article.get('category', 'N/A')}")
            print(f"👁️  وضعیت: {article.get('status', 'N/A')}")
            print(f"📄 محتوای Markdown: {article.get('content_markdown', 'N/A')[:200]}...")
            print("="*50)
            
            # بررسی اینکه آیا خلاصه و تگ‌ها توسط AI تولید شده‌اند
            summary = article.get('summary', '')
            tags = article.get('tags', [])
            
            if summary and 'محتوای استخراج شده از فایل' not in summary:
                print("✅ احتمالاً خلاصه توسط AI تولید شده است")
            else:
                print("⚠️  ممکن است از فراداده پیش‌فرض استفاده شده باشد")
                
            if tags and len(tags) > 0 and 'آپلود شده' not in tags:
                print("✅ احتمالاً تگ‌ها توسط AI تولید شده‌اند")
            else:
                print("⚠️  ممکن است از تگ‌های پیش‌فرض استفاده شده باشد")
                
        else:
            print(f"❌ خطا در دریافت مقاله: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"❌ خطا در بررسی مقاله: {e}")

def main():
    """اجرای تست کامل"""
    print("🚀 شروع تست عملکرد AI در آپلود فایل...")
    print("="*60)
    
    # بررسی وجود فایل تستی
    if not os.path.exists("test_ai_upload.txt"):
        print("❌ فایل تستی یافت نشد. لطفاً ابتدا فایل test_ai_upload.txt را ایجاد کنید")
        return
    
    # ورود به سیستم
    token = login_and_get_token()
    if not token:
        return
    
    print("-" * 40)
    
    # آپلود فایل
    upload_file_with_ai_test(token)

if __name__ == "__main__":
    main()