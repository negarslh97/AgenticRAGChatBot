"""
🧪 تست Agentic Playwright Service

این فایل شامل مثال‌های مختلف برای تست و استفاده از Agentic Playwright Service است.
"""

import asyncio
import os
from app.services.agentic_playwright_service import AgenticPlaywrightService, agentic_playwright_service
from app.core.logging_config import get_logger

logger = get_logger(__name__)


async def test_basic_admin_creation():
    """تست ساده ساخت ادمین"""
    print("\n" + "="*60)
    print("🧪 تست 1: ساخت ادمین ساده")
    print("="*60)
    
    try:
        result = await agentic_playwright_service.create_admin(
            admin_email="test_admin@example.com",
            admin_password="test123456",
            login_email="xtra_admin@sally.com",
            login_password="123456",
            admin_full_name="Test Admin",
            admin_role="Admin",
            url="http://localhost:3000/super-admin"
        )
        
        print(f"\n✅ نتیجه:")
        print(f"  Success: {result.success}")
        print(f"  Result: {result.result}")
        print(f"  Steps: {len(result.steps_taken) if result.steps_taken else 0}")
        print(f"  Screenshots: {len(result.screenshots) if result.screenshots else 0}")
        
        if result.error:
            print(f"  Error: {result.error}")
        
        # نمایش مراحل
        if result.steps_taken:
            print(f"\n📊 مراحل انجام شده:")
            for i, step in enumerate(result.steps_taken, 1):
                print(f"  {i}. {step.get('action', 'unknown')}: {step.get('success', False)} "
                      f"(confidence: {step.get('ai_confidence', 0):.2f})")
        
        return result.success
        
    except Exception as e:
        print(f"\n❌ خطا: {e}")
        logger.error(f"Test failed: {e}", exc_info=True)
        return False


async def test_with_openrouter_model():
    """تست با استفاده از مدل OpenRouter"""
    print("\n" + "="*60)
    print("🧪 تست 2: استفاده از مدل OpenRouter")
    print("="*60)
    
    # مدل‌های پیشنهادی OpenRouter با Vision:
    # - google/gemini-2.5-flash (رایگان)
    # - google/gemini-pro-vision
    # - anthropic/claude-3.5-sonnet
    # - x-ai/grok-beta
    
    # فقط مدل‌هایی که از Vision پشتیبانی می‌کنند
    openrouter_models = [
        "google/gemini-2.5-flash"
        "amazon/nova-2-lite-v1",  # Vision-capable
        # "anthropic/claude-3.5-sonnet",  # نیاز به API key
    ]
    
    for model_name in openrouter_models:
        print(f"\n🔍 تست با مدل: {model_name}")
        
        try:
            # ساخت سرویس با مدل OpenRouter
            service = AgenticPlaywrightService(vision_model=model_name)
            
            result = await service.create_admin(
                admin_email="test_openrouter@example.com",
                admin_password="test123456",
                login_email="xtra_admin@sally.com",
                login_password="123456",
                admin_full_name="OpenRouter Test",
                admin_role="Admin",
                url="http://localhost:3000/super-admin"
            )
            
            print(f"  ✅ Success: {result.success}")
            print(f"  📊 Steps: {len(result.steps_taken) if result.steps_taken else 0}")
            
            if result.success:
                print(f"  ✅ مدل {model_name} کار کرد!")
                return True
            else:
                print(f"  ⚠️ مدل {model_name} خطا داشت: {result.error}")
                
        except Exception as e:
            print(f"  ❌ خطا با مدل {model_name}: {e}")
            continue
    
    return False


async def test_with_custom_settings():
    """تست با تنظیمات سفارشی"""
    print("\n" + "="*60)
    print("🧪 تست 3: تنظیمات سفارشی")
    print("="*60)
    
    try:
        # ساخت سرویس با تنظیمات سفارشی
        service = AgenticPlaywrightService(
            vision_model="google/gemini-2.5-flash"  # مدل رایگان
        )
        service.max_iterations = 15  # کاهش تعداد تکرار برای تست سریع‌تر
        
        result = await service.create_admin(
            admin_email="custom_test@example.com",
            admin_password="custom123",
            login_email="xtra_admin@sally.com",
            login_password="123456",
            admin_full_name="Custom Test",
            admin_role="Admin",
            url="http://localhost:3000/super-admin"
        )
        
        print(f"\n✅ نتیجه:")
        print(f"  Success: {result.success}")
        print(f"  Max Iterations: {service.max_iterations}")
        print(f"  Actual Steps: {len(result.steps_taken) if result.steps_taken else 0}")
        
        return result.success
        
    except Exception as e:
        print(f"\n❌ خطا: {e}")
        return False


async def test_step_by_step():
    """تست مرحله به مرحله با نمایش جزئیات"""
    print("\n" + "="*60)
    print("🧪 تست 4: نمایش جزئیات مراحل")
    print("="*60)
    
    try:
        service = AgenticPlaywrightService(
            vision_model="google/gemini-2.5-flash"
        )
        
        # Override برای نمایش جزئیات بیشتر
        original_analyze = service._analyze_page_with_ai
        
        async def detailed_analyze(*args, **kwargs):
            result = await original_analyze(*args, **kwargs)
            print(f"\n  🤖 AI Decision:")
            print(f"    Action: {result.get('action')}")
            print(f"    Element: {result.get('element_description', 'N/A')}")
            print(f"    Confidence: {result.get('confidence', 0):.2f}")
            print(f"    Reasoning: {result.get('reasoning', 'N/A')[:100]}...")
            return result
        
        service._analyze_page_with_ai = detailed_analyze
        
        result = await service.create_admin(
            admin_email="detailed_test@example.com",
            admin_password="detailed123",
            login_email="xtra_admin@sally.com",
            login_password="123456",
            admin_full_name="Detailed Test",
            admin_role="Admin",
            url="http://localhost:3000/super-admin"
        )
        
        print(f"\n✅ نتیجه نهایی:")
        print(f"  Success: {result.success}")
        
        return result.success
        
    except Exception as e:
        print(f"\n❌ خطا: {e}")
        return False


async def test_error_handling():
    """تست مدیریت خطا"""
    print("\n" + "="*60)
    print("🧪 تست 5: مدیریت خطا")
    print("="*60)
    
    try:
        # تست با URL اشتباه
        result = await agentic_playwright_service.create_admin(
            admin_email="error_test@example.com",
            admin_password="error123",
            login_email="wrong@example.com",
            login_password="wrong",
            url="http://invalid-url-that-does-not-exist:3000"
        )
        
        print(f"\n⚠️ نتیجه (انتظار خطا):")
        print(f"  Success: {result.success}")
        print(f"  Error: {result.error}")
        
        # اگر خطا به درستی مدیریت شد، موفق است
        return not result.success and result.error is not None
        
    except Exception as e:
        print(f"\n✅ خطا به درستی مدیریت شد: {e}")
        return True


async def main():
    """اجرای تمام تست‌ها"""
    print("\n" + "="*60)
    print("🚀 شروع تست‌های Agentic Playwright Service")
    print("="*60)
    
    # بررسی تنظیمات
    from app.core.config import settings
    
    print("\n📋 تنظیمات:")
    print(f"  OpenRouter API Key: {'✅ تنظیم شده' if settings.openai_api_key_loaded else '❌ تنظیم نشده'}")
    print(f"  OpenRouter Base URL: {settings.openai_base_url_loaded or 'پیش‌فرض'}")
    print(f"  OpenAI API Key: {'✅ تنظیم شده' if settings.embedder_api_key_loaded else '❌ تنظیم نشده'}")
    
    if not settings.openai_api_key_loaded and not settings.embedder_api_key_loaded:
        print("\n⚠️ هشدار: هیچ API Key تنظیم نشده است!")
        print("   لطفاً در فایل .env یکی از موارد زیر را تنظیم کنید:")
        print("   - OPENAI_API_KEY=sk-... (برای OpenRouter)")
        print("   - Embedder_API_KEY=sk-... (برای OpenAI)")
        return
    
    # لیست تست‌ها
    tests = [
        ("تست ساده", test_basic_admin_creation),
        ("تست با OpenRouter", test_with_openrouter_model),
        ("تست تنظیمات سفارشی", test_with_custom_settings),
        # ("تست جزئیات", test_step_by_step),  # غیرفعال برای سرعت بیشتر
        # ("تست مدیریت خطا", test_error_handling),  # غیرفعال برای سرعت بیشتر
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            print(f"\n{'='*60}")
            print(f"▶️  اجرای {test_name}...")
            print(f"{'='*60}")
            
            success = await test_func()
            results.append((test_name, success))
            
            if success:
                print(f"\n✅ {test_name} موفق بود!")
            else:
                print(f"\n❌ {test_name} ناموفق بود!")
                
        except Exception as e:
            print(f"\n❌ خطا در {test_name}: {e}")
            results.append((test_name, False))
    
    # خلاصه نتایج
    print("\n" + "="*60)
    print("📊 خلاصه نتایج")
    print("="*60)
    
    for test_name, success in results:
        status = "✅" if success else "❌"
        print(f"{status} {test_name}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    print(f"\n🎯 نتیجه کلی: {passed}/{total} تست موفق")


if __name__ == "__main__":
    # اجرای تست‌ها
    asyncio.run(main())

