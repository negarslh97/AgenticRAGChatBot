from typing import List, Dict, Any, Optional, Union
from abc import ABC, abstractmethod
import openai
from app.core.config import settings
from app.domain.entities import KnowledgeBaseArticle, ArticleStatus, User, UserRole
from app.domain.entities_refactored import Customer, Admin


class RAGService(ABC):
    """Abstract base class for RAG services."""
    
    def __init__(self):
        if settings.openai_api_key_loaded:
            openai.api_key = settings.openai_api_key_loaded
            # Configure base URL if using OpenRouter
            if settings.openai_base_url_loaded:
                openai.base_url = settings.openai_base_url_loaded
    
    @abstractmethod
    async def generate_response(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate response using RAG."""
        pass
    
    async def retrieve_relevant_documents(self, query: str, is_public_only: bool = True) -> List[Dict[str, Any]]:
        """Retrieve relevant documents from knowledge base."""
        # Build query for articles
        article_query = KnowledgeBaseArticle.status == ArticleStatus.PUBLISHED
        
        if is_public_only:
            article_query = article_query & (KnowledgeBaseArticle.is_public == True)
        
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
        """Generate response using simple RAG for guests."""
        
        # Retrieve relevant documents from public knowledge base
        relevant_docs = await self.retrieve_relevant_documents(query, is_public_only=True)
        
        if not relevant_docs:
            print("DEBUG: No relevant documents found, using OpenAI for direct response")
            # Use OpenAI directly instead of fallback when no documents found
            if settings.openai_api_key_loaded:
                try:
                    direct_response = await self._generate_direct_openai_response(query, {})
                    return {
                        "response": direct_response,
                        "sources": [],
                        "confidence": 0.7
                    }
                except Exception as e:
                    print(f"Direct OpenAI API error: {e}")
            
            # Fallback response only if OpenAI fails
            return {
                "response": "I couldn't find specific information about your question in our knowledge base. Please try rephrasing your question or contact our support team for assistance.",
                "sources": [],
                "confidence": 0.1
            }
        
        # Build context from retrieved documents
        context_text = "\n\n".join([
            f"Document: {doc['title']}\nContent: {doc['content']}"
            for doc in relevant_docs[:3]
        ])
        
        # Generate response using OpenAI (if available) or fallback
        if settings.openai_api_key_loaded:
            try:
                response = await self._generate_openai_response(query, context_text)
                return {
                    "response": response,
                    "sources": [{"title": doc["title"], "id": doc["id"]} for doc in relevant_docs[:3]],
                    "confidence": 0.8
                }
            except Exception as e:
                print(f"OpenAI API error: {e}")
        
        # Fallback response
        best_doc = relevant_docs[0]
        return {
            "response": f"Based on our knowledge base, here's what I found about '{query}':\n\n{best_doc['summary'] or best_doc['content'][:300]}...\n\nFor more detailed information, please refer to our documentation or contact support.",
            "sources": [{"title": best_doc["title"], "id": best_doc["id"]}],
            "confidence": 0.6
        }
    
    async def _generate_openai_response(self, query: str, context: str) -> str:
        """Generate response using OpenAI API."""
        prompt = f"""You are Sally, a helpful customer support assistant. Use the following context to answer the user's question accurately and helpfully.

Context:
{context}

User Question: {query}

Please provide a clear, helpful response based on the context provided. If the context doesn't contain enough information to fully answer the question, acknowledge this and suggest contacting support for more help."""

        model = settings.openai_model_loaded or "moonshotai/kimi-k2:free"
        print(f"DEBUG: Using model: {model}")
        print(f"DEBUG: Base URL: {openai.base_url}")
        print(f"DEBUG: API Key: {openai.api_key[:20]}..." if openai.api_key else "No API key")
        
        try:
            # Use the new OpenAI API (v1.0+)
            response = openai.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are Sally, a helpful customer support assistant."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.7
            )
            print(f"DEBUG: Simple RAG OpenAI API call successful")
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"OpenAI API error in simple RAG: {e}")
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

        model = settings.openai_model_loaded or "moonshotai/kimi-k2:free"
        print(f"DEBUG: Using model: {model}")
        print(f"DEBUG: Base URL: {openai.base_url}")
        print(f"DEBUG: API Key: {openai.api_key[:20]}..." if openai.api_key else "No API key")
        
        try:
            # Use the new OpenAI API (v1.0+) which is compatible with OpenRouter
            response = openai.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are Sally, a helpful customer support assistant."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.7
            )
            print(f"DEBUG: API response received successfully")
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"OpenAI API error: {e}")
            # Fallback response if API fails
            return f"سلام! من سالی، دستیار هوشمند شما هستم. متأسفانه در حال حاضر به پایگاه دانش دسترسی ندارم، اما می‌توانم به سوالات شما پاسخ دهم. لطفاً سوال خود را با جزئیات بیشتری مطرح کنید تا بهتر کمک کنم."


class AgenticRAGService(RAGService):
    """Agentic RAG for authenticated customers - uses full knowledge base and customer context."""
    
    async def generate_response(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate response using agentic RAG for customers."""
        
        user_context = context or {}
        user_id = user_context.get("user_id")
        
        # Retrieve relevant documents from full knowledge base (including private)
        print(f"DEBUG: Retrieving documents for query: '{query}'")
        relevant_docs = await self.retrieve_relevant_documents(query, is_public_only=False)
        print(f"DEBUG: Found {len(relevant_docs)} relevant documents")
        if relevant_docs:
            print(f"DEBUG: Top document: {relevant_docs[0]['title']} (score: {relevant_docs[0]['score']})")
        
        # Get user-specific context if available
        user_info = ""
        if user_id:
            # Try to get user from Customer entity first
            user = None

            try:
                user = await Customer.get(user_id)
                if user:
                    user_info = f"Customer: {user.full_name} ({user.email})\nRole: Customer\n"
                else:
                    user = await Admin.get(user_id)
                    if user:
                        user_info = f"Admin: {user.full_name} ({user.email})\nRole: Admin\n"
            except Exception as e:
                print(f"Error fetching user info: {e}")
                user_info = "Customer information not available\n"
        
        if not relevant_docs:
            print("DEBUG: No relevant documents found, using OpenAI for direct response")
            # Use OpenAI directly instead of fallback when no documents found
            if settings.openai_api_key_loaded:
                try:
                    direct_response = await self._generate_direct_openai_response(query, user_context)
                    return {
                        "response": direct_response,
                        "sources": [],
                        "confidence": 0.7,
                        "suggested_actions": self._suggest_actions(query, [])
                    }
                except Exception as e:
                    print(f"Direct OpenAI API error: {e}")
            
            # Fallback response only if OpenAI fails
            return {
                "response": "I couldn't find specific information about your question in our knowledge base. As a registered customer, I can create a support ticket for you to get personalized assistance from our team. Would you like me to help you with that?",
                "sources": [],
                "confidence": 0.2,
                "suggested_actions": ["create_ticket"]
            }
        
        # Build enhanced context
        context_text = f"{user_info}\n" + "\n\n".join([
            f"Document: {doc['title']}\nContent: {doc['content']}"
            for doc in relevant_docs[:5]
        ])
        
        # Generate response using OpenAI (if available) or enhanced fallback
        if settings.openai_api_key_loaded:
            try:
                print(f"DEBUG: Attempting to call OpenAI API with model: {settings.openai_model_loaded}")
                print(f"DEBUG: API Base URL: {settings.openai_base_url_loaded}")
                print(f"DEBUG: API Key loaded: {bool(settings.openai_api_key_loaded)}")
                
                response = await self._generate_agentic_response(query, context_text, user_context)
                print(f"DEBUG: OpenAI API call successful, response length: {len(response)}")
                
                return {
                    "response": response,
                    "sources": [{"title": doc["title"], "id": doc["id"]} for doc in relevant_docs[:5]],
                    "confidence": 0.9,
                    "suggested_actions": self._suggest_actions(query, relevant_docs)
                }
            except Exception as e:
                print(f"OpenAI API error: {e}")
                print(f"Error type: {type(e).__name__}")
                import traceback
                print(f"Traceback: {traceback.format_exc()}")
        
        # Enhanced fallback response for customers
        best_docs = relevant_docs[:2]
        response_parts = []
        
        for doc in best_docs:
            response_parts.append(f"**{doc['title']}**\n{doc['summary'] or doc['content'][:200]}...")
        
        response = f"Based on your question about '{query}', here's what I found:\n\n" + "\n\n".join(response_parts)
        response += "\n\nAs a registered customer, I can also help you create a support ticket if you need more personalized assistance."
        
        return {
            "response": response,
            "sources": [{"title": doc["title"], "id": doc["id"]} for doc in best_docs],
            "confidence": 0.7,
            "suggested_actions": ["create_ticket", "view_related_articles"]
        }
    
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
            response = openai.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are Sally, an advanced AI customer support agent with agentic capabilities."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.7
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
                print(f"Error fetching user info: {e}")
                user_info = "User information not available\n"
        
        prompt = f"""{user_info}You are Sally, a helpful customer support assistant. The user has asked: "{query}"

Please provide a helpful response to their question. Since I don't have specific information from our knowledge base available, respond in a general but helpful way. If appropriate:
- Offer to help create a support ticket for more specific assistance
- Suggest they provide more details if they need a more specific answer
- Be friendly and professional in your response

Your response:"""

        model = settings.openai_model_loaded or "moonshotai/kimi-k2:free"
        try:
            # Use the new OpenAI API (v1.0+)
            response = openai.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are Sally, a helpful customer support assistant."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.7
            )
            print(f"DEBUG: Direct OpenAI API call successful")
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"OpenAI API error in direct response: {e}")
            # Fallback response
            return "متأسفانه در حال حاضر به سرویس هوش مصنوعی دسترسی ندارم، اما می‌توانم به شما کمک کنم. لطفاً سوال خود را با جزئیات بیشتری مطرح کنید یا با تیم پشتیبانی تماس بگیرید."
    
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
