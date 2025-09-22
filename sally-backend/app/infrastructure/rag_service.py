from typing import List, Dict, Any, Optional, Union
from abc import ABC, abstractmethod
import openai
import logging
from app.core.config import settings
from app.domain.entities_refactored import KnowledgeBaseArticle, ArticleStatus, ArticleVisibility, Customer, Admin

logger = logging.getLogger(__name__)


class RAGService(ABC):
    """Abstract base class for RAG services."""

    def __init__(self):
        # Initialize OpenAI client
        # Temporarily disable OpenAI client due to Pydantic compatibility issues
        # TODO: Fix OpenAI client version compatibility
        self.client = None
        logger.warning("RAGService client disabled - OpenAI client compatibility issues")
    
    @abstractmethod
    async def generate_response(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate response using RAG."""
        pass
    
    async def retrieve_relevant_documents(self, query: str, is_public_only: bool = True) -> List[Dict[str, Any]]:
        """Retrieve relevant documents from knowledge base."""
        # Build query for articles
        article_query = KnowledgeBaseArticle.status == ArticleStatus.PUBLISHED

        if is_public_only:
            article_query = article_query & (KnowledgeBaseArticle.visibility == ArticleVisibility.PUBLIC)
        
        articles = await KnowledgeBaseArticle.find(article_query).to_list()
        
        # Simple keyword-based retrieval (in production, use vector embeddings)
        query_lower = query.lower()
        relevant_docs = []
        
        for article in articles:
            score = 0
            
            # Score based on title match
            if any(word in article.title.lower() for word in query_lower.split()):
                score += 10
            
            # Score based on content match
            content_matches = sum(1 for word in query_lower.split() if word in article.content.lower())
            score += content_matches * 2
            
            # Score based on summary match
            if article.summary and any(word in article.summary.lower() for word in query_lower.split()):
                score += 5
            
            if score > 0:
                relevant_docs.append({
                    "id": str(article.id),
                    "title": article.title,
                    "content": article.content[:1000],  # Truncate for context
                    "summary": article.summary,
                    "score": score
                })
        
        # Sort by relevance and return top 5
        relevant_docs.sort(key=lambda x: x["score"], reverse=True)
        return relevant_docs[:5]


class SimpleRAGService(RAGService):
    """Simple RAG for guest users - uses public knowledge base only."""
    
    async def generate_response(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate response using direct OpenAI for guests (no RAG)."""

        logger.info(f"SimpleRAGService: Generating response for query: '{query}' (guest mode)")

        # Always use OpenAI directly for chat
        if settings.openai_api_key_loaded:
            try:
                direct_response = await self._generate_direct_openai_response(query, {})
                logger.info(f"SimpleRAGService: API success - Response preview: '{direct_response[:100]}...'")
                return {
                    "response": direct_response,
                    "sources": [],
                    "confidence": 0.8
                }
            except Exception as e:
                logger.error(f"SimpleRAGService: Direct OpenAI API error for query '{query}': {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")

        # Fallback response if OpenAI fails
        fallback_msg = "متأسفانه در حال حاضر به سرویس هوش مصنوعی دسترسی ندارم، اما می‌توانم به شما کمک کنم. لطفاً سوال خود را مطرح کنید."
        logger.warning(f"SimpleRAGService: Using fallback response for query '{query}': '{fallback_msg}'")
        return {
            "response": fallback_msg,
            "sources": [],
            "confidence": 0.1
        }
    
    async def _generate_openai_response(self, query: str, context: str) -> str:
        """Generate response using OpenAI API."""
        prompt = f"""You are Sally, a helpful customer support assistant. Use the following context to answer the user's question accurately and helpfully.

Context:
{context}

User Question: {query}

Please provide a clear, helpful response based on the context provided. If the context doesn't contain enough information to fully answer the question, acknowledge this and suggest contacting support for more help."""

        model = settings.openai_model_loaded or "moonshotai/kimi-k2:free"
        logger.info(f"_generate_openai_response: Using model '{model}', base_url '{self.client.base_url if self.client else None}', api_key prefix '{settings.openai_api_key_loaded[:10]}...'")
        
        try:
            # Use the new OpenAI API (v1.0+)
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are Sally, a helpful customer support assistant."},
                    {"role": "user", "content": prompt}
                ]
            )
            logger.info(f"_generate_openai_response: API call successful for query '{query[:50]}...'")
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"_generate_openai_response: API error for query '{query[:50]}...': {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # Fallback response
            raise Exception("OpenAI API unavailable")
    
    async def _generate_direct_openai_response(self, query: str, user_context: Dict[str, Any]) -> str:
        """Generate response using OpenAI API directly without RAG context."""
        prompt = f"""You are Sally, a helpful customer support assistant. The user has asked: "{query}"

Please provide a helpful response to their question. Since I don't have specific information from our knowledge base available, respond in a general but helpful way. If appropriate:
- Offer to help contact support for more specific assistance
- Suggest they provide more details if they need a more specific answer
- Be friendly and professional in your response

Your response:"""

        model = settings.openai_model_loaded or "gpt-3.5-turbo"
        logger.info(f"_generate_direct_openai_response: Using model '{model}', base_url '{self.client.base_url if self.client else None}', api_key prefix '{settings.openai_api_key_loaded[:10]}...' for query '{query[:50]}...'")

        try:
            # Use OpenAI API with minimal parameters
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are Sally, a helpful customer support assistant."},
                    {"role": "user", "content": prompt}
                ]
            )
            logger.info(f"_generate_direct_openai_response: API success - Response preview: '{response.choices[0].message.content[:100]}...'")
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"_generate_direct_openai_response: API error for query '{query[:50]}...': {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # Fallback response if API fails
            fallback = f"سلام! من سالی، دستیار هوشمند شما هستم. متأسفانه در حال حاضر به پایگاه دانش دسترسی ندارم، اما می‌توانم به سوالات شما پاسخ دهم. لطفاً سوال خود را با جزئیات بیشتری مطرح کنید تا بهتر کمک کنم."
            logger.warning(f"Using fallback response: '{fallback}'")
            return fallback


class AgenticRAGService(RAGService):
    """Agentic RAG for authenticated customers - uses full knowledge base and customer context."""
    
    async def generate_response(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate response using RAG with fallback to OpenAI for customers."""

        user_context = context or {}
        user_id = user_context.get("user_id")
        logger.info(f"AgenticRAGService: Generating response for query: '{query}' (user_id: {user_id})")

        # Try to retrieve relevant documents from knowledge base
        relevant_docs = await self.retrieve_relevant_documents(query, is_public_only=False)
        logger.info(f"AgenticRAGService: Found {len(relevant_docs)} relevant documents for query '{query[:50]}...'")

        # Get user-specific context if available
        user_info = ""
        if user_id:
            # Try to get user from Customer entity first
            user = None

            try:
                user = await Customer.get(user_id)
                if user:
                    user_info = f"You are a customer: {user.full_name} ({user.email}). "
                else:
                    user = await Admin.get(user_id)
                    if user:
                        user_info = f"You are an admin: {user.full_name} ({user.email}). "
            except Exception as e:
                logger.error(f"AgenticRAGService: Error fetching user info for {user_id}: {e}")
                user_info = "User information not available. "

        if relevant_docs:
            logger.info("AgenticRAGService: Using RAG with knowledge base documents")
            # Build context from retrieved documents
            context_text = user_info + "\n\n".join([
                f"Document: {doc['title']}\nContent: {doc['content']}"
                for doc in relevant_docs[:3]
            ])

            # Generate response using OpenAI with context
            if settings.openai_api_key_loaded and self.client:
                try:
                    response = await self._generate_openai_response_with_context(query, context_text)
                    logger.info(f"AgenticRAGService: RAG API success - Response preview: '{response[:100]}...'")
                    return {
                        "response": response,
                        "sources": [{"title": doc["title"], "id": doc["id"]} for doc in relevant_docs[:3]],
                        "confidence": 0.9,
                        "suggested_actions": self._suggest_actions(query, relevant_docs)
                    }
                except Exception as e:
                    logger.error(f"AgenticRAGService: OpenAI API error with context for query '{query[:50]}...': {e}")
                    import traceback
                    logger.error(f"Traceback: {traceback.format_exc()}")

        logger.info("AgenticRAGService: Falling back to direct OpenAI (no docs or RAG error)")

        # Fallback to direct OpenAI without context
        if settings.openai_api_key_loaded and self.client:
            try:
                direct_response = await self._generate_direct_openai_response(query, user_context)
                logger.info(f"AgenticRAGService: Direct API success - Response preview: '{direct_response[:100]}...'")
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

        model = settings.openai_model_loaded or "gpt-3.5-turbo"
        logger.info(f"_generate_openai_response_with_context: Using model '{model}', base_url '{self.client.base_url if self.client else None}' for query '{query[:50]}...'")

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are Sally, a helpful customer support assistant. Always respond in Persian (Farsi)."},
                    {"role": "user", "content": prompt}
                ]
            )
            logger.info(f"_generate_openai_response_with_context: API success - Response preview: '{response.choices[0].message.content[:100]}...'")
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"_generate_openai_response_with_context: API error for query '{query[:50]}...': {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise Exception("OpenAI API unavailable")

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

        model = settings.openai_model_loaded or "moonshotai/kimi-k2:free"
        try:
            # Use the new OpenAI API (v1.0+)
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are Sally, an advanced AI customer support agent with agentic capabilities."},
                    {"role": "user", "content": prompt}
                ]
            )
            print(f"DEBUG: Agentic OpenAI API call successful")
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"OpenAI API error in agentic response: {e}")
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

        model = settings.openai_model_loaded or "gpt-3.5-turbo"
        logger.info(f"_generate_direct_openai_response (Agentic): Using model '{model}', base_url '{self.client.base_url if self.client else None}' for query '{query[:50]}...'")

        try:
            # Use OpenAI API with minimal parameters
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are Sally, a helpful customer support assistant."},
                    {"role": "user", "content": prompt}
                ]
            )
            logger.info(f"_generate_direct_openai_response (Agentic): API success - Response preview: '{response.choices[0].message.content[:100]}...'")
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"_generate_direct_openai_response (Agentic): API error for query '{query[:50]}...': {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
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
