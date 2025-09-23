import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

async def check_db():
    database_url_parts = settings.database_url.rstrip('/').split('/')
    database_name = database_url_parts[-1] if len(database_url_parts) > 1 else 'SallyChatBot'

    client = AsyncIOMotorClient(settings.database_url)
    db = client[database_name]
    collection = db['knowledge_base_articles']

    articles = await collection.find({}).to_list(length=None)
    print(f'Total articles in DB: {len(articles)}')

    for i, article in enumerate(articles):
        print(f'{i+1}. {article.get("title", "No title")}')

    client.close()

if __name__ == "__main__":
    asyncio.run(check_db())
