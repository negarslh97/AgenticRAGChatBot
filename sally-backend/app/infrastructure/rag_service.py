from typing import List, Dict, Any, Optional, Union
from abc import ABC, abstractmethod
import logging
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
        """
        logger.info("🗄️ Enriching Weaviate results with MongoDB metadata...")

        # Initialize database connection
        from app.infrastructure.database.mongodb import init_db, get_mongo_client
        from app.domain.entities import KnowledgeBaseArticle, ArticleStatus, ArticleVisibility

        if get_mongo_client() is None:
            await init_db()

        enriched_docs = []

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

                # Try to fetch full article from MongoDB
                article = None
                try:
                    article = await KnowledgeBaseArticle.get(article_id)
                except Exception as e:
                    logger.debug(f"Could not fetch article {article_id} from MongoDB: {e}")

                if article:
                    # Apply visibility filter if needed
                    if is_public_only and article.visibility != ArticleVisibility.PUBLIC:
                        logger.info(f"🔒 Skipping non-public article: {article_id}")
                        continue

                    # Create enriched document with MongoDB metadata
                    enriched_doc = {
                        "id": str(article.id),
                        "title": article.title,
                        "content": article.content_markdown[:1000],  # Use Markdown content
                        "summary": article.summary,
                        "score": weaviate_doc.get("score", 0.5),
                        "source": "hybrid",
                        "path": weaviate_doc.get("path", ""),
                        "node_id": weaviate_doc.get("node_id", ""),
                        "url": getattr(article, 'url', None),
                        "tags": [tag.name for tag in getattr(article, 'tags', [])] if hasattr(article, 'tags') else [],
                        "category": getattr(article, 'category', {}).name if hasattr(article, 'category') and article.category else None
                    }
                    logger.info(f"✅ Enriched with MongoDB: '{article.title[:50]}...' (Score: {enriched_doc['score']:.3f})")
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

    def _format_sources_markdown(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format sources with rich metadata and relevant snippets for highlighting."""
        formatted_sources = []
        seen_ids = set()  # برای جلوگیری از تکرار منابع

        for i, doc in enumerate(documents, 1):
            # چک کردن ID تکراری
            doc_id = str(doc.get("id", ""))
            if doc_id in seen_ids:
                logger.debug(f"⏭️ Skipping duplicate source: {doc_id}")
                continue
            
            seen_ids.add(doc_id)
            
            # استخراج snippet (بخش مرتبط) برای highlighting
            content = doc.get("content", "")
            snippet = content[:300] + "..." if len(content) > 300 else content
            
            # Create source with snippet for highlighting
            formatted_sources.append({
                "id": doc_id,
                "title": doc.get("title", "بدون عنوان"),
                "score": doc.get("score", 0),
                "category": doc.get("category"),
                "tags": doc.get("tags", []),
                "url": doc.get("url"),
                "snippet": snippet,  # 🔥 بخش مرتبط برای preview
                "full_content": content,  # 🔥 محتوای کامل برای highlighting
                "path": doc.get("path", ""),
                "summary": doc.get("summary", "")
            })

        logger.info(f"📋 Formatted {len(formatted_sources)} unique sources with snippets")
        
        # 🔥 DEBUG: نمایش منابع برگشتی
        for src in formatted_sources:
            logger.info(f"   🔖 Source: ID={src['id']}, Title={src['title'][:50]}...")
        
        return formatted_sources

    async def _retrieve_from_weaviate(self, query: str, is_public_only: bool = True) -> List[Dict[str, Any]]:
        """Retrieve documents using Weaviate vector search with Client-Side Vectorization."""
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

            # تولید vector از query
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
                
                logger.info("⚡ Executing Weaviate vector search...")
                
                # Execute query using v4 API
                try:
                    response = collection.query.near_vector(
                        near_vector=query_vector,
                        limit=10,
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
                for i, obj in enumerate(objects):
                    # در v4، metadata در obj.metadata قرار دارد
                    certainty = obj.metadata.certainty if hasattr(obj.metadata, 'certainty') else 0.5
                    score = certainty  # Keep as float between 0-1
                    
                    # در v4، properties در obj.properties قرار دارند
                    title = obj.properties.get("title", "")
                    node_id = obj.properties.get("node_id", "")
                    article_id = obj.properties.get("article_id", "")
                    path = obj.properties.get("path", "")

                    logger.info(f"   📄 Node {i+1}: '{title[:30]}...' (Path: {path}, Score: {score:.3f})")

                    # Combine title and content for better context
                    full_content = obj.properties.get("full_content", "")[:1000]
                    node_content = obj.properties.get("content", "")

                    # Create a more informative content by combining path, title and content
                    combined_content = f"Path: {path}\nTitle: {title}\nContent: {node_content}"
                    if full_content:
                        combined_content += f"\n\nFull Article Context: {full_content[:500]}..."

                    relevant_docs.append({
                        "id": article_id,
                        "node_id": node_id,
                        "title": f"{path} - {title}",  # Include path in title for better context
                        "content": combined_content,
                        "path": path,
                        "score": score,
                        "source": "weaviate"
                    })

                logger.info(f"✅ Weaviate search completed: {len(relevant_docs)} documents found")
                logger.info(f"🎯 Query: '{query[:50]}{'...' if len(query) > 50 else ''}'")
                
                return relevant_docs
            # client به صورت خودکار بسته می‌شود توسط context manager

        except Exception as e:
            logger.error(f"Weaviate search error: {e}")
            raise e

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

        logger.info("=" * 60)
        logger.info("🤖 SimpleRAGService: Starting STRICT RAG operation")
        logger.info(f"📝 Query: '{query[:100]}{'...' if len(query) > 100 else ''}'")
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
            logger.info("🧠 Generating RAG response with knowledge base context...")
            # Use RAG with context from knowledge base
            try:
                context_text = "\n\n".join([
                    f"Document: {doc['title']}\nContent: {doc['content']}"
                    for doc in relevant_docs[:3]
                ])
                
                logger.info(f"📝 Context length: {len(context_text)} characters")
                logger.info("🤖 Calling LangChain for response generation...")
                
                # Get conversation history from context
                conversation_history = context.get("conversation_history", []) if context else []
                
                rag_response = await self._generate_openai_response(query, context_text, conversation_history)
                logger.info(f"✅ RAG response generated successfully")
                logger.info(f"📄 Response preview: '{rag_response[:100]}...'")

                total_rag_time = time.time() - start_time
                logger.info(f"⏱️  Total RAG time: {total_rag_time:.3f}s")

                return {
                    "response": rag_response,
                    "sources": self._format_sources_markdown(relevant_docs[:3]),
                    "confidence": 0.9
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
    """Agentic RAG for authenticated customers - STRICT MODE - uses full knowledge base only."""
    
    async def generate_response(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate response using RAG for authenticated customers.
        STRICT MODE: فقط بر اساس documents موجود پاسخ می‌دهد.
        """

        import time
        start_time = time.time()

        user_context = context or {}
        user_id = user_context.get("user_id")

        logger.info("=" * 60)
        logger.info("🧠 AgenticRAGService: Starting STRICT advanced RAG operation")
        logger.info(f"📝 Query: '{query[:100]}{'...' if len(query) > 100 else ''}'")
        logger.info(f"👤 User ID: {user_id if user_id else 'Anonymous'}")
        logger.info(f"🔓 Access Level: Full knowledge base")
        logger.info(f"🧠 LLM Model: {settings.rag_model_loaded}")
        logger.info(f"⚠️  STRICT MODE: Only knowledge base answers")
        logger.info("=" * 60)

        # Try to retrieve relevant documents from knowledge base
        relevant_docs = await self.retrieve_relevant_documents(query, is_public_only=False)
        logger.info(f"📚 Retrieved {len(relevant_docs)} relevant documents")
        
        # اگر هیچ سندی پیدا نشد، پاسخ مناسب برگردان
        if not relevant_docs:
            logger.warning("❌ No relevant documents found in knowledge base")
            no_docs_response = "متأسفانه اطلاعات مربوط به سوال شما در پایگاه دانش موجود نیست. لطفاً سوال خود را واضح‌تر بیان کنید یا تیکت پشتیبانی ایجاد کنید."
            
            total_time = time.time() - start_time
            logger.info(f"⏱️  Total time: {total_time:.3f}s")
            
            return {
                "response": no_docs_response,
                "sources": [],
                "confidence": 0.0,
                "suggested_actions": ["create_ticket", "refine_question"]
            }

        # Get user-specific context if available
        user_info = ""
        if user_id:
            logger.info(f"👤 Fetching user context for ID: {user_id}")
            # Try to get user from Customer entity first
            user = None

            try:
                user = await Customer.get(user_id)
                if user:
                    user_info = f"You are a customer: {user.full_name} ({user.email}). "
                    logger.info(f"✅ User context loaded: Customer - {user.full_name}")
                else:
                    user = await Admin.get(user_id)
                    if user:
                        user_info = f"You are an admin: {user.full_name} ({user.email}). "
                        logger.info(f"✅ User context loaded: Admin - {user.full_name}")
            except Exception as e:
                logger.error(f"❌ Error fetching user info for {user_id}: {e}")
                user_info = "User information not available. "
        else:
            logger.info("👤 No user ID provided - anonymous user")

        if relevant_docs:
            logger.info("🧠 Generating advanced RAG response with full context...")
            # Build context from retrieved documents
            context_text = user_info + "\n\n".join([
                f"Document: {doc['title']}\nContent: {doc['content']}"
                for doc in relevant_docs[:3]
            ])

            logger.info(f"📝 Full context length: {len(context_text)} characters")
            logger.info(f"👤 User context included: {'Yes' if user_info else 'No'}")

            # Generate response using OpenAI with context
            if settings.openai_api_key_loaded:
                try:
                    logger.info("🤖 Calling LangChain for advanced RAG response...")
                    
                    # Get conversation history from context
                    conversation_history = user_context.get("conversation_history", []) if user_context else []
                    
                    response = await self._generate_openai_response_with_context(query, context_text, conversation_history)
                    logger.info(f"✅ Advanced RAG response generated successfully")
                    logger.info(f"📄 Response preview: '{response[:100]}...'")
                    
                    suggested_actions = self._suggest_actions(query, relevant_docs)
                    logger.info(f"💡 Suggested actions: {suggested_actions}")
                    
                    total_rag_time = time.time() - start_time
                    logger.info(f"⏱️  Total RAG time: {total_rag_time:.3f}s")
                    return {
                        "response": response,
                        "sources": self._format_sources_markdown(relevant_docs[:3]),
                        "confidence": 0.9,
                        "suggested_actions": suggested_actions
                    }
                except Exception as e:
                    logger.error(f"❌ Advanced RAG response generation failed: {e}")
                    import traceback
                    logger.error(f"Traceback: {traceback.format_exc()}")
                    
                    # در STRICT MODE، اگر خطا رخ داد، پیام خطا برمی‌گردانیم
                    total_rag_time = time.time() - start_time
                    logger.info(f"⏱️  Total RAG time: {total_rag_time:.3f}s")
                    return {
                        "response": "متأسفانه در پردازش اطلاعات پایگاه دانش خطایی رخ داد. لطفاً دوباره تلاش کنید.",
                        "sources": [],
                        "confidence": 0.0,
                        "suggested_actions": ["retry", "create_ticket"]
                    }

        # اگر API key نداریم
        logger.error("❌ OpenAI API key not configured")
        total_rag_time = time.time() - start_time
        logger.info(f"⏱️  Total RAG time: {total_rag_time:.3f}s")
        return {
            "response": "متأسفانه سرویس هوش مصنوعی در حال حاضر در دسترس نیست.",
            "sources": [],
            "confidence": 0.0,
            "suggested_actions": ["contact_support"]
        }
    
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

    async def _generate_agentic_response(self, query: str, context: str, user_context: Dict[str, Any]) -> str:
        """Generate response using OpenAI with agentic capabilities."""
        prompt = f"""You are Sally, an advanced AI customer support agent. You have access to the full knowledge base and customer information. Use this context to provide personalized, actionable responses.

Context:
{context}

User Question: {query}

As an agentic assistant, you can:
1. Provide detailed answers from the knowledge base
2. Suggest creating support tickets for complex issues
3. Recommend specific articles or resources
4. Offer step-by-step guidance

Provide a helpful, personalized response that goes beyond just answering the question - anticipate follow-up needs and offer proactive assistance."""

        from app.infrastructure.langchain_utils import langchain_service

        try:
            logger.info(f"_generate_agentic_response: Using LangChain chat model for query '{query[:50]}...'")

            # Convert to messages format
            messages = [
                {"role": "user", "content": query}
            ]

            return await langchain_service.generate_chat_response(messages, context)
        except Exception as e:
            logger.error(f"_generate_agentic_response: LangChain error for query '{query[:50]}...': {e}")
            # Fallback to simple response
            return f"متأسفانه در حال حاضر به سرویس هوش مصنوعی دسترسی ندارم. اما می‌توانم به شما کمک کنم: {query}"
    
    async def _generate_direct_openai_response(self, query: str, user_context: Dict[str, Any]) -> str:
        """Generate response using OpenAI API directly without RAG context."""
        user_info = ""
        if user_context.get("user_id"):
            user_id = user_context.get("user_id")
            # Try to get user from Customer entity first
            user = None

            try:
                user = await Customer.get(user_id)
                if user:
                    user_info = f"You are {user.full_name} ({user.email}), a Customer.\n"
                else:
                    user = await Admin.get(user_id)
                    if user:
                        user_info = f"You are {user.full_name} ({user.email}), an Admin.\n"
            except Exception as e:
                logger.error(f"_generate_direct_openai_response: Error fetching user info for {user_id}: {e}")
                user_info = "User information not available\n"
        
        prompt = f"""{user_info}You are Sally, a helpful customer support assistant. The user has asked: "{query}"

Please provide a helpful response to their question. Since I don't have specific information from our knowledge base available, respond in a general but helpful way. If appropriate:
- Offer to help create a support ticket for more specific assistance
- Suggest they provide more details if they need a more specific answer
- Be friendly and professional in your response

Your response:"""

        from app.infrastructure.langchain_utils import langchain_service

        try:
            logger.info(f"_generate_direct_openai_response (Agentic): Using LangChain chat model for query '{query[:50]}...'")

            # Convert to messages format
            messages = [
                {"role": "user", "content": query}
            ]

            return await langchain_service.generate_chat_response(messages)
        except Exception as e:
            logger.error(f"_generate_direct_openai_response (Agentic): LangChain error for query '{query[:50]}...': {e}")
            logger.error(f"Error details: {str(e)}")
            # Fallback response
            fallback = "متأسفانه در حال حاضر به سرویس هوش مصنوعی دسترسی ندارم، اما می‌توانم به شما کمک کنم. لطفاً سوال خود را با جزئیات بیشتری مطرح کنید یا با تیم پشتیبانی تماس بگیرید."
            logger.warning(f"Using fallback response: '{fallback}'")
            return fallback
    
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
def get_rag_service(user: Optional[Union['Customer', 'Admin', 'User']] = None) -> RAGService:
    """Get appropriate RAG service based on user type."""
    if user:
        # Check if user is authenticated (has an id attribute)
        return AgenticRAGService()
    else:
        return SimpleRAGService()
