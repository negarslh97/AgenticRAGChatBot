from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from typing import List, Optional
from pydantic import BaseModel, EmailStr
from datetime import datetime
from app.domain.entities import (
    User, UserRole, KnowledgeBaseArticle, ArticleStatus, Category, Tag,
    Ticket, TicketStatus, ActivityLog
)
from app.api.dependencies import get_current_admin, get_current_SuperAdmin
from app.core.security import get_password_hash

router = APIRouter()


# User Management Models
class adminUserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: UserRole


class adminUserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime


# Knowledge Base Models
class ArticleCreate(BaseModel):
    title: str
    content: str
    summary: Optional[str] = None
    category_id: Optional[str] = None
    tags: List[str] = []
    is_public: bool = True


class ArticleUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    summary: Optional[str] = None
    category_id: Optional[str] = None
    tags: Optional[List[str]] = None
    is_public: Optional[bool] = None


# User Management Endpoints (Super admin only)
@router.get("/users", response_model=List[adminUserResponse])
async def get_all_users(current_user: User = Depends(get_current_SuperAdmin)):
    """Get all users (Super admin only)."""
    users = await User.find_all().to_list()
    
    return [
        adminUserResponse(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at
        )
        for user in users
    ]


@router.post("/users", response_model=adminUserResponse)
async def create_admin_user(
    user_data: adminUserCreate,
    current_user: User = Depends(get_current_SuperAdmin)
):
    """Create a new admin user (Super admin only)."""
    # Check if user already exists
    existing_user = await User.find_one(User.email == user_data.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new admin user
    new_user = User(
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        role=user_data.role
    )
    
    await new_user.insert()
    
    # Log activity
    activity_log = ActivityLog(
        user_id=str(current_user.id),
        action="create_user",
        resource_type="user",
        resource_id=str(new_user.id),
        details={"created_user_role": user_data.role}
    )
    await activity_log.insert()
    
    return adminUserResponse(
        id=str(new_user.id),
        email=new_user.email,
        full_name=new_user.full_name,
        role=new_user.role,
        is_active=new_user.is_active,
        created_at=new_user.created_at
    )


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user: User = Depends(get_current_SuperAdmin)
):
    """Delete a user (Super admin only)."""
    user = await User.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent deleting self
    if str(user.id) == str(current_user.id):
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    await user.delete()
    
    # Log activity
    activity_log = ActivityLog(
        user_id=str(current_user.id),
        action="delete_user",
        resource_type="user",
        resource_id=user_id,
        details={"deleted_user_email": user.email}
    )
    await activity_log.insert()
    
    return {"message": "User deleted successfully"}


# Knowledge Base Management
@router.get("/kb/articles")
async def get_all_articles(current_user: User = Depends(get_current_admin)):
    """Get all articles including drafts (admin access)."""
    articles = await KnowledgeBaseArticle.find_all().sort(-KnowledgeBaseArticle.updated_at).to_list()
    
    return [
        {
            "id": str(article.id),
            "title": article.title,
            "summary": article.summary,
            "status": article.status,
            "is_public": article.is_public,
            "author_id": article.author_id,
            "created_at": article.created_at,
            "updated_at": article.updated_at
        }
        for article in articles
    ]


@router.post("/kb/articles")
async def create_article(
    article_data: ArticleCreate,
    current_user: User = Depends(get_current_admin)
):
    """Create a new knowledge base article."""
    article = KnowledgeBaseArticle(
        title=article_data.title,
        content=article_data.content,
        summary=article_data.summary,
        category_id=article_data.category_id,
        tags=article_data.tags,
        is_public=article_data.is_public,
        author_id=str(current_user.id),
        status=ArticleStatus.DRAFT  # Always start as draft
    )
    
    await article.insert()
    
    # Log activity
    activity_log = ActivityLog(
        user_id=str(current_user.id),
        action="create_article",
        resource_type="article",
        resource_id=str(article.id),
        details={"title": article.title}
    )
    await activity_log.insert()
    
    return {"id": str(article.id), "message": "Article created as draft"}


@router.put("/kb/articles/{article_id}")
async def update_article(
    article_id: str,
    article_data: ArticleUpdate,
    current_user: User = Depends(get_current_admin)
):
    """Update a knowledge base article."""
    article = await KnowledgeBaseArticle.get(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    # Update fields
    update_data = article_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(article, field, value)
    
    article.updated_at = datetime.utcnow()
    await article.save()
    
    # Log activity
    activity_log = ActivityLog(
        user_id=str(current_user.id),
        action="update_article",
        resource_type="article",
        resource_id=article_id,
        details={"updated_fields": list(update_data.keys())}
    )
    await activity_log.insert()
    
    return {"message": "Article updated successfully"}


@router.post("/kb/articles/{article_id}/publish")
async def publish_article(
    article_id: str,
    current_user: User = Depends(get_current_SuperAdmin)
):
    """Publish an article (Super admin only)."""
    article = await KnowledgeBaseArticle.get(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    article.status = ArticleStatus.PUBLISHED
    article.published_by = str(current_user.id)
    article.published_at = datetime.utcnow()
    await article.save()
    
    # Log activity
    activity_log = ActivityLog(
        user_id=str(current_user.id),
        action="publish_article",
        resource_type="article",
        resource_id=article_id,
        details={"title": article.title}
    )
    await activity_log.insert()
    
    return {"message": "Article published successfully"}


@router.delete("/kb/articles/{article_id}")
async def delete_article(
    article_id: str,
    current_user: User = Depends(get_current_SuperAdmin)
):
    """Delete an article (Super admin only)."""
    article = await KnowledgeBaseArticle.get(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    await article.delete()
    
    # Log activity
    activity_log = ActivityLog(
        user_id=str(current_user.id),
        action="delete_article",
        resource_type="article",
        resource_id=article_id,
        details={"title": article.title}
    )
    await activity_log.insert()
    
    return {"message": "Article deleted successfully"}


# Ticket Management
@router.get("/tickets")
async def get_all_tickets(current_user: User = Depends(get_current_admin)):
    """Get all support tickets."""
    tickets = await Ticket.find_all().sort(-Ticket.updated_at).to_list()
    
    return [
        {
            "id": str(ticket.id),
            "title": ticket.title,
            "status": ticket.status,
            "priority": ticket.priority,
            "customer_id": ticket.customer_id,
            "assigned_to": ticket.assigned_to,
            "created_at": ticket.created_at,
            "updated_at": ticket.updated_at
        }
        for ticket in tickets
    ]


@router.put("/tickets/{ticket_id}/assign")
async def assign_ticket(
    ticket_id: str,
    assigned_to: Optional[str] = None,
    current_user: User = Depends(get_current_admin)
):
    """Assign a ticket to an admin."""
    ticket = await Ticket.get(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    ticket.assigned_to = assigned_to
    await ticket.save()
    
    # Log activity
    activity_log = ActivityLog(
        user_id=str(current_user.id),
        action="assign_ticket",
        resource_type="ticket",
        resource_id=ticket_id,
        details={"assigned_to": assigned_to}
    )
    await activity_log.insert()
    
    return {"message": "Ticket assignment updated"}


@router.put("/tickets/{ticket_id}/status")
async def update_ticket_status(
    ticket_id: str,
    status_data: dict,
    current_user: User = Depends(get_current_admin)
):
    """Update ticket status."""
    ticket = await Ticket.get(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    new_status = status_data.get("status")
    if new_status not in ["open", "in_progress", "resolved", "closed"]:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    ticket.status = TicketStatus(new_status)
    await ticket.save()
    
    # Log activity
    activity_log = ActivityLog(
        user_id=str(current_user.id),
        action="update_ticket_status",
        resource_type="ticket",
        resource_id=ticket_id,
        details={"new_status": new_status, "old_status": ticket.status}
    )
    await activity_log.insert()
    
    return {"message": "Ticket status updated successfully"}


# Activity Logs (Super admin only)
@router.get("/activity-logs")
async def get_activity_logs(
    limit: int = 100,
    current_user: User = Depends(get_current_SuperAdmin)
):
    """Get system activity logs (Super admin only)."""
    logs = await ActivityLog.find_all().sort(-ActivityLog.created_at).limit(limit).to_list()
    
    return [
        {
            "id": str(log.id),
            "user_id": log.user_id,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "details": log.details,
            "created_at": log.created_at
        }
        for log in logs
    ]
