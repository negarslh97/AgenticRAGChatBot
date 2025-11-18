#!/usr/bin/env python3
"""
Test script to debug model registration issues
"""

import sys
import os
sys.path.append('.')

def main():
    print("🔍 Testing model registration...")
    
    try:
        from app.infrastructure.model_factory import model_factory
        from app.core.config import settings
        
        print("\n📋 Environment Models:")
        print(f"  RAG_MODEL: {settings.rag_model_loaded}")
        print(f"  CHAT_MODEL: {settings.chat_model_loaded}")
        print(f"  METADATA_MODEL: {settings.metadata_model_loaded}")
        print(f"  INTENT_MODEL: {settings.intent_model_loaded}")
        print(f"  OPENAI_API_KEY: {settings.openai_api_key_loaded[:20]}..." if settings.openai_api_key_loaded else "  OPENAI_API_KEY: None")
        print(f"  OPENAI_BASE_URL: {settings.openai_base_url_loaded}")
        
        print("\n✅ Registered Models:")
        models = model_factory.list_models()
        if not models:
            print("  ❌ No models registered!")
        else:
            for model in models:
                print(f"  - {model['name']} ({model['provider']}) - Type: {model['type']}")
        
        print("\n🧪 Testing model selection...")
        try:
            # Test getting optimal models
            chat_model = model_factory.get_optimal_model("chat")
            print(f"  ✅ Optimal chat model: {chat_model}")
            
            rag_model = model_factory.get_optimal_model("rag") 
            print(f"  ✅ Optimal RAG model: {rag_model}")
            
        except Exception as e:
            print(f"  ❌ Model selection failed: {e}")
        
        print("\n🔍 Testing specific model access...")
        try:
            # Try to get a specific model
            test_model = model_factory.get_model("google/gemini-2.5-flash-lite")
            print(f"  ✅ Successfully retrieved: google/gemini-2.5-flash-lite")
        except Exception as e:
            print(f"  ❌ Failed to get google/gemini-2.5-flash-lite: {e}")
            
        try:
            # Try to get the minimax model (this should fail)
            test_model = model_factory.get_model("minimax/minimax-m2:free")
            print(f"  ❌ Unexpectedly found: minimax/minimax-m2:free")
        except Exception as e:
            print(f"  ✅ Expected failure for minimax/minimax-m2:free: {e}")
            
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()