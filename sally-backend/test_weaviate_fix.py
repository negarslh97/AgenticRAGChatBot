#!/usr/bin/env python3
"""
🔧 Weaviate Fix Test Script
===========================
این اسکریپت برای تست و رفع مشکلات Weaviate استفاده می‌شود.
"""

import asyncio
import sys
from pathlib import Path

# Add root directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.config import settings
from app.infrastructure.connection_manager import weaviate_client
import requests
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_weaviate_connection():
    """تست اتصال به Weaviate"""
    logger.info("🔍 Testing Weaviate connection...")
    
    try:
        with weaviate_client() as client:
            # Test basic connection
            is_ready = client.is_ready()
            logger.info(f"✅ Weaviate client ready: {is_ready}")
            
            # Test collection access
            collection_name = "MarkdownNode"
            if client.collections.exists(collection_name):
                collection = client.collections.get(collection_name)
                logger.info(f"✅ Collection '{collection_name}' exists")
                
                # Test query
                response = collection.query.fetch_objects(limit=3)
                objects = response.objects
                logger.info(f"✅ Found {len(objects)} objects in collection")
                
                # Check for vectors
                if objects:
                    for i, obj in enumerate(objects):
                        title = obj.properties.get('title', 'No title')[:50]
                        # Check if object has vectors
                        has_vectors = hasattr(obj, 'metadata') and obj.metadata and hasattr(obj.metadata, 'certainty')
                        logger.info(f"  {i+1}. {title} - Vectors: {'✅' if has_vectors else '❌'}")
                        
                        if not has_vectors:
                            logger.warning(f"    ⚠️ Object {i+1} has no vectors!")
                
                return len(objects) > 0, len(objects)
            else:
                logger.error(f"❌ Collection '{collection_name}' does not exist")
                return False, 0
                
    except Exception as e:
        logger.error(f"❌ Weaviate connection failed: {e}")
        return False, 0

async def test_semantic_search():
    """تست جستجوی معنایی"""
    logger.info("🔍 Testing semantic search...")
    
    try:
        with weaviate_client() as client:
            collection_name = "MarkdownNode"
            collection = client.collections.get(collection_name)
            
            # Test search with a simple query
            query = "نقدینگی"
            response = collection.query.near_text(
                query=query,
                limit=3,
                return_metadata=['distance', 'certainty']
            )
            
            objects = response.objects
            logger.info(f"✅ Semantic search returned {len(objects)} results")
            
            if objects:
                for i, obj in enumerate(objects):
                    title = obj.properties.get('title', 'No title')[:50]
                    certainty = getattr(obj.metadata, 'certainty', None)
                    distance = getattr(obj.metadata, 'distance', None)
                    logger.info(f"  {i+1}. {title}")
                    logger.info(f"     Certainty: {certainty}")
                    logger.info(f"     Distance: {distance}")
            else:
                logger.warning("⚠️ No results from semantic search")
                
            return len(objects) > 0
            
    except Exception as e:
        logger.error(f"❌ Semantic search failed: {e}")
        return False

async def main():
    """اجرای تست‌های کامل"""
    logger.info("=" * 80)
    logger.info("🔧 Weaviate Fix Test Suite")
    logger.info("=" * 80)
    
    # Test 1: Connection
    connection_ok, object_count = await test_weaviate_connection()
    
    # Test 2: Semantic Search
    search_ok = await test_semantic_search()
    
    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("📊 Test Results Summary:")
    logger.info(f"   Connection: {'✅ PASS' if connection_ok else '❌ FAIL'}")
    logger.info(f"   Objects Found: {object_count}")
    logger.info(f"   Semantic Search: {'✅ PASS' if search_ok else '❌ FAIL'}")
    
    if connection_ok and search_ok:
        logger.info("🎉 All tests passed! Weaviate is working correctly.")
    elif connection_ok and not search_ok:
        logger.warning("⚠️ Connection works but semantic search fails.")
        logger.warning("💡 This indicates missing vectors. Run reindexing script.")
    else:
        logger.error("❌ Connection failed. Check Weaviate server and configuration.")
    
    logger.info("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())