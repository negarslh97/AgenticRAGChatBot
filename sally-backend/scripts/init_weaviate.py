# scripts/init_weaviate.py
import weaviate
import os
from weaviate import WeaviateClient
from weaviate.connect import ConnectionParams
from weaviate.classes.init import AdditionalConfig, Timeout

def initialize_weaviate_v4():
    print("🔗 Connecting to Weaviate...")
    
    # اتصال از طریق HTTP REST API با غیرفعال کردن چک اولیه
    client = weaviate.WeaviateClient(
        connection_params=ConnectionParams.from_params(
            http_host="localhost",
            http_port=8080,
            http_secure=False,
            grpc_host="localhost",
            grpc_port=50051,
            grpc_secure=False,
        ),
        skip_init_checks=True,  # غیرفعال کردن چک اولیه gRPC
        additional_headers={
            "X-OpenAI-Api-Key": os.getenv("OPENAI_API_KEY", "")
        },
        additional_config=AdditionalConfig(
            timeout=Timeout(init=10, query=30)
        )
    )
    
    try:
        client.connect()
        print("✅ Connected to Weaviate successfully!")
        
        # حذف کلاس اگر وجود دارد
        try:
            client.collections.delete("KnowledgeBaseArticle")
            print("✅ Existing class deleted")
        except:
            print("ℹ️ No existing class to delete")
        
        # اسکیمای مقالات دانش‌پایه
        article_schema = {
            "class": "KnowledgeBaseArticle",
            "description": "Articles in the knowledge base",
            "vectorizer": "text2vec-openai",
            "moduleConfig": {
                "text2vec-openai": {
                    "model": "text-embedding-3-small",
                    "type": "text",
                    "vectorizeClassName": False
                }
            },
            "properties": [
                {
                    "name": "title",
                    "dataType": ["text"],
                    "description": "Title of the article"
                },
                {
                    "name": "content", 
                    "dataType": ["text"],
                    "description": "Content of the article"
                },
                {
                    "name": "summary",
                    "dataType": ["text"],
                    "description": "Summary of the article"
                },
                {
                    "name": "status",
                    "dataType": ["text"],
                    "description": "Status of the article"
                },
                {
                    "name": "visibility",
                    "dataType": ["text"],
                    "description": "Visibility of the article"
                },
                {
                    "name": "category",
                    "dataType": ["text"],
                    "description": "Category of the article"
                },
                {
                    "name": "tags",
                    "dataType": ["text[]"],
                    "description": "Tags for the article"
                },
                {
                    "name": "mongoId",
                    "dataType": ["text"],
                    "description": "Original MongoDB ID"
                }
            ]
        }
        
        # ایجاد کلاس جدید
        client.collections.create_from_dict(article_schema)
        print("✅ KnowledgeBaseArticle schema created successfully!")
        
        # تأیید ایجاد schema
        collections = client.collections.list_all()
        print("📋 Available collections:", collections)
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        client.close()

if __name__ == "__main__":
    success = initialize_weaviate_v4()
    if success:
        print("🎉 Weaviate initialization completed successfully!")
    else:
        print("💥 Weaviate initialization failed!")