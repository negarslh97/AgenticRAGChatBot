#!/usr/bin/env python3
"""
مثال استفاده از Browser Automation Service در SallyBot

این اسکریپت نمونه‌ای از نحوه استفاده از browser automation service را نشان می‌دهد.
"""

import asyncio
import sys
import os

# اضافه کردن مسیر پروژه به sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.browser_automation_service import browser_automation_service


async def example_1_simple_search():
    """مثال 1: جستجوی ساده"""
    print("\n" + "="*60)
    print("مثال 1: جستجوی قیمت محصول")
    print("="*60)
    
    result = await browser_automation_service.execute_task(
        task_description="Find the price of iPhone 15 on Amazon",
        url="https://www.amazon.com",
        max_steps=15
    )
    
    if result.success:
        print(f"✅ موفقیت‌آمیز!")
        print(f"نتیجه: {result.result[:200]}...")  # فقط 200 کاراکتر اول
        print(f"زمان اجرا: {result.execution_time:.2f} ثانیه")
    else:
        print(f"❌ خطا: {result.error}")


async def example_2_custom_model():
    """مثال 2: استفاده از مدل خاص"""
    print("\n" + "="*60)
    print("مثال 2: استفاده از مدل خاص")
    print("="*60)
    
    # استفاده از یک مدل خاص (باید در model_factory ثبت شده باشد)
    result = await browser_automation_service.execute_task_with_custom_llm(
        task_description="Search for Python tutorials on YouTube and get top 3 results",
        model_name="deepseek/deepseek-chat",  # یا هر مدل دیگری
        url="https://www.youtube.com",
        max_steps=20
    )
    
    if result.success:
        print(f"✅ موفقیت‌آمیز!")
        print(f"نتیجه: {result.result[:200]}...")
        print(f"مدل استفاده شده: {result.metadata.get('model_used', 'default')}")
    else:
        print(f"❌ خطا: {result.error}")


async def example_3_health_check():
    """مثال 3: بررسی وضعیت سلامت"""
    print("\n" + "="*60)
    print("مثال 3: بررسی وضعیت سلامت")
    print("="*60)
    
    health = browser_automation_service.get_health_status()
    
    print(f"وضعیت: {health['status']}")
    print(f"Browser initialized: {health['browser_initialized']}")
    print(f"LLM initialized: {health['llm_initialized']}")
    print(f"OpenRouter configured: {health['openrouter_configured']}")


async def main():
    """تابع اصلی"""
    print("🌐 Browser Automation Service Examples")
    print("="*60)
    
    try:
        # بررسی وضعیت سلامت
        await example_3_health_check()
        
        # اجرای مثال‌ها (می‌توانید comment کنید اگر نمی‌خواهید اجرا شوند)
        # await example_1_simple_search()
        # await example_2_custom_model()
        
        print("\n✅ تمام مثال‌ها اجرا شدند!")
        
    except Exception as e:
        print(f"\n❌ خطا در اجرای مثال‌ها: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # بستن browser instance
        await browser_automation_service.close()


if __name__ == "__main__":
    # اجرای مثال‌ها
    asyncio.run(main())

