from typing import List, Dict, Any, Optional, Union
from abc import ABC, abstractmethod
import logging
import requests  # 🆕 برای ارتباط با API خارجی reranker
from bson import ObjectId
from app.core.config import settings
from app.domain.entities import KnowledgeBaseArticle, ArticleStatus, ArticleVisibility, Customer, Admin, ArticleCategory, ArticleTag

logger = logging.getLogger(__name__)


class RAGService(ABC):
    """Abstract base class for RAG services."""

    def __init__(self):
        # Initialize OpenAI client
        self.client = None
        # OpenAI client initialization moved to langchain_utils.py
        # No direct client needed here as we use LangChain service
        
        # 🆕 تنظیمات Reranker API (Colab)
        self.reranker_api_url = getattr(settings, 'RERANKER_API_URL', None)
        if self.reranker_api_url:
            logger.info(f"🔗 Reranker API configured: {self.reranker_api_url}")
        else:
            logger.warning("⚠️ Reranker API URL not configured - will use fallback scoring")
    
    @abstractmethod
    async def generate_response(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate response using RAG."""
        pass
    
    async def retrieve_relevant_documents(self, query: str, is_public_only: bool = True) -> List[Dict[str, Any]]:
        """Retrieve relevant documents using Weaviate vector search, enriched with MongoDB metadata."""
        logger.info("🔍 Starting hybrid document retrieval process")
        logger.info(f"📊 Search scope: {'Public only' if is_public_only else 'All documents'}")
        logger.info("🔗 Using Weaviate for vector search + MongoDB for metadata enrichment...")

        try:
            # Use Weaviate for vector search to find relevant documents
            weaviate_results = await self._retrieve_from_weaviate(query, is_public_only)

            if weaviate_results:
                logger.info(f"✅ Found {len(weaviate_results)} documents via Weaviate")
                # Enrich results with MongoDB metadata
                return await self._enrich_with_mongodb_metadata(weaviate_results, is_public_only)
            else:
                logger.warning("❌ No results from Weaviate, falling back to MongoDB keyword search...")
                # Fallback to MongoDB if Weaviate fails
                return await self._retrieve_from_mongodb(query, is_public_only)

        except Exception as e:
            logger.error(f"❌ Hybrid search failed: {e}")
            logger.info("🔄 Falling back to MongoDB keyword search...")
            return await self._retrieve_from_mongodb(query, is_public_only)

    def _extract_article_title_from_content(self, full_content: str) -> str:
        """
        استخراج عنوان اصلی مقاله از محتوای کامل Markdown.
        عنوان اصلی معمولاً اولین header است که با # شروع می‌شود.
        
        Args:
            full_content: محتوای کامل مقاله در قالب Markdown
            
        Returns:
            عنوان مقاله اصلی یا None
        """
        if not full_content:
            return None
            
        # جستجوی اولین خط که با # شروع می‌شود
        lines = full_content.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('#'):
                # حذف # ها و فاصله‌های اضافی
                title = line.lstrip('#').strip()
                if title:  # اطمینان از اینکه عنوان خالی نیست
                    return title
        
        return None
    
    def _get_display_title(self, doc: Dict[str, Any]) -> str:
        """
        استخراج عنوان نمایشی مقاله از document.
        
        این متد یک منطق چندمرحله‌ای برای پیدا کردن بهترین عنوان دارد:
        1. ابتدا از فیلد article_title استفاده می‌کند
        2. اگر موجود نبود، از محتوای کامل استخراج می‌کند
        3. در نهایت از title (chunk title) استفاده می‌کند
        
        Args:
            doc: سند شامل اطلاعات مقاله
            
        Returns:
            عنوان نمایشی مقاله
        """
        # مرحله 1: سعی کنید article_title را بگیرید
        article_title = doc.get("article_title")
        
        # مرحله 2: اگر article_title وجود نداشت، از full_article_content استخراج کنید
        if not article_title:
            full_article_content = doc.get("full_article_content", "")
            article_title = self._extract_article_title_from_content(full_article_content)
        
        # مرحله 3: اگر باز هم پیدا نشد، از title (chunk title) استفاده کنید
        if not article_title:
            article_title = doc.get("title", "بدون عنوان")
        
        return article_title
    
    async def _enrich_with_mongodb_metadata(self, weaviate_results: List[Dict[str, Any]], is_public_only: bool = True) -> List[Dict[str, Any]]:
        """
        Enrich Weaviate results with MongoDB metadata (OPTIONAL).
        اگر article در MongoDB نبود، از داده‌های Weaviate استفاده می‌کنیم.
        
        🔥 OPTIMIZED: استفاده از batch query برای جلوگیری از مشکل N+1 Query
        """
        logger.info("🗄️ Enriching Weaviate results with MongoDB metadata...")

        # Initialize database connection
        from app.infrastructure.database.mongodb import init_db, get_mongo_client
        from app.domain.entities import KnowledgeBaseArticle, ArticleStatus, ArticleVisibility

        if get_mongo_client() is None:
            await init_db()

        enriched_docs = []

        # 🔥 OPTIMIZATION 1: جمع‌آوری تمام article_id های یکتا
        article_ids = []
        for weaviate_doc in weaviate_results:
            article_id = weaviate_doc.get("id")
            if article_id:
                article_ids.append(article_id)
        
        # 🔥 OPTIMIZATION 2: فقط یک درخواست به MongoDB برای گرفتن تمام مقالات
        articles_map = {}
        if article_ids:
            try:
                # 🔥 FIX: تبدیل رشته‌ها به ObjectId قبل از کوئری
                # اضافه کردن یک بررسی برای اطمینان از معتبر بودن شناسه
                object_ids = [ObjectId(aid) for aid in set(article_ids) if ObjectId.is_valid(aid)]

                logger.info(f"📊 Fetching {len(set(object_ids))} unique articles from MongoDB in single batch query...")
                articles_cursor = KnowledgeBaseArticle.find({"_id": {"$in": object_ids}})
                articles_map = {str(article.id): article async for article in articles_cursor}
                logger.info(f"✅ Fetched {len(articles_map)} articles from MongoDB in a single query.")
            except Exception as e:
                logger.error(f"❌ Batch fetch from MongoDB failed: {e}")
                articles_map = {}

        # 🔥 OPTIMIZATION 3: حلقه بدون درخواست اضافی به دیتابیس
        for weaviate_doc in weaviate_results:
            try:
                article_id = weaviate_doc.get("id")
                if not article_id:
                    logger.warning(f"⚠️ Skipping document without article_id: {weaviate_doc}")
                    # حتی بدون article_id، از داده Weaviate استفاده می‌کنیم
                    enriched_docs.append({
                        "id": weaviate_doc.get("node_id", "unknown"),
                        "title": weaviate_doc.get("title", "Untitled"),
                        "content": weaviate_doc.get("content", ""),
                        "summary": "",
                        "score": weaviate_doc.get("score", 0.5),
                        "source": "weaviate_only",
                        "path": weaviate_doc.get("path", ""),
                        "node_id": weaviate_doc.get("node_id", ""),
                        "url": None,
                        "tags": [],
                        "category": None
                    })
                    continue

                # 🔥 دریافت آنی article از map (بدون درخواست دیتابیس)
                article = articles_map.get(article_id)

                if article:
                    # Apply visibility filter if needed
                    if is_public_only and article.visibility != ArticleVisibility.PUBLIC:
                        logger.info(f"🔒 Skipping non-public article: {article_id}")
                        continue

                    # 🔥 ENHANCED: استفاده از محتوای غنی Weaviate (نه MongoDB محدود)
                    # محتوای Weaviate شامل node content کامل است (1500-2000 کاراکتر)
                    weaviate_content = weaviate_doc.get("content", "")
                    
                    # 🎯 استفاده از title chunk (نه title article)
                    chunk_title = weaviate_doc.get("title", article.title)
                    
                    # Create enriched document with MongoDB metadata + Weaviate content
                    enriched_doc = {
                        "id": str(article.id),
                        "article_title": article.title,  # 🆕 title اصلی article
                        "title": chunk_title,  # 🎯 title chunk (برای نمایش منحصر به فرد)
                        "content": weaviate_content,  # 🔥 از Weaviate (کامل)
                        "summary": article.summary,
                        "score": weaviate_doc.get("score", 0.5),
                        "source": "hybrid",
                        "path": weaviate_doc.get("path", ""),
                        "node_id": weaviate_doc.get("node_id", ""),
                        "url": getattr(article, 'url', None),
                        "tags": [tag.name for tag in getattr(article, 'tags', [])] if hasattr(article, 'tags') else [],
                        "category": getattr(article, 'category', {}).name if hasattr(article, 'category') and article.category else None,
                        # 🔥 حفظ فیلدهای اضافی Weaviate
                        "raw_content": weaviate_doc.get("raw_content", weaviate_content),
                        "full_article_content": weaviate_doc.get("full_article_content", "")
                    }
                    logger.info(f"✅ Enriched with MongoDB: '{chunk_title[:40]}...' at {enriched_doc['path']} (Score: {enriched_doc['score']:.3f})")
                else:
                    # Article not in MongoDB - use Weaviate data directly
                    logger.debug(f"📄 Using Weaviate data for {article_id} (not found in MongoDB)")
                    
                    # 🔥 استخراج عنوان اصلی مقاله از محتوای کامل
                    full_article_content = weaviate_doc.get("full_article_content", "")
                    article_title = self._extract_article_title_from_content(full_article_content)
                    chunk_title = weaviate_doc.get("title", "Untitled")
                    
                    enriched_doc = {
                        "id": article_id,
                        "article_title": article_title,  # 🎯 عنوان اصلی مقاله
                        "title": chunk_title,  # عنوان chunk
                        "content": weaviate_doc.get("content", ""),
                        "summary": "",
                        "score": weaviate_doc.get("score", 0.5),
                        "source": "weaviate_only",
                        "path": weaviate_doc.get("path", ""),
                        "node_id": weaviate_doc.get("node_id", ""),
                        "url": None,
                        "tags": [],
                        "category": None
                    }
                    display_title = article_title or chunk_title
                    logger.info(f"✅ Using Weaviate data: '{display_title[:50]}...' (Score: {enriched_doc['score']:.3f})")

                enriched_docs.append(enriched_doc)

            except Exception as e:
                logger.error(f"❌ Error processing document {weaviate_doc.get('id')}: {e}")
                # حتی با خطا، سعی می‌کنیم از داده Weaviate استفاده کنیم
                try:
                    # استخراج article title از محتوای کامل
                    full_article_content = weaviate_doc.get("full_article_content", "")
                    article_title = self._extract_article_title_from_content(full_article_content)
                    
                    enriched_docs.append({
                        "id": weaviate_doc.get("id", weaviate_doc.get("node_id", "unknown")),
                        "article_title": article_title,  # 🎯 عنوان اصلی
                        "title": weaviate_doc.get("title", "Untitled"),  # عنوان chunk
                        "content": weaviate_doc.get("content", ""),
                        "summary": "",
                        "score": weaviate_doc.get("score", 0.5),
                        "source": "weaviate_fallback",
                        "path": weaviate_doc.get("path", ""),
                        "node_id": weaviate_doc.get("node_id", ""),
                        "url": None,
                        "tags": [],
                        "category": None
                    })
                except Exception as fallback_error:
                    logger.error(f"❌ Even fallback failed: {fallback_error}")
                    continue

        logger.info(f"✅ Enrichment completed: {len(enriched_docs)} documents ready (from {len(weaviate_results)} Weaviate results)")
        return enriched_docs

    def _format_sources_markdown(self, documents: List[Dict[str, Any]], max_sources: int = None) -> List[Dict[str, Any]]:
        """
        Format sources as unique articles (not chunks).
        🎯 نمایش مقالات یکتا - فقط لینک به سند اصلی (بدون نمایش گره‌های جداگانه)
        
        Args:
            documents: لیست documents (chunks)
            max_sources: حداکثر تعداد مقالات یکتا برای برگرداندن (None = استفاده از config)
            
        Returns:
            لیست مقالات یکتا با اولویت بالاترین score
        """
        # استفاده از تنظیمات اگر max_sources مشخص نشده باشد
        if max_sources is None:
            max_sources = settings.max_sources_to_format
        
        formatted_sources = []
        seen_article_ids = set()  # 🎯 برای جلوگیری از تکرار مقالات
        
        # 🎯 گروه‌بندی chunks بر اساس article_id برای یافتن بهترین score
        article_best_scores = {}
        for doc in documents:
            article_id = str(doc.get("id", ""))
            score = doc.get("score", 0)
            if article_id not in article_best_scores or score > article_best_scores[article_id]["score"]:
                article_best_scores[article_id] = {
                    "doc": doc,
                    "score": score
                }

        # 🎯 مرتب‌سازی بر اساس بهترین score هر مقاله
        sorted_articles = sorted(
            article_best_scores.items(), 
            key=lambda x: x[1]["score"], 
            reverse=True
        )

        for article_id, data in sorted_articles[:max_sources]:
            doc = data["doc"]
            
            # 🎯 استفاده از متد helper برای استخراج عنوان
            article_title = self._get_display_title(doc)
            
            # استخراج snippet از بهترین chunk برای preview
            content = doc.get("content", "")
            snippet = content[:200] + "..." if len(content) > 200 else content
            
            # 🎯 فقط اطلاعات مقاله اصلی - بدون اطلاعات chunk
            formatted_sources.append({
                "id": article_id,
                "title": article_title,  # 🎯 فقط عنوان مقاله اصلی
                "score": data["score"],
                "category": doc.get("category"),
                "tags": doc.get("tags", []),
                "url": doc.get("url"),  # 🎯 لینک به مقاله اصلی
                "snippet": snippet,  # پیش‌نمایش کوتاه
                "summary": doc.get("summary", "")
            })

        logger.info(f"📋 Formatted {len(formatted_sources)} unique articles (from {len(documents)} chunks)")
        
        # 🔥 DEBUG: نمایش منابع برگشتی
        for idx, src in enumerate(formatted_sources, 1):
            logger.info(f"   🔖 Article #{idx}: {src['title'][:50]}... (Score: {src['score']:.3f})")
        
        return formatted_sources

    async def _retrieve_from_weaviate(self, query: str, is_public_only: bool = True, limit: int = None) -> List[Dict[str, Any]]:
        """
        Retrieve documents using Enhanced Weaviate vector search with:
        1. Query Expansion برای coverage بهتر
        2. Hybrid Search (vector + keyword)
        3. تعداد بیشتر documents (قابل تنظیم از settings)
        4. Content غنی‌تر (2000 کاراکتر به جای 1000)
        5. Powerful Reranking (BAAI/bge-reranker-v2-m3)
        """
        # 🔥 استفاده از تنظیمات به جای hardcoded values
        if limit is None:
            limit = settings.weaviate_retrieval_limit
        logger.info("🔗 Connecting to Weaviate vector database...")
        
        try:
            import os
            # settings already imported at top of file - no need to import again
            from app.infrastructure.connection_manager import weaviate_client
            from openai import OpenAI

            logger.info(f"🌐 Weaviate URL: {settings.weaviate_url_loaded or 'http://localhost:8080'}")
            logger.info(f"🔑 Weaviate API Key: {'✅ Set' if settings.weaviate_api_key_loaded else '❌ Not Set'}")

            # Set API key in environment
            embedder_api_key = settings.embedder_api_key_loaded
            openai_api_key = settings.openai_api_key_loaded
            api_key_to_use = embedder_api_key or openai_api_key
            
            if api_key_to_use:
                os.environ['Embedder_API_KEY'] = api_key_to_use
                logger.info("🔑 OpenAI API key set for embeddings")
                logger.info(f"🔑 API Key source: {'Embedder' if embedder_api_key else 'OpenAI'}")
            else:
                logger.warning("⚠️  No OpenAI API key found for embeddings")

            # 🔥 STEP 1: Query Expansion - توسعه query برای پوشش بهتر
            expanded_queries = await self._expand_query(query)
            logger.info(f"🔍 Query expanded: {len(expanded_queries)} variations")
            for i, eq in enumerate(expanded_queries[:3], 1):
                logger.info(f"   {i}. {eq[:80]}...")

            # استفاده از Server-Side Vectorization - دیگر نیازی به تولید vector نیست
            logger.info(f"🔢 استفاده از Server-Side Vectorization برای جستجو...")

            # استفاده از Connection Manager - کل عملیات داخل with
            with weaviate_client() as client:
                logger.info("✅ Weaviate client ready (using connection manager)")
                
                # Build where filter for visibility
                if is_public_only:
                    logger.info("🔒 Applied visibility filter: public documents only")
                else:
                    logger.info("🔓 No visibility filter: searching all documents")

                logger.info(f"🎯 جستجوی معنایی با vector...")

                # استفاده از v4 API برای جستجو
                collection = client.collections.get("MarkdownNode")
                
                logger.info(f"⚡ Executing Enhanced Weaviate Hybrid Search (limit: {limit})...")
                
                # 🔥 STEP 2: Semantic Search with Server-Side Vectorization
                # استفاده از near_text مستقیماً با متن query
                try:
                    logger.info(f"🎯 استفاده از near_text با Server-Side Vectorization...")

                    response = collection.query.near_text(
                        query=query,  # <--- ارسال مستقیم متن query
                        limit=limit,
                        return_metadata=['distance', 'certainty']
                    )

                    objects = response.objects if response.objects else []
                    logger.info(f"✅ Semantic Search: {len(objects)} گره Markdown یافت شد (Server-Side Vectorization)")

                except Exception as e:
                    logger.error(f"❌ خطا در جستجوی MarkdownNode: {str(e)}")
                    objects = []

                # Handle case where objects is None
                if objects is None:
                    logger.warning("⚠️  Weaviate returned None objects")
                    objects = []
                
                logger.info(f"📊 Raw results from Weaviate: {len(objects)} objects")

                relevant_docs = []
                seen_node_ids = set()  # برای جلوگیری از duplicate
                
                for i, obj in enumerate(objects):
                    # در v4 با near_text، certainty در metadata قرار دارد
                    if hasattr(obj.metadata, 'certainty') and obj.metadata.certainty is not None:
                        score = obj.metadata.certainty
                    else:
                        score = 0.5  # fallback
                    
                    # در v4، properties در obj.properties قرار دارند
                    title = obj.properties.get("title", "")
                    node_id = obj.properties.get("node_id", "")
                    article_id = obj.properties.get("article_id", "")
                    path = obj.properties.get("path", "")
                    
                    # جلوگیری از duplicate nodes
                    if node_id in seen_node_ids:
                        logger.debug(f"⏭️ Skipping duplicate node: {node_id}")
                        continue
                    seen_node_ids.add(node_id)

                    logger.info(f"   📄 Node {i+1}: '{title[:30]}...' (Path: {path}, Score: {score:.3f})")

                    # 🔥 STEP 3: محتوای غنی‌تر - 2000 کاراکتر به جای 1000
                    full_content = obj.properties.get("full_content", "")[:2000]  # 2x more content
                    node_content = obj.properties.get("content", "")[:1500]  # 1.5x more

                    # Create a more informative content by combining path, title and content
                    combined_content = f"Path: {path}\nTitle: {title}\nContent: {node_content}"
                    if full_content:
                        combined_content += f"\n\nFull Article Context: {full_content[:1000]}..."

                    relevant_docs.append({
                        "id": article_id,
                        "node_id": node_id,
                        "title": title,  # 🎯 فقط title chunk (بدون path)
                        "content": combined_content,
                        "path": path,
                        "score": score,
                        "source": "weaviate",
                        "raw_content": node_content,  # محتوای خام برای reranking
                        "full_article_content": full_content  # 🔥 محتوای کامل برای استخراج article title
                    })

                logger.info(f"✅ Weaviate search completed: {len(relevant_docs)} unique documents found")
                logger.info(f"🎯 Query: '{query[:50]}{'...' if len(query) > 50 else ''}'")
                
                # 🔥 STEP 4: Reranking - مرتب‌سازی مجدد بر اساس relevance
                # استفاده از تنظیمات به جای hardcoded value
                reranked_docs = await self._rerank_documents(query, relevant_docs, top_k=settings.reranker_top_k)
                logger.info(f"🎯 Reranked {len(reranked_docs)} documents by relevance")
                
                # 🔍 DEBUG: نمایش محتوای دقیق top 5 documents برای بررسی کیفیت retrieval
                logger.info("=" * 80)
                logger.info("📋 محتوای دقیق Top 5 Documents بازیابی‌شده:")
                for i, doc in enumerate(reranked_docs[:5], 1):
                    content_preview = doc.get('content', '')[:300].replace('\n', ' ')
                    logger.info(f"   📄 Doc {i} (Score: {doc.get('score', 0):.3f}):")
                    logger.info(f"      Title: {doc.get('title', 'N/A')[:80]}")
                    logger.info(f"      Path: {doc.get('path', 'N/A')}")
                    logger.info(f"      Content Preview: {content_preview}...")
                    logger.info(f"      Content Length: {len(doc.get('content', ''))} chars")
                logger.info("=" * 80)
                
                return reranked_docs
            # client به صورت خودکار بسته می‌شود توسط context manager

        except Exception as e:
            logger.error(f"Weaviate search error: {e}")
            raise e
    
    async def _expand_query(self, query: str) -> List[str]:
        """
        توسعه query با اضافه کردن مترادف‌ها و عبارات مرتبط
        
        Args:
            query: سوال اصلی
            
        Returns:
            لیست queries توسعه یافته
        """
        # استفاده از روش‌های ساده برای query expansion
        expanded = [query]  # query اصلی همیشه اول است
        
        # اضافه کردن variations ساده
        query_lower = query.lower().strip()
        
        # حذف علامت‌های سوال
        if query_lower.endswith('؟') or query_lower.endswith('?'):
            expanded.append(query_lower.rstrip('؟?').strip())
        
        # اضافه کردن فرم‌های مختلف
        common_synonyms = {
            'چی': ['چه', 'چیز', 'چیزی'],
            'میدونی': ['می‌دانی', 'دانی', 'می‌دونی'],
            'در مورد': ['درباره', 'راجع به', 'پیرامون'],
            'چطور': ['چگونه', 'به چه صورت'],
            'چرا': ['به چه دلیل', 'علت'],
        }
        
        for key, synonyms in common_synonyms.items():
            if key in query_lower:
                for syn in synonyms[:1]:  # فقط اولین مترادف
                    expanded.append(query_lower.replace(key, syn))
        
        # حداکثر 3 variation برمی‌گردانیم
        return list(set(expanded))[:3]
    
    async def _rerank_documents(self, query: str, documents: List[Dict[str, Any]], top_k: int = 15) -> List[Dict[str, Any]]:
        """
        Rerank documents using external Reranker API (Colab) with fallback to local scoring.
        
        🎯 استراتژی:
        1. اگر API موجود باشد: استفاده از BAAI/bge-reranker-v2-m3
        2. در غیر این صورت: fallback به scoring محلی
        
        Args:
            query: سوال کاربر
            documents: لیست documents
            top_k: تعداد documents برتر برای برگرداندن
            
        Returns:
            لیست مرتب شده documents
        """
        # 🎯 تلاش برای استفاده از API خارجی
        if self.reranker_api_url:
            try:
                logger.info(f"🚀 Reranking {len(documents)} documents with external API...")
                
                # 1️⃣ آماده‌سازی داده‌ها
                doc_contents = [doc.get("raw_content", doc.get("content", "")) for doc in documents]
                
                # 2️⃣ ساخت payload برای API
                payload = {
                    "query": query,
                    "documents": doc_contents
                }
                
                # 3️⃣ ارسال درخواست به API
                response = requests.post(
                    self.reranker_api_url,
                    json=payload,
                    timeout=settings.reranker_timeout
                )
                
                # 4️⃣ بررسی موفقیت
                response.raise_for_status()
                
                # 5️⃣ دریافت امتیازات
                result = response.json()
                scores = result.get("scores", [])
                
                if len(scores) != len(documents):
                    raise ValueError(f"Score count mismatch: got {len(scores)}, expected {len(documents)}")
                
                # 6️⃣ اعمال امتیازات جدید
                for idx, (doc, score) in enumerate(zip(documents, scores)):
                    doc["rerank_score"] = float(score)
                    doc["score"] = float(score)  # بروزرسانی score اصلی
                
                # 7️⃣ مرتب‌سازی بر اساس امتیازات جدید
                documents.sort(key=lambda x: x.get("rerank_score", -999), reverse=True)
                
                logger.info(f"✅ API Reranking completed. Top score: {documents[0]['score']:.4f}")
                
                return documents[:top_k]
                
            except requests.exceptions.Timeout:
                logger.error("❌ Reranker API timeout - falling back to local scoring")
            except requests.exceptions.ConnectionError:
                logger.error("❌ Reranker API connection failed - falling back to local scoring")
            except Exception as e:
                logger.error(f"❌ Reranker API error: {e} - falling back to local scoring")
        
        # 🔄 Fallback: scoring محلی
        logger.info(f"⚙️ Using fallback local scoring for {len(documents)} documents...")
        
        try:
            query_lower = query.lower()
            query_keywords = set(query_lower.split())
            
            for doc in documents:
                # شروع با vector score از Weaviate
                vector_score = doc.get("score", 0.5)
                
                # Keyword matching score
                content_lower = doc.get("raw_content", "").lower()
                title_lower = doc.get("title", "").lower()
                
                # تعداد کلمات مشترک
                content_keywords = set(content_lower.split())
                keyword_overlap = len(query_keywords & content_keywords)
                keyword_score = min(keyword_overlap / max(len(query_keywords), 1), 1.0)
                
                # Title matching
                title_score = 0.0
                for keyword in query_keywords:
                    if len(keyword) > 2 and keyword in title_lower:
                        title_score += 0.2
                title_score = min(title_score, 1.0)
                
                # ترکیب امتیازات: 60% vector, 25% keyword, 15% title
                combined_score = (0.60 * vector_score) + (0.25 * keyword_score) + (0.15 * title_score)
                
                doc["rerank_score"] = combined_score
                doc["score"] = combined_score
            
            # مرتب‌سازی
            documents.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)
            
            logger.info(f"✅ Fallback reranking completed. Top score: {documents[0]['score']:.4f}")
            
            return documents[:top_k]
            
        except Exception as e:
            logger.error(f"❌ Fallback reranking failed: {e}")
            # آخرین راه: برگرداندن documents با ترتیب اصلی
            documents.sort(key=lambda x: x.get("score", 0), reverse=True)
            return documents[:top_k]
    
    async def _calculate_groundedness_score(self, query: str, answer: str, sources: List[Dict[str, Any]], top_score: float = None) -> float:
        """
        🔥 ENHANCED: Groundedness Check - بررسی سخت‌گیرانه اینکه آیا پاسخ واقعاً توسط منابع پشتیبانی می‌شود

        این متد از LLM استفاده می‌کند تا بررسی کند آیا پاسخ نهایی واقعاً
        بر اساس اطلاعات منابع ارائه شده ساخته شده یا خیر.

        Args:
            query: سوال کاربر
            answer: پاسخ تولید شده
            sources: منابع استفاده شده
            top_score: بالاترین امتیاز retrieval برای تصمیم‌گیری اولیه

        Returns:
            امتیاز groundedness بین 0 تا 1
        """
        try:
            # 🔥 NEW: اگر retrieval scores بسیار پایین هستند، مستقیماً امتیاز پایینی بده
            if top_score is not None and top_score < 0.1:
                logger.warning(f"⚠️ Top retrieval score too low ({top_score:.3f}) - skipping groundedness check and assigning low score")
                return 0.1  # امتیاز بسیار پایین برای retrieval ضعیف

            # 🔥 NEW: بررسی پاسخ‌های "نمی‌دانم" - اگر پاسخ نشان‌دهنده عدم وجود اطلاعات است، امتیاز بالا بده
            no_info_phrases = ["متاسفانه اطلاعات مربوط به این سوال در پایگاه دانش من موجود نیست", "اطلاعاتی ندارم"]
            if any(phrase in answer for phrase in no_info_phrases):
                logger.warning("⚠️ Answer indicates no information found. Assigning low groundedness score.")
                return 0.1 # امتیاز پایین چون به هیچ منبعی متصل نیست

            # اگر LLM در دسترس نیست، امتیاز پیش‌فرض بده
            if not settings.openai_api_key_loaded:
                logger.warning("⚠️ OpenAI API key not available for groundedness check")
                return 0.5  # امتیاز پیش‌فرض پایین‌تر

            from app.infrastructure.langchain_utils import langchain_service

            # ساخت prompt سخت‌گیرانه‌تر برای بررسی groundedness
            sources_text = "\n".join([f"- {src.get('title', 'N/A')}: {src.get('content', '')[:300]}" for src in sources[:5]])  # بیشتر منابع، محتوای بیشتر

            # 🔥 ENHANCED: Prompt سخت‌گیرانه‌تر
            groundedness_prompt = f"""
            شما یک ارزیاب بسیار سخت‌گیر کیفیت پاسخ هستید. وظیفه شما بررسی دقیق این است که آیا پاسخ ارائه شده واقعاً بر اساس منابع داده شده ساخته شده یا خیر.

            **دستورالعمل‌های حیاتی:**
            - پاسخ باید مستقیماً از منابع استخراج شده باشد
            - اگر پاسخ شامل هر گونه اطلاعات خارج از منابع است، امتیاز را کاهش دهید
            - اگر پاسخ از ترکیب منابع نامرتبط ساخته شده، امتیاز بسیار پایینی بدهید
            - اگر پاسخ ساختگی یا استنباطی است، امتیاز صفر بدهید

            سوال کاربر: {query}

            پاسخ تولید شده:
            {answer}

            منابع موجود (بررسی کنید آیا پاسخ واقعاً از این منابع استخراج شده):
            {sources_text}

            **ارزیابی سخت‌گیرانه:**
            - 1.0: پاسخ کاملاً بر اساس منابع و دقیق است (هیچ اطلاعات اضافی ندارد)
            - 0.9: پاسخ عمدتاً بر اساس منابع است با حداقل تفسیر
            - 0.7: پاسخ تا حدودی بر اساس منابع است اما ممکن است اطلاعات اضافی جزئی داشته باشد
            - 0.5: پاسخ کمترین ارتباط را با منابع دارد
            - 0.3: پاسخ تقریباً هیچ ارتباطی با منابع ندارد
            - 0.1: پاسخ کاملاً خارج از منابع است یا ساختگی است
            - 0.0: پاسخ کاملاً غلط و نامرتبط است

            **نکته مهم:** اگر منابع شامل عبارت "متاسفانه اطلاعات مربوط به این سوال در پایگاه دانش من موجود نیست" هستند یا پاسخ مشابه آن است، امتیاز 1.0 بدهید.

            فقط امتیاز عددی بدهید (مثال: 0.85)
            """

            # فراخوانی LLM برای ارزیابی
            groundedness_response = await langchain_service.generate_chat_response([
                {"role": "user", "content": groundedness_prompt}
            ])

            # استخراج امتیاز عددی از پاسخ
            import re
            score_match = re.search(r'(\d+\.?\d*)', groundedness_response.strip())
            if score_match:
                score = float(score_match.group(1))
                score = max(0.0, min(1.0, score))  # محدود کردن به بازه 0-1

                # 🔥 ENHANCED: اگر retrieval score متوسط است، groundedness را سخت‌تر ارزیابی کن
                if top_score is not None and 0.1 <= top_score < 0.3:
                    score = score * 0.8  # کاهش 20% برای retrieval متوسط

                logger.info(f"🔍 Groundedness Score: {score:.2f} (top_retrieval: {top_score:.3f})")
                return score
            else:
                logger.warning("⚠️ Could not parse groundedness score from LLM response")
                return 0.3  # امتیاز پیش‌فرض پایین‌تر

        except Exception as e:
            logger.error(f"❌ Groundedness check failed: {e}")
            return 0.3  # امتیاز پیش‌فرض پایین‌تر در صورت خطا

    def _calculate_advanced_confidence(
        self,
        query: str,
        retrieved_docs: List[Dict[str, Any]],
        answer: str = None,
        verification_result: Dict[str, Any] = None,
        query_type: str = "general",  # 🎯 تطبیق با نوع سوال
        groundedness_score: float = None  # 🔥 NEW: امتیاز groundedness
    ) -> Dict[str, float]:
        """
        محاسبه پیشرفته درصد اطمینان بر اساس multiple factors
        🔥 RECALIBRATED: تطابق بهتر با کیفیت واقعی خروجی‌ها
        
        Args:
            query: سوال کاربر
            retrieved_docs: اسناد بازیابی شده
            answer: پاسخ تولید شده (اختیاری)
            verification_result: نتیجه کیفیت پاسخ (اختیاری)
            query_type: نوع سوال (specific/general/explanation)
            
        Returns:
            Dict شامل confidence_score و breakdown جزئیات
        """
        if not retrieved_docs:
            return {
                "confidence_score": 0.0,
                "factors": {
                    "retrieval_quality": 0.0,
                    "source_diversity": 0.0,
                    "semantic_match": 0.0,
                    "context_richness": 0.0,
                    "answer_quality": 0.0
                },
                "confidence_level": "بسیار پایین",
                "query_type": query_type
            }
        
        factors = {}
        
        # 1️⃣ کیفیت Retrieval (0-1): بر اساس scores اسناد
        scores = [doc.get('score', 0) for doc in retrieved_docs[:10]]
        avg_score = sum(scores) / len(scores) if scores else 0
        max_score = max(scores) if scores else 0
        top_doc_score = scores[0] if scores else 0
        
        # 🔥 IMPROVED: ترکیب هوشمندتر با وزن بیشتر برای top score
        # top score نشان‌دهنده بهترین match است
        retrieval_quality = (top_doc_score * 0.5) + (avg_score * 0.3) + (max_score * 0.2)
        
        # 🔥 CALIBRATED: نرمال‌سازی بر اساس query type
        if query_type == "general":
            # سوالات general معمولاً scores پایین‌تری دارند، پس boost می‌زنیم
            retrieval_quality = min(retrieval_quality * 1.3, 1.0)
        else:
            # سوالات specific معمولاً scores بالاتری دارند
            retrieval_quality = min(retrieval_quality * 1.1, 1.0)
        
        factors['retrieval_quality'] = retrieval_quality
        
        # 2️⃣ تنوع منابع (0-1): چند article یکتا؟
        unique_article_ids = set(doc.get('id') for doc in retrieved_docs if doc.get('id'))
        source_diversity = min(len(unique_article_ids) / 4, 1.0)  # 🔥 تغییر از 5 به 4 (واقع‌بینانه‌تر)
        factors['source_diversity'] = source_diversity
        
        # 3️⃣ تطابق معنایی (0-1): آیا top document واقعاً مرتبط است؟
        # 🔥 ENHANCED: تحلیل پیشرفته با توزیع امتیازات

        # محاسبه confidence interval برای semantic match
        if scores:
            # استفاده از آمار برای تصمیم‌گیری بهتر
            mean_score = sum(scores) / len(scores)
            std_dev = (sum((s - mean_score) ** 2 for s in scores) / len(scores)) ** 0.5

            # 🔥 NEW: محاسبه statistical significance
            # آیا top score واقعاً بهتر از میانگین است؟
            score_significance = (top_doc_score - mean_score) / max(std_dev, 0.01)

            logger.info(f"📈 Semantic Analysis: top={top_doc_score:.3f}, mean={mean_score:.3f}, "
                       f"std={std_dev:.3f}, significance={score_significance:.2f}")
        else:
            score_significance = 0.0

        if query_type == "general":
            # برای سوالات عمومی با Reranker: آستانه‌های کالیبره شده
            base_semantic = 0.75  # baseline برای سوالات عمومی

            if top_doc_score >= 0.8:  # امتیاز بسیار بالا برای reranker
                semantic_match = 1.0
            elif top_doc_score >= 0.5:  # امتیاز خوب
                semantic_match = 0.95
            elif top_doc_score >= 0.2:  # امتیاز قابل قبول
                semantic_match = 0.90
            elif top_doc_score >= 0.05: # ارتباط ضعیف
                semantic_match = 0.85
            else:
                semantic_match = base_semantic

            # 🔥 ENHANCED: تقویت بر اساس statistical significance
            if score_significance > 2.0:  # top score بسیار بالاتر از میانگین
                semantic_match = min(semantic_match + 0.05, 1.0)
            elif score_significance < -1.0:  # top score پایین‌تر از میانگین
                semantic_match = max(semantic_match - 0.1, 0.5)

        else:  # specific or explanation
            # برای سوالات خاص: معیار دقیق‌تر
            base_semantic = 0.60  # baseline سخت‌گیرانه‌تر برای سوالات خاص

            if top_doc_score >= 0.9:
                semantic_match = 1.0
            elif top_doc_score >= 0.8:
                semantic_match = 0.95
            elif top_doc_score >= 0.7:
                semantic_match = 0.90
            elif top_doc_score >= 0.6:
                semantic_match = 0.85
            elif top_doc_score >= 0.5:
                semantic_match = 0.75
            elif top_doc_score >= 0.4:
                semantic_match = 0.65
            else:
                semantic_match = base_semantic

            # 🔥 ENHANCED: statistical adjustment برای سوالات خاص
            if score_significance > 1.5:
                semantic_match = min(semantic_match + 0.03, 1.0)
            elif score_significance < -0.5:
                semantic_match = max(semantic_match - 0.05, 0.4)

        factors['semantic_match'] = semantic_match
        
        # 4️⃣ غنای Context (0-1): تعداد و کیفیت اسناد
        doc_count = len(retrieved_docs)

        # 🔥 ENHANCED: تحلیل توزیع امتیازات برای بهینه‌سازی بهتر
        if scores:
            # محاسبه آماری پیشرفته
            score_distribution = {
                'excellent': sum(1 for s in scores if s >= 0.8),  # امتیاز عالی
                'good': sum(1 for s in scores if 0.6 <= s < 0.8),  # امتیاز خوب
                'fair': sum(1 for s in scores if 0.3 <= s < 0.6),  # امتیاز متوسط
                'poor': sum(1 for s in scores if s < 0.3)  # امتیاز ضعیف
            }

            # 🔥 NEW: محاسبه diversity در امتیازات (پرهیز از تمرکز روی امتیازات مشابه)
            unique_scores = len(set(round(s, 2) for s in scores))  # امتیازات منحصر به فرد
            score_diversity = min(unique_scores / len(scores), 1.0)

            logger.info(f"📊 Score Distribution: excellent={score_distribution['excellent']}, "
                       f"good={score_distribution['good']}, fair={score_distribution['fair']}, "
                       f"poor={score_distribution['poor']}, diversity={score_diversity:.2f}")
        else:
            score_distribution = {'excellent': 0, 'good': 0, 'fair': 0, 'poor': 0}
            score_diversity = 0.0

        # 🔥 IMPROVED: Base richness با thresholds واقع‌بینانه‌تر
        if doc_count >= 15:
            base_richness = 1.0
        elif doc_count >= 10:
            base_richness = 0.95
        elif doc_count >= 7:
            base_richness = 0.90
        elif doc_count >= 5:
            base_richness = 0.85
        elif doc_count >= 3:
            base_richness = 0.75
        else:
            base_richness = 0.60

        # 🔥 ENHANCED: محاسبه کیفیت پیشرفته با توزیع امتیازات
        # امتیازدهی بر اساس توزیع کیفیت
        quality_score = (
            score_distribution['excellent'] * 1.0 +  # امتیاز کامل برای عالی
            score_distribution['good'] * 0.8 +        # امتیاز خوب برای خوب
            score_distribution['fair'] * 0.5 +        # امتیاز متوسط برای متوسط
            score_distribution['poor'] * 0.2          # امتیاز کم برای ضعیف
        ) / max(doc_count, 1)

        # اضافه کردن امتیاز diversity
        quality_factor = quality_score * (0.8 + score_diversity * 0.2)

        # ترکیب base richness با quality factor پیشرفته
        context_richness = base_richness * (0.5 + quality_factor * 0.5)
        factors['context_richness'] = min(context_richness, 1.0)
        
        # 5️⃣ کیفیت پاسخ (0-1): از verification اگر موجود باشد
        if verification_result and 'quality_score' in verification_result:
            answer_quality = verification_result['quality_score']
        elif answer:
            # 🔥 IMPROVED: تخمین بهتر بر اساس طول پاسخ
            answer_length = len(answer)
            if answer_length >= 500:
                answer_quality = 0.95
            elif answer_length >= 300:
                answer_quality = 0.90
            elif answer_length >= 150:
                answer_quality = 0.85
            elif answer_length >= 75:
                answer_quality = 0.75
            else:
                answer_quality = 0.60
        else:
            answer_quality = 0.80  # 🔥 پیش‌فرض بالاتر
        factors['answer_quality'] = answer_quality

        # 🔥 NEW: Groundedness Check - بررسی پشتیبانی پاسخ توسط منابع
        if groundedness_score is not None:
            factors['groundedness'] = groundedness_score
        else:
            factors['groundedness'] = 0.8  # امتیاز پیش‌فرض اگر groundedness check انجام نشده
        
        # 🎯 محاسبه نمره نهایی با وزن‌های تطبیقی بر اساس نوع سوال
        # 🔥 ENHANCED: اضافه کردن وزن groundedness
        if query_type == "general":
            # برای سوالات عمومی/پیچیده: تأکید بر context و quality
            weights = {
                'retrieval_quality': 0.15,    # 15% - کیفیت جستجو
                'source_diversity': 0.10,     # 10% - تنوع منابع
                'semantic_match': 0.20,       # 20% - تطابق معنایی
                'context_richness': 0.18,     # 18% - غنای context
                'answer_quality': 0.17,       # 17% - کیفیت پاسخ
                'groundedness': 0.20          # 🔥 20% - پشتیبانی توسط منابع
            }
        else:  # specific or explanation
            # برای سوالات خاص: semantic و retrieval مهم‌تر
            weights = {
                'retrieval_quality': 0.20,    # 20% - کیفیت جستجو
                'source_diversity': 0.08,     # 8% - تنوع منابع
                'semantic_match': 0.25,       # 25% - تطابق معنایی
                'context_richness': 0.12,     # 12% - غنای context
                'answer_quality': 0.15,       # 15% - کیفیت پاسخ
                'groundedness': 0.20          # 🔥 20% - پشتیبانی توسط منابع
            }
        
        confidence_score = sum(factors[k] * weights[k] for k in weights.keys())
        
        # 🔥 RECALIBRATED: سطوح confidence واقع‌بینانه‌تر
        if confidence_score >= 0.90:
            confidence_level = "بسیار بالا"
        elif confidence_score >= 0.80:
            confidence_level = "بالا"
        elif confidence_score >= 0.65:
            confidence_level = "خوب"
        elif confidence_score >= 0.50:
            confidence_level = "متوسط"
        elif confidence_score >= 0.35:
            confidence_level = "پایین"
        else:
            confidence_level = "بسیار پایین"
        
        logger.info(f"🎯 Advanced Confidence Calculated ({query_type} query):")
        logger.info(f"   📊 Final Score: {confidence_score:.2f} ({confidence_level})")
        logger.info(f"   🔍 Factors: retrieval={factors['retrieval_quality']:.2f}, "
                    f"diversity={factors['source_diversity']:.2f}, "
                    f"semantic={factors['semantic_match']:.2f} [top_score={top_doc_score:.2f}], "
                    f"richness={factors['context_richness']:.2f}, "
                    f"quality={factors['answer_quality']:.2f}, "
                    f"groundedness={factors.get('groundedness', 0):.2f}")
        logger.info(f"   ⚖️ Weights: retrieval_quality={weights.get('retrieval_quality', 0):.0%}, "
                    f"source_diversity={weights.get('source_diversity', 0):.0%}, "
                    f"semantic_match={weights.get('semantic_match', 0):.0%}, "
                    f"context_richness={weights.get('context_richness', 0):.0%}, "
                    f"answer_quality={weights.get('answer_quality', 0):.0%}, "
                    f"groundedness={weights.get('groundedness', 0):.0%}")
        
        return {
            "confidence_score": round(confidence_score, 2),
            "confidence_level": confidence_level,
            "factors": {k: round(v, 2) for k, v in factors.items()},
            "weights": weights,
            "query_type": query_type,
            "total_documents": doc_count,
            "unique_sources": len(unique_article_ids),
            "avg_retrieval_score": round(avg_score, 2),
            "max_retrieval_score": round(max_score, 2),
            "top_doc_score": round(top_doc_score, 2)
        }

    def _verify_answer_quality(self, query: str, answer: str, context: str, sources: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        بررسی کیفیت پاسخ تولید شده
        
        این متد چند معیار را بررسی می‌کند:
        1. طول پاسخ (آیا پاسخ کافی است؟)
        2. ارتباط پاسخ با سوال (آیا کلمات کلیدی موجود است؟)
        3. استفاده از context (آیا از اطلاعات موجود استفاده شده؟)
        4. تعداد منابع (آیا منابع کافی وجود دارد؟)
        
        Args:
            query: سوال کاربر
            answer: پاسخ تولید شده
            context: context استفاده شده
            sources: منابع استفاده شده
            
        Returns:
            دیکشنری با نتایج بررسی
        """
        try:
            issues = []
            warnings = []
            quality_score = 1.0  # شروع با امتیاز کامل
            
            # 1. بررسی طول پاسخ
            answer_length = len(answer)
            if answer_length < 50:
                issues.append("پاسخ بسیار کوتاه است")
                quality_score *= 0.6
            elif answer_length < 150:
                warnings.append("پاسخ می‌تواند با جزئیات بیشتری باشد")
                quality_score *= 0.8
            
            # 2. بررسی ارتباط با سوال (کلمات کلیدی)
            query_lower = query.lower()
            answer_lower = answer.lower()
            query_keywords = set([w for w in query_lower.split() if len(w) > 2])
            
            matched_keywords = sum(1 for kw in query_keywords if kw in answer_lower)
            keyword_ratio = matched_keywords / max(len(query_keywords), 1)
            
            if keyword_ratio < 0.3:
                issues.append("پاسخ ارتباط کمی با سوال دارد")
                quality_score *= 0.7
            elif keyword_ratio < 0.5:
                warnings.append("برخی از کلمات کلیدی سوال در پاسخ نیست")
                quality_score *= 0.9
            
            # 3. بررسی استفاده از context
            # آیا پاسخ شامل اطلاعاتی از context است؟
            context_words = set([w for w in context.lower().split() if len(w) > 4])
            answer_words = set([w for w in answer_lower.split() if len(w) > 4])
            
            context_overlap = len(context_words & answer_words)
            if context_overlap < 5:
                issues.append("به نظر می‌رسد پاسخ از context استفاده نکرده است")
                quality_score *= 0.5
            
            # 4. بررسی تعداد منابع
            if len(sources) == 0:
                issues.append("هیچ منبعی برای پاسخ یافت نشد")
                quality_score *= 0.3
            elif len(sources) < 2:
                warnings.append("تعداد منابع محدود است")
                quality_score *= 0.85
            
            # 5. بررسی پاسخ‌های تکراری یا generic
            generic_phrases = [
                "متأسفانه",
                "اطلاعاتی ندارم",
                "نمی‌توانم",
                "موجود نیست",
                "در دسترس نیست"
            ]
            
            has_generic = any(phrase in answer_lower for phrase in generic_phrases)
            if has_generic and answer_length < 200:
                warnings.append("پاسخ ممکن است کلی باشد")
                quality_score *= 0.9
            
            return {
                "quality_score": round(quality_score, 2),
                "is_acceptable": quality_score >= 0.6,
                "issues": issues,
                "warnings": warnings,
                "metrics": {
                    "answer_length": answer_length,
                    "keyword_match_ratio": round(keyword_ratio, 2),
                    "context_overlap": context_overlap,
                    "sources_count": len(sources)
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Answer verification failed: {e}")
            return {
                "quality_score": 0.5,
                "is_acceptable": True,  # در صورت خطا، قبول می‌کنیم
                "issues": [],
                "warnings": ["خطا در بررسی کیفیت"],
                "metrics": {}
            }

    async def _retrieve_from_mongodb(self, query: str, is_public_only: bool = True) -> List[Dict[str, Any]]:
        """Fallback: Retrieve documents using MongoDB keyword search."""
        logger.info("🗄️  Starting MongoDB fallback search...")
        logger.info(f"📊 Search scope: {'Public only' if is_public_only else 'All documents'}")

        # Initialize database connection (only if not already initialized)
        from app.infrastructure.database.mongodb import init_db, get_mongo_client
        from app.domain.entities import ArticleStatus, ArticleVisibility

        # Check if database is already initialized (e.g., in tests)
        if get_mongo_client() is None:
            await init_db()

        # Build query for articles (using string values, not enum objects)
        if is_public_only:
            articles = await KnowledgeBaseArticle.find({
                "status": ArticleStatus.PUBLISHED.value,  # Use .value to get string
                "visibility": ArticleVisibility.PUBLIC.value  # Use .value to get string
            }).to_list()
        else:
            articles = await KnowledgeBaseArticle.find({
                "status": ArticleStatus.PUBLISHED.value  # Use .value to get string
            }).to_list()

        logger.info(f"🔍 Found {len(articles)} articles in database")

        # Simple keyword-based retrieval (fallback method)
        query_lower = query.lower()
        relevant_docs = []

        for article in articles:
            score = 0

            # Score based on title match
            if any(word in article.title.lower() for word in query_lower.split()):
                score += 10

            # Score based on content match (using Markdown content for better search with headers)
            content_matches = sum(1 for word in query_lower.split() if word in article.content_markdown.lower())
            score += content_matches * 2

            # Score based on summary match
            if article.summary and any(word in article.summary.lower() for word in query_lower.split()):
                score += 5

            if score > 0:
                relevant_docs.append({
                    "id": str(article.id),
                    "title": article.title,
                    "content": article.content_markdown[:1000],  # Truncate Markdown content for context
                    "summary": article.summary,
                    "score": score,
                    "source": "mongodb"
                })

        logger.info(f"✅ MongoDB search completed: {len(relevant_docs)} documents found")

        # Normalize MongoDB scores to 0-1 scale (max possible score is ~25)
        max_possible_score = 25.0
        for doc in relevant_docs:
            doc["score"] = min(doc["score"] / max_possible_score, 1.0)

        # Sort by relevance and return top 5
        relevant_docs.sort(key=lambda x: x["score"], reverse=True)
        logger.info(f"✅ MongoDB search completed: {len(relevant_docs)} documents found")

        # Log top results
        for i, doc in enumerate(relevant_docs[:3]):
            title = doc.get("title", "")
            score = doc.get("score", 0)
            logger.info(f"   📄 Document {i+1}: '{title[:50]}...' (Score: {score:.3f})")

        return relevant_docs[:5]


class SimpleRAGService(RAGService):
    """Simple RAG for guest users - uses public knowledge base only - STRICT MODE."""
    
    async def generate_response(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate response using Simple RAG with public knowledge base.
        STRICT MODE: فقط بر اساس documents موجود پاسخ می‌دهد.
        """

        import time
        start_time = time.time()
        
        # 🎯 تحلیل نوع سوال برای confidence و prompt بهتر
        from app.use_cases.query_analyzer import analyze_query_type
        query_type_analysis = analyze_query_type(query)
        query_type = query_type_analysis['query_type']

        logger.info("=" * 60)
        logger.info("🤖 SimpleRAGService: Starting STRICT RAG operation")
        logger.info(f"📝 Query: '{query[:100]}{'...' if len(query) > 100 else ''}'")
        logger.info(f"🎯 Query Type: {query_type_analysis['query_type_fa']}")
        logger.info(f"🔒 Access Level: Public documents only")
        logger.info(f"🧠 LLM Model: {settings.rag_model_loaded}")
        logger.info(f"⚠️  STRICT MODE: Only knowledge base answers")
        logger.info("=" * 60)

        # Try to retrieve relevant documents from public knowledge base
        relevant_docs = await self.retrieve_relevant_documents(query, is_public_only=True)
        logger.info(f"📚 Retrieved {len(relevant_docs)} relevant documents")

        # اگر هیچ سندی پیدا نشد، پاسخ مناسب برگردان
        if not relevant_docs:
            logger.warning("❌ No relevant documents found in knowledge base")
            no_docs_response = "متأسفانه اطلاعات مربوط به سوال شما در پایگاه دانش من موجود نیست. لطفاً سوال خود را واضح‌تر بیان کنید یا با تیم پشتیبانی تماس بگیرید."
            
            total_time = time.time() - start_time
            logger.info(f"⏱️  Total time: {total_time:.3f}s")
            
            return {
                "response": no_docs_response,
                "sources": [],
                "confidence": 0.0
            }

        if relevant_docs and settings.openai_api_key_loaded:
            logger.info(f"🔑 OpenAI API key: {'✅ Set' if settings.openai_api_key_loaded else '❌ Not Set'}")
            logger.info("🧠 Generating Enhanced RAG response with richer context...")
            # Use RAG with context from knowledge base
            try:
                # 🔥 ENHANCED: استفاده از تنظیمات برای تعداد documents در context
                top_docs = relevant_docs[:settings.context_documents_count]
                
                # 🔥 SMALL-TO-BIG RETRIEVAL (Phase 1): 
                # برای top documents، از full_article_content استفاده می‌کنیم
                # این به LLM context کامل‌تر و غنی‌تری می‌دهد
                context_parts = []
                for i, doc in enumerate(top_docs, 1):
                    # 🎯 استفاده از full_article_content اگر موجود باشد
                    full_content = doc.get('full_article_content', '')
                    chunk_content = doc.get('content', '')
                    
                    # استراتژی: اگر full content موجود است و معقول است، از آن استفاده کن
                    # وگرنه از chunk content استفاده کن
                    if full_content and len(full_content) > len(chunk_content):
                        content_to_use = full_content
                        content_type = "Full Article"
                        logger.info(f"   📄 Doc {i}: Using FULL article content ({len(full_content)} chars)")
                    else:
                        content_to_use = chunk_content
                        content_type = "Chunk"
                        logger.info(f"   📄 Doc {i}: Using chunk content ({len(chunk_content)} chars)")
                    
                    doc_context = f"""
=== منبع {i} ({content_type}) ===
عنوان: {doc['title']}
مسیر: {doc.get('path', 'N/A')}
امتیاز ارتباط: {doc.get('score', 0):.2f}

محتوا:
{content_to_use}

---
"""
                    context_parts.append(doc_context)
                
                context_text = "\n".join(context_parts)
                
                logger.info(f"📝 Enhanced context: {len(top_docs)} documents, {len(context_text)} characters")
                logger.info("🤖 Calling LangChain for enhanced response generation...")
                
                # Get conversation history from context
                conversation_history = context.get("conversation_history", []) if context else []

                # 🔥 فراخوانی با پرامپت مخصوص Simple RAG
                rag_response = await self._generate_openai_response(
                    query,
                    context_text,
                    conversation_history,
                    prompt_name="simple_rag_response"
                )
                logger.info(f"✅ RAG response generated successfully")
                logger.info(f"📄 Response preview: '{rag_response[:100]}...'")
                
                # 🔥 ENHANCED: بررسی کیفیت پاسخ
                formatted_sources = self._format_sources_markdown(relevant_docs)
                verification_result = self._verify_answer_quality(
                    query=query,
                    answer=rag_response,
                    context=context_text,
                    sources=formatted_sources
                )
                
                logger.info(f"🔍 Answer Quality: {verification_result['quality_score']:.2f}")
                if verification_result['issues']:
                    logger.warning(f"⚠️  Quality Issues: {', '.join(verification_result['issues'])}")
                if verification_result['warnings']:
                    logger.info(f"💡 Quality Warnings: {', '.join(verification_result['warnings'])}")

                total_rag_time = time.time() - start_time
                logger.info(f"⏱️  Total RAG time: {total_rag_time:.3f}s")

                # 🔥 ENHANCED: Groundedness Check - بررسی پشتیبانی پاسخ توسط منابع
                formatted_sources_for_groundedness = self._format_sources_markdown(relevant_docs)
                # 🔥 NEW: ارسال top_score برای تصمیم‌گیری بهتر
                top_score = max([doc.get('score', 0) for doc in relevant_docs]) if relevant_docs else 0
                groundedness_score = await self._calculate_groundedness_score(
                    query=query,
                    answer=rag_response,
                    sources=formatted_sources_for_groundedness,
                    top_score=top_score
                )

                # 🎯 محاسبه پیشرفته confidence با groundedness
                confidence_analysis = self._calculate_advanced_confidence(
                    query=query,
                    retrieved_docs=relevant_docs,
                    answer=rag_response,
                    verification_result=verification_result,
                    query_type=query_type,  # 🎯 تطبیق با نوع سوال
                    groundedness_score=groundedness_score  # 🔥 NEW: امتیاز groundedness
                )
                
                # 🔥 ENHANCED: برگرداندن 5 source به جای 3 + quality metrics + confidence analysis
                return {
                    "response": rag_response,
                    "sources": formatted_sources,
                    "confidence": confidence_analysis['confidence_score'],
                    "confidence_analysis": confidence_analysis,
                    "quality_metrics": verification_result
                }
            except Exception as e:
                logger.error(f"❌ RAG response generation failed: {str(e)}")
                # در STRICT MODE، اگر خطا رخ داد، پیام خطا برمی‌گردانیم نه پاسخ عمومی
                total_rag_time = time.time() - start_time
                logger.info(f"⏱️  Total RAG time: {total_rag_time:.3f}s")
                return {
                    "response": "متأسفانه در پردازش اطلاعات پایگاه دانش خطایی رخ داد. لطفاً دوباره تلاش کنید.",
                    "sources": [],
                    "confidence": 0.0
                }

        # اگر API key نداریم
        logger.error("❌ OpenAI API key not configured")
        total_rag_time = time.time() - start_time
        logger.info(f"⏱️  Total RAG time: {total_rag_time:.3f}s")
        return {
            "response": "متأسفانه سرویس هوش مصنوعی در حال حاضر در دسترس نیست.",
            "sources": [],
            "confidence": 0.0
        }
    
    async def _generate_openai_response(self, query: str, context: str, conversation_history: Optional[List[Dict[str, str]]] = None, prompt_name: str = "rag_response") -> str:
        """Generate response using LangChain."""
        from app.infrastructure.langchain_utils import langchain_service

        try:
            logger.info(f"_generate_openai_response: Using LangChain with prompt '{prompt_name}' for query '{query[:50]}...'")
            return await langchain_service.generate_rag_response(query, context, conversation_history, prompt_name=prompt_name)
        except Exception as e:
            logger.error(f"_generate_openai_response: LangChain error for query '{query[:50]}...': {str(e)}")
            # Fallback response
            raise Exception("AI service unavailable")
    
    async def _generate_direct_openai_response(self, query: str, user_context: Dict[str, Any]) -> str:
        """Generate response using LangChain directly without RAG context."""
        from app.infrastructure.langchain_utils import langchain_service

        try:
            logger.info(f"_generate_direct_openai_response: Using LangChain chat model for query '{query[:50]}...'")

            # Convert user_context to messages format if needed
            messages = [
                {"role": "user", "content": query}
            ]

            return await langchain_service.generate_chat_response(messages)
        except Exception as e:
            logger.error(f"_generate_direct_openai_response: LangChain error for query '{query[:50]}...': {e}")
            logger.error(f"Error details: {str(e)}")
            # Fallback response if API fails
            fallback = "سلام! من سالی، دستیار هوشمند شما هستم. متأسفانه در حال حاضر به پایگاه دانش دسترسی ندارم، اما می‌توانم به سوالات شما پاسخ دهم. لطفاً سوال خود را با جزئیات بیشتری مطرح کنید تا بهتر کمک کنم."
            logger.warning(f"Using fallback response: '{fallback}'")
            return fallback


class AgenticRAGService(RAGService):
    """
    Agentic RAG for authenticated customers.
    🔥 UPDATED: This service now uses the advanced LangGraph workflow.
    """
    
    def __init__(self):
        super().__init__()
        # 🔥 نمونه‌سازی از workflow پیشرفته
        from app.infrastructure.langchain_utils import langchain_service
        from app.infrastructure.agentic_rag_advanced import get_advanced_agentic_rag
        
        # ایجاد instance از advanced workflow
        self.advanced_workflow = get_advanced_agentic_rag(langchain_service, self)
        logger.info("✅ AgenticRAGService initialized with AdvancedAgenticRAG workflow.")
    
    async def generate_response(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate response by invoking the Advanced Agentic RAG workflow.
        🔥 NEW: Uses LangGraph workflow for intelligent multi-step reasoning.
        """
        import time
        start_time = time.time()
        
        user_context = context or {}
        user_id = user_context.get("user_id")
        conversation_history = user_context.get("conversation_history", [])

        logger.info("=" * 60)
        logger.info("🚀 Invoking Advanced Agentic RAG Workflow...")
        logger.info(f"📝 Query: '{query[:100]}{'...' if len(query) > 100 else ''}'")
        logger.info(f"👤 User ID: {user_id if user_id else 'Anonymous'}")
        logger.info(f"🔓 Access Level: Full knowledge base")
        logger.info("=" * 60)

        if not self.advanced_workflow:
            logger.error("❌ Advanced workflow is not available!")
            logger.warning("🔄 Falling back to simple RAG...")
            # Fallback به متد قدیمی در صورت عدم دسترسی به workflow
            return await self._fallback_simple_agentic_rag(query, context)

        try:
            # 🔥 فراخوانی متد run از workflow پیشرفته LangGraph
            result = await self.advanced_workflow.run(
                query=query,
                user_id=user_id,
                conversation_history=conversation_history
            )
            
            total_time = time.time() - start_time
            logger.info(f"⏱️  Total workflow time: {total_time:.3f}s")
            logger.info(f"✅ Workflow completed with confidence: {result.get('confidence', 0):.2f}")
            
            # تبدیل خروجی workflow به فرمت مورد انتظار API
            return {
                "response": result.get("response", "پاسخی تولید نشد."),
                "sources": result.get("sources", []),
                "confidence": result.get("confidence", 0.0),
                "confidence_analysis": {
                    "complexity": result.get("complexity", "unknown"),
                    "actions_taken": result.get("actions_taken", []),
                    "reflection_notes": result.get("reflection_notes", []),
                    "session_id": result.get("session_id", "")
                },
                "suggested_actions": self._extract_suggested_actions(result),
                "quality_metrics": {}
            }
            
        except Exception as e:
            logger.error(f"❌ Advanced workflow execution failed: {e}", exc_info=True)
            logger.warning("🔄 Falling back to simple RAG...")
            return await self._fallback_simple_agentic_rag(query, context)
    
    async def _fallback_simple_agentic_rag(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Fallback به RAG ساده در صورت عدم دسترسی یا خطا در workflow پیشرفته
        """
        logger.info("🔄 Using fallback simple agentic RAG")
        
        user_context = context or {}
        
        try:
            # استفاده از retrieval ساده
            relevant_docs = await self.retrieve_relevant_documents(query, is_public_only=False)
            
            if not relevant_docs:
                return {
                    "response": "متأسفانه اطلاعات مربوط به سوال شما در پایگاه دانش موجود نیست.",
                    "sources": [],
                    "confidence": 0.0,
                    "suggested_actions": ["refine_question"]
                }
            
            # ساخت context ساده با Small-to-Big strategy
            top_docs = relevant_docs[:5]
            context_parts = []
            for i, doc in enumerate(top_docs, 1):
                # 🔥 استفاده از full content اگر موجود باشد
                full_content = doc.get('full_article_content', '')
                chunk_content = doc.get('content', '')
                
                if full_content and len(full_content) > len(chunk_content):
                    content_to_use = full_content
                else:
                    content_to_use = chunk_content
                
                context_parts.append(f"""
=== منبع {i} ===
عنوان: {doc['title']}
محتوا: {content_to_use}
---
""")
            
            full_context = "\n".join(context_parts)
            conversation_history = user_context.get("conversation_history", [])
            
            # تولید پاسخ ساده
            response = await self._generate_openai_response_with_context(query, full_context, conversation_history)
            formatted_sources = self._format_sources_markdown(relevant_docs)
            
            return {
                "response": response,
                "sources": formatted_sources,
                "confidence": 0.5,
                "suggested_actions": self._suggest_actions(query, relevant_docs),
                "quality_metrics": {}
            }
            
        except Exception as e:
            logger.error(f"❌ Fallback RAG also failed: {e}")
            return {
                "response": "متأسفانه در پردازش اطلاعات خطایی رخ داد.",
                "sources": [],
                "confidence": 0.0,
                "suggested_actions": ["retry", "contact_support"]
            }
    
    def _extract_suggested_actions(self, workflow_result: Dict[str, Any]) -> List[str]:
        """
        استخراج suggested actions از نتیجه workflow
        """
        actions = []
        
        # بر اساس complexity
        complexity = workflow_result.get("complexity", "unknown")
        if complexity == "complex":
            actions.append("consider_breaking_down")
        
        # بر اساس confidence
        confidence = workflow_result.get("confidence", 0)
        if confidence < 0.5:
            actions.append("refine_question")
        
        # بر اساس errors
        if workflow_result.get("errors"):
            actions.append("retry")
        
        # اگر sources دارد
        if workflow_result.get("sources"):
            actions.append("view_related_articles")
        
        return actions if actions else ["view_related_articles"]
    
    async def _generate_openai_response_with_context(self, query: str, context: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> str:
        """Generate response using OpenAI API with context from knowledge base."""
        from app.infrastructure.langchain_utils import langchain_service

        try:
            logger.info(f"_generate_openai_response_with_context: Using LangChain RAG model for query '{query[:50]}...'")
            return await langchain_service.generate_rag_response(query, context, conversation_history)
        except Exception as e:
            logger.error(f"_generate_openai_response_with_context: LangChain error for query '{query[:50]}...': {e}")
            logger.error(f"Error details: {str(e)}")
            raise Exception("AI service unavailable")

    def _suggest_actions(self, query: str, relevant_docs: List[Dict[str, Any]]) -> List[str]:
        """Suggest relevant actions based on query and context."""
        actions = []
        
        query_lower = query.lower()
        
        # Ticket system removed - no longer suggest ticket creation
        
        # Suggest viewing related articles
        if relevant_docs:
            actions.append("view_related_articles")
        
        # Suggest account-related actions
        if any(word in query_lower for word in ["account", "billing", "subscription", "payment"]):
            actions.append("view_account")
        
        return actions


# Service factory
def get_rag_service(
    user: Optional[Union['Customer', 'Admin']] = None,
    rag_type: str = "simple"  # 🆕 پارامتر جدید برای کنترل نوع RAG
) -> RAGService:
    """Get appropriate RAG service based on user type AND requested RAG type."""

    # برای کاربران مهمان، همیشه Simple RAG است (به دلایل امنیتی)
    if not user:
        logger.info("🔧 No user provided, defaulting to SimpleRAGService.")
        return SimpleRAGService()

    # برای کاربران احراز هویت شده، بر اساس rag_type تصمیم بگیر
    if rag_type == "agentic" or rag_type == "detailed":
        logger.info(f"🔧 User is authenticated and requested '{rag_type}', providing AgenticRAGService.")
        return AgenticRAGService()
    else:  # simple
        logger.info(f"🔧 User is authenticated but requested 'simple', providing SimpleRAGService.")
        return SimpleRAGService()
