#!/usr/bin/env python3
"""
🧪 اسکریپت تست streaming برای مدل‌های مختلف

این اسکریپت برای تست سریع مدل‌های OpenRouter، OpenAI و Ollama استفاده می‌شود.

استفاده:
    cd sally-backend
    python scripts/test_streaming_models.py

یا برای تست یک مدل خاص:
    python scripts/test_streaming_models.py gpt-4o-mini
"""

import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# 🔑 بارگذاری متغیرهای محیطی از فایل .env
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
    print(f"✅ Loaded .env from: {env_path}\n")
else:
    print(f"⚠️ .env file not found at: {env_path}")
    print(f"   Trying to load from current directory...\n")
    load_dotenv()


async def test_model(model_id: str, verbose: bool = True):
    """
    تست یک مدل خاص
    
    Args:
        model_id: شناسه مدل (e.g., "gpt-4o-mini", "google/gemini-2.0-flash-exp:free")
        verbose: نمایش جزئیات بیشتر
    
    Returns:
        True اگر مدل کار کند، False در غیر این صورت
    """
    if verbose:
        print(f"\n{'='*60}")
        print(f"🧪 Testing model: {model_id}")
        print(f"{'='*60}")
    
    try:
        # 🔍 تشخیص provider و انتخاب API key مناسب
        model_lower = model_id.lower()
        
        if model_lower.startswith("gpt-"):
            # OpenAI رسمی
            api_key = os.getenv("Embedder_API_KEY") or os.getenv("OPENAI_API_KEY")
            base_url = os.getenv("Embedder_OPENAI_BASE_URL") or "https://api.openai.com/v1"
            provider = "OpenAI (Official)"
        elif model_lower.startswith("ollama:"):
            # Ollama محلی
            api_key = "ollama"  # Ollama doesn't need API key
            base_url = os.getenv("OLLAMA_URL") or "http://localhost:11434"
            provider = "Ollama (Local)"
        else:
            # OpenRouter (Gemini, Grok, DeepSeek, ...)
            api_key = os.getenv("OPENAI_API_KEY")
            base_url = os.getenv("OPENAI_BASE_URL") or "https://openrouter.ai/api/v1"
            provider = "OpenRouter"
        
        if not api_key:
            if verbose:
                print(f"❌ API Key not found in environment!")
                print(f"   Provider: {provider}")
                print(f"   Required env var: {'Embedder_API_KEY' if provider == 'OpenAI (Official)' else 'OPENAI_API_KEY'}")
            return False
        
        if verbose:
            print(f"🔑 Provider: {provider}")
            print(f"🔗 API URL: {base_url}")
            print(f"🔑 API Key: {api_key[:10]}...{api_key[-4:] if len(api_key) > 14 else ''}")
            print(f"📝 Testing with a simple question...")
        
        # ساخت مدل
        llm = ChatOpenAI(
            model_name=model_id,
            openai_api_key=api_key,
            base_url=base_url,
            temperature=0.7,
            streaming=True
        )
        
        # تست streaming
        if verbose:
            print(f"🌊 Starting stream...")
        
        chunk_count = 0
        empty_count = 0
        content_parts = []
        
        async for chunk in llm.astream("سلام! یک جمله ساده فارسی بگو."):
            chunk_count += 1
            
            if hasattr(chunk, 'content'):
                content = chunk.content
            else:
                content = str(chunk)
            
            if not content or len(content.strip()) == 0:
                empty_count += 1
                if verbose and empty_count <= 5:
                    print(f"  Chunk {chunk_count}: [EMPTY] (type: {type(chunk).__name__})")
            else:
                content_parts.append(content)
                if verbose and chunk_count <= 5:
                    print(f"  Chunk {chunk_count}: [{content[:50]}...] (len: {len(content)})")
        
        # نتیجه
        full_response = "".join(content_parts)
        
        if verbose:
            print(f"\n{'='*60}")
            print(f"📊 Results:")
            print(f"  Total chunks: {chunk_count}")
            print(f"  Empty chunks: {empty_count}")
            print(f"  Content chunks: {chunk_count - empty_count}")
            print(f"  Response length: {len(full_response)} chars")
            print(f"\n💬 Full Response:")
            print(f"  {full_response[:200]}{'...' if len(full_response) > 200 else ''}")
            print(f"{'='*60}")
        
        if len(full_response) > 0:
            if verbose:
                print(f"✅ Model works! Response received.")
            return True
        else:
            if verbose:
                print(f"❌ Model failed! No content received.")
            return False
            
    except Exception as e:
        if verbose:
            print(f"❌ Error testing model: {e}")
            import traceback
            traceback.print_exc()
        return False


async def main():
    """تست چند مدل مختلف"""
    
    # اگر مدل خاصی در command line داده شده، فقط اون رو تست کن
    if len(sys.argv) > 1:
        model_id = sys.argv[1]
        success = await test_model(model_id, verbose=True)
        sys.exit(0 if success else 1)
    
    # لیست مدل‌های پیشنهادی برای تست
    models_to_test = [
        # مدل‌های OpenAI رسمی
        "gpt-4o-mini",
        
        # مدل‌های OpenRouter رایگان
        "google/gemini-2.0-flash-exp:free",
        "deepseek/deepseek-chat-v3.1:free",
        
        # مدل‌های تست‌نشده (می‌توانید uncomment کنید)
        # "z-ai/glm-4.6",
        # "x-ai/grok-4-fast",
    ]
    
    results = {}
    
    print("🚀 Starting model tests...")
    print(f"   Testing {len(models_to_test)} models")
    print()
    
    for model_id in models_to_test:
        success = await test_model(model_id, verbose=True)
        results[model_id] = "✅ Works" if success else "❌ Failed"
        await asyncio.sleep(1)  # کمی تاخیر بین تست‌ها
    
    # خلاصه نتایج
    print(f"\n\n{'='*60}")
    print(f"📋 SUMMARY OF TESTS:")
    print(f"{'='*60}")
    for model_id, result in results.items():
        print(f"  {result}  {model_id}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(main())
