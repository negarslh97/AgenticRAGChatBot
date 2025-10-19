"""
بررسی ساختار کامل MongoDB - یافتن databases و collections
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings


async def check_structure():
    """بررسی تمام databases و collections"""
    
    print("\n" + "=" * 80)
    print("[INFO] Checking MongoDB Structure")
    print("=" * 80)
    
    print(f"\n[CONFIG] Connection URL: {settings.database_url}")
    
    # اتصال
    client = AsyncIOMotorClient(settings.database_url)
    
    # لیست تمام databases
    print("\n[DATABASES] Available databases:")
    db_list = await client.list_database_names()
    for db_name in db_list:
        print(f"   - {db_name}")
    
    # بررسی database فعلی
    db = client.get_database()
    current_db_name = db.name
    print(f"\n[CURRENT] Current database: {current_db_name}")
    
    # لیست collections در database فعلی
    print(f"\n[COLLECTIONS] Collections in '{current_db_name}':")
    coll_list = await db.list_collection_names()
    
    if not coll_list:
        print("   [WARNING] No collections found!")
    else:
        for coll_name in coll_list:
            coll = db[coll_name]
            count = await coll.count_documents({})
            print(f"   - {coll_name}: {count} documents")
            
            # اگر knowledge_base پیدا شد، جزئیات بیشتر
            if coll_name == "knowledge_base":
                print(f"\n[DETAILS] 'knowledge_base' collection:")
                if count > 0:
                    # نمونه اولین document
                    sample = await coll.find_one()
                    print("      Sample document fields:")
                    for key in sample.keys():
                        print(f"         - {key}")
                else:
                    print("      [WARNING] Collection is empty!")
    
    # بررسی دیگر databases
    print("\n" + "=" * 80)
    print("[SEARCH] Searching for articles in all databases...")
    print("=" * 80)
    
    for db_name in db_list:
        if db_name in ["admin", "config", "local"]:
            continue  # Skip system databases
        
        db_temp = client[db_name]
        collections = await db_temp.list_collection_names()
        
        for coll_name in collections:
            if "knowledge" in coll_name.lower() or "article" in coll_name.lower():
                count = await db_temp[coll_name].count_documents({})
                print(f"\n[FOUND] Database: {db_name}, Collection: {coll_name}")
                print(f"        Documents: {count}")
                
                if count > 0:
                    sample = await db_temp[coll_name].find_one()
                    print("        Sample fields:")
                    for key in list(sample.keys())[:10]:  # First 10 fields
                        print(f"           - {key}")
    
    print("\n" + "=" * 80)
    print("[SOLUTION] If articles are in a different database/collection:")
    print("=" * 80)
    print("\n1. Update .env file:")
    print("   DATABASE_URL=mongodb://localhost:27017/<correct_database_name>")
    print("\n2. Or check if collection name is different from 'knowledge_base'")
    
    client.close()


if __name__ == "__main__":
    asyncio.run(check_structure())

