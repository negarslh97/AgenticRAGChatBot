"""
🔍 Direct Retriever Testing Script
===================================

این اسکریپت مستقیماً Retriever را بدون LLM تست می‌کند.
هدف: اطمینان از اینکه قطعات مرتبط درست بازیابی می‌شوند.

⚠️ CRITICAL TEST:
باید بتواند جمله "نکته: از نظر اهمیت، گروه بندی مشتریان از اهمیت بیشتری..." را پیدا کند.

استفاده:
    python scripts/test_retriever_direct.py
"""

import sys
import os
from pathlib import Path
import asyncio

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.core.logging_config import get_logger
from app.infrastructure.connection_manager import weaviate_client
from openai import OpenAI

logger = get_logger(__name__)


class DirectRetrieverTester:
    """تست مستقیم Retriever"""
    
    def __init__(self):
        self.openai_client = None
        
    def initialize(self):
        """راه‌اندازی"""
        logger.info("🔌 راه‌اندازی OpenAI client...")
        self.openai_client = OpenAI(
            api_key=settings.embedder_api_key_loaded,
            base_url=settings.embedder_openai_base_url_loaded
        )
        logger.info("✅ Client آماده است")
    
    async def test_retrieval(self, query: str, top_k: int = 10):
        """
        تست بازیابی برای یک سوال
        
        Args:
            query: سوال برای تست
            top_k: تعداد نتایج برتر
        """
        logger.info("=" * 80)
        logger.info(f"🔍 Testing retrieval for query:")
        logger.info(f"   {query}")
        logger.info("=" * 80)
        
        try:
            # 1️⃣ تولید embedding برای query
            logger.info("🔢 تولید embedding...")
            response = self.openai_client.embeddings.create(
                model=settings.embedder_model_loaded,
                input=query
            )
            query_vector = response.data[0].embedding
            logger.info(f"✅ Embedding تولید شد (ابعاد: {len(query_vector)})")
            
            # 2️⃣ جستجو در Weaviate
            logger.info(f"🔍 جستجو در Weaviate (top {top_k})...")
            
            with weaviate_client() as client:
                collection = client.collections.get("MarkdownNode")
                
                # Hybrid Search
                search_response = collection.query.hybrid(
                    query=query,
                    vector=query_vector,
                    alpha=0.5,  # وزن برابر vector و keyword
                    limit=top_k,
                    return_metadata=['distance', 'score']
                )
                
                if not search_response.objects:
                    logger.warning("❌ هیچ نتیجه‌ای پیدا نشد!")
                    return []
                
                logger.info(f"✅ {len(search_response.objects)} نتیجه پیدا شد")
                
                # 3️⃣ نمایش نتایج
                results = []
                logger.info("\n" + "=" * 80)
                logger.info("📋 نتایج بازیابی شده:")
                logger.info("=" * 80)
                
                for i, obj in enumerate(search_response.objects, 1):
                    score = obj.metadata.score if hasattr(obj.metadata, 'score') else 0.5
                    
                    result = {
                        'rank': i,
                        'title': obj.properties.get('title', ''),
                        'path': obj.properties.get('path', ''),
                        'content': obj.properties.get('content', ''),
                        'full_content': obj.properties.get('full_content', ''),
                        'score': score,
                        'node_id': obj.properties.get('node_id', ''),
                        'article_id': obj.properties.get('article_id', '')
                    }
                    results.append(result)
                    
                    # نمایش خلاصه
                    logger.info(f"\n🔹 Rank #{i} (Score: {score:.4f})")
                    logger.info(f"   📄 Title: {result['title']}")
                    logger.info(f"   📍 Path: {result['path']}")
                    logger.info(f"   📏 Content Length: {len(result['content'])} chars")
                    
                    # نمایش محتوا
                    content_preview = result['content'][:300]
                    logger.info(f"   📝 Content Preview:")
                    logger.info(f"      {content_preview}...")
                    
                    # اگر این محتوا شامل کلمات کلیدی است، هایلایت کن
                    if self._contains_keywords(result['content'], query):
                        logger.info(f"   ✅ این نتیجه شامل کلمات کلیدی است!")
                
                logger.info("\n" + "=" * 80)
                
                return results
                
        except Exception as e:
            logger.error(f"❌ خطا در تست: {e}", exc_info=True)
            return []
    
    def _contains_keywords(self, content: str, query: str) -> bool:
        """بررسی اینکه آیا محتوا شامل کلمات کلیدی query است"""
        content_lower = content.lower()
        query_words = query.lower().split()
        
        # حداقل 50% از کلمات باید موجود باشد
        matched = sum(1 for word in query_words if len(word) > 2 and word in content_lower)
        return matched >= len(query_words) * 0.5
    
    async def critical_test_grouping_vs_categorization(self):
        """
        تست حیاتی: تفاوت طبقه‌بندی و گروه‌بندی
        
        این تست باید جمله کلیدی را پیدا کند:
        "نکته: از نظر اهمیت، گروه بندی مشتریان از اهمیت بیشتری نسبت به طبقه بندی..."
        """
        logger.info("\n" + "🔴" * 40)
        logger.info("🎯 CRITICAL TEST: تفاوت طبقه‌بندی و گروه‌بندی")
        logger.info("🔴" * 40)
        
        query = "تفاوت طبقه بندی و گروه بندی مشتریان از نظر اهمیت گزارش گیری چیست؟"
        
        results = await self.test_retrieval(query, top_k=15)
        
        # بررسی اینکه آیا جمله کلیدی پیدا شد
        logger.info("\n" + "=" * 80)
        logger.info("🔍 بررسی نتایج برای جمله کلیدی...")
        logger.info("=" * 80)
        
        target_phrases = [
            "نکته",
            "از نظر اهمیت",
            "گروه بندی",
            "طبقه بندی",
            "اهمیت بیشتری",
            "گزارشات پایش"
        ]
        
        found_critical_content = False
        for result in results:
            content = result['content'].lower()
            
            # بررسی وجود تمام عبارات کلیدی
            matches = [phrase for phrase in target_phrases if phrase in content]
            
            if len(matches) >= 4:  # حداقل 4 از 6 عبارت کلیدی
                logger.info(f"\n✅ جمله کلیدی در Rank #{result['rank']} پیدا شد!")
                logger.info(f"   📄 Title: {result['title']}")
                logger.info(f"   📍 Path: {result['path']}")
                logger.info(f"   ✅ Matched phrases: {', '.join(matches)}")
                logger.info(f"   📝 Full Content:")
                logger.info(f"   {result['content'][:500]}...")
                found_critical_content = True
                break
        
        if not found_critical_content:
            logger.error("\n❌ CRITICAL FAILURE: جمله کلیدی پیدا نشد!")
            logger.error("⚠️  Retriever نتوانست اطلاعات مهم را بازیابی کند.")
            logger.error("⚠️  نیاز به بهبود در:")
            logger.error("   1. Chunking strategy")
            logger.error("   2. Embedding quality")
            logger.error("   3. Reranking mechanism")
            return False
        else:
            logger.info("\n✅ CRITICAL TEST PASSED!")
            logger.info("✅ Retriever می‌تواند اطلاعات مهم را بازیابی کند.")
            return True


async def main():
    """اجرای تست‌ها"""
    print("""
    ╔════════════════════════════════════════════════════════════════╗
    ║        🔍 Direct Retriever Testing Script                     ║
    ║                                                                ║
    ║  این اسکریپت مستقیماً Retriever را تست می‌کند.              ║
    ║  هدف: اطمینان از بازیابی صحیح اطلاعات کلیدی                 ║
    ╚════════════════════════════════════════════════════════════════╝
    """)
    
    tester = DirectRetrieverTester()
    tester.initialize()
    
    # تست حیاتی
    success = await tester.critical_test_grouping_vs_categorization()
    
    # تست‌های اضافی
    logger.info("\n\n" + "=" * 80)
    logger.info("📝 تست‌های اضافی")
    logger.info("=" * 80)
    
    additional_queries = [
        "نقشه راه استقرار سیستم حسابداری",
        "سند تعدیل ماهیت چیست؟",
        "چگونه فاکتور فروش ثبت کنم؟"
    ]
    
    for query in additional_queries:
        await tester.test_retrieval(query, top_k=5)
        logger.info("\n" + "-" * 80 + "\n")
    
    # نتیجه نهایی
    print("\n" + "=" * 80)
    if success:
        print("✅ تست حیاتی موفقیت‌آمیز بود!")
        print("✅ Retriever آماده برای استفاده در سیستم RAG است.")
        print("\n📝 مرحله بعدی:")
        print("   - می‌توانید سیستم کامل RAG را تست کنید")
        print("   - سوالات را از frontend بپرسید")
    else:
        print("❌ تست حیاتی شکست خورد!")
        print("⚠️  قبل از استفاده از RAG، باید مشکل Retriever را حل کنید.")
        print("\n📝 اقدامات پیشنهادی:")
        print("   1. بررسی کیفیت chunks در Weaviate")
        print("   2. بررسی embedding model")
        print("   3. تست با query های مختلف")
    print("=" * 80)
    
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

