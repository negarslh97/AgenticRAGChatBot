"""
اسکریپت بررسی embedding model در Weaviate

این اسکریپت مشخص می‌کند:
- چه embedding model در Weaviate استفاده شده (1536 یا 3072 dimension)
- چه embedding model در .env تنظیم شده
- آیا سازگار هستند؟

نحوه استفاده:
    python scripts/check_embedding_model.py
"""

import weaviate
from weaviate.classes.init import Auth
import os
from dotenv import load_dotenv

load_dotenv()


def check_embedding_model():
    """بررسی embedding model"""
    
    weaviate_url = os.getenv("WEAVIATE_URL")
    weaviate_api_key = os.getenv("WEAVIATE_API_KEY")
    embedder_model = os.getenv("EMBEDDER_MODEL")
    
    print("="*80)
    print("🔍 Checking Embedding Model Configuration")
    print("="*80)
    
    print(f"\n📋 Configuration (.env):")
    print(f"   Weaviate URL: {weaviate_url}")
    print(f"   EMBEDDER_MODEL: {embedder_model}")
    
    # تشخیص dimension از نام مدل
    expected_dimension = None
    if "3-small" in embedder_model or "ada-002" in embedder_model:
        expected_dimension = 1536
    elif "3-large" in embedder_model:
        expected_dimension = 3072
    
    if expected_dimension:
        print(f"   Expected Dimension: {expected_dimension}")
    
    # اتصال به Weaviate (v4 API)
    print(f"\n🔗 Connecting to Weaviate...")
    
    client = None
    try:
        # Parse URL to extract host and port
        from urllib.parse import urlparse
        parsed = urlparse(weaviate_url)
        host = parsed.hostname or "localhost"
        port = parsed.port or 8080
        
        # Weaviate v4 client
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
        
        if not client.is_ready():
            print("❌ Cannot connect to Weaviate!")
            return
        
        print("✅ Connected to Weaviate")
        
        # بررسی collections (v4 API)
        collections = client.collections.list_all()
        
        if "MarkdownNode" not in collections:
            print("\n⚠️  Collection 'MarkdownNode' not found in Weaviate")
            print("   یعنی هنوز هیچ document ایندکس نشده است")
            print("\n✅ می‌توانید با هر embedding model که می‌خواهید شروع کنید!")
            return
        
        print(f"\n📊 Weaviate Collection Info:")
        print(f"   Collection: MarkdownNode")
        
        # دریافت collection config
        collection = client.collections.get("MarkdownNode")
        config = collection.config.get()
        
        # تلاش برای پیدا کردن dimension
        actual_dimension = None
        
        # روش: Query یک object و بررسی طول vector
        try:
            response = collection.query.fetch_objects(
                limit=1,
                include_vector=True
            )
            
            if response.objects and len(response.objects) > 0:
                obj = response.objects[0]
                if obj.vector is not None:
                    if isinstance(obj.vector, dict):
                        # multi-vector
                        for key, vec in obj.vector.items():
                            if vec:
                                actual_dimension = len(vec)
                                break
                    elif isinstance(obj.vector, list):
                        # single vector
                        actual_dimension = len(obj.vector)
        except Exception as e:
            print(f"   ⚠️  Could not retrieve vector: {e}")
        
        if actual_dimension:
            print(f"   Vector Dimension: {actual_dimension}")
            
            # تشخیص مدل از dimension
            if actual_dimension == 1536:
                detected_model = "text-embedding-3-small یا text-embedding-ada-002"
            elif actual_dimension == 3072:
                detected_model = "text-embedding-3-large"
            else:
                detected_model = "Unknown"
            
            print(f"   Detected Model: {detected_model}")
            
            # بررسی سازگاری
            print(f"\n🎯 Compatibility Check:")
            
            if expected_dimension and expected_dimension == actual_dimension:
                print(f"   ✅ COMPATIBLE!")
                print(f"   .env config ({embedder_model}) matches Weaviate embeddings ({actual_dimension}D)")
            elif expected_dimension:
                print(f"   ❌ INCOMPATIBLE!")
                print(f"   .env: {embedder_model} ({expected_dimension}D)")
                print(f"   Weaviate: {actual_dimension}D")
                print(f"\n⚠️  این باعث خطا می‌شود:")
                print(f"   'vector lengths don't match: {expected_dimension} vs {actual_dimension}'")
                print(f"\n🔧 راه حل‌ها:")
                print(f"   1️⃣  تغییر .env به مدل مناسب:")
                if actual_dimension == 1536:
                    print(f"      EMBEDDER_MODEL=text-embedding-3-small")
                elif actual_dimension == 3072:
                    print(f"      EMBEDDER_MODEL=text-embedding-3-large")
                print(f"\n   2️⃣  یا حذف embeddings و re-index:")
                print(f"      python scripts/reset_weaviate_embeddings.py")
            else:
                print(f"   ⚠️  Cannot determine expected dimension from model name")
        else:
            print(f"   ⚠️  Could not determine vector dimension")
        
        # تعداد objects (v4 API)
        try:
            agg_result = collection.aggregate.over_all(total_count=True)
            count = agg_result.total_count if agg_result else 0
            print(f"\n📈 Statistics:")
            print(f"   Total Documents: {count:,}")
        except Exception as e:
            print(f"   ⚠️  Could not get count: {e}")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Close connection (v4 API)
        if client:
            client.close()
            print("\n🔌 Connection closed")


if __name__ == "__main__":
    check_embedding_model()

