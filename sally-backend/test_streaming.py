#!/usr/bin/env python3
"""
تست ساده برای بررسی streaming واقعی
"""
import asyncio
from app.infrastructure.langchain_utils import langchain_service
from app.core.config import settings

async def test_streaming():
    """تست streaming با یک سوال ساده"""
    print("=" * 60)
    print("🧪 Test Streaming")
    print(f"📊 Model: {settings.rag_model_loaded}")
    print(f"🌐 Base URL: {settings.openai_base_url_loaded}")
    print("=" * 60)
    
    query = "سلام چطوری؟"
    context = "این یک تست ساده است."
    
    print(f"\n📝 Query: {query}")
    print(f"📋 Context: {context}\n")
    print("🎬 Starting stream...\n")
    
    chunk_count = 0
    async for chunk in langchain_service.generate_rag_response_stream(query, context):
        chunk_count += 1
        print(f"Chunk #{chunk_count}: '{chunk}' ({len(chunk)} chars)")
        # نمایش در همان خط
        print(chunk, end='', flush=True)
    
    print(f"\n\n✅ Stream completed: {chunk_count} chunks")

if __name__ == "__main__":
    asyncio.run(test_streaming())

