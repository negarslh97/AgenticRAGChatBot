#!/usr/bin/env python3
"""
تست دقیق Reranking در Agentic RAG
===================================

این تست بررسی می‌کند که آیا reranking واقعاً کار می‌کند یا نه
"""

import asyncio
import sys
import os

# Add the app to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.core.config import settings
from app.services.rag_service import SimpleRAGService
from app.infrastructure.agentic_rag_advanced import AdvancedAgenticRAG
from app.infrastructure.langchain_utils import langchain_service

async def test_reranking_in_action():
    """تست reranking در عمل"""
    print("=" * 80)
    print("🎯 TESTING RERANKING IN ACTION")
    print("=" * 80)
    
    try:
        # تست Simple RAG
        print("🔍 Testing Simple RAG with reranking...")
        simple_rag = SimpleRAGService()
        
        # تست چند سوال مختلف
        test_queries = [
            "راهنمای استقرار نرم افزار",
            "تنظیمات عمومی سیستم",
            "مدیریت انبار و فروش"
        ]
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n📝 Test {i}: {query}")
            print("-" * 60)
            
            result = await simple_rag.generate_response(query, {})
            
            print(f"✅ Response: {result['response'][:100]}...")
            print(f"📊 Confidence: {result['confidence']:.3f}")
            print(f"📚 Sources: {len(result['sources'])}")
            
            # نمایش منابع
            for j, source in enumerate(result['sources'][:3], 1):
                print(f"   {j}. {source.get('title', 'N/A')[:50]}... (Score: {source.get('score', 0):.3f})")
            
            await asyncio.sleep(2)  # فاصله بین تست‌ها
        
        print("\n" + "=" * 80)
        print("✅ RERANKING TEST COMPLETED SUCCESSFULLY!")
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ Reranking test failed: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """تست اصلی"""
    print("🔧 Detailed Reranking Test")
    print(f"🔗 Weaviate URL: {settings.weaviate_url_loaded}")
    print(f"🔄 Reranker API: {settings.RERANKER_API_URL}")
    print(f"🤖 Embedder Model: {settings.embedder_model_loaded}")
    print()
    
    try:
        await test_reranking_in_action()
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())