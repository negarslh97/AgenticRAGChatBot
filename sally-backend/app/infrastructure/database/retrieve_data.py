from app.infrastructure.database.weaviate_connector import WeaviateMongoDBConnector

connector = WeaviateMongoDBConnector()
connector.connect_weaviate()

# دریافت همه داده‌ها
all_data = connector.retrieve_weaviate_data("MarkdownNode")

# دریافت داده‌های خاص یک مقاله
article_data = connector.retrieve_weaviate_data(
    "MarkdownNode", 
    properties=["title", "content", "path"],
    limit=50
)

print(f"کل داده‌ها: {len(all_data)}")
# خروجی: کل داده‌ها: 104
