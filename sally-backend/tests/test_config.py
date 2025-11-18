"""
🔍 تست کامل تنظیمات Config
این اسکریپت تمام تنظیمات پروژه رو چک می‌کنه
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.core.config import settings

def print_section(title: str):
    """Print a section header"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def check_value(name: str, value: any, is_secret: bool = False):
    """Print a config value"""
    if value is None:
        status = "❌ NOT SET"
        display_value = "None"
    elif value == "":
        status = "⚠️ EMPTY"
        display_value = '""'
    else:
        status = "✅ SET"
        if is_secret and isinstance(value, str):
            # Show only first 15 chars for secrets
            display_value = f"{value[:15]}..." if len(value) > 15 else value
        else:
            display_value = value
    
    print(f"  {name:35} {status:12} {display_value}")

def main():
    print("\n🔍 SallyBot Configuration Test")
    print(f"📁 Working Directory: {os.getcwd()}")
    print(f"📁 Project Root: {project_root}")
    
    # =================================================================
    # 1. Basic Settings
    # =================================================================
    print_section("1️⃣  Basic Settings")
    check_value("App Name", getattr(settings, 'app_name', 'SallyBot'))
    check_value("CORS Origins", f"{len(settings.cors_origins)} origins" if settings.cors_origins else "None")
    
    # =================================================================
    # 2. Database Settings
    # =================================================================
    print_section("2️⃣  Database Settings")
    check_value("MongoDB URI", settings.MONGODB_URL, is_secret=True)
    check_value("Weaviate URL", settings.weaviate_url)
    check_value("Weaviate API Key", settings.weaviate_api_key_loaded, is_secret=True)
    
    # =================================================================
    # 3. Security Settings
    # =================================================================
    print_section("3️⃣  Security Settings")
    check_value("JWT Secret Key", settings.jwt_secret_key, is_secret=True)
    check_value("JWT Token Expire (min)", settings.jwt_access_token_expire_minutes)
    check_value("JWT Algorithm", settings.jwt_algorithm)
    check_value("Default SuperAdmin Email", settings.default_SuperAdmin_email)
    
    # =================================================================
    # 4. OpenAI / LLM Settings
    # =================================================================
    print_section("4️⃣  OpenAI / LLM Settings")
    check_value("OpenAI API Key", settings.openai_api_key_loaded, is_secret=True)
    check_value("OpenAI Base URL", settings.openai_base_url_loaded)
    check_value("Metadata Model", settings.metadata_model_loaded)
    check_value("RAG Model", settings.rag_model_loaded)
    check_value("Chat Model", settings.chat_model_loaded)
    
    # =================================================================
    # 5. Embedder Settings (for Weaviate)
    # =================================================================
    print_section("5️⃣  Embedder Settings (Weaviate Vectorization)")
    check_value("Embedder API Key", settings.embedder_api_key_loaded, is_secret=True)
    check_value("Embedder Base URL", settings.embedder_openai_base_url_loaded)
    check_value("Embedder Model", settings.embedder_model_loaded)
    
    # =================================================================
    # 6. Ollama Settings (Local LLM)
    # =================================================================
    print_section("6️⃣  Ollama Settings (Local LLM)")
    check_value("Ollama URL", settings.ollama_url_loaded)
    check_value("Ollama Embedding Model", settings.ollama_embedding_model_loaded)
    
    # =================================================================
    # 7. Git / Docs-as-Code Settings
    # =================================================================
    print_section("7️⃣  Git / Docs-as-Code Settings")
    check_value("Git Repo URL", settings.kb_git_repo_url)
    check_value("Git Branch", settings.kb_git_branch)
    check_value("Git Local Path", settings.kb_git_local_path)
    check_value("Git Sync Interval (sec)", settings.kb_sync_interval)
    
    # =================================================================
    # 8. RAG Settings
    # =================================================================
    print_section("8️⃣  RAG Settings")
    check_value("Weaviate Retrieval Limit", settings.weaviate_retrieval_limit)
    check_value("Reranker Top K", settings.reranker_top_k)
    check_value("Context Documents Count", settings.context_documents_count)
    check_value("Reranker API URL", settings.reranker_api_url)
    check_value("Use Hybrid Model Strategy", settings.use_hybrid_model_strategy)
    if settings.use_hybrid_model_strategy:
        check_value("  └─ Fast Model", settings.agentic_fast_model)
        check_value("  └─ Power Model", settings.agentic_power_model)
    
    # =================================================================
    # Summary
    # =================================================================
    print_section("📊 Summary")
    
    # Count configured items
    configured_items = []
    missing_items = []
    
    items_to_check = [
        ("MongoDB", settings.MONGODB_URL),
        ("Weaviate", settings.weaviate_url),
        ("OpenAI API Key", settings.openai_api_key_loaded),
        ("Embedder API Key", settings.embedder_api_key_loaded),
        ("JWT Secret Key", settings.jwt_secret_key),
    ]
    
    for name, value in items_to_check:
        if value and value != "":
            configured_items.append(name)
        else:
            missing_items.append(name)
    
    print(f"\n  ✅ Configured: {len(configured_items)}/{len(items_to_check)}")
    if configured_items:
        for item in configured_items:
            print(f"     - {item}")
    
    if missing_items:
        print(f"\n  ❌ Missing: {len(missing_items)}")
        for item in missing_items:
            print(f"     - {item}")
    
    # =================================================================
    # Recommendations
    # =================================================================
    print_section("💡 Recommendations")
    
    recommendations = []
    
    if not settings.embedder_api_key_loaded:
        recommendations.append("⚠️  Embedder_API_KEY is not set - Weaviate vectorization will fail")
    
    if not settings.openai_api_key_loaded:
        recommendations.append("⚠️  OPENAI_API_KEY is not set - Chat will not work")
    
    if not settings.weaviate_api_key_loaded:
        recommendations.append("ℹ️  WEAVIATE_API_KEY is not set (optional for local Weaviate)")
    
    if settings.embedder_model_loaded != "text-embedding-3-small" and settings.embedder_model_loaded != "text-embedding-3-large":
        recommendations.append(f"⚠️  Embedder model '{settings.embedder_model_loaded}' - Make sure it's compatible with your setup")
    
    if recommendations:
        for rec in recommendations:
            print(f"\n  {rec}")
    else:
        print("\n  ✅ All critical settings are configured!")
    
    print("\n" + "="*60)
    print()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

