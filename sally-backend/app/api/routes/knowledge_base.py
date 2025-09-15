from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from pydantic import BaseModel
from app.domain.entities import KnowledgeBaseArticle, Category, Tag, ArticleStatus, ArticleVisibility
from app.api.dependencies import get_optional_user, get_current_user
from app.domain.entities import User

router = APIRouter()


class ArticleResponse(BaseModel):
    id: str
    title: str
    content: str
    summary: Optional[str]
    category_id: Optional[str]
    tags: List[str]
    status: ArticleStatus
    visibility: Optional[ArticleVisibility]
    created_at: str
    updated_at: str


class CategoryResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    is_public: bool


@router.get("/articles", response_model=List[ArticleResponse])
async def get_public_articles(
    category_id: Optional[str] = None,
    search: Optional[str] = None
):
    """Get public knowledge base articles (visible to guests)."""
    query = (KnowledgeBaseArticle.status == ArticleStatus.PUBLISHED) & \
            (KnowledgeBaseArticle.visibility == ArticleVisibility.PUBLIC)
    
    if category_id:
        query = query & (KnowledgeBaseArticle.category_id == category_id)
    
    articles = await KnowledgeBaseArticle.find(query).to_list()
    
    # Simple search filter
    if search:
        search_lower = search.lower()
        articles = [
            article for article in articles
            if search_lower in article.title.lower() or search_lower in article.content.lower()
        ]
    
    return [
        ArticleResponse(
            id=str(article.id),
            title=article.title,
            content=article.content,
            summary=article.summary,
            category_id=article.category_id,
            tags=article.tags,
            status=article.status,
            visibility=article.visibility,
            created_at=article.created_at.isoformat(),
            updated_at=article.updated_at.isoformat()
        )
        for article in articles
    ]


@router.get("/customer/articles", response_model=List[ArticleResponse])
async def get_customer_articles(
    category_id: Optional[str] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get knowledge base articles for authenticated customers."""
    query = (KnowledgeBaseArticle.status == ArticleStatus.PUBLISHED) & \
            (KnowledgeBaseArticle.visibility.in_([ArticleVisibility.PUBLIC, ArticleVisibility.CUSTOMER]))
    
    if category_id:
        query = query & (KnowledgeBaseArticle.category_id == category_id)
    
    articles = await KnowledgeBaseArticle.find(query).to_list()
    
    # Simple search filter
    if search:
        search_lower = search.lower()
        articles = [
            article for article in articles
            if search_lower in article.title.lower() or search_lower in article.content.lower()
        ]
    
    return [
        ArticleResponse(
            id=str(article.id),
            title=article.title,
            content=article.content,
            summary=article.summary,
            category_id=article.category_id,
            tags=article.tags,
            status=article.status,
            visibility=article.visibility,
            created_at=article.created_at.isoformat(),
            updated_at=article.updated_at.isoformat()
        )
        for article in articles
    ]


@router.get("/articles/{article_id}", response_model=ArticleResponse)
async def get_article(
    article_id: str,
    current_user: Optional[User] = Depends(get_optional_user)
):
    """Get a specific article."""
    article = await KnowledgeBaseArticle.get(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    if article.status != ArticleStatus.PUBLISHED:
        raise HTTPException(status_code=404, detail="Article not found")
    
    # Check access permissions
    if not current_user:
        if article.visibility != ArticleVisibility.PUBLIC:
            raise HTTPException(status_code=403, detail="Access denied")
    else:
        if article.visibility not in [ArticleVisibility.PUBLIC, ArticleVisibility.CUSTOMER]:
            raise HTTPException(status_code=403, detail="Access denied")
    
    return ArticleResponse(
        id=str(article.id),
        title=article.title,
        content=article.content,
        summary=article.summary,
        category_id=article.category_id,
        tags=article.tags,
        status=article.status,
        visibility=article.visibility,
        created_at=article.created_at.isoformat(),
        updated_at=article.updated_at.isoformat()
    )


@router.get("/categories", response_model=List[CategoryResponse])
async def get_categories(current_user: Optional[User] = Depends(get_optional_user)):
    """Get knowledge base categories."""
    query = Category.is_public == True if not current_user else {}
    categories = await Category.find(query).to_list()
    
    return [
        CategoryResponse(
            id=str(category.id),
            name=category.name,
            description=category.description,
            is_public=category.is_public
        )
        for category in categories
    ]


@router.get("/search")
async def search_articles(
    q: str,
    current_user: Optional[User] = Depends(get_optional_user)
):
    """Search knowledge base articles."""
    # Set visibility based on authentication
    if not current_user:
        visibility_query = (KnowledgeBaseArticle.visibility == ArticleVisibility.PUBLIC)
    else:
        visibility_query = (KnowledgeBaseArticle.visibility.in_([ArticleVisibility.PUBLIC, ArticleVisibility.CUSTOMER]))
    
    query = (KnowledgeBaseArticle.status == ArticleStatus.PUBLISHED) & visibility_query
    
    articles = await KnowledgeBaseArticle.find(query).to_list()
    
    # Simple text search
    search_lower = q.lower()
    results = []
    
    for article in articles:
        score = 0
        if search_lower in article.title.lower():
            score += 10
        if search_lower in article.content.lower():
            score += 5
        if article.summary and search_lower in article.summary.lower():
            score += 7
        
        if score > 0:
            results.append({
                "id": str(article.id),
                "title": article.title,
                "summary": article.summary,
                "score": score
            })
    
    # Sort by relevance score
    results.sort(key=lambda x: x["score"], reverse=True)
    
    return {"results": results[:10]}  # Return top 10 results
