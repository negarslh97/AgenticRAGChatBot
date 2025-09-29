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
        """Retrieve relevant documents from knowledge base using Weaviate vector search."""
        logger.info("🔍 Starting document retrieval process")
        logger.info(f"📊 Search scope: {'Public only' if is_public_only else 'All documents'}")
        
        try:
            logger.info("🚀 Attempting Weaviate vector search...")
            # Try to use Weaviate for vector search first
            return await self._retrieve_from_weaviate(query, is_public_only)
        except Exception as e:
            logger.warning(f"❌ Weaviate search failed: {e}")
            logger.info("🔄 Falling back to MongoDB search...")
            # Fallback to MongoDB-based search
            return await self._retrieve_from_mongodb(query, is_public_only)

    async def _retrieve_from_weaviate(self, query: str, is_public_only: bool = True) -> List[Dict[str, Any]]:
        """Retrieve documents using Weaviate vector search."""
        logger.info("🔗 Connecting to Weaviate vector database...")
        
        try:
            import weaviate
            import warnings
            from app.core.config import settings

            # Connect to Weaviate (using v3 client like the connector script)
            weaviate_url = settings.weaviate_url_loaded or "http://localhost:8080"
            weaviate_api_key = settings.weaviate_api_key_loaded
            
            logger.info(f"🌐 Weaviate URL: {weaviate_url}")
            logger.info(f"🔑 Weaviate API Key: {'✅ Set' if weaviate_api_key else '❌ Not Set'}")

            # Suppress warnings temporarily
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                client = weaviate.Client(url=weaviate_url)
            
            logger.info("✅ Weaviate client created successfully")

            # Set API key in environment AFTER creating client (like in connector)
            import os
            embedder_api_key = settings.embedder_api_key_loaded
            openai_api_key = settings.openai_api_key_loaded
            
            # Try embedder_api_key first, then openai_api_key
            api_key_to_use = embedder_api_key or openai_api_key
            
            if api_key_to_use:
                # Set both environment variables for compatibility
                os.environ['Embedder_API_KEY'] = api_key_to_use
                logger.info("🔑 OpenAI API key set for embeddings")
                logger.info(f"🔑 API Key source: {'Embedder' if embedder_api_key else 'OpenAI'}")
            else:
                logger.warning("⚠️  No OpenAI API key found for embeddings")
                logger.warning("⚠️  Please set OPENAI_API_KEY or Embedder_API_KEY environment variable")

            # Build where filter for visibility
            where_filter = None
            if is_public_only:
                where_filter = {
                    "path": ["visibility"],
                    "operator": "Equal",
                    "valueText": "public"
                }
                logger.info("🔒 Applied visibility filter: public documents only")
            else:
                logger.info("🔓 No visibility filter: searching all documents")

            # Perform near text search
            near_text = {
                "concepts": [query],
                "distance": 0.7  # Cosine similarity threshold
            }
            
            logger.info(f"🎯 Building semantic search query...")
            logger.info(f"📝 Search concepts: {near_text['concepts']}")
            logger.info(f"📏 Distance threshold: {near_text['distance']}")

            # Build the query with API key header (like in connector)
            query_builder = client.query.get(
                "KnowledgeBaseArticle",
                ["title", "content", "summary", "article_id"]
            ).with_near_text(near_text).with_limit(5).with_additional("certainty")
            
            # Add where filter if specified
            if where_filter:
                query_builder = query_builder.with_where(where_filter)
            
            logger.info("⚡ Executing Weaviate vector search...")
            
            # Execute query using client - vectorizer config handles API keys
            try:
                # ابتدا سعی می‌کنیم از کلاس OpenAI
                result = query_builder.do()
                logger.info("✅ Weaviate query executed successfully with OpenAI vectorizer")

                # اگر نتیجه خالی بود، از کلاس محلی هم جستجو کنیم
                objects = result.get("data", {}).get("Get", {}).get("KnowledgeBaseArticle", [])
                if not objects or len(objects) == 0:
                    logger.info("🔄 نتیجه خالی از OpenAI، جستجو در کلاس محلی...")
                    local_query_builder = client.query.get(
                        "KnowledgeBaseArticleLocal",
                        ["title", "content", "summary", "article_id"]
                    ).with_near_text(near_text).with_limit(5).with_additional("certainty")

                    # Add where filter if specified
                    if where_filter:
                        local_query_builder = local_query_builder.with_where(where_filter)

                    local_result = local_query_builder.do()
                    local_objects = local_result.get("data", {}).get("Get", {}).get("KnowledgeBaseArticleLocal", [])

                    if local_objects:
                        logger.info(f"✅ {len(local_objects)} نتیجه از vectorizer محلی یافت شد")
                        # ترکیب نتایج
                        result = local_result
                        # تغییر نام کلاس به KnowledgeBaseArticle برای سازگاری
                        if "data" in result and "Get" in result["data"]:
                            result["data"]["Get"]["KnowledgeBaseArticle"] = result["data"]["Get"]["KnowledgeBaseArticleLocal"]
                            del result["data"]["Get"]["KnowledgeBaseArticleLocal"]

            except Exception as e:
                logger.warning(f"⚠️ OpenAI vectorizer شکست خورد، استفاده از fallback محلی: {str(e)}")
                try:
                    # استفاده از کلاس محلی
                    local_query_builder = client.query.get(
                        "KnowledgeBaseArticleLocal",
                        ["title", "content", "summary", "article_id"]
                    ).with_near_text(near_text).with_limit(5).with_additional("certainty")

                    # Add where filter if specified
                    if where_filter:
                        local_query_builder = local_query_builder.with_where(where_filter)

                    result = local_query_builder.do()
                    logger.info("✅ Weaviate query executed successfully with local vectorizer")

                    # تغییر نام کلاس برای سازگاری
                    if "data" in result and "Get" in result["data"]:
                        result["data"]["Get"]["KnowledgeBaseArticle"] = result["data"]["Get"]["KnowledgeBaseArticleLocal"]
                        del result["data"]["Get"]["KnowledgeBaseArticleLocal"]

                except Exception as local_e:
                    logger.error(f"❌ هر دو vectorizer شکست خوردند: OpenAI={str(e)}, Local={str(local_e)}")
                    raise local_e

            objects = result.get("data", {}).get("Get", {}).get("KnowledgeBaseArticle", [])

            # Handle case where objects is None (due to API key issues or other errors)
            if objects is None:
                logger.warning("⚠️  Weaviate returned None objects (possible API key issue)")
                objects = []
            
            logger.info(f"📊 Raw results from Weaviate: {len(objects) if objects else 0} objects")

            relevant_docs = []
            for i, obj in enumerate(objects):
                certainty = obj.get("_additional", {}).get("certainty", 0.5)
                score = certainty  # Keep as float between 0-1
                title = obj.get("title", "")

                logger.info(f"   📄 Document {i+1}: '{title[:50]}...' (Score: {score:.3f})")

                relevant_docs.append({
                    "id": obj.get("article_id", ""),
                    "title": title,
                    "content": obj.get("content", "")[:1000] if obj.get("content") else "",  # Truncate content
                    "summary": obj.get("summary", ""),
                    "score": score,
                    "source": "weaviate"
                })

            logger.info(f"✅ Weaviate search completed: {len(relevant_docs)} documents found")
            logger.info(f"🎯 Query: '{query[:50]}{'...' if len(query) > 50 else ''}'")
            return relevant_docs

        except Exception as e:
            logger.error(f"Weaviate search error: {e}")
            raise e

    async def _retrieve_from_mongodb(self, query: str, is_public_only: bool = True) -> List[Dict[str, Any]]:
        """Fallback: Retrieve documents using MongoDB keyword search."""
        logger.info("🗄️  Starting MongoDB fallback search...")
        logger.info(f"📊 Search scope: {'Public only' if is_public_only else 'All documents'}")

        # Initialize database connection
        from app.infrastructure.database.mongodb import init_db
        await init_db()

        # Build query for articles
        if is_public_only:
            articles = await KnowledgeBaseArticle.find({
                "status": "published",
                "visibility": "public"
            }).to_list()
        else:
            articles = await KnowledgeBaseArticle.find({
                "status": "published"
            }).to_list()

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
    """Simple RAG for guest users - uses public knowledge base only."""
    
    async def generate_response(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate response using Simple RAG with public knowledge base."""

        import time
        start_time = time.time()

        logger.info("=" * 60)
        logger.info("🤖 SimpleRAGService: Starting RAG operation")
        logger.info(f"📝 Query: '{query[:100]}{'...' if len(query) > 100 else ''}'")
        logger.info(f"🔒 Access Level: Public documents only")
        logger.info(f"🧠 LLM Model: {settings.rag_model_loaded}")
        logger.info("=" * 60)

        # Try to retrieve relevant documents from public knowledge base
        relevant_docs = await self.retrieve_relevant_documents(query, is_public_only=True)
        logger.info(f"📚 Retrieved {len(relevant_docs)} relevant documents")

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
                
                rag_response = await self._generate_openai_response(query, context_text)
                logger.info(f"✅ RAG response generated successfully")
                logger.info(f"📄 Response preview: '{rag_response[:100]}...'")

                total_rag_time = time.time() - start_time
                logger.info(f"⏱️  Total RAG time: {total_rag_time:.3f}s")

                return {
                    "response": rag_response,
                    "sources": [{"title": doc["title"], "id": doc["id"]} for doc in relevant_docs[:3]],
                    "confidence": 0.9
                }
            except Exception as e:
                logger.error(f"❌ RAG response generation failed: {str(e)}")
                logger.info("🔄 Falling back to direct OpenAI response...")

        # Fallback to direct OpenAI if no documents found or RAG fails
        if settings.openai_api_key_loaded:
            try:
                direct_response = await self._generate_direct_openai_response(query, {})
                logger.info(f"SimpleRAGService: Direct API success - Response preview: '{direct_response[:100]}...'")
                total_rag_time = time.time() - start_time
                logger.info(f"⏱️  Total RAG time: {total_rag_time:.3f}s")
                return {
                    "response": direct_response,
                    "sources": [],
                    "confidence": 0.7
                }
            except Exception as e:
                logger.error(f"SimpleRAGService: Direct OpenAI API error for query '{query[:50]}...': {str(e)}")

        # Final fallback response if all fails
        fallback_msg = "متأسفانه در حال حاضر به سرویس هوش مصنوعی دسترسی ندارم، اما می‌توانم به شما کمک کنم. لطفاً سوال خود را مطرح کنید."
        logger.warning(f"SimpleRAGService: Using fallback response for query '{query}': '{fallback_msg}'")
        total_rag_time = time.time() - start_time
        logger.info(f"⏱️  Total RAG time: {total_rag_time:.3f}s")
        return {
            "response": fallback_msg,
            "sources": [],
            "confidence": 0.1
        }
    
    async def _generate_openai_response(self, query: str, context: str) -> str:
        """Generate response using LangChain."""
        from app.infrastructure.langchain_utils import langchain_service

        try:
            logger.info(f"_generate_openai_response: Using LangChain RAG model for query '{query[:50]}...'")
            return await langchain_service.generate_rag_response(query, context)
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
    """Agentic RAG for authenticated customers - uses full knowledge base and customer context."""
    
    async def generate_response(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate response using RAG with fallback to OpenAI for customers."""

        import time
        start_time = time.time()

        user_context = context or {}
        user_id = user_context.get("user_id")

        logger.info("=" * 60)
        logger.info("🧠 AgenticRAGService: Starting advanced RAG operation")
        logger.info(f"📝 Query: '{query[:100]}{'...' if len(query) > 100 else ''}'")
        logger.info(f"👤 User ID: {user_id if user_id else 'Anonymous'}")
        logger.info(f"🔓 Access Level: Full knowledge base")
        logger.info(f"🧠 LLM Model: {settings.rag_model_loaded}")
        logger.info("=" * 60)

        # Try to retrieve relevant documents from knowledge base
        relevant_docs = await self.retrieve_relevant_documents(query, is_public_only=False)
        logger.info(f"📚 Retrieved {len(relevant_docs)} relevant documents")

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
                    response = await self._generate_openai_response_with_context(query, context_text)
                    logger.info(f"✅ Advanced RAG response generated successfully")
                    logger.info(f"📄 Response preview: '{response[:100]}...'")
                    
                    suggested_actions = self._suggest_actions(query, relevant_docs)
                    logger.info(f"💡 Suggested actions: {suggested_actions}")
                    
                    total_rag_time = time.time() - start_time
                    logger.info(f"⏱️  Total RAG time: {total_rag_time:.3f}s")
                    return {
                        "response": response,
                        "sources": [{"title": doc["title"], "id": doc["id"]} for doc in relevant_docs[:3]],
                        "confidence": 0.9,
                        "suggested_actions": suggested_actions
                    }
                except Exception as e:
                    logger.error(f"❌ Advanced RAG response generation failed: {e}")
                    import traceback
                    logger.error(f"Traceback: {traceback.format_exc()}")

        logger.info("🔄 Falling back to direct OpenAI (no docs or RAG error)")

        # Fallback to direct OpenAI without context
        if settings.openai_api_key_loaded and self.client:
            try:
                direct_response = await self._generate_direct_openai_response(query, user_context)
                logger.info(f"AgenticRAGService: Direct API success - Response preview: '{direct_response[:100]}...'")
                total_rag_time = time.time() - start_time
                logger.info(f"⏱️  Total RAG time: {total_rag_time:.3f}s")
                return {
                    "response": direct_response,
                    "sources": [],
                    "confidence": 0.7,
                    "suggested_actions": []
                }
            except Exception as e:
                logger.error(f"AgenticRAGService: Direct OpenAI API error for query '{query[:50]}...': {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")

        # Final fallback response
        fallback_msg = f"{user_info}متأسفانه در حال حاضر به سرویس هوش مصنوعی دسترسی ندارم، اما می‌توانم به شما کمک کنم. لطفاً سوال خود را مطرح کنید."
        logger.warning(f"AgenticRAGService: Using final fallback for query '{query[:50]}...': '{fallback_msg}'")
        total_rag_time = time.time() - start_time
        logger.info(f"⏱️  Total RAG time: {total_rag_time:.3f}s")
        return {
            "response": fallback_msg,
            "sources": [],
            "confidence": 0.1,
            "suggested_actions": ["contact_support"]
        }
    
    async def _generate_openai_response_with_context(self, query: str, context: str) -> str:
        """Generate response using OpenAI API with context from knowledge base."""
        prompt = f"""You are Sally, a helpful customer support assistant. Use the following context to answer the user's question accurately and helpfully. Answer in Persian (Farsi) language.

Context:
{context}

User Question: {query}

Please provide a clear, helpful response based on the context provided. If the context doesn't contain enough information, acknowledge this and offer to help with other ways."""

        from app.infrastructure.langchain_utils import langchain_service

        try:
            logger.info(f"_generate_openai_response_with_context: Using LangChain RAG model for query '{query[:50]}...'")
            return await langchain_service.generate_rag_response(query, context)
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
