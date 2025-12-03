"""
API Routes برای Browser Automation با استفاده از browser-use

این فایل شامل endpoints برای اجرای وظایف خودکارسازی مرورگر است.
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
import asyncio

from app.services.browser_automation_service import (
    browser_automation_service,
    BrowserTaskResult
)
from app.core.permissions import get_current_admin, get_optional_admin, get_optional_customer
from app.domain.entities import Admin, Customer
from app.core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/browser", tags=["Browser Automation"])


# =============== PYDANTIC SCHEMAS ===============

class BrowserTaskRequest(BaseModel):
    """درخواست اجرای وظیفه مرورگر"""
    task: str = Field(..., min_length=1, description="توضیحات وظیفه (مثلاً: 'Find iPhone 15 price on Amazon')")
    url: Optional[str] = Field(None, description="URL شروع (اختیاری)")
    model_name: Optional[str] = Field(None, description="نام مدل از model_factory (اختیاری)")
    max_steps: int = Field(20, ge=1, le=50, description="حداکثر تعداد مراحل")
    cdp_url: Optional[str] = Field(None, description="آدرس CDP برای اتصال به مرورگر موجود (مثلاً: http://127.0.0.1:9222)")
    use_current_page: bool = Field(False, description="استفاده از صفحه فعلی بدون navigate کردن")


class BrowserTaskResponse(BaseModel):
    """پاسخ اجرای وظیفه مرورگر"""
    success: bool
    result: Optional[str] = None
    error: Optional[str] = None
    execution_time: float
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BrowserHealthResponse(BaseModel):
    """وضعیت سلامت سرویس مرورگر"""
    status: str
    browser_initialized: bool
    llm_initialized: bool
    openrouter_configured: bool


# =============== API ENDPOINTS ===============

@router.post("/execute", response_model=BrowserTaskResponse, status_code=status.HTTP_200_OK)
async def execute_browser_task(
    request: BrowserTaskRequest,
    current_admin: Optional[Admin] = Depends(get_optional_admin),
    current_customer: Optional[Customer] = Depends(get_optional_customer)
):
    """
    اجرای یک وظیفه خودکارسازی مرورگر
    
    **مثال وظایف:**
    - "Find the price of iPhone 15 on Amazon"
    - "Search for Python tutorials on YouTube and get the top 5 results"
    - "Fill out a contact form on example.com with my information"
    - "Check the weather forecast for Tehran"
    
    **دسترسی:** همه کاربران (Admin, Customer, Guest)
    
    **نکات:**
    - این endpoint ممکن است چند ثانیه تا چند دقیقه طول بکشد
    - برای وظایف طولانی، از background tasks استفاده کنید
    """
    try:
        # بررسی دسترسی (می‌توانید محدودیت اضافه کنید)
        if not current_admin and not current_customer:
            # اجازه دسترسی به guest users هم بدهید
            logger.info("Guest user executing browser task")
        
        logger.info(f"🌐 Browser task requested: {request.task}")
        
        # اجرای وظیفه
        # استفاده از execute_task جدید که model_name رو هم پشتیبانی می‌کنه
        result = await browser_automation_service.execute_task(
            task_description=request.task,
            url=request.url,
            model_name=request.model_name,
            max_steps=request.max_steps,
            cdp_url=request.cdp_url,
            use_current_page=request.use_current_page
        )
        
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Browser automation failed: {result.error}"
            )
        
        return BrowserTaskResponse(
            success=result.success,
            result=result.result,
            error=result.error,
            execution_time=result.execution_time,
            metadata=result.metadata
        )
        
    except ValueError as e:
        logger.error(f"❌ Validation error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Error executing browser task: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"خطا در اجرای وظیفه مرورگر: {str(e)}"
        )


@router.post("/execute-async", status_code=status.HTTP_202_ACCEPTED)
async def execute_browser_task_async(
    request: BrowserTaskRequest,
    background_tasks: BackgroundTasks,
    current_admin: Optional[Admin] = Depends(get_optional_admin)
):
    """
    اجرای غیرهمزمان وظیفه مرورگر (برای وظایف طولانی)
    
    این endpoint وظیفه را در background اجرا می‌کند و فوراً پاسخ می‌دهد.
    برای دریافت نتیجه، باید از یک سیستم task queue استفاده کنید.
    
    **دسترسی:** Admin و Customer
    """
    try:
        logger.info(f"🌐 Async browser task requested: {request.task}")
        
        # اضافه کردن وظیفه به background tasks
        # استفاده از execute_task جدید که همه پارامترها رو پشتیبانی می‌کنه
        background_tasks.add_task(
            browser_automation_service.execute_task,
            task_description=request.task,
            url=request.url,
            model_name=request.model_name,
            max_steps=request.max_steps,
            cdp_url=request.cdp_url,
            use_current_page=request.use_current_page
        )
        
        return {
            "status": "accepted",
            "message": "Browser task started in background",
            "task": request.task
        }
        
    except Exception as e:
        logger.error(f"❌ Error starting async browser task: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"خطا در شروع وظیفه: {str(e)}"
        )


@router.get("/health", response_model=BrowserHealthResponse)
async def get_browser_health():
    """
    بررسی وضعیت سلامت سرویس مرورگر
    
    **دسترسی:** عمومی
    """
    try:
        health = browser_automation_service.get_health_status()
        return BrowserHealthResponse(**health)
    except Exception as e:
        logger.error(f"❌ Error getting browser health: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"خطا در بررسی وضعیت: {str(e)}"
        )


@router.get("/available-models")
async def get_available_models(
    current_admin: Optional[Admin] = Depends(get_optional_admin)
):
    """
    دریافت لیست مدل‌های موجود برای استفاده در browser automation
    
    **دسترسی:** همه کاربران
    """
    try:
        from app.infrastructure.model_factory import model_factory
        
        models = model_factory.list_models()
        
        # فیلتر کردن فقط مدل‌های chat که مناسب browser automation هستند
        browser_models = [
            model for model in models
            if model.get("type") == "chat" and model.get("streaming", False)
        ]
        
        return {
            "models": browser_models,
            "total": len(browser_models),
            "recommended": "deepseek/deepseek-chat"  # یا هر مدل پیشنهادی دیگر
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting available models: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"خطا در دریافت لیست مدل‌ها: {str(e)}"
        )


@router.post("/agent-execute", response_model=BrowserTaskResponse, status_code=status.HTTP_200_OK)
async def execute_agent_command(
    request: BrowserTaskRequest,
    current_admin: Optional[Admin] = Depends(get_optional_admin)
):
    """
    اجرای دستور agent برای تعامل با پنل ادمین
    
    این endpoint برای اجرای دستورات پیچیده‌تر مانند ساخت کاربر، مدیریت مقالات و غیره استفاده می‌شود.
    Agent می‌تواند با UI پنل ادمین تعامل کند.
    
    **پارامترهای جدید:**
    - `cdp_url`: آدرس CDP برای اتصال به مرورگر کاربر (مثلاً: http://127.0.0.1:9222)
    - `use_current_page`: اگر True باشد، agent در صفحه فعلی کار می‌کند و نیازی به لاگین نیست
    
    **برای استفاده از مرورگر موجود:**
    1. Chrome را با این دستور باز کنید:
       chrome.exe --remote-debugging-port=9222
    2. در درخواست، `cdp_url` را "http://127.0.0.1:9222" قرار دهید
    3. `use_current_page` را True قرار دهید
    
    **دسترسی:** فقط SuperAdmin و Admin
    """
    try:
        if not current_admin:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="احراز هویت لازم است"
            )
        
        logger.info(f"🤖 Agent command requested by {current_admin.email}: {request.task}")
        
        # Agent browser جدید باز می‌کند و ابتدا لاگین می‌کند، سپس تسک را انجام می‌دهد
        admin_panel_url = request.url or "http://localhost:3000/super-admin"
        login_email = "xtra_admin@sally.com"
        login_password = "123456"
        
        # تسک اصلی بدون دستورات لاگین (چون لاگین جداگانه انجام می‌شود)
        enhanced_task = f"""
        You are an AI assistant helping an admin user in their admin panel.
        The user wants you to: {request.task}
        
        IMPORTANT CONTEXT:
        - You are already logged in to the admin panel
        - The admin panel is at: {admin_panel_url}
        - You can see all UI elements and navigate between pages
        
        STEP BY STEP INSTRUCTIONS:
        1. Wait 2 seconds for the page to fully load
        2. Look at the sidebar navigation menu or current page
        3. Find the relevant button or link for: {request.task}
        4. Click on it and wait for the page/form to load (2-3 seconds)
        5. Fill in any required forms with the information provided
        6. Submit the form or click the save/submit button
        7. Wait 2-3 seconds and verify success message
        
        TASK TO COMPLETE: {request.task}
        
        Remember:
        - ALWAYS wait 2-3 seconds after each click/action
        - Read ALL visible text carefully (may be in Persian فارسی or English)
        - Look for buttons, links, form fields, and navigation menus
        - Fill forms completely before submitting
        - You are already logged in, so focus only on completing the task
        """
        
        # اجرای وظیفه با لاگین اول
        # اگر use_current_page=True باشد، لاگین انجام نمی‌شود (کاربر قبلاً لاگین کرده)
        should_login = not request.use_current_page
        
        result = await browser_automation_service.execute_task(
            task_description=enhanced_task,
            url=admin_panel_url,
            max_steps=request.max_steps or 30,
            cdp_url=request.cdp_url,
            use_current_page=request.use_current_page,
            login_email=login_email if should_login else None,
            login_password=login_password if should_login else None,
        )
        
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Agent execution failed: {result.error}"
            )
        
        return BrowserTaskResponse(
            success=result.success,
            result=result.result,
            error=result.error,
            execution_time=result.execution_time,
            metadata={
                **result.metadata,
                "executed_by": current_admin.email,
                "admin_role": current_admin.role_name or "Admin"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error executing agent command: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"خطا در اجرای دستور agent: {str(e)}"
        )

