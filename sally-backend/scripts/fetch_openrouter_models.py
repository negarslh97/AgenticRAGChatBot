#!/usr/bin/env python3
"""
اسکریپت برای بازیابی لیست کامل مدل‌های موجود در OpenRouter

استفاده:
    python scripts/fetch_openrouter_models.py

خروجی:
    لیست کامل مدل‌های OpenRouter با جزئیات
"""

import requests
import json
from typing import List, Dict

def fetch_openrouter_models() -> List[Dict]:
    """
    بازیابی لیست مدل‌های OpenRouter از API
    
    Returns:
        لیست دیکشنری‌های حاوی اطلاعات مدل‌ها
    """
    url = "https://openrouter.ai/api/v1/models"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        models = data.get("data", [])
        
        return models
    
    except Exception as e:
        print(f"❌ خطا در دریافت مدل‌ها: {e}")
        return []


def filter_popular_models(models: List[Dict]) -> List[Dict]:
    """
    فیلتر کردن مدل‌های محبوب و پرکاربرد
    
    Args:
        models: لیست همه مدل‌ها
        
    Returns:
        لیست مدل‌های محبوب
    """
    keywords = [
        "grok", "gemini", "claude", "llama", "mistral", 
        "deepseek", "qwen", "o1", "gpt", "phi"
    ]
    
    popular = []
    for model in models:
        model_id = model.get("id", "").lower()
        model_name = model.get("name", "").lower()
        
        if any(keyword in model_id or keyword in model_name for keyword in keywords):
            popular.append({
                "id": model.get("id"),
                "name": model.get("name"),
                "description": model.get("description", "")[:100] + "..." if len(model.get("description", "")) > 100 else model.get("description", ""),
                "context_length": model.get("context_length"),
                "pricing": model.get("pricing", {})
            })
    
    return popular


def print_models_for_frontend(models: List[Dict]):
    """
    چاپ مدل‌ها به فرمت مناسب برای استفاده در Frontend
    
    Args:
        models: لیست مدل‌ها
    """
    print("\n" + "="*80)
    print("📋 مدل‌های محبوب OpenRouter برای استفاده در Frontend:")
    print("="*80 + "\n")
    
    # دسته‌بندی مدل‌ها
    categories = {
        "Google (Gemini)": [],
        "xAI (Grok)": [],
        "Anthropic (Claude)": [],
        "Meta (Llama)": [],
        "Mistral": [],
        "DeepSeek": [],
        "Qwen": [],
        "OpenAI": [],
        "Other": []
    }
    
    for model in models:
        model_id = model["id"]
        model_name = model["name"]
        
        if "google" in model_id or "gemini" in model_id:
            categories["Google (Gemini)"].append(model)
        elif "x-ai" in model_id or "grok" in model_id:
            categories["xAI (Grok)"].append(model)
        elif "anthropic" in model_id or "claude" in model_id:
            categories["Anthropic (Claude)"].append(model)
        elif "llama" in model_id:
            categories["Meta (Llama)"].append(model)
        elif "mistral" in model_id:
            categories["Mistral"].append(model)
        elif "deepseek" in model_id:
            categories["DeepSeek"].append(model)
        elif "qwen" in model_id:
            categories["Qwen"].append(model)
        elif "openai" in model_id:
            categories["OpenAI"].append(model)
        else:
            categories["Other"].append(model)
    
    # چاپ به فرمت TypeScript
    for category, models_list in categories.items():
        if not models_list:
            continue
            
        print(f"  // {category}")
        for model in models_list[:5]:  # فقط 5 مدل اول هر دسته
            desc = model["description"][:50] + "..." if len(model["description"]) > 50 else model["description"]
            desc_fa = desc  # می‌تونی ترجمه فارسی بذاری
            
            print(f"  {{ id: '{model['id']}', name: '{model['name']}', provider: 'OpenRouter', description: '{desc_fa}' }},")
        print()


def main():
    print("🔄 در حال دریافت لیست مدل‌های OpenRouter...\n")
    
    # دریافت همه مدل‌ها
    all_models = fetch_openrouter_models()
    
    if not all_models:
        print("❌ هیچ مدلی دریافت نشد!")
        return
    
    print(f"✅ تعداد کل مدل‌ها: {len(all_models)}\n")
    
    # فیلتر مدل‌های محبوب
    popular = filter_popular_models(all_models)
    print(f"✅ تعداد مدل‌های محبوب: {len(popular)}\n")
    
    # چاپ برای Frontend
    print_models_for_frontend(popular)
    
    # ذخیره در فایل JSON
    output_file = "sally-backend/scripts/openrouter_models.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(popular, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ لیست کامل در فایل ذخیره شد: {output_file}")
    
    # نمایش چند مدل نمونه
    print("\n" + "="*80)
    print("📊 نمونه مدل‌های محبوب:")
    print("="*80 + "\n")
    
    for model in popular[:10]:
        print(f"🤖 {model['name']}")
        print(f"   ID: {model['id']}")
        print(f"   توضیحات: {model['description']}")
        print(f"   Context: {model['context_length']:,} tokens" if model.get('context_length') else "")
        print()


if __name__ == "__main__":
    main()
