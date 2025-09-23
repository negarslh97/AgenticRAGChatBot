#!/usr/bin/env python3
"""
Check status values in articles.
"""

import asyncio
import sys
import os

# Add the parent directory to the path to import app modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'sally-backend'))

from app.core.config import settings
from motor.motor_asyncio import AsyncIOMotorClient

async def check_status():
    """Check status values in articles."""
    client = AsyncIOMotorClient(settings.database_url)
    db = client.get_default_database()
    articles = await db.knowledge_base_articles.find({}).to_list(None)

    for article in articles:
        title = article.get('title', 'No title')
        status = article.get('status')
        print(f'{title}: status={status}')

    client.close()

if __name__ == "__main__":
    asyncio.run(check_status())
