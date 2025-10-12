"""
API endpoints for Knowledge Base Re-indexing (Super Admin Only)
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List
from app.domain.entities import Admin
from app.api.dependencies import get_current_admin
from app.core.permissions import Permission
from app.api.dependencies import get_current_admin_with_permission
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter()


class ReindexRequest(BaseModel):
    """درخواست re-indexing"""
    mode: str = Field(..., description="نوع عملیات: all, single, multiple")
    article_id: Optional[str] = Field(None, description="ID مقاله (برای mode=single)")
    article_ids: Optional[List[str]] = Field(None, description="لیست ID مقالات (برای mode=multiple)")
    article_title: Optional[str] = Field(None, description="عنوان مقاله (برای mode=single)")
    article_titles: Optional[List[str]] = Field(None, description="لیست عناوین (برای mode=multiple)")
    remove_old: bool = Field(True, description="حذف chunks قبلی")
    clear_all_first: bool = Field(False, description="پاکسازی کامل Weaviate قبل از شروع")


class ReindexResponse(BaseModel):
    """پاسخ عملیات re-indexing"""
    success: bool
    message: str
    task_id: Optional[str] = None
    details: Optional[dict] = None


# ذخیره وضعیت job های در حال اجرا
reindex_jobs = {}


async def run_reindex_job(job_id: str, request: ReindexRequest):
    """اجرای job re-indexing در background"""
    try:
        reindex_jobs[job_id] = {
            "status": "running",
            "progress": 0,
            "message": "در حال راه‌اندازی...",
            "started_at": datetime.now().isoformat(),
            "details": {}
        }
        
        # Import here to avoid circular dependency
        from motor.motor_asyncio import AsyncIOMotorClient
        from app.core.config import settings
        from app.infrastructure.connection_manager import weaviate_client
        from app.infrastructure.markdown_parser import markdown_parser
        from openai import OpenAI
        from weaviate.classes.config import Configure, Property, DataType
        
        # اتصال به MongoDB
        mongodb_client = AsyncIOMotorClient(settings.database_url)
        db = mongodb_client.get_database()
        
        # اتصال به OpenAI
        openai_client = OpenAI(
            api_key=settings.embedder_api_key_loaded,
            base_url=settings.embedder_openai_base_url_loaded
        )
        
        reindex_jobs[job_id]["message"] = "اتصال به پایگاه‌های داده برقرار شد"
        reindex_jobs[job_id]["progress"] = 10
        
        # مرحله 1: پاکسازی (در صورت نیاز)
        if request.clear_all_first:
            reindex_jobs[job_id]["message"] = "پاکسازی Weaviate..."
            logger.info(f"[Job {job_id}] پاکسازی Weaviate collection")
            
            try:
                with weaviate_client() as client:
                    try:
                        client.collections.delete("MarkdownNode")
                        logger.info(f"[Job {job_id}] Collection حذف شد")
                    except:
                        pass
                    
                    # ایجاد مجدد
                    vectorizer_config = Configure.Vectorizer.none()
                    client.collections.create(
                        name="MarkdownNode",
                        vectorizer_config=vectorizer_config,
                        properties=[
                            Property(name="node_id", data_type=DataType.TEXT),
                            Property(name="article_id", data_type=DataType.TEXT),
                            Property(name="title", data_type=DataType.TEXT),
                            Property(name="content", data_type=DataType.TEXT),
                            Property(name="full_content", data_type=DataType.TEXT),
                            Property(name="level", data_type=DataType.INT),
                            Property(name="path", data_type=DataType.TEXT),
                            Property(name="order", data_type=DataType.INT),
                            Property(name="parent_id", data_type=DataType.TEXT),
                            Property(name="visibility", data_type=DataType.TEXT),
                            Property(name="category", data_type=DataType.TEXT),
                        ]
                    )
                    logger.info(f"[Job {job_id}] Collection جدید ایجاد شد")
            except Exception as e:
                logger.error(f"[Job {job_id}] خطا در پاکسازی: {e}")
                reindex_jobs[job_id]["status"] = "failed"
                reindex_jobs[job_id]["message"] = f"خطا در پاکسازی: {str(e)}"
                return
        
        reindex_jobs[job_id]["progress"] = 20
        
        # مرحله 2: بازیابی مقالات
        reindex_jobs[job_id]["message"] = "بازیابی مقالات از MongoDB..."
        
        query = {}
        if request.mode == "single":
            if request.article_id:
                from bson import ObjectId
                try:
                    query["_id"] = ObjectId(request.article_id)
                except:
                    query["_id"] = request.article_id
            elif request.article_title:
                query["title"] = {"$regex": request.article_title, "$options": "i"}
        elif request.mode == "multiple":
            query["$or"] = []
            if request.article_ids:
                from bson import ObjectId
                for aid in request.article_ids:
                    try:
                        query["$or"].append({"_id": ObjectId(aid)})
                    except:
                        query["$or"].append({"_id": aid})
            if request.article_titles:
                for title in request.article_titles:
                    query["$or"].append({"title": {"$regex": title, "$options": "i"}})
        # mode == "all": query خالی می‌ماند
        
        query["status"] = "published"
        
        articles_cursor = db.knowledge_base_articles.find(query)
        articles = await articles_cursor.to_list(length=None)
        
        total_articles = len(articles)
        logger.info(f"[Job {job_id}] {total_articles} مقاله پیدا شد")
        
        if total_articles == 0:
            reindex_jobs[job_id]["status"] = "completed"
            reindex_jobs[job_id]["message"] = "هیچ مقاله‌ای برای پردازش پیدا نشد"
            reindex_jobs[job_id]["progress"] = 100
            return
        
        reindex_jobs[job_id]["details"]["total_articles"] = total_articles
        reindex_jobs[job_id]["progress"] = 30
        
        # مرحله 3: پردازش و ایندکس
        successful = 0
        failed = 0
        total_chunks = 0
        
        for idx, article in enumerate(articles, 1):
            try:
                article_id = str(article["_id"])
                title = article.get("title", "بدون عنوان")
                content = article.get("content_markdown", "")
                
                # بروزرسانی پیشرفت
                progress = 30 + int((idx / total_articles) * 60)
                reindex_jobs[job_id]["progress"] = progress
                reindex_jobs[job_id]["message"] = f"پردازش {idx}/{total_articles}: {title[:50]}..."
                
                logger.info(f"[Job {job_id}] پردازش [{idx}/{total_articles}]: {title}")
                
                if not content or len(content.strip()) < 10:
                    logger.warning(f"[Job {job_id}] محتوای خالی: {title}")
                    failed += 1
                    continue
                
                # حذف chunks قبلی
                if request.remove_old:
                    try:
                        with weaviate_client() as client:
                            collection = client.collections.get("MarkdownNode")
                            collection.data.delete_many(
                                where={
                                    "path": ["article_id"],
                                    "operator": "Equal",
                                    "valueText": article_id
                                }
                            )
                    except Exception as e:
                        logger.warning(f"[Job {job_id}] خطا در حذف chunks قبلی: {e}")
                
                # پارس و تقسیم
                tree = markdown_parser.parse_to_tree(content, article_id, article_title=title)
                nodes = tree.get_all_nodes()
                
                logger.info(f"[Job {job_id}] {len(nodes)} chunk ایجاد شد")
                
                # تولید embeddings
                texts_to_vectorize = [f"{node.title}\n\n{node.content}" for node in nodes]
                embedder_model = settings.embedder_model_loaded
                
                response = openai_client.embeddings.create(
                    model=embedder_model,
                    input=texts_to_vectorize
                )
                vectors = [item.embedding for item in response.data]
                
                # ذخیره در Weaviate
                with weaviate_client() as client:
                    collection = client.collections.get("MarkdownNode")
                    
                    visibility = article.get("visibility", "public")
                    category = article.get("category", {}).get("name", "عمومی") if isinstance(article.get("category"), dict) else "عمومی"
                    full_article_content = content
                    
                    with collection.batch.dynamic() as batch:
                        for node, vector in zip(nodes, vectors):
                            properties = {
                                "node_id": node.id,
                                "article_id": article_id,
                                "title": node.title,
                                "content": node.content,
                                "full_content": full_article_content[:2000],
                                "level": node.level,
                                "path": node.path,
                                "order": node.order,
                                "parent_id": node.parent_id or "",
                                "visibility": visibility,
                                "category": category
                            }
                            batch.add_object(properties=properties, vector=vector)
                
                total_chunks += len(nodes)
                successful += 1
                logger.info(f"[Job {job_id}] ✅ {len(nodes)} chunk ذخیره شد")
                
            except Exception as e:
                logger.error(f"[Job {job_id}] خطا در پردازش '{title}': {e}")
                failed += 1
                continue
        
        # تکمیل
        reindex_jobs[job_id]["status"] = "completed"
        reindex_jobs[job_id]["progress"] = 100
        reindex_jobs[job_id]["message"] = f"تکمیل شد! {successful} موفق، {failed} ناموفق"
        reindex_jobs[job_id]["completed_at"] = datetime.now().isoformat()
        reindex_jobs[job_id]["details"].update({
            "successful": successful,
            "failed": failed,
            "total_chunks": total_chunks
        })
        
        logger.info(f"[Job {job_id}] ✅ عملیات تکمیل شد")
        
        mongodb_client.close()
        
    except Exception as e:
        logger.error(f"[Job {job_id}] ❌ خطای غیرمنتظره: {e}", exc_info=True)
        reindex_jobs[job_id]["status"] = "failed"
        reindex_jobs[job_id]["message"] = f"خطا: {str(e)}"
        reindex_jobs[job_id]["progress"] = 0


@router.post("/reindex", response_model=ReindexResponse, tags=["Super Admin - Re-indexing"])
async def reindex_knowledge_base(
    request: ReindexRequest,
    background_tasks: BackgroundTasks,
    current_admin: Admin = Depends(get_current_admin_with_permission(Permission.MANAGE_KB_ARTICLES))
):
    """
    🔄 Re-indexing پایگاه دانش
    
    - **all**: ایندکس مجدد همه مقالات
    - **single**: ایندکس یک مقاله با ID یا عنوان
    - **multiple**: ایندکس چند مقاله
    """
    try:
        # اعتبارسنجی
        if request.mode == "single":
            if not request.article_id and not request.article_title:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="برای mode=single باید article_id یا article_title مشخص شود"
                )
        elif request.mode == "multiple":
            if not request.article_ids and not request.article_titles:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="برای mode=multiple باید article_ids یا article_titles مشخص شود"
                )
        
        # ایجاد job ID
        import uuid
        job_id = str(uuid.uuid4())
        
        # اضافه کردن به background tasks
        background_tasks.add_task(run_reindex_job, job_id, request)
        
        logger.info(f"Re-indexing job {job_id} شروع شد توسط {current_admin.email}")
        
        return ReindexResponse(
            success=True,
            message="عملیات re-indexing در پس‌زمینه شروع شد",
            task_id=job_id,
            details={"mode": request.mode}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"خطا در شروع re-indexing: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"خطا در شروع عملیات: {str(e)}"
        )


@router.get("/reindex/status/{job_id}", tags=["Super Admin - Re-indexing"])
async def get_reindex_status(
    job_id: str,
    current_admin: Admin = Depends(get_current_admin)
):
    """دریافت وضعیت یک job re-indexing"""
    if job_id not in reindex_jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job پیدا نشد"
        )
    
    return reindex_jobs[job_id]


@router.get("/reindex/jobs", tags=["Super Admin - Re-indexing"])
async def get_all_reindex_jobs(
    current_admin: Admin = Depends(get_current_admin)
):
    """دریافت لیست همه job های re-indexing"""
    return {
        "jobs": list(reindex_jobs.values()),
        "total": len(reindex_jobs)
    }


@router.get("/reindex/debug", tags=["Super Admin - Re-indexing"])
async def debug_reindex_status(
    current_admin: Admin = Depends(get_current_admin)
):
    """بررسی وضعیت MongoDB و Weaviate برای debugging"""
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        from app.core.config import settings
        from app.infrastructure.connection_manager import weaviate_client
        
        # اتصال به MongoDB
        mongodb_client = AsyncIOMotorClient(settings.database_url)
        db = mongodb_client.get_database()
        
        # شمارش مقالات در MongoDB
        total_articles = await db.knowledge_base_articles.count_documents({})
        published_articles = await db.knowledge_base_articles.count_documents({"status": "published"})
        
        # نمونه مقالات
        sample_articles = []
        async for article in db.knowledge_base_articles.find({"status": "published"}).limit(5):
            sample_articles.append({
                "id": str(article["_id"]),
                "title": article.get("title", ""),
                "content_length": len(article.get("content_markdown", ""))
            })
        
        # شمارش chunks در Weaviate
        weaviate_chunks = 0
        weaviate_error = None
        try:
            with weaviate_client() as client:
                collection = client.collections.get("MarkdownNode")
                # دریافت تعداد اشیاء
                result = collection.aggregate.over_all(total_count=True)
                weaviate_chunks = result.total_count if hasattr(result, 'total_count') else 0
        except Exception as e:
            weaviate_error = str(e)
        
        mongodb_client.close()
        
        return {
            "mongodb": {
                "total_articles": total_articles,
                "published_articles": published_articles,
                "sample_articles": sample_articles
            },
            "weaviate": {
                "total_chunks": weaviate_chunks,
                "error": weaviate_error
            },
            "embedder_config": {
                "model": settings.embedder_model_loaded,
                "api_key_set": bool(settings.embedder_api_key_loaded),
                "base_url": settings.embedder_openai_base_url_loaded
            }
        }
        
    except Exception as e:
        logger.error(f"Debug error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Debug error: {str(e)}"
        )

