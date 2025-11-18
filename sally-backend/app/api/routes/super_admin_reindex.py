"""
API endpoints for Knowledge Base Re-indexing (Super Admin Only)
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List
from app.domain.entities import Admin, KnowledgeBaseArticle
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
        from weaviate.classes.config import Configure, Property, DataType
        
        # اتصال به MongoDB - استفاده از MONGODB_URL از config.py
        mongodb_client = AsyncIOMotorClient(settings.MONGODB_URL)
        db = mongodb_client.get_database()
        
        # ❌ حذف اتصال به OpenAI - تولید embeddings توسط Weaviate انجام می‌شود
        
        reindex_jobs[job_id]["message"] = "اتصال به پایگاه‌های داده برقرار شد"
        reindex_jobs[job_id]["progress"] = 10
        
        # مرحله 1: اطمینان از وجود collection یکپارچه (بدون پاکسازی)
        reindex_jobs[job_id]["message"] = "بررسی Collection یکپارچه..."
        logger.info(f"[Job {job_id}] بررسی Collection یکپارچه")

        try:
            with weaviate_client() as client:
                from app.core.weaviate_utils import get_weaviate_collection_name

                collection_name = get_weaviate_collection_name()

                # پاکسازی collection موجود اگر clear_all_first=True
                if request.clear_all_first:
                    try:
                        client.collections.delete(collection_name)
                        logger.info(f"[Job {job_id}] Collection {collection_name} حذف شد")
                    except:
                        pass

                # اگر collection وجود نداشت، آن را ایجاد کن
                if not client.collections.exists(collection_name):
                    from app.core.weaviate_utils import create_unified_collection
                    success = create_unified_collection()
                    if not success:
                        raise Exception("فشل در ایجاد Collection یکپارچه")
                    logger.info(f"[Job {job_id}] Collection {collection_name} ایجاد شد")
                else:
                    logger.info(f"[Job {job_id}] Collection {collection_name} از قبل موجود است")

        except Exception as e:
            logger.error(f"[Job {job_id}] خطا در بررسی Collection یکپارچه: {e}")
            reindex_jobs[job_id]["status"] = "failed"
            reindex_jobs[job_id]["message"] = f"خطا در بررسی Collection یکپارچه: {str(e)}"
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
        
        # مرحله 3: استفاده از دکمه همگام‌سازی برای همه مقالات
        successful = 0
        failed = 0
        total_chunks = 0

        from app.infrastructure.knowledge_base_repository import KnowledgeBaseRepository
        knowledge_base_repository = KnowledgeBaseRepository()

        for idx, article in enumerate(articles, 1):
            try:
                article_id = str(article["_id"])
                title = article.get("title", "بدون عنوان")

                # بروزرسانی پیشرفت
                progress = 30 + int((idx / total_articles) * 60)
                reindex_jobs[job_id]["progress"] = progress
                reindex_jobs[job_id]["message"] = f"همگام‌سازی {idx}/{total_articles}: {title[:50]}..."

                logger.info(f"[Job {job_id}] همگام‌سازی [{idx}/{total_articles}]: {title}")

                # ایجاد مقاله کلاس برای استفاده از متد دکمه همگام‌سازی
                temp_article = KnowledgeBaseArticle(
                    id=article_id,
                    title=title,
                    content_markdown=article.get("content_markdown", ""),
                    content_html="",
                    status="published",
                    visibility=article.get("visibility", "public"),
                    category=article.get("category"),
                    tags=[],
                    summary=article.get("summary"),
                    author_id="reindex",
                    version=1,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    last_synced_at=None
                )

                # استفاده از متد دکمه همگام‌سازی (Server-Side پیش‌فرض)
                try:
                    await knowledge_base_repository._sync_to_weaviate(
                        article=temp_article,
                        operation="create"
                    )
                except Exception as sync_error:
                    logger.error(f"[Job {job_id}] خطا در همگام‌سازی داخلی '{title}': {sync_error}")
                    # برای جلوگیری از شکست کل عملیات، خطا را raise نکنید
                    # اما خطا را log کنیم تا قابل پیگیری باشد
                    failed += 1
                    continue

                # محاسبه chunks برای آمار
                try:
                    tree = markdown_parser.parse_to_tree(
                        article.get("content_markdown", ""),
                        article_id,
                        article_title=title
                    )
                    nodes = tree.get_all_nodes()
                    total_chunks += len(nodes)
                    logger.info(f"[Job {job_id}] ✅ {len(nodes)} chunk همگام‌سازی شد")
                except Exception as parse_error:
                    logger.warning(f"[Job {job_id}] خطا در پارس کردن مقاله '{title}': {parse_error}")
                    total_chunks += 1  # حداقل یک chunk

                successful += 1

            except Exception as e:
                logger.error(f"[Job {job_id}] خطا در همگام‌سازی '{title}': {e}")
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
    🔄 همگام‌سازی پایگاه دانش با استفاده از دکمه همگام‌سازی

    - **all**: همگام‌سازی همه مقالات منتشر شده
    - **single**: همگام‌سازی یک مقاله با ID یا عنوان
    - **multiple**: همگام‌سازی چند مقاله
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
    """
    🔍 بررسی وضعیت MongoDB و Weaviate برای debugging
    
    اطلاعات بازگشتی:
    - MongoDB: تعداد مقالات، نمونه مقالات
    - Weaviate: تعداد chunks، تعداد مقالات ایندکس شده، نمونه chunks
    - Embedder Config: تنظیمات مدل embedding
    - Chunking Config: استراتژی chunking
    """
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        from app.core.config import settings
        from app.infrastructure.connection_manager import weaviate_client
        
        # اتصال به MongoDB - استفاده از MONGODB_URL از config.py
        mongodb_client = AsyncIOMotorClient(settings.MONGODB_URL)
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
        
        # شمارش و نمونه‌برداری از chunks در Weaviate
        weaviate_chunks = 0
        weaviate_sample_chunks = []
        weaviate_articles_count = 0
        weaviate_error = None
        try:
            with weaviate_client() as client:
                collection = client.collections.get("MarkdownNode")
                
                # دریافت تعداد کل chunks
                result = collection.aggregate.over_all(total_count=True)
                weaviate_chunks = result.total_count if hasattr(result, 'total_count') else 0
                
                # دریافت نمونه chunks (5 عدد اول)
                query_result = collection.query.fetch_objects(limit=5)
                for obj in query_result.objects:
                    props = obj.properties
                    weaviate_sample_chunks.append({
                        "article_id": props.get("article_id", "N/A"),
                        "title": props.get("title", "N/A"),
                        "content_preview": props.get("content", "")[:100] + "..." if props.get("content") else "",
                        "content_length": len(props.get("content", "")),
                        "level": props.get("level", 0),
                        "visibility": props.get("visibility", "N/A"),
                        "category": props.get("category", "N/A"),
                    })
                
                # شمارش تعداد article_id های یکتا
                try:
                    # گروه‌بندی بر اساس article_id
                    agg_result = collection.aggregate.over_all(
                        group_by="article_id"
                    )
                    if hasattr(agg_result, 'groups') and agg_result.groups:
                        weaviate_articles_count = len(agg_result.groups)
                except:
                    # اگر group by کار نکرد، از روش دستی استفاده می‌کنیم
                    article_ids = set()
                    all_chunks = collection.query.fetch_objects(limit=10000)
                    for obj in all_chunks.objects:
                        article_ids.add(obj.properties.get("article_id"))
                    weaviate_articles_count = len(article_ids)
                    
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
                "indexed_articles_count": weaviate_articles_count,
                "avg_chunks_per_article": round(weaviate_chunks / weaviate_articles_count, 2) if weaviate_articles_count > 0 else 0,
                "sample_chunks": weaviate_sample_chunks,
                "error": weaviate_error
            },
            "embedder_config": {
                "model": settings.embedder_model_loaded,
                "api_key_set": bool(settings.embedder_api_key_loaded),
                "base_url": settings.embedder_openai_base_url_loaded
            },
            "chunking_config": {
                "max_chunk_size": 512,
                "chunk_overlap": 50,
                "strategy": "Small-to-Big Retrieval"
            }
        }
        
    except Exception as e:
        logger.error(f"Debug error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Debug error: {str(e)}"
        )


@router.get("/reindex/debug/article/{article_id}", tags=["Super Admin - Re-indexing"])
async def debug_article_chunks(
    article_id: str,
    current_admin: Admin = Depends(get_current_admin)
):
    """
    🔍 مشاهده تمام chunks یک مقاله خاص در Weaviate
    
    این endpoint برای دیباگ و بررسی نحوه تقسیم یک مقاله به chunks مفید است.
    """
    try:
        from app.infrastructure.connection_manager import weaviate_client
        from weaviate.classes.query import Filter
        
        with weaviate_client() as client:
            collection = client.collections.get("MarkdownNode")
            
            # جستجوی chunks این مقاله
            query_result = collection.query.fetch_objects(
                filters=Filter.by_property("article_id").equal(article_id),
                limit=1000
            )
            
            chunks = []
            for obj in query_result.objects:
                props = obj.properties
                chunks.append({
                    "node_id": props.get("node_id", ""),
                    "title": props.get("title", ""),
                    "content": props.get("content", ""),
                    "content_length": len(props.get("content", "")),
                    "level": props.get("level", 0),
                    "path": props.get("path", ""),
                    "order": props.get("order", 0),
                    "parent_id": props.get("parent_id", ""),
                    "visibility": props.get("visibility", ""),
                    "category": props.get("category", "")
                })
            
            # مرتب‌سازی بر اساس order
            chunks.sort(key=lambda x: x["order"])
            
            # محاسبه آمار
            if chunks:
                chunk_sizes = [c["content_length"] for c in chunks]
                stats = {
                    "total_chunks": len(chunks),
                    "avg_chunk_size": round(sum(chunk_sizes) / len(chunk_sizes), 2),
                    "min_chunk_size": min(chunk_sizes),
                    "max_chunk_size": max(chunk_sizes),
                    "total_content_length": sum(chunk_sizes)
                }
            else:
                stats = {
                    "total_chunks": 0,
                    "message": "هیچ chunk‌ای برای این مقاله پیدا نشد"
                }
            
            return {
                "article_id": article_id,
                "stats": stats,
                "chunks": chunks
            }
            
    except Exception as e:
        logger.error(f"Debug article error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Debug error: {str(e)}"
        )
@router.post("/create-server-side-collection", tags=["Super Admin - Collections"])
async def create_server_side_collection(
    current_admin: Admin = Depends(get_current_admin_with_permission(Permission.MANAGE_KB_ARTICLES))
):
    """
    🔧 ایجاد Server-Side Collection برای vectorization توسط Weaviate
    
    این collection برای روش Server-Side Vectorization استفاده می‌شود.
    """
    try:
        from app.core.weaviate_utils import create_unified_collection
        
        success = create_unified_collection()
        
        if success:
            return {
                "success": True,
                "message": "Collection یکپارچه با موفقیت ایجاد شد",
                "collection_name": "MarkdownNode"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="خطا در ایجاد Collection یکپارچه"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"خطا در ایجاد Server-Side Collection: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"خطا در ایجاد collection: {str(e)}"
        )


@router.post("/sync-all-articles", response_model=ReindexResponse, tags=["Super Admin - Sync"])
async def sync_all_articles_to_weaviate(
    request: ReindexRequest,
    background_tasks: BackgroundTasks,
    current_admin: Admin = Depends(get_current_admin_with_permission(Permission.MANAGE_KB_ARTICLES))
):
    """
    🔄 همگام‌سازی همه مقالات منتشر شده با استفاده از دکمه همگام‌سازی

    این endpoint همه مقالات منتشر شده را با استفاده از مکانیسم دکمه همگام‌سازی همگام می‌کند.
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
        
        # اضافه کردن به background tasks با sync logic
        background_tasks.add_task(run_sync_job, job_id, request)

        logger.info(f"Sync job {job_id} شروع شد توسط {current_admin.email}")

        return ReindexResponse(
            success=True,
            message="عملیات همگام‌سازی در پس‌زمینه شروع شد",
            task_id=job_id,
            details={"mode": request.mode, "method": "sync_button"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"خطا در شروع server-side re-indexing: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"خطا در شروع عملیات: {str(e)}"
        )


async def run_sync_job(job_id: str, request: ReindexRequest):
    """اجرای job همگام‌سازی با استفاده از دکمه همگام‌سازی در background"""
    try:
        reindex_jobs[job_id] = {
            "status": "running",
            "progress": 0,
            "message": "در حال راه‌اندازی همگام‌سازی...",
            "started_at": datetime.now().isoformat(),
            "details": {"method": "sync_button"}
        }
        
        # Import here to avoid circular dependency
        from motor.motor_asyncio import AsyncIOMotorClient
        from app.core.config import settings
        from app.infrastructure.connection_manager import weaviate_client
        from app.infrastructure.markdown_parser import markdown_parser
        
        # اتصال به MongoDB
        mongodb_client = AsyncIOMotorClient(settings.MONGODB_URL)
        db = mongodb_client.get_database()
        
        reindex_jobs[job_id]["message"] = "اتصال به پایگاه‌های داده برقرار شد"
        reindex_jobs[job_id]["progress"] = 10
        
        # مرحله 1: اطمینان از وجود Collection یکپارچه
        reindex_jobs[job_id]["message"] = "آماده‌سازی Collection یکپارچه..."
        logger.info(f"[Job {job_id}] آماده‌سازی Collection یکپارچه")

        try:
            from app.core.weaviate_utils import get_weaviate_collection_name

            with weaviate_client() as client:
                collection_name = get_weaviate_collection_name()

                # اگر collection وجود نداشت، آن را ایجاد کن
                if not client.collections.exists(collection_name):
                    from app.core.weaviate_utils import create_unified_collection
                    success = create_unified_collection()
                    if not success:
                        raise Exception("فشل در ایجاد Collection یکپارچه")

                logger.info(f"[Job {job_id}] Collection یکپارچه آماده: {collection_name}")

        except Exception as e:
            logger.error(f"[Job {job_id}] خطا در آماده‌سازی Collection یکپارچه: {e}")
            reindex_jobs[job_id]["status"] = "failed"
            reindex_jobs[job_id]["message"] = f"خطا در آماده‌سازی Collection یکپارچه: {str(e)}"
            return
        
        reindex_jobs[job_id]["progress"] = 20
        
        # مرحله 2: بازیابی مقالات (مانند قبل)
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
        
        # مرحله 3: استفاده از دکمه همگام‌سازی برای همه مقالات (Server-Side)
        successful = 0
        failed = 0
        total_chunks = 0

        from app.infrastructure.knowledge_base_repository import KnowledgeBaseRepository
        knowledge_base_repository = KnowledgeBaseRepository()

        for idx, article in enumerate(articles, 1):
            try:
                article_id = str(article["_id"])
                title = article.get("title", "بدون عنوان")

                # بروزرسانی پیشرفت
                progress = 30 + int((idx / total_articles) * 60)
                reindex_jobs[job_id]["progress"] = progress
                reindex_jobs[job_id]["message"] = f"همگام‌سازی {idx}/{total_articles}: {title[:50]}..."

                logger.info(f"[Job {job_id}] همگام‌سازی [{idx}/{total_articles}]: {title}")

                # ایجاد مقاله کلاس برای استفاده از متد دکمه همگام‌سازی
                temp_article = KnowledgeBaseArticle(
                    id=article_id,
                    title=title,
                    content_markdown=article.get("content_markdown", ""),
                    content_html="",
                    status="published",
                    visibility=article.get("visibility", "public"),
                    category=article.get("category"),
                    tags=[],
                    summary=article.get("summary"),
                    author_id="reindex",
                    version=1,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    last_synced_at=None
                )

                # استفاده از متد دکمه همگام‌سازی (Server-Side پیش‌فرض)
                try:
                    await knowledge_base_repository._sync_to_weaviate(
                        article=temp_article,
                        operation="create"
                    )
                except Exception as sync_error:
                    logger.error(f"[Job {job_id}] خطا در همگام‌سازی داخلی '{title}': {sync_error}")
                    raise sync_error

                # محاسبه chunks برای آمار
                tree = markdown_parser.parse_to_tree(
                    article.get("content_markdown", ""),
                    article_id,
                    article_title=title
                )
                nodes = tree.get_all_nodes()

                total_chunks += len(nodes)
                successful += 1
                logger.info(f"[Job {job_id}] ✅ {len(nodes)} chunk همگام‌سازی شد")

            except Exception as e:
                logger.error(f"[Job {job_id}] خطا در همگام‌سازی '{title}': {e}")
                failed += 1
                continue
        
        # تکمیل
        reindex_jobs[job_id]["status"] = "completed"
        reindex_jobs[job_id]["progress"] = 100
        reindex_jobs[job_id]["message"] = f"همگام‌سازی تکمیل شد! {successful} موفق، {failed} ناموفق"
        reindex_jobs[job_id]["completed_at"] = datetime.now().isoformat()
        reindex_jobs[job_id]["details"].update({
            "successful": successful,
            "failed": failed,
            "total_chunks": total_chunks,
            "method": "sync_button"
        })

        logger.info(f"[Job {job_id}] ✅ عملیات همگام‌سازی تکمیل شد")
        
        mongodb_client.close()
        
    except Exception as e:
        logger.error(f"[Job {job_id}] ❌ خطای غیرمنتظره: {e}", exc_info=True)
        reindex_jobs[job_id]["status"] = "failed"
        reindex_jobs[job_id]["message"] = f"خطا: {str(e)}"
        reindex_jobs[job_id]["progress"] = 0


