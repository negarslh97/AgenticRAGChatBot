"""
🧹 Complete Weaviate Cleanup Script
====================================

این اسکریپت تمام Schema/Collection های Weaviate را به طور کامل پاک می‌کند.
⚠️ WARNING: این عملیات غیرقابل بازگشت است!

استفاده:
    python scripts/clean_weaviate_completely.py
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)


def cleanup_weaviate_completely():
    """
    پاکسازی کامل Weaviate - حذف تمام collections
    """
    try:
        import weaviate
        from weaviate.classes.config import Configure
        
        logger.info("=" * 80)
        logger.info("🧹 Starting COMPLETE Weaviate Cleanup")
        logger.info("⚠️  WARNING: This will DELETE ALL data in Weaviate!")
        logger.info("=" * 80)
        
        # اتصال به Weaviate
        weaviate_url = settings.weaviate_url_loaded or "http://localhost:8080"
        weaviate_api_key = settings.weaviate_api_key_loaded
        
        logger.info(f"🔗 Connecting to Weaviate: {weaviate_url}")
        
        # ساخت client
        if weaviate_api_key:
            client = weaviate.connect_to_custom(
                http_host=weaviate_url.replace("http://", "").replace("https://", ""),
                http_port=8080,
                http_secure=False,
                auth_credentials=weaviate.auth.AuthApiKey(weaviate_api_key)
            )
        else:
            client = weaviate.connect_to_local(
                host=weaviate_url.replace("http://", "").replace("https://", "").split(":")[0],
                port=8080
            )
        
        logger.info("✅ Connected to Weaviate")
        
        # لیست تمام collections موجود
        collections = client.collections.list_all()
        
        if not collections:
            logger.info("✅ Weaviate is already empty - no collections found")
            client.close()
            return True
        
        logger.info(f"📊 Found {len(collections)} collection(s) to delete:")
        for name in collections.keys():
            logger.info(f"   - {name}")
        
        # تأیید از کاربر
        print("\n" + "=" * 80)
        print("⚠️  WARNING: You are about to DELETE ALL collections in Weaviate!")
        print("=" * 80)
        confirmation = input("Type 'DELETE ALL' to confirm: ")
        
        if confirmation != "DELETE ALL":
            logger.warning("❌ Operation cancelled by user")
            client.close()
            return False
        
        # حذف هر collection
        deleted_count = 0
        for collection_name in collections.keys():
            try:
                logger.info(f"🗑️  Deleting collection: {collection_name}")
                client.collections.delete(collection_name)
                logger.info(f"✅ Deleted: {collection_name}")
                deleted_count += 1
            except Exception as e:
                logger.error(f"❌ Failed to delete {collection_name}: {e}")
        
        logger.info("=" * 80)
        logger.info(f"✅ Cleanup completed: {deleted_count}/{len(collections)} collections deleted")
        logger.info("=" * 80)
        
        # بستن connection
        client.close()
        
        return deleted_count == len(collections)
        
    except Exception as e:
        logger.error(f"❌ Cleanup failed: {e}", exc_info=True)
        return False


def verify_cleanup():
    """
    تأیید اینکه Weaviate خالی شده است
    """
    try:
        import weaviate
        
        logger.info("🔍 Verifying cleanup...")
        
        weaviate_url = settings.weaviate_url_loaded or "http://localhost:8080"
        weaviate_api_key = settings.weaviate_api_key_loaded
        
        if weaviate_api_key:
            client = weaviate.connect_to_custom(
                http_host=weaviate_url.replace("http://", "").replace("https://", ""),
                http_port=8080,
                http_secure=False,
                auth_credentials=weaviate.auth.AuthApiKey(weaviate_api_key)
            )
        else:
            client = weaviate.connect_to_local(
                host=weaviate_url.replace("http://", "").replace("https://", "").split(":")[0],
                port=8080
            )
        
        collections = client.collections.list_all()
        
        if not collections:
            logger.info("✅ Verification passed: Weaviate is empty")
            client.close()
            return True
        else:
            logger.warning(f"⚠️  Verification failed: {len(collections)} collection(s) still exist")
            for name in collections.keys():
                logger.warning(f"   - {name}")
            client.close()
            return False
            
    except Exception as e:
        logger.error(f"❌ Verification failed: {e}")
        return False


if __name__ == "__main__":
    print("""
    ╔════════════════════════════════════════════════════════════════╗
    ║          🧹 Weaviate Complete Cleanup Script                  ║
    ║                                                                ║
    ║  This script will DELETE ALL data in Weaviate.                ║
    ║  ⚠️  This operation CANNOT be undone!                         ║
    ║                                                                ║
    ║  Use this only when you want to start fresh from scratch.     ║
    ╚════════════════════════════════════════════════════════════════╝
    """)
    
    success = cleanup_weaviate_completely()
    
    if success:
        print("\n✅ Cleanup successful!")
        
        # تأیید
        if verify_cleanup():
            print("✅ Verification passed - Weaviate is now empty and ready for re-indexing")
            print("\n📝 Next steps:")
            print("   1. Run: python scripts/reindex_knowledge_base.py")
            print("   2. Wait for complete indexing")
            print("   3. Test with: python scripts/test_retriever_direct.py")
        else:
            print("⚠️  Verification failed - some collections may still exist")
    else:
        print("\n❌ Cleanup failed or was cancelled")
        sys.exit(1)

