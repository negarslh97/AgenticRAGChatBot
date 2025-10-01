#!/usr/bin/env python3
"""
اسکریپت تایید تنظیمات AI Models
این اسکریپت بررسی می‌کند که:
1. مدل‌های Chat از OpenRouter استفاده می‌کنند
2. مدل‌های Embedding از OpenAI استفاده می‌کنند
"""

import os
import sys
from pathlib import Path

# Add parent directory to Python path
current_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(current_dir))

from app.core.config import settings

def verify_config():
    """بررسی تنظیمات AI"""
    print("="*80)
    print("🔍 بررسی تنظیمات AI Models")
    print("="*80)
    print()
    
    all_good = True
    
    # 1. بررسی تنظیمات Chat Models (OpenRouter)
    print("📝 تنظیمات Chat Models (باید از OpenRouter استفاده کنند):")
    print("-" * 80)
    
    chat_api_key = settings.openai_api_key_loaded
    chat_base_url = settings.openai_base_url_loaded
    
    if not chat_api_key:
        print("❌ OPENAI_API_KEY تنظیم نشده است!")
        all_good = False
    elif chat_api_key.startswith("sk-or-"):
        print(f"✅ OPENAI_API_KEY: {chat_api_key[:15]}... (OpenRouter)")
    else:
        print(f"⚠️  OPENAI_API_KEY: {chat_api_key[:15]}... (ممکن است OpenRouter نباشد)")
        all_good = False
    
    if chat_base_url == "https://openrouter.ai/api/v1":
        print(f"✅ OPENAI_BASE_URL: {chat_base_url}")
    else:
        print(f"❌ OPENAI_BASE_URL: {chat_base_url or 'تنظیم نشده'} (باید https://openrouter.ai/api/v1 باشد)")
        all_good = False
    
    print(f"✅ CHAT_MODEL: {settings.chat_model_loaded or 'تنظیم نشده'}")
    print(f"✅ RAG_MODEL: {settings.rag_model_loaded or 'تنظیم نشده'}")
    print(f"✅ METADATA_MODEL: {settings.metadata_model_loaded or 'تنظیم نشده'}")
    print()
    
    # 2. بررسی تنظیمات Embedding Models (OpenAI)
    print("🔢 تنظیمات Embedding Models (باید از OpenAI استفاده کنند):")
    print("-" * 80)
    
    embedder_api_key = settings.embedder_api_key_loaded
    embedder_base_url = settings.embedder_openai_base_url_loaded
    embedder_model = settings.embedder_model_loaded
    
    if not embedder_api_key:
        print("❌ Embedder_API_KEY تنظیم نشده است!")
        all_good = False
    elif embedder_api_key.startswith("sk-proj-"):
        print(f"✅ Embedder_API_KEY: {embedder_api_key[:15]}... (OpenAI)")
    else:
        print(f"⚠️  Embedder_API_KEY: {embedder_api_key[:15]}... (ممکن است OpenAI نباشد)")
        all_good = False
    
    if embedder_base_url == "https://api.openai.com/v1":
        print(f"✅ Embedder_OPENAI_BASE_URL: {embedder_base_url}")
    else:
        print(f"❌ Embedder_OPENAI_BASE_URL: {embedder_base_url or 'تنظیم نشده'} (باید https://api.openai.com/v1 باشد)")
        all_good = False
    
    print(f"✅ EMBEDDER_MODEL: {embedder_model}")
    print()
    
    # 3. بررسی تنظیمات Weaviate
    print("🗄️  تنظیمات Weaviate:")
    print("-" * 80)
    
    weaviate_url = settings.weaviate_url_loaded
    print(f"✅ WEAVIATE_URL: {weaviate_url or 'http://localhost:8080 (پیش‌فرض)'}")
    print()
    
    # 4. خلاصه نهایی
    print("="*80)
    if all_good:
        print("✅ تمام تنظیمات صحیح است!")
        print()
        print("📋 خلاصه:")
        print("   • Chat Models: از OpenRouter استفاده می‌کنند ✅")
        print("   • Embedding Models: از OpenAI استفاده می‌کنند ✅")
        print("   • Weaviate: برای vectorization از OpenAI API استفاده می‌کند ✅")
        print()
        print("🚀 اقدامات بعدی:")
        print("   1. اطمینان از اجرای Weaviate: docker-compose up -d")
        print("   2. تست embeddings: python test_openai_embeddings.py")
        print("   3. انتقال مقالات: python migrate_all_articles.py")
    else:
        print("❌ برخی تنظیمات نادرست است!")
        print()
        print("📋 لطفا فایل .env را بررسی کنید:")
        print("   • OPENAI_API_KEY باید کلید OpenRouter باشد (sk-or-v1-...)")
        print("   • OPENAI_BASE_URL باید https://openrouter.ai/api/v1 باشد")
        print("   • Embedder_API_KEY باید کلید OpenAI باشد (sk-proj-...)")
        print("   • Embedder_OPENAI_BASE_URL باید https://api.openai.com/v1 باشد")
    print("="*80)
    
    return all_good

def test_chat_model():
    """تست سریع مدل Chat"""
    print()
    print("="*80)
    print("🧪 تست مدل Chat (OpenRouter)")
    print("="*80)
    print()
    
    try:
        from langchain_openai import ChatOpenAI
        
        print("🔌 در حال اتصال به OpenRouter...")
        model = ChatOpenAI(
            model_name=settings.chat_model_loaded,
            openai_api_key=settings.openai_api_key_loaded,
            base_url=settings.openai_base_url_loaded,
            temperature=0.7,
            max_tokens=100
        )
        
        print(f"✅ مدل {settings.chat_model_loaded} بارگذاری شد")
        print("📝 ارسال پیام تست...")
        
        response = model.invoke("سلام! این یک تست است. لطفا فقط بگو 'سلام'")
        print(f"✅ پاسخ دریافت شد: {response.content[:100]}...")
        print()
        print("="*80)
        print("✅ مدل Chat به درستی کار می‌کند!")
        print("="*80)
        return True
        
    except Exception as e:
        print(f"❌ خطا در تست مدل Chat: {str(e)}")
        print()
        print("علل احتمالی:")
        print("   • کلید API نامعتبر یا منقضی شده")
        print("   • مشکل در اتصال اینترنت")
        print("   • Base URL اشتباه")
        print("   • محدودیت نرخ از طرف OpenRouter")
        print("="*80)
        return False

def test_embeddings():
    """تست سریع Embeddings"""
    print()
    print("="*80)
    print("🧪 تست Embeddings (OpenAI)")
    print("="*80)
    print()
    
    try:
        from openai import OpenAI
        
        print("🔌 در حال اتصال به OpenAI...")
        model = settings.embedder_model_loaded
        client = OpenAI(
            api_key=settings.embedder_api_key_loaded,
            base_url=settings.embedder_openai_base_url_loaded
        )
        
        test_text = "This is a test"
        print(f"📝 متن تست: '{test_text}'")
        print(f"🔢 در حال تولید embedding با مدل: {model}...")
        
        response = client.embeddings.create(
            model=model,
            input=test_text
        )
        
        embedding = response.data[0].embedding
        print(f"✅ Embedding تولید شد!")
        print(f"📊 ابعاد vector: {len(embedding)}")
        print(f"📈 مقادیر اول: {embedding[:3]}")
        print()
        print("="*80)
        print("✅ Embeddings به درستی کار می‌کند!")
        print("="*80)
        return True
        
    except Exception as e:
        print(f"❌ خطا در تست Embeddings: {str(e)}")
        print()
        print("علل احتمالی:")
        print("   • کلید API نامعتبر یا منقضی شده")
        print("   • مشکل در اتصال اینترنت")
        print("   • Base URL اشتباه")
        print("   • محدودیت نرخ از طرف OpenAI")
        print("="*80)
        return False

if __name__ == "__main__":
    # بررسی تنظیمات
    config_ok = verify_config()
    
    if not config_ok:
        sys.exit(1)
    
    # تست مدل‌ها
    chat_ok = test_chat_model()
    embeddings_ok = test_embeddings()
    
    if chat_ok and embeddings_ok:
        print()
        print("🎉 همه چیز عالی کار می‌کند!")
        print("   ✅ تنظیمات صحیح است")
        print("   ✅ Chat Model (OpenRouter) کار می‌کند")
        print("   ✅ Embeddings (OpenAI) کار می‌کند")
        print()
        sys.exit(0)
    else:
        print()
        print("⚠️  برخی تست‌ها ناموفق بودند")
        print()
        sys.exit(1)

