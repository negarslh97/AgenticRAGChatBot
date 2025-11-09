#!/usr/bin/env python3
"""
تست بررسی رفع مشکل Reranking در Agentic RAG
===============================================

این تست بررسی می‌کند که آیا Agentic RAG حالا از reranking استفاده می‌کند یا نه
"""

import asyncio
import sys
import os

# Add the app to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.core.config import settings
from app.services.rag_service import SimpleRAGService, AgenticRAGService
from app.infrastructure.langchain_utils import langchain_service

async def test_simple_rag():
    """تست RAG ساده"""
    print("=" * 60)
    print("🔍 Testing Simple RAG...")
    print("=" * 60)
    
    try:
        simple_rag = SimpleRAGService()
        result = await simple_rag.generate_response("راهنمای استفاده از سیستم", {})
        
        print(f"✅ Simple RAG Response: {result['response'][:100]}...")
        print(f"📊 Confidence: {result['confidence']}")
        print(f"📚 Sources count: {len(result['sources'])}")
        print(f"🔧 Has reranking: {hasattr(simple_rag, '_rerank_documents')}")
        
        return result
        
    except Exception as e:
        print(f"❌ Simple RAG failed: {e}")
        return None

async def test_agentic_rag():
    """تست Agentic RAG"""
    print("=" * 60)
    print("🚀 Testing Agentic RAG...")
    print("=" * 60)
    
    try:
        agentic_rag = AgenticRAGService()
        result = await agentic_rag.generate_response("راهنمای استفاده از سیستم", {})
        
        print(f"✅ Agentic RAG Response: {result['response'][:100]}...")
        print(f"📊 Confidence: {result['confidence']}")
        print(f"📚 Sources count: {len(result['sources'])}")
        print(f"🔧 Has reranking: {hasattr(agentic_rag, '_rerank_documents')}")
        
        # بررسی workflow
        if 'confidence_analysis' in result:
            print(f"🔄 Actions: {result['confidence_analysis'].get('actions_taken', [])}")
        
        return result
        
    except Exception as e:
        print(f"❌ Agentic RAG failed: {e}")
        return None

async def compare_results():
    """مقایسه نتایج"""
    print("=" * 80)
    print("🔬 COMPARISON: Simple RAG vs Agentic RAG")
    print("=" * 80)
    
    # تست RAG ساده
    simple_result = await test_simple_rag()
    await asyncio.sleep(2)  # کمی فاصله
    
    # تست Agentic RAG
    agentic_result = await test_agentic_rag()
    
    # مقایسه
    print("=" * 80)
    print("📊 COMPARISON RESULTS:")
    print("=" * 80)
    
    if simple_result and agentic_result:
        print(f"🎯 Simple RAG confidence: {simple_result['confidence']}")
        print(f"🎯 Agentic RAG confidence: {agentic_result['confidence']}")
        print(f"📚 Simple RAG sources: {len(simple_result['sources'])}")
        print(f"📚 Agentic RAG sources: {len(agentic_result['sources'])}")
        
        # بررسی کیفیت پاسخ
        if simple_result['confidence'] > agentic_result['confidence']:
            print("🏆 Simple RAG has better confidence!")
        elif agentic_result['confidence'] > simple_result['confidence']:
            print("🏆 Agentic RAG has better confidence!")
        else:
            print("🤝 Similar confidence levels")
            
        # بررسی تعداد منابع
        if len(agentic_result['sources']) > len(simple_result['sources']):
            print("📚 Agentic RAG found more sources!")
        elif len(simple_result['sources']) > len(agentic_result['sources']):
            print("📚 Simple RAG found more sources!")
        else:
            print("🤝 Similar number of sources")
    else:
        print("❌ Could not compare - one of the services failed")

async def main():
    """تست اصلی"""
    print("🔧 Weaviate Reranking Fix Test")
    print(f"🔗 Weaviate URL: {settings.weaviate_url_loaded}")
    print(f"🔑 Weaviate API Key: {'Set' if settings.weaviate_api_key_loaded else 'Not set'}")
    print(f"🔄 Reranker API: {settings.RERANKER_API_URL}")
    print(f"🤖 Embedder Model: {settings.embedder_model_loaded}")
    print()
    
    try:
        await compare_results()
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())