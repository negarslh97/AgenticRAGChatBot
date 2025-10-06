"""
اسکریپت حذف تمام embeddings از Weaviate

⚠️ هشدار: این اسکریپت تمام vector embeddings را حذف می‌کند!
بعد از اجرا باید تمام documents را دوباره آپلود کنید.

نحوه استفاده:
    python scripts/reset_weaviate_embeddings.py
"""

import weaviate
from weaviate.classes.init import Auth
import os
from dotenv import load_dotenv

load_dotenv()

def reset_weaviate():
    """حذف collection و تمام embeddings"""
    
    weaviate_url = os.getenv("WEAVIATE_URL", "http://localhost:8080")
    weaviate_api_key = os.getenv("WEAVIATE_API_KEY")
    
    print(f"🔗 Connecting to Weaviate: {weaviate_url}")
    
    client = None
    try:
        # Parse URL to extract host and port
        from urllib.parse import urlparse
        parsed = urlparse(weaviate_url)
        host = parsed.hostname or "localhost"
        port = parsed.port or 8080
        
        # اتصال به Weaviate (v4 API)
        if weaviate_api_key:
            client = weaviate.connect_to_custom(
                http_host=host,
                http_port=port,
                http_secure=False,
                auth_credentials=Auth.api_key(weaviate_api_key)
            )
        else:
            client = weaviate.connect_to_local(
                host=host,
                port=port
            )
        
        # بررسی اتصال
        if not client.is_ready():
            print("❌ Cannot connect to Weaviate!")
            return
        
        print("✅ Connected to Weaviate")
        
        # حذف collection MarkdownNode
        collection_name = "MarkdownNode"
        
        # بررسی وجود collection
        collections = client.collections.list_all()
        
        if collection_name in collections:
            print(f"\n⚠️  Found collection '{collection_name}'")
            print("⚠️  این عملیات تمام vector embeddings را حذف می‌کند!")
            
            confirm = input("❓ آیا مطمئن هستید؟ (yes/no): ")
            
            if confirm.lower() in ['yes', 'y']:
                print(f"🗑️  Deleting collection '{collection_name}'...")
                client.collections.delete(collection_name)
                print(f"✅ Collection '{collection_name}' deleted successfully!")
                print("\n📝 حالا می‌توانید:")
                print("   1. در .env مدل جدید را تنظیم کنید:")
                print("      EMBEDDER_MODEL=text-embedding-3-small")
                print("   2. سرور را restart کنید")
                print("   3. تمام documents را دوباره آپلود کنید")
            else:
                print("❌ عملیات لغو شد")
        else:
            print(f"ℹ️  Collection '{collection_name}' not found - nothing to delete")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if client:
            client.close()
            print("\n🔌 Connection closed")


if __name__ == "__main__":
    reset_weaviate()

