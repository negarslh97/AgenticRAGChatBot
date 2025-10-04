from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from typing import Optional, List, Union
from pydantic import BaseModel, ConfigDict
from bson import ObjectId
from app.domain.entities import (
    Customer, Admin, Conversation, Message, GuestSession, UnansweredQuestion,
    MessageRating
)
from app.core.permissions import get_current_customer, get_optional_customer, get_optional_admin, get_current_admin
from app.use_cases.chat_use_cases_refactored import ChatUseCases
import json
from datetime import datetime
import logging
import asyncio

from app.core.logging_config import get_logger

logger = get_logger(__name__)

# Wrapper dependency for async get_current_admin
async def get_admin_dependency() -> Admin:
    """Wrapper dependency for get_current_admin"""
    return await get_current_admin()

router = APIRouter()


class ChatMessage(BaseModel):
    content: str
    conversation_id: Optional[str] = None
    guest_session_id: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class AdminChatMessage(BaseModel):
    content: str
    conversation_id: Optional[str] = None
    rag_type: str = "simple"  # "simple", "agentic", or "advanced_agentic"
    
    model_config = ConfigDict(from_attributes=True)


class AdvancedAgenticRequest(BaseModel):
    """درخواست برای Advanced Agentic RAG"""
    query: str
    conversation_id: Optional[str] = None
    include_metadata: bool = True  # شامل شدن metadata مثل action_history
    
    model_config = ConfigDict(from_attributes=True)


class AdvancedAgenticResponse(BaseModel):
    """پاسخ Advanced Agentic RAG"""
    response: str
    sources: List[dict]
    confidence: float
    complexity: str
    actions_taken: List[str]
    reflection_notes: List[str]
    errors: List[str]
    session_id: str
    conversation_id: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class ChatResponse(BaseModel):
    conversation_id: str
    message: str
    sources: List[dict] = []
    confidence: float
    suggested_actions: List[str] = []
    message_id: str


@router.post("/message", response_model=ChatResponse)
async def send_message(
    request: Request,
    message: ChatMessage,
    current_customer: Optional[Customer] = Depends(get_optional_customer),
    current_admin: Optional[Admin] = Depends(get_optional_admin)
):
    """Send a chat message and get AI response."""
    
    # Determine user type - prefer authenticated users over guests
    current_user = current_customer or current_admin
    user_type = "Customer" if current_customer else ("Admin" if current_admin else "guest")
    
    try:
        # Log message for monitoring
        logger.info(f"Chat message received - User type: {user_type}, Content length: {len(message.content)}, Conversation ID: {message.conversation_id}")
        
        # Validate guest session ID for guests only
        if not current_user and not message.guest_session_id:
            raise HTTPException(status_code=400, detail="guest_session_id is required for guest users")
        
        response = await ChatUseCases.send_message(
            content=message.content,
            user=current_user,
            user_type=user_type,
            conversation_id=message.conversation_id,
            guest_session_id=message.guest_session_id
        )
        
        return ChatResponse(**response)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        print(f"Unexpected error in send_message: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/admin/message", response_model=ChatResponse)
async def send_admin_message(
    request: Request,
    message: AdminChatMessage,
    current_admin: Admin = Depends(get_optional_admin)
):
    """Send a chat message as admin with RAG type selection (non-streaming)."""
    
    if not current_admin:
        raise HTTPException(status_code=401, detail="Admin authentication required")
    
    try:
        # Log message for monitoring
        logger.info(f"Admin chat message received - Admin: {current_admin.email}, RAG type: {message.rag_type}, Content length: {len(message.content)}, Conversation ID: {message.conversation_id}")
        
        # Validate RAG type
        if message.rag_type not in ["simple", "agentic", "advanced_agentic"]:
            raise HTTPException(status_code=400, detail="Invalid RAG type. Must be 'simple', 'agentic', or 'advanced_agentic'")
        
        response = await ChatUseCases.send_admin_message(
            content=message.content,
            admin=current_admin,
            conversation_id=message.conversation_id,
            rag_type=message.rag_type
        )
        
        return ChatResponse(**response)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        logger.error(f"Unexpected error in send_admin_message: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/admin/message/stream")
async def send_admin_message_stream(
    request: Request,
    message: AdminChatMessage,
    current_admin: Admin = Depends(get_optional_admin)
):
    """Send a chat message as admin with RAG type selection (streaming)."""
    
    if not current_admin:
        raise HTTPException(status_code=401, detail="Admin authentication required")
    
    try:
        logger.info(f"🌊 Admin streaming message - Admin: {current_admin.email}, RAG type: {message.rag_type}")
        
        # Validate RAG type
        if message.rag_type not in ["simple", "agentic", "advanced_agentic"]:
            raise HTTPException(status_code=400, detail="Invalid RAG type. Must be 'simple', 'agentic', or 'advanced_agentic'")
        
        async def generate_stream():
            """Generator for admin streaming"""
            try:
                async for event_data in ChatUseCases.send_admin_message_stream(
                    content=message.content,
                    admin=current_admin,
                    conversation_id=message.conversation_id,
                    rag_type=message.rag_type
                ):
                    yield f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"
                    await asyncio.sleep(0.01)
                
                yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"
                
            except Exception as e:
                logger.error(f"❌ Admin streaming error: {e}", exc_info=True)
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"
        
        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Admin streaming error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/conversations")
async def get_conversations(
    current_customer: Optional[Customer] = Depends(get_optional_customer),
    current_admin: Optional[Admin] = Depends(get_optional_admin)
):
    """Get conversations - authenticated users only"""
    try:
        # Determine user type and get appropriate conversations
        if current_customer:
            conversations = await ChatUseCases.get_user_conversations(current_customer)
        elif current_admin:
            conversations = await ChatUseCases.get_admin_conversations(current_admin)
        else:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        return {"conversations": conversations}
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        logger.error(f"Error getting conversations: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


class TitleUpdateRequest(BaseModel):
    title: str


class MessageRatingRequest(BaseModel):
    rating: int  # 1-5 scale
    comment: Optional[str] = None

@router.put("/conversations/{conversation_id}/title")
async def update_conversation_title(
    conversation_id: str,
    title_request: TitleUpdateRequest,
    current_customer: Customer = Depends(get_current_customer)
):
    """Update conversation title."""
    try:
        # Get the conversation to check ownership
        conversation = await Conversation.get(ObjectId(conversation_id))
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Check if customer owns the conversation
        if conversation.customer_id != str(current_customer.id):
            raise HTTPException(status_code=403, detail="Access denied")

        # Update the title
        conversation.title = title_request.title
        conversation.updated_at = datetime.utcnow()
        await conversation.save()

        return {"message": "Title updated successfully"}
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/conversations/{conversation_id}/generate-title-tags")
async def generate_conversation_title_tags(
    conversation_id: str,
    current_customer: Optional[Customer] = Depends(get_optional_customer),
    current_admin: Optional[Admin] = Depends(get_optional_admin)
):
    """Generate AI-powered title and tags for a conversation."""
    try:
        # Get the conversation to check ownership
        conversation = await Conversation.get(ObjectId(conversation_id))
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Check permissions
        if current_customer and conversation.customer_id != str(current_customer.id):
            raise HTTPException(status_code=403, detail="Access denied")
        elif not current_customer and not current_admin:
            # For guests, check guest session ownership
            raise HTTPException(status_code=403, detail="Access denied - authentication required")

        # Generate title and tags
        result = await ChatUseCases.generate_conversation_title_and_tags(conversation_id)

        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])

        return {
            "message": "Title and tags generated successfully",
            "title": result["title"],
            "tags": result["tags"]
        }
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        print(f"Error generating title and tags: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/messages/{message_id}/rate")
async def rate_message(
    message_id: str,
    rating_request: MessageRatingRequest,
    current_customer: Optional[Customer] = Depends(get_optional_customer),
    current_admin: Optional[Admin] = Depends(get_optional_admin)
):
    """Rate an AI message response."""
    try:
        # Validate rating range
        if not 1 <= rating_request.rating <= 5:
            raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")

        # Get the message
        message = await Message.get(ObjectId(message_id))
        if not message:
            raise HTTPException(status_code=404, detail="Message not found")

        # Check if message is from AI
        if message.sender_type != "ai":
            raise HTTPException(status_code=400, detail="Only AI messages can be rated")

        # Get the conversation to check ownership
        conversation = await Conversation.get(ObjectId(message.conversation_id))
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Check permissions - only conversation owner can rate messages
        rater_id = None
        if current_customer and conversation.customer_id == str(current_customer.id):
            rater_id = str(current_customer.id)
        elif current_admin:
            rater_id = str(current_admin.id)
        else:
            raise HTTPException(status_code=403, detail="Access denied - only conversation participants can rate messages")

        # Create or update rating
        message.rating = MessageRating(
            rating=rating_request.rating,
            comment=rating_request.comment,
            rated_by=rater_id,
            rated_at=datetime.utcnow()
        )

        await message.save()

        return {
            "message": "Rating submitted successfully",
            "rating": rating_request.rating,
            "comment": rating_request.comment
        }

    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        print(f"Error rating message: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/conversations/{conversation_id}/rating-stats")
async def get_conversation_rating_stats(
    conversation_id: str,
    current_customer: Optional[Customer] = Depends(get_optional_customer),
    current_admin: Optional[Admin] = Depends(get_optional_admin)
):
    """Get rating statistics for a conversation."""
    try:
        # Get the conversation to check ownership
        conversation = await Conversation.get(ObjectId(conversation_id))
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Check permissions
        if current_customer and conversation.customer_id != str(current_customer.id):
            raise HTTPException(status_code=403, detail="Access denied")
        elif not current_customer and not current_admin:
            raise HTTPException(status_code=403, detail="Access denied - authentication required")

        # Get rating statistics
        stats = await ChatUseCases.get_message_rating_stats(conversation_id)

        return {
            "conversation_id": conversation_id,
            "rating_stats": stats
        }

    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        print(f"Error getting rating stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: str,
    current_customer: Optional[Customer] = Depends(get_optional_customer),
    current_admin: Optional[Admin] = Depends(get_optional_admin),
    guest_session_id: Optional[str] = None
):
    """Get messages from a conversation."""
    try:
        # Determine user type and ID for access control
        user_type = "Customer" if current_customer else ("Admin" if current_admin else "Guest")
        user_id = str(current_customer.id) if current_customer else (str(current_admin.id) if current_admin else None)
        
        logger.info(f"Getting conversation history - Conversation ID: {conversation_id}, User type: {user_type}")
        
        # Validate guest session ID for guests
        if not current_customer and not current_admin and not guest_session_id:
            raise HTTPException(status_code=400, detail="guest_session_id is required for guest users")
        
        messages = await ChatUseCases.get_conversation_history(
            conversation_id, 
            user_type=user_type, 
            user_id=user_id, 
            guest_session_id=guest_session_id
        )
        logger.info(f"Returning {len(messages)} messages for conversation {conversation_id}")
        
        return {"messages": messages}
    except ValueError as e:
        logger.error(f"Chat API error: {e}")
        if "Conversation not found" in str(e):
            raise HTTPException(status_code=404, detail="Conversation not found")
        elif "Access denied" in str(e):
            raise HTTPException(status_code=403, detail="Access denied")
        else:
            raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        logger.error(f"Unexpected error in chat API: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/article/{article_id}")
async def get_article_for_highlighting(
    article_id: str,
    query: Optional[str] = None,
    current_customer: Optional[Customer] = Depends(get_optional_customer),
    current_admin: Optional[Admin] = Depends(get_optional_admin)
):
    """
    Get article with highlighting information based on user query.
    برای نمایش مقاله با highlight کردن قسمت‌های مرتبط.
    """
    try:
        from bson import ObjectId
        from app.domain.entities import KnowledgeBaseArticle
        from app.infrastructure.database.mongodb import init_db, get_mongo_client
        
        if get_mongo_client() is None:
            await init_db()
        
        # دریافت مقاله
        article = await KnowledgeBaseArticle.get(ObjectId(article_id))
        
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")
        
        # استخراج کلمات کلیدی از query برای highlighting
        highlight_keywords = []
        if query:
            # لیست stop words فارسی (کلماتی که نباید highlight بشن)
            persian_stop_words = {
                'است', 'هست', 'که', 'در', 'به', 'از', 'را', 'با', 'برای', 'این', 'آن',
                'یک', 'چه', 'چی', 'چند', 'کدام', 'چطور', 'چگونه', 'چرا', 'کی', 'کجا',
                'می', 'شود', 'میشود', 'می‌شود', 'بود', 'باشد', 'های', 'ها', 'ای', 'ان',
                'و', 'یا', 'اما', 'ولی', 'تا', 'اگر', 'چون', 'پس', 'نه', 'بله', 'آره'
            }
            
            # تمیز کردن query از علائم نگارشی
            import re
            cleaned_query = re.sub(r'[؟?!،,.\-_]', ' ', query)
            
            # تقسیم به کلمات
            words = cleaned_query.split()
            
            # فقط کلمات معنادار (بیشتر از 2 حرف و نه stop word)
            highlight_keywords = [
                w.strip() for w in words 
                if len(w.strip()) > 2 and w.strip().lower() not in persian_stop_words
            ]
            
            logger.info(f"🎯 Extracted {len(highlight_keywords)} keywords from query: {highlight_keywords}")
        
        return {
            "id": str(article.id),
            "title": article.title,
            "content": article.content_markdown,
            "summary": article.summary,
            "category": article.category.name if article.category else None,
            "tags": [tag.name for tag in article.tags] if article.tags else [],
            "highlight_keywords": highlight_keywords,  # 🔥 کلمات کلیدی برای highlight
            "created_at": article.created_at.isoformat(),
            "updated_at": article.updated_at.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting article: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/advanced-agentic", response_model=AdvancedAgenticResponse)
async def advanced_agentic_rag(
    request: AdvancedAgenticRequest,
    current_admin: Optional[Admin] = Depends(get_optional_admin),
    current_customer: Optional[Customer] = Depends(get_optional_customer)
):
    """
    Advanced Agentic RAG endpoint با قابلیت‌های پیشرفته:
    - Multi-agent workflow با LangGraph
    - Tree-aware search در ساختار درختی Markdown
    - Query decomposition برای سوالات پیچیده
    - Self-reflection و quality assessment
    
    این endpoint برای سوالات پیچیده و تحقیقات عمیق مناسب است.
    """
    
    try:
        logger.info("="*80)
        logger.info("🚀 Advanced Agentic RAG Request Received")
        logger.info(f"📝 Query: {request.query}")
        logger.info(f"👤 User: {'Admin' if current_admin else 'Customer' if current_customer else 'Guest'}")
        logger.info("="*80)
        
        # بررسی دسترسی - فقط کاربران احراز هویت شده
        current_user = current_admin or current_customer
        if not current_user:
            raise HTTPException(
                status_code=401, 
                detail="Authentication required for Advanced Agentic RAG"
            )
        
        # Import services
        from app.infrastructure.langchain_utils import langchain_service
        from app.infrastructure.rag_service import get_rag_service
        from app.infrastructure.agentic_rag_advanced import get_advanced_agentic_rag
        from app.domain.entities import Conversation, Message
        from bson import ObjectId
        
        # دریافت RAG service
        rag_service = get_rag_service(current_user)
        
        # دریافت Advanced Agentic RAG
        advanced_rag = get_advanced_agentic_rag(
            langchain_service, 
            rag_service
        )
        
        # دریافت تاریخچه مکالمه از MongoDB
        conversation_history = []
        if request.conversation_id:
            try:
                conversation = await Conversation.get(ObjectId(request.conversation_id))
                if conversation:
                    # دریافت پیام‌های قبلی
                    messages = await Message.find(
                        {"conversation_id": request.conversation_id}
                    ).sort("created_at", 1).to_list()
                    
                    # تبدیل به فرمت مورد نیاز
                    for msg in messages[-10:]:  # فقط 10 پیام آخر
                        conversation_history.append({
                            "role": "user" if msg.sender_type in ["Customer", "Admin"] else "assistant",
                            "content": msg.content
                        })
                    
                    logger.info(f"📚 Loaded {len(conversation_history)} messages from conversation history")
            except Exception as e:
                logger.warning(f"⚠️ Could not load conversation history: {e}")
        
        # اجرای workflow با تاریخچه
        result = await advanced_rag.run(
            query=request.query,
            user_id=str(current_user.id),
            conversation_history=conversation_history
        )
        
        logger.info("="*80)
        logger.info("✅ Advanced Agentic RAG Completed")
        logger.info(f"🎯 Confidence: {result['confidence']:.2f}")
        logger.info(f"🔍 Complexity: {result['complexity']}")
        logger.info(f"📊 Actions Taken: {len(result['actions_taken'])}")
        logger.info("="*80)
        
        # آماده‌سازی پاسخ
        response_data = {
            "response": result["response"],
            "sources": result["sources"],
            "confidence": result["confidence"],
            "complexity": result["complexity"],
            "actions_taken": result["actions_taken"],
            "reflection_notes": result.get("reflection_notes", []),
            "errors": result.get("errors", []),
            "session_id": result["session_id"],
            "conversation_id": request.conversation_id
        }
        
        return AdvancedAgenticResponse(**response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Advanced Agentic RAG error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail=f"Advanced Agentic RAG failed: {str(e)}"
        )


@router.post("/create-sample-articles")
async def create_sample_articles(
    current_admin: Admin = Depends(get_admin_dependency)
):
    """Create sample articles for testing RAG functionality"""
    try:
        from app.infrastructure.database.mongodb import init_db, get_mongo_client
        from app.domain.entities import KnowledgeBaseArticle, ArticleStatus, ArticleVisibility

        if get_mongo_client() is None:
            await init_db()

        # Check existing articles
        existing = await KnowledgeBaseArticle.find().to_list()

        if existing:
            return {
                "message": f"Already have {len(existing)} articles in MongoDB",
                "articles": [{"id": str(a.id), "title": a.title} for a in existing]
            }

        # Create sample articles
        sample_articles = [
            {
                "title": "Database Design",
                "content_markdown": """# Database Design

Database design is one of the most important steps in software development.

## Design Stages

1. **Requirements Analysis** - Identify entities and relationships
2. **Conceptual Modeling** - Design ERD
3. **Logical Modeling** - Convert to tables
4. **Physical Modeling** - Implement in DBMS

## Important Notes

- Use appropriate foreign keys
- Define proper constraints
- Optimize for performance""",
                "summary": "Complete guide to database design including analysis, modeling and implementation",
                "status": ArticleStatus.PUBLISHED,
                "visibility": ArticleVisibility.PUBLIC
            },
            {
                "title": "Web Development",
                "content_markdown": """# Web Development

Web development includes both frontend and backend design.

## Main Technologies

### Frontend
- HTML/CSS/JavaScript
- React, Vue, Angular
- Responsive Design

### Backend
- Node.js, Python, PHP
- RESTful APIs
- Database Management""",
                "summary": "Introduction to web development technologies including frontend and backend",
                "status": ArticleStatus.PUBLISHED,
                "visibility": ArticleVisibility.PUBLIC
            },
            {
                "title": "Machine Learning with Python",
                "content_markdown": """# Machine Learning with Python

Python is the best language for machine learning.

## Important Libraries

- **Scikit-learn** - Basic ML tools
- **TensorFlow** - Deep neural networks
- **PyTorch** - Research and production
- **Pandas** - Data analysis
- **NumPy** - Numerical computations""",
                "summary": "Guide to machine learning with Python and introduction to important libraries",
                "status": ArticleStatus.PUBLISHED,
                "visibility": ArticleVisibility.PUBLIC
            }
        ]

        created_articles = []
        for article_data in sample_articles:
            article = KnowledgeBaseArticle(
                title=article_data["title"],
                content_markdown=article_data["content_markdown"],
                content_html=f"<h1>{article_data['title']}</h1><p>{article_data['content_markdown'].replace('#', '').replace('##', '')}</p>",
                summary=article_data["summary"],
                status=article_data["status"],
                visibility=article_data["visibility"],
                author_id=str(current_admin.id),
            )

            await article.insert()
            created_articles.append({
                "id": str(article.id),
                "title": article.title
            })

        return {
            "message": f"Created {len(created_articles)} sample articles",
            "articles": created_articles
        }

    except Exception as e:
        logger.error(f"Error creating sample articles: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/message/stream")
async def send_message_stream(
    request: Request,
    message: ChatMessage,
    current_customer: Optional[Customer] = Depends(get_optional_customer),
    current_admin: Optional[Admin] = Depends(get_optional_admin)
):
    """
    Send a chat message and get AI response as a stream (Server-Sent Events).
    این endpoint پاسخ را به صورت تدریجی و لحظه‌ای ارسال می‌کند.
    """
    
    # Determine user type
    current_user = current_customer or current_admin
    user_type = "Customer" if current_customer else ("Admin" if current_admin else "guest")
    
    try:
        logger.info(
            f"🌊 Streaming chat message received",
            extra={
                'extra_data': {
                    'user_type': user_type,
                    'content_length': len(message.content),
                    'conversation_id': message.conversation_id
                }
            }
        )
        
        # Validate guest session ID for guests
        if not current_user and not message.guest_session_id:
            raise HTTPException(status_code=400, detail="guest_session_id is required for guest users")
        
        async def generate_stream():
            """Generator function for streaming response"""
            try:
                # استفاده از streaming use case
                chunk_count = 0
                async for event_data in ChatUseCases.send_message_stream(
                    content=message.content,
                    user=current_user,
                    user_type=user_type,
                    conversation_id=message.conversation_id,
                    guest_session_id=message.guest_session_id
                ):
                    chunk_count += 1
                    # 🔥 DEBUG: Log each chunk
                    if event_data.get('type') == 'chunk':
                        logger.info(f"📤 Sending chunk #{chunk_count}: {len(event_data.get('content', ''))} chars")
                    
                    # ارسال داده به فرمت Server-Sent Events (SSE)
                    yield f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"
                    # Force flush به client
                    await asyncio.sleep(0.01)  # کمی تاخیر برای اطمینان از flush شدن
                
                logger.info(f"✅ Stream completed: {chunk_count} total events sent")
                # ارسال پیام پایان
                yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"
                
            except Exception as e:
                logger.error(f"❌ Streaming error: {e}", exc_info=True)
                error_data = {
                    'type': 'error',
                    'message': str(e)
                }
                yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
        
        # Return streaming response با SSE headers
        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # برای nginx
            }
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error in streaming: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


# WebSocket functionality - temporarily disabled
# TODO: Implement WebSocket support when real-time features are needed
"""
# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            await websocket.send_text(message)
        except:
            self.disconnect(websocket)


manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # WebSocket endpoint temporarily disabled
    await websocket.close(code=1001)  # Going away
"""