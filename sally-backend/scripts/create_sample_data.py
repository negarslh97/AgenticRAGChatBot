# scripts/create_sample_data.py
from pymongo import MongoClient
import datetime

def create_sample_articles():
    client = MongoClient("mongodb://localhost:27017/")
    db = client["sallybot"]
    collection = db["knowledgebasearticles"]
    
    sample_articles = [
        {
            "title": "نحوه ایجاد حساب کاربری",
            "content": "برای ایجاد حساب کاربری در سیستم، به صفحه ثبت‌نام مراجعه کرده و اطلاعات خواسته شده را تکمیل نمایید. پس از تأیید ایمیل، حساب شما فعال خواهد شد.",
            "summary": "راهنمای کامل ایجاد حساب کاربری در سیستم",
            "status": "PUBLISHED",
            "visibility": "PUBLIC",
            "category": "حساب کاربری",
            "tags": ["حساب", "ثبت‌نام", "ورود"],
            "createdAt": datetime.datetime.now(),
            "updatedAt": datetime.datetime.now()
        },
        {
            "title": "راهنمای بازیابی رمز عبور",
            "content": "اگر رمز عبور خود را فراموش کرده‌اید، روی لینک 'فراموشی رمز عبور' کلیک کرده و ایمیل خود را وارد نمایید. لینک بازیابی برای شما ارسال خواهد شد.",
            "summary": "مراحل بازیابی رمز عبور فراموش شده",
            "status": "PUBLISHED", 
            "visibility": "PUBLIC",
            "category": "امنیت",
            "tags": ["رمز عبور", "بازیابی", "امنیت"],
            "createdAt": datetime.datetime.now(),
            "updatedAt": datetime.datetime.now()
        }
    ]
    
    result = collection.insert_many(sample_articles)
    print(f"✅ Created {len(result.inserted_ids)} sample articles")
    
    client.close()

if __name__ == "__main__":
    create_sample_articles()