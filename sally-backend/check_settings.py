#!/usr/bin/env python3
"""
Check current AI model settings
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'sally-backend'))

from app.core.config import settings

print("🎯 تنظیمات فعلی مدل‌های هوش مصنوعی:")
print(f"📝 METADATA_MODEL: {settings.metadata_model_loaded}")
print(f"💬 CHAT_MODEL: {settings.chat_model_loaded}")
print(f"🔍 RAG_MODEL: {settings.rag_model_loaded}")
print(f"🔑 OPENAI_API_KEY: {'تنظیم شده ✅' if settings.openai_api_key_loaded else 'تنظیم نشده ❌'}")
print(f"🌐 OPENAI_BASE_URL: {settings.openai_base_url_loaded or 'پیش‌فرض OpenAI'}")
print()
print("📋 متغیرهای محیطی مورد انتظار در فایل .env:")
print("METADATA_MODEL=gpt-3.5-turbo")
print("CHAT_MODEL=gpt-3.5-turbo")
print("RAG_MODEL=gpt-3.5-turbo")
print("OPENAI_API_KEY=your-api-key")
print("# OPENAI_BASE_URL=https://api.openai.com/v1 (اختیاری)")
