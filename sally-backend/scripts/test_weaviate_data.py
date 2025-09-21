# scripts/test_weaviate_data.py
import weaviate

def test_weaviate_data():
    print("🧪 Testing Weaviate data...")
    
    client = weaviate.connect_to_local(
        host="localhost",
        port=8080,
        skip_init_checks=True
    )
    
    # شمارش کل اشیاء
    collection = client.collections.get("KnowledgeBaseArticle")
    count = collection.aggregate.over_all(total_count=True)
    print(f"📊 Total objects in Weaviate: {count.total_count}")
    
    # تست جستجوی ساده
    response = collection.query.near_text(
        query="حساب کاربری",
        limit=3
    )
    
    print("\n🔍 Search results for 'حساب کاربری':")
    for i, obj in enumerate(response.objects):
        print(f"{i+1}. {obj.properties['title']}")
        print(f"   {obj.properties['content'][:100]}...")
        print()
    
    client.close()

if __name__ == "__main__":
    test_weaviate_data()