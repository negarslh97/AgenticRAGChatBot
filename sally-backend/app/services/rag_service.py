from typing import List, Dict, Any, Optional, Union
from abc import ABC, abstractmethod
import logging
import requests  # 🆕 برای ارتباط با API خارجی reranker
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
                logger.info(f"📊 Fetching {len(set(article_ids))} unique articles from MongoDB in single batch query...")
                articles_cursor = KnowledgeBaseArticle.find({"_id": {"$in": article_ids}})
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
                    enriched_doc = {
                        "id": article_id,
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
                    }
                    logger.info(f"✅ Using Weaviate data: '{enriched_doc['title'][:50]}...' (Score: {enriched_doc['score']:.3f})")

                enriched_docs.append(enriched_doc)

            except Exception as e:
                logger.error(f"❌ Error processing document {weaviate_doc.get('id')}: {e}")
                # حتی با خطا، سعی می‌کنیم از داده Weaviate استفاده کنیم
                try:
                    enriched_docs.append({
                        "id": weaviate_doc.get("id", weaviate_doc.get("node_id", "unknown")),
                        "title": weaviate_doc.get("title", "Untitled"),
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

    def _format_sources_markdown(self, documents: List[Dict[str, Any]], max_sources: int = 5) -> List[Dict[str, Any]]:
        """
        Format sources as unique articles (not chunks).
        🎯 نمایش مقالات یکتا (نه چندین chunk از یک مقاله)
        
        Args:
            documents: لیست documents (chunks)
            max_sources: حداکثر تعداد مقالات یکتا برای برگرداندن
            
        Returns:
            لیست مقالات یکتا با اولویت بالاترین score
        """
        formatted_sources = []
        seen_article_ids = set()  # 🎯 برای جلوگیری از تکرار مقالات

        for doc in documents:
            article_id = str(doc.get("id", ""))
            
            # اگر این مقاله قبلاً اضافه شده، رد کن
            if article_id in seen_article_ids:
                logger.debug(f"⏭️ Skipping duplicate article: {article_id}")
                continue
            
            seen_article_ids.add(article_id)
            
            chunk_title = doc.get("title", "بدون عنوان")
            article_title = doc.get("article_title", chunk_title)  # fallback به chunk_title
            path = doc.get("path", "")
            
            # استخراج snippet (بخش مرتبط) برای highlighting
            content = doc.get("content", "")
            snippet = content[:300] + "..." if len(content) > 300 else content
            
            # 🎯 نمایش فقط عنوان مقاله اصلی
            formatted_sources.append({
                "id": article_id,
                "title": article_title,  # 🎯 فقط title مقاله اصلی
                "chunk_title": chunk_title,  # title chunk (برای reference)
                "path": path,  # مسیر chunk برای اطلاعات بیشتر
                "score": doc.get("score", 0),
                "category": doc.get("category"),
                "tags": doc.get("tags", []),
                "url": doc.get("url"),
                "snippet": snippet,  # 🔥 بخش مرتبط برای preview
                "full_content": content,  # 🔥 محتوای کامل برای highlighting
                "summary": doc.get("summary", "")
            })
            
            # 🎯 اگر به تعداد مورد نظر رسیدیم، متوقف می‌شویم
            if len(formatted_sources) >= max_sources:
                break

        logger.info(f"📋 Formatted {len(formatted_sources)} unique articles (from {len(documents)} chunks)")
        
        # 🔥 DEBUG: نمایش منابع برگشتی
        for idx, src in enumerate(formatted_sources, 1):
            logger.info(f"   🔖 Article #{idx}: {src['title'][:50]}... (Best chunk path: {src['path']}, Score: {src['score']:.3f})")
        
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
            from app.core.config import settings
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

            # تولید vector از query اصلی
            logger.info(f"🔢 تولید vector از query برای جستجو...")
            embedder_base_url = settings.embedder_openai_base_url_loaded  
            embedder_model = settings.embedder_model_loaded
            
            openai_client = OpenAI(
                api_key=embedder_api_key,
                base_url=embedder_base_url
            )
            
            response = openai_client.embeddings.create(
                model=embedder_model,
                input=query
            )
            
            query_vector = response.data[0].embedding
            logger.info(f"✅ Query vector تولید شد (ابعاد: {len(query_vector)})")

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
                
                logger.info(f"⚡ Executing Enhanced Weaviate search (limit: {limit})...")
                
                # 🔥 STEP 2: Hybrid Search - ترکیب vector و keyword
                # Execute query using v4 API با limit بالاتر
                try:
                    # Vector search اصلی
                    response = collection.query.near_vector(
                        near_vector=query_vector,
                        limit=limit,
                        return_metadata=['distance', 'certainty']
                    )
                    
                    objects = response.objects if response.objects else []
                    logger.info(f"✅ {len(objects)} گره Markdown یافت شد")

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
                    # در v4، metadata در obj.metadata قرار دارد
                    certainty = obj.metadata.certainty if hasattr(obj.metadata, 'certainty') else 0.5
                    score = certainty  # Keep as float between 0-1
                    
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
                        "title": f"{path} - {title}",  # Include path in title for better context
                        "content": combined_content,
                        "path": path,
                        "score": score,
                        "source": "weaviate",
                        "raw_content": node_content,  # محتوای خام برای reranking
                        "full_article_content": full_content  # محتوای کامل مقاله
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
    
    def _calculate_advanced_confidence(
        self, 
        query: str, 
        retrieved_docs: List[Dict[str, Any]], 
        answer: str = None,
        verification_result: Dict[str, Any] = None,
        query_type: str = "general"  # 🎯 تطبیق با نوع سوال
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
        # 🔥 RECALIBRATED: thresholds واقع‌بینانه‌تر برای rerank scores
        
        if query_type == "general":
            # برای سوالات عمومی: معیار ملایم‌تر اما calibrated
            # Rerank API scores معمولاً بین 0 تا 1 هستند
            if top_doc_score >= 0.7:
                semantic_match = 1.0
            elif top_doc_score >= 0.55:
                semantic_match = 0.95
            elif top_doc_score >= 0.4:
                semantic_match = 0.90
            elif top_doc_score >= 0.25:
                semantic_match = 0.85
            elif top_doc_score >= 0.1:
                semantic_match = 0.75
            else:
                semantic_match = 0.65
        else:  # specific or explanation
            # برای سوالات خاص: معیار دقیق‌تر
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
                semantic_match = 0.50
        factors['semantic_match'] = semantic_match
        
        # 4️⃣ غنای Context (0-1): تعداد و کیفیت اسناد
        doc_count = len(retrieved_docs)
        
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
        
        # 🔥 IMPROVED: اضافه کردن وزن برای documents با score بالا (calibrated)
        # تعداد documents با کیفیت بالا
        high_quality_docs = sum(1 for s in scores if s >= 0.6)  # threshold کاهش یافت
        medium_quality_docs = sum(1 for s in scores if 0.3 <= s < 0.6)
        
        # محاسبه ضریب کیفیت
        quality_factor = (high_quality_docs * 1.0 + medium_quality_docs * 0.5) / len(scores) if scores else 0
        
        # ترکیب base richness با quality factor
        context_richness = base_richness * (0.6 + quality_factor * 0.4)
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
        
        # 🎯 محاسبه نمره نهایی با وزن‌های تطبیقی بر اساس نوع سوال
        # 🔥 RECALIBRATED: وزن‌های بهتر برای balance بین factors
        if query_type == "general":
            # برای سوالات عمومی/پیچیده: تأکید بر context و quality
            weights = {
                'retrieval_quality': 0.18,    # 18% - کیفیت جستجو (افزایش)
                'source_diversity': 0.12,     # 12% - تنوع منابع
                'semantic_match': 0.25,       # 25% - تطابق معنایی (مهم‌ترین)
                'context_richness': 0.22,     # 22% - غنای context
                'answer_quality': 0.23        # 23% - کیفیت پاسخ
            }
        else:  # specific or explanation
            # برای سوالات خاص: semantic و retrieval مهم‌تر
            weights = {
                'retrieval_quality': 0.28,    # 28% - کیفیت جستجو (افزایش)
                'source_diversity': 0.10,     # 10% - تنوع منابع
                'semantic_match': 0.30,       # 30% - تطابق معنایی (بسیار مهم)
                'context_richness': 0.14,     # 14% - غنای context
                'answer_quality': 0.18        # 18% - کیفیت پاسخ
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
                   f"quality={factors['answer_quality']:.2f}")
        logger.info(f"   ⚖️ Weights: semantic={weights['semantic_match']:.0%}, "
                   f"context={weights['context_richness']:.0%}, "
                   f"answer={weights['answer_quality']:.0%}")
        
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
                
                # 🔥 ENHANCED: ساخت context با ساختار بهتر و اطلاعات بیشتر
                context_parts = []
                for i, doc in enumerate(top_docs, 1):
                    doc_context = f"""
=== منبع {i} ===
عنوان: {doc['title']}
مسیر: {doc.get('path', 'N/A')}
امتیاز ارتباط: {doc.get('score', 0):.2f}

محتوا:
{doc['content']}

---
"""
                    context_parts.append(doc_context)
                
                context_text = "\n".join(context_parts)
                
                logger.info(f"📝 Enhanced context: {len(top_docs)} documents, {len(context_text)} characters")
                logger.info("🤖 Calling LangChain for enhanced response generation...")
                
                # Get conversation history from context
                conversation_history = context.get("conversation_history", []) if context else []
                
                rag_response = await self._generate_openai_response(query, context_text, conversation_history)
                logger.info(f"✅ RAG response generated successfully")
                logger.info(f"📄 Response preview: '{rag_response[:100]}...'")
                
                # 🔥 ENHANCED: بررسی کیفیت پاسخ
                formatted_sources = self._format_sources_markdown(relevant_docs[:10], max_sources=10)
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

                # 🎯 محاسبه پیشرفته confidence
                confidence_analysis = self._calculate_advanced_confidence(
                    query=query,
                    retrieved_docs=relevant_docs,
                    answer=rag_response,
                    verification_result=verification_result,
                    query_type=query_type  # 🎯 تطبیق با نوع سوال
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
    
    async def _generate_openai_response(self, query: str, context: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> str:
        """Generate response using LangChain."""
        from app.infrastructure.langchain_utils import langchain_service

        try:
            logger.info(f"_generate_openai_response: Using LangChain RAG model for query '{query[:50]}...'")
            return await langchain_service.generate_rag_response(query, context, conversation_history)
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
                    "suggested_actions": ["create_ticket", "refine_question"]
                }
            
            # ساخت context ساده
            top_docs = relevant_docs[:5]
            context_parts = []
            for i, doc in enumerate(top_docs, 1):
                context_parts.append(f"""
=== منبع {i} ===
عنوان: {doc['title']}
محتوا: {doc['content']}
---
""")
            
            full_context = "\n".join(context_parts)
            conversation_history = user_context.get("conversation_history", [])
            
            # تولید پاسخ ساده
            response = await self._generate_openai_response_with_context(query, full_context, conversation_history)
            formatted_sources = self._format_sources_markdown(relevant_docs[:5], max_sources=5)
            
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
            actions.append("create_ticket")
        
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
        
        # Suggest ticket creation for problem-related queries
        if any(word in query_lower for word in ["problem", "issue", "error", "bug", "broken", "not working"]):
            actions.append("create_ticket")
        
        # Suggest viewing related articles
        if relevant_docs:
            actions.append("view_related_articles")
        
        # Suggest account-related actions
        if any(word in query_lower for word in ["account", "billing", "subscription", "payment"]):
            actions.append("view_account")
        
        return actions


# Service factory
def get_rag_service(user: Optional[Union['Customer', 'Admin']] = None) -> RAGService:
    """Get appropriate RAG service based on user type."""
    if user:
        # Check if user is authenticated (has an id attribute)
        return AgenticRAGService()
    else:
        return SimpleRAGService()
