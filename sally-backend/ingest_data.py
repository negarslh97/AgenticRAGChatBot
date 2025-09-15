import asyncio
import os
import sys
from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

# --- Path Setup ---
# Add the project root to the Python path to allow imports from 'app'
# This is crucial for running the script as a standalone file
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from app.domain.entities import KnowledgeBaseArticle, ArticleStatus
from app.core.config import settings

async def ingest_data():
    """Connects to the database and ingests a sample knowledge base article."""
    print("Connecting to the database...")
    
    # The settings object should now be correctly populated
    db_url = settings.DATABASE_URL
    if not db_url:
        raise ValueError("DATABASE_URL not found in settings. Make sure your .env file is configured correctly.")

    # Use the DATABASE_URL from settings
    client = AsyncIOMotorClient(db_url)
    
    # Initialize Beanie with the document models
    # The database name is typically part of the connection string, but let's get it explicitly
    db_name = client.get_default_database().name
    await init_beanie(database=client[db_name], document_models=[KnowledgeBaseArticle])
    
    print("Database connection successful.")

    # --- Sample Article Data ---
    # You can modify this content or add more articles as needed.
    article_title = "راهنمای کامل استفاده از Sally ChatBot"
    article_content = """# Sally ChatBot - راهنمای کامل

## معرفی Sally
Sally یک دستیار هوشمند مکالمه‌ای است که می‌تواند به سوالات کاربران پاسخ دهد و در حل مشکلات آن‌ها کمک کند.

## ویژگی‌های اصلی
- پاسخگویی به سوالات کاربران
- جستجو در پایگاه دانش
- ایجاد تیکت پشتیبانی
- راهنمایی قدم به قدم

## نحوه استفاده
1. به صفحه چت بروید
2. سوال خود را بنویسید
3. منتظر پاسخ Sally بمانید
4. در صورت نیاز، از گزینه‌های پیشنهادی استفاده کنید

## ارتباط با پشتیبانی
اگر Sally نتوانست مشکلتان را حل کند، می‌توانید یک تیکت پشتیبانی ایجاد کنید.
"""
    article_summary = "راهنمای کامل استفاده از Sally ChatBot شامل ویژگی‌ها و نحوه کار با سیستم"
    
    # Check if an article with the same title already exists
    existing_article = await KnowledgeBaseArticle.find_one(KnowledgeBaseArticle.title == article_title)
    
    if existing_article:
        print(f"Article with title '{article_title}' already exists. Skipping ingestion.")
    else:
        print(f"Ingesting article: '{article_title}'")
        
        # Create a new knowledge base article instance
        # Note: In a real application, author_id should be a valid user ID.
        # For this script, we'll use a placeholder.
        new_article = KnowledgeBaseArticle(
            title=article_title,
            content=article_content,
            summary=article_summary,
            status=ArticleStatus.PUBLISHED,
            is_public=True,
            author_id="ingestion_script"  # Placeholder author ID
        )
        
        # Insert the new article into the database
        await new_article.insert()
        
        print("Article ingested successfully!")

if __name__ == "__main__":
    # Run the async function
    asyncio.run(ingest_data())
