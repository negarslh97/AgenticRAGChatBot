#!/usr/bin/env python3
"""
🧪 تست مدل‌های مختلف با RAG Context واقعی

این اسکریپت مدل‌ها رو با یک context طولانی شبیه RAG تست می‌کنه
تا ببینیم کدوم مدل‌ها برای RAG مناسب هستن.

استفاده:
    cd sally-backend
    python scripts/test_rag_models.py

یا برای تست یک مدل خاص:
    python scripts/test_rag_models.py gpt-4o-mini
"""

import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

# 🔑 بارگذاری متغیرهای محیطی
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
    print(f"✅ Loaded .env from: {env_path}\n")
else:
    load_dotenv()

# 📝 Context طولانی شبیه RAG واقعی (2000+ characters)
SAMPLE_RAG_CONTEXT = """
Document: شرکت صدگان سامانه هوشمند
Content: # شرکت صدگان سامانه هوشمند

شرکت صدگان سامانه هوشمند (سهامی خاص) در اردیبهشت ۹۴ ثبت شده است. این شرکت به صورت تخصصی در زمینه ی تولید و عرضه ی نرم افزارهای یکپارچه مالی و کسب و کار برای انواع شرکت‌ها فعالیت می‌کند. صدگان با **شعار تفاوت در جزئیات است**، متعهد است با دقت در جزئیات تولید محصول، به حسابداران کشورمان محصولی متمایز ارائه کند.

## اطلاعات تماس

**دفتر مرکزی:** تهران، خیابان ملاصدرا، خیابان شیخ بهایی، خیابان برزیل غربی، پلاک ۱۴۰، طبقه دوم، واحد ۷

**تلفن:** ۰۲۱-۸۸۷۴۴۲۲۲

**ایمیل:** info@sadegan.com

**وب‌سایت:** https://sadegan.com

## محصولات

شرکت صدگان دارای چندین محصول نرم‌افزاری است:

### ۱. نرم افزار حسابداری

سیستم یکپارچه حسابداری با امکانات کامل برای مدیریت مالی شرکت‌ها.

### ۲. نرم افزار مدیریت فروش

سیستم مدیریت فروش و فاکتور با قابلیت‌های پیشرفته.

### ۳. نرم افزار انبارداری

سیستم مدیریت انبار و کنترل موجودی.

## تاریخچه

شرکت صدگان از سال ۱۳۹۴ فعالیت خود را آغاز کرد و تا کنون توانسته محصولات متنوعی را به بازار ارائه دهد.
"""


async def test_model_with_rag(
    model_id: str, 
    verbose: bool = True,
    context: str = SAMPLE_RAG_CONTEXT,
    query: str = "شرکت صدگان چه محصولاتی دارد؟"
):
    """
    تست یک مدل با RAG context
    
    Args:
        model_id: شناسه مدل
        verbose: نمایش جزئیات
        context: Context طولانی (شبیه RAG)
        query: سوال کاربر
        
    Returns:
        Dict با اطلاعات تست
    """
    if verbose:
        print(f"\n{'='*70}")
        print(f"🧪 Testing model: {model_id}")
        print(f"{'='*70}")
    
    try:
        # 🔍 تشخیص provider
        model_lower = model_id.lower()
        
        if model_lower.startswith("gpt-"):
            api_key = os.getenv("Embedder_API_KEY") or os.getenv("OPENAI_API_KEY")
            base_url = os.getenv("Embedder_OPENAI_BASE_URL") or "https://api.openai.com/v1"
            provider = "OpenAI (Official)"
        elif model_lower.startswith("ollama:"):
            api_key = "ollama"
            base_url = os.getenv("OLLAMA_URL") or "http://localhost:11434"
            provider = "Ollama (Local)"
        else:
            api_key = os.getenv("OPENAI_API_KEY")
            base_url = os.getenv("OPENAI_BASE_URL") or "https://openrouter.ai/api/v1"
            provider = "OpenRouter"
        
        if not api_key:
            if verbose:
                print(f"❌ API Key not found!")
            return {"success": False, "error": "No API Key"}
        
        if verbose:
            print(f"🔑 Provider: {provider}")
            print(f"🔗 API URL: {base_url}")
            print(f"📏 Context length: {len(context)} chars")
            print(f"❓ Query: {query}")
            print(f"🌊 Starting RAG test...")
        
        # ساخت مدل
        llm = ChatOpenAI(
            model_name=model_id,
            openai_api_key=api_key,
            base_url=base_url,
            temperature=0.7,
            streaming=True
        )
        
        # Template شبیه RAG واقعی
        prompt = ChatPromptTemplate.from_template("""شما یک دستیار هوشمند هستید.

**دستورالعمل‌های پاسخ‌دهی:**

1. از اطلاعات موجود در Context زیر برای پاسخ استفاده کنید
2. اگر پاسخ در Context وجود دارد، پاسخ کامل و واضح بدهید
3. پاسخ را به زبان فارسی بنویسید

**Context:**
{context}

**سوال کاربر:** {query}

**پاسخ شما:**""")
        
        chain = prompt | llm
        
        # تست streaming
        chunk_count = 0
        empty_count = 0
        content_parts = []
        first_content_found = False
        
        import time
        start_time = time.time()
        
        async for chunk in chain.astream({"context": context, "query": query}):
            chunk_count += 1
            
            if hasattr(chunk, 'content'):
                content = chunk.content
            else:
                content = str(chunk)
            
            if not first_content_found:
                if not content or len(content.strip()) == 0:
                    empty_count += 1
                    continue
                else:
                    first_content_found = True
                    if verbose and empty_count > 0:
                        print(f"  ⏭️  Skipped {empty_count} empty chunks")
            
            content_parts.append(content)
        
        end_time = time.time()
        elapsed = end_time - start_time
        
        full_response = "".join(content_parts)
        content_chunks = chunk_count - empty_count
        
        # تحلیل نتیجه
        success = len(full_response) > 10  # حداقل 10 کاراکتر محتوا
        
        if verbose:
            print(f"\n{'='*70}")
            print(f"📊 Results:")
            print(f"  Total chunks: {chunk_count}")
            print(f"  Empty chunks: {empty_count} ({empty_count/chunk_count*100:.1f}%)")
            print(f"  Content chunks: {content_chunks}")
            print(f"  Response length: {len(full_response)} chars")
            print(f"  Time elapsed: {elapsed:.2f}s")
            print(f"  Speed: {len(full_response)/elapsed:.0f} chars/s")
            
            if len(full_response) > 0:
                print(f"\n💬 Response Preview:")
                preview = full_response[:150].replace('\n', ' ')
                print(f"  {preview}{'...' if len(full_response) > 150 else ''}")
            
            print(f"{'='*70}")
            
            if success:
                print(f"✅ Model works with RAG!")
            else:
                print(f"❌ Model failed! No meaningful content.")
        
        return {
            "success": success,
            "model_id": model_id,
            "provider": provider,
            "total_chunks": chunk_count,
            "empty_chunks": empty_count,
            "content_chunks": content_chunks,
            "response_length": len(full_response),
            "time_elapsed": elapsed,
            "chars_per_second": len(full_response)/elapsed if elapsed > 0 else 0
        }
            
    except Exception as e:
        if verbose:
            print(f"❌ Error: {e}")
        return {"success": False, "error": str(e)}


async def main():
    """تست چند مدل مختلف با RAG"""
    
    # اگر مدل خاصی داده شده
    if len(sys.argv) > 1:
        model_id = sys.argv[1]
        result = await test_model_with_rag(model_id, verbose=True)
        sys.exit(0 if result["success"] else 1)
    
    # لیست مدل‌ها برای تست
    models_to_test = [
        # OpenAI رسمی
        "gpt-4o-mini",
        
        # OpenRouter رایگان
        "google/gemini-2.5-flash",
        "google/gemini-2.0-flash-exp:free",
        "deepseek/deepseek-chat-v3.1:free",
        
        # OpenRouter پولی
        "x-ai/grok-4-fast",
        "x-ai/grok-3-mini-beta",
        
        # مدل‌های مشکل‌دار
        "z-ai/glm-4.6",
    ]
    
    results = []
    
    print("🚀 Starting RAG model tests...")
    print(f"   Testing {len(models_to_test)} models with RAG context")
    print(f"   Context length: {len(SAMPLE_RAG_CONTEXT)} chars")
    print()
    
    for model_id in models_to_test:
        result = await test_model_with_rag(model_id, verbose=True)
        results.append(result)
        await asyncio.sleep(1)
    
    # خلاصه نتایج
    print(f"\n\n{'='*70}")
    print(f"📋 SUMMARY - RAG COMPATIBLE MODELS:")
    print(f"{'='*70}")
    
    # دسته‌بندی
    working = [r for r in results if r.get("success")]
    failed = [r for r in results if not r.get("success")]
    
    print(f"\n✅ Working Models ({len(working)}/{len(results)}):")
    print(f"{'='*70}")
    for r in working:
        speed = f"{r['chars_per_second']:.0f} ch/s" if r.get('chars_per_second') else "N/A"
        empty_pct = f"{r['empty_chunks']/r['total_chunks']*100:.0f}%" if r.get('total_chunks') else "N/A"
        print(f"  ✅ {r['model_id']}")
        print(f"     Provider: {r.get('provider', 'N/A')}")
        print(f"     Chunks: {r.get('content_chunks', 0)} content / {r.get('empty_chunks', 0)} empty ({empty_pct})")
        print(f"     Speed: {speed}")
        print(f"     Response: {r.get('response_length', 0)} chars in {r.get('time_elapsed', 0):.1f}s")
        print()
    
    if failed:
        print(f"\n❌ Failed Models ({len(failed)}/{len(results)}):")
        print(f"{'='*70}")
        for r in failed:
            model_id = r.get('model_id', 'Unknown')
            error = r.get('error', 'No content received')
            print(f"  ❌ {model_id}")
            print(f"     Error: {error[:100]}{'...' if len(str(error)) > 100 else ''}")
            print()
    
    print(f"{'='*70}\n")
    
    # توصیه‌ها
    print("💡 Recommendations:")
    print("   ⭐⭐⭐ Best for RAG (tested and verified):")
    for r in working[:3]:  # 3 مدل برتر
        print(f"      - {r['model_id']}")
    print()


if __name__ == "__main__":
    asyncio.run(main())
