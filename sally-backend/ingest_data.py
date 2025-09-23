import asyncio
import os
import sys
import markdown  # For markdown to HTML conversion

# --- Path Setup ---
# Add the project root to the Python path to allow imports from 'app'
# This is crucial for running the script as a standalone file
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from app.domain.entities_refactored import KnowledgeBaseArticle, ArticleStatus, Admin
from app.infrastructure.database_refactored import init_db, create_default_SuperAdmin
from app.core.config import settings

async def ingest_data():
    """Connects to the database and ingests a sample knowledge base article."""
    print("Connecting to the database...")
    
    # Initialize database with refactored models
    await init_db()
    print("Database connection successful.")
    
    # Ensure default admin exists
    await create_default_SuperAdmin()
    print("Default admin ensured.")

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
        
        # Get an admin to use as author
        admin = await Admin.find_one()
        if not admin:
            raise Exception("No admin found in database. Cannot create article.")
        
        # Generate HTML from markdown content
        content_html = markdown.markdown(article_content)
        
        # Create a new knowledge base article instance with refactored model
        new_article = KnowledgeBaseArticle(
            title=article_title,
            content_markdown=article_content,
            content_html=content_html,
            summary=article_summary,
            status=ArticleStatus.PUBLISHED,
            visibility=None,  # Will be set when published, but for sample, we can leave as published
            author=admin
        )
        
        # Insert the new article into the database
        await new_article.insert()
        
        print("Article ingested successfully!")

if __name__ == "__main__":
    # Run the async function
    asyncio.run(ingest_data())
