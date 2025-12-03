"""
API Routes برای Browser Automation با استفاده از browser-use

این فایل شامل endpoints برای اجرای وظایف خودکارسازی مرورگر است.
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
import asyncio
import json
import re

from app.services.browser_automation_service import (
    browser_automation_service,
    BrowserTaskResult
)
from app.services.playwright_service import playwright_service
from app.services.agentic_playwright_service import agentic_playwright_service
from app.services.model_service import ModelService
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


class AgenticAdminRequest(BaseModel):
    """درخواست ساخت ادمین با Agentic AI"""
    admin_email: str = Field(..., description="ایمیل ادمین جدید")
    admin_password: str = Field(..., description="رمز عبور ادمین جدید")
    admin_full_name: str = Field("test", description="نام کامل ادمین")
    admin_role: str = Field("Admin", description="نقش ادمین")
    login_email: str = Field(..., description="ایمیل برای لاگین")
    login_password: str = Field(..., description="رمز عبور برای لاگین")
    url: str = Field("http://localhost:3000/super-admin", description="URL پنل ادمین")
    cdp_url: Optional[str] = Field(None, description="آدرس CDP برای اتصال به مرورگر موجود (مثلاً: http://127.0.0.1:9222)")
    use_current_page: bool = Field(False, description="استفاده از صفحه فعلی بدون باز کردن browser جدید")


class NaturalLanguageRequest(BaseModel):
    """درخواست اجرای دستور زبان طبیعی"""
    command: str = Field(..., min_length=1, description="دستور زبان طبیعی (مثلاً: 'ایجاد ادمین جدید با ایمیل test@example.com')")
    login_email: Optional[str] = Field(None, description="ایمیل برای لاگین (اختیاری)")
    login_password: Optional[str] = Field(None, description="رمز عبور برای لاگین (اختیاری)")
    url: str = Field("http://localhost:3000/super-admin", description="URL پنل ادمین")
    cdp_url: Optional[str] = Field(None, description="آدرس CDP برای اتصال به مرورگر موجود (مثلاً: http://127.0.0.1:9222)")
    use_current_page: bool = Field(False, description="استفاده از صفحه فعلی بدون باز کردن browser جدید")


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


@router.post("/agentic-create-admin", response_model=BrowserTaskResponse, status_code=status.HTTP_200_OK)
async def agentic_create_admin(
    request: AgenticAdminRequest,
    current_admin: Optional[Admin] = Depends(get_optional_admin)
):
    """
    🤖 ساخت ادمین با استفاده از Agentic AI (Vision-based)
    
    این endpoint از Vision AI استفاده می‌کند تا:
    - صفحه را ببیند و تحلیل کند
    - تصمیم بگیرد چه کاری انجام دهد
    - اقدامات را با دقت بالا اجرا کند
    
    **مزایا نسبت به روش معمولی:**
    - ✅ دقت بالاتر (90-95%)
    - ✅ مقاوم در برابر تغییرات UI
    - ✅ پشتیبانی خودکار از فارسی و انگلیسی
    - ✅ تصمیم‌گیری هوشمند
    
    **نکات:**
    - نیاز به OpenAI API Key (Vision API)
    - کندتر از روش معمولی (~30-60 ثانیه)
    - هزینه: ~$0.01-0.05 per task
    
    **دسترسی:** فقط SuperAdmin و Admin
    """
    try:
        if not current_admin:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="احراز هویت لازم است"
            )
        
        logger.info(f"🤖 Agentic admin creation requested by {current_admin.email}")
        logger.info(f"📧 Admin Email: {request.admin_email}")
        
        # اجرای Agentic Playwright Service
        result = await agentic_playwright_service.create_admin(
            admin_email=request.admin_email,
            admin_password=request.admin_password,
            admin_full_name=request.admin_full_name,
            admin_role=request.admin_role,
            login_email=request.login_email,
            login_password=request.login_password,
            url=request.url,
            cdp_url=request.cdp_url,
            use_current_page=request.use_current_page
        )
        
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Agentic admin creation failed: {result.error}"
            )
        
        return BrowserTaskResponse(
            success=result.success,
            result=result.result,
            error=result.error,
            execution_time=0.0,
            metadata={
                "service": "agentic_playwright",
                "steps_taken": len(result.steps_taken) if result.steps_taken else 0,
                "screenshots": len(result.screenshots) if result.screenshots else 0,
                "executed_by": current_admin.email,
                "admin_role": current_admin.role_name or "Admin",
                "steps_detail": [
                    {
                        "iteration": step.get("iteration"),
                        "action": step.get("action"),
                        "success": step.get("success"),
                        "confidence": step.get("ai_confidence")
                    }
                    for step in (result.steps_taken or [])[-10:]  # آخرین 10 مرحله
                ]
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in agentic admin creation: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"خطا در ساخت ادمین با AI: {str(e)}"
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
    
    **استفاده از Agentic Mode:**
    برای استفاده از Vision AI (دقت بالاتر)، در task بنویسید:
    - "create admin with AI" یا "ساخت ادمین با AI"
    - "create admin agentic" یا "ساخت ادمین agentic"
    
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
        
        # بررسی اینکه آیا task مربوط به ساخت ادمین است (فارسی یا انگلیسی)
        task_lower = request.task.lower()
        task_original = request.task  # برای چک کردن فارسی
        
        # چک کردن الگوهای مختلف فارسی و انگلیسی
        is_create_admin = (
            "create admin" in task_lower or 
            "create new admin" in task_lower or
            "add admin" in task_lower or
            "add new admin" in task_lower or
            "ساخت ادمین" in task_original or 
            "ایجاد ادمین" in task_original or
            "ایجاد یه ادمین" in task_original or
            "ایجاد یک ادمین" in task_original or
            "افزودن ادمین" in task_original or
            "افزودن ادمین جدید" in task_original or
            ("ایجاد" in task_original and "ادمین" in task_original) or
            ("ساخت" in task_original and "ادمین" in task_original)
        )
        
        # لاگ برای دیباگ
        logger.info(f"🔍 Task analysis:")
        logger.info(f"   Task (first 200 chars): {request.task[:200]}")
        logger.info(f"   Task lower: {task_lower[:200]}")
        logger.info(f"   Contains 'ایجاد': {'ایجاد' in task_original}")
        logger.info(f"   Contains 'ادمین': {'ادمین' in task_original}")
        logger.info(f"   Contains 'create admin': {'create admin' in task_lower}")
        logger.info(f"   is_create_admin: {is_create_admin}")
        
        # اگر task مربوط به ساخت ادمین است، از agentic_playwright_service استفاده کن
        if is_create_admin:
            logger.info("🤖 Detected admin creation task, using Agentic Playwright service")
            
            # استخراج اطلاعات از دستور زبان طبیعی با LLM
            try:
                model_service = ModelService()
                llm = model_service.get_model(
                    model_name="google/gemini-2.5-flash",
                    temperature=0.1,
                    max_tokens=500
                )
                
                extraction_prompt = f"""
Extract admin creation details from this command (Persian or English):
{request.task}

Extract and return ONLY a JSON object with these fields:
- admin_email: email address
- admin_password: password
- admin_full_name: full name (default: "test" if not provided)
- admin_role: role (default: "Admin" if not provided)

Example response:
{{"admin_email": "test@example.com", "admin_password": "123456", "admin_full_name": "Test User", "admin_role": "Admin"}}

Return ONLY the JSON, no explanations.
"""
                
                from langchain_core.messages import HumanMessage
                human_message = HumanMessage(content=extraction_prompt)
                
                if hasattr(llm, 'ainvoke'):
                    response = await llm.ainvoke([human_message])
                elif hasattr(llm, 'invoke'):
                    response = await asyncio.to_thread(llm.invoke, [human_message])
                else:
                    raise Exception("LLM model not supported")
                
                response_text = response.content if hasattr(response, 'content') else str(response)
                response_text = response_text.strip()
                
                # استخراج JSON از پاسخ (با پشتیبانی از nested braces)
                # روش 1: اگر پاسخ JSON خالص است
                if response_text.strip().startswith('{'):
                    try:
                        admin_data = json.loads(response_text)
                    except:
                        # روش 2: پیدا کردن JSON با regex پیشرفته‌تر
                        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
                        json_matches = re.findall(json_pattern, response_text, re.DOTALL)
                        if json_matches:
                            admin_data = json.loads(max(json_matches, key=len))
                        else:
                            raise ValueError("No JSON found in response")
                else:
                    # روش 3: پیدا کردن JSON در متن
                    json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
                    json_matches = re.findall(json_pattern, response_text, re.DOTALL)
                    if json_matches:
                        admin_data = json.loads(max(json_matches, key=len))
                    else:
                        raise ValueError("No JSON found in response")
                
                logger.info(f"📝 Extracted admin data: {admin_data}")
                
            except Exception as e:
                logger.warning(f"⚠️ Failed to extract admin data from command: {e}, using defaults")
                # Fallback: استفاده از مقادیر پیش‌فرض
                admin_data = {
                    "admin_email": "test@example.com",
                    "admin_password": "123456",
                    "admin_full_name": "Test Admin",
                    "admin_role": "Admin"
                }
            
            # استفاده از agentic_playwright_service (همیشه برای دقت بالاتر)
            result = await agentic_playwright_service.create_admin(
                admin_email=admin_data.get("admin_email", "test@example.com"),
                admin_password=admin_data.get("admin_password", "123456"),
                admin_full_name=admin_data.get("admin_full_name", "Test Admin"),
                admin_role=admin_data.get("admin_role", "Admin"),
                login_email=login_email,
                login_password=login_password,
                url=admin_panel_url,
                cdp_url=request.cdp_url,
                use_current_page=request.use_current_page
            )
            
            # تبدیل AgenticPlaywrightResult به BrowserTaskResult
            if result.success:
                browser_result = BrowserTaskResult(
                    success=True,
                    result=result.result,
                    execution_time=0.0,
                    metadata={
                        "service": "agentic_playwright",
                        "steps_taken": len(result.steps_taken) if result.steps_taken else 0,
                        "screenshots": len(result.screenshots) if result.screenshots else 0,
                        "extracted_data": admin_data
                    }
                )
            else:
                browser_result = BrowserTaskResult(
                    success=False,
                    error=result.error,
                    execution_time=0.0,
                    metadata={"service": "agentic_playwright"}
                )
        else:
            # استفاده از browser-use برای وظایف دیگر
            result = await browser_automation_service.execute_task(
                task_description=enhanced_task,
                url=admin_panel_url,
                max_steps=request.max_steps or 30,
                cdp_url=request.cdp_url,
                use_current_page=request.use_current_page,
                login_email=login_email if should_login else None,
                login_password=login_password if should_login else None,
            )
            browser_result = result
        
        if not browser_result.success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Agent execution failed: {browser_result.error}"
            )
        
        return BrowserTaskResponse(
            success=browser_result.success,
            result=browser_result.result,
            error=browser_result.error,
            execution_time=browser_result.execution_time,
            metadata={
                **(browser_result.metadata or {}),
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


@router.post("/natural-language", response_model=BrowserTaskResponse, status_code=status.HTTP_200_OK)
async def execute_natural_language_command(
    request: NaturalLanguageRequest,
    current_admin: Optional[Admin] = Depends(get_optional_admin)
):
    """
    🤖 اجرای دستور زبان طبیعی با استفاده از Agentic AI
    
    این endpoint دستورات زبان طبیعی را می‌گیرد و با استفاده از LLM آن‌ها را به task description تبدیل می‌کند.
    سپس از Vision AI برای اجرای دقیق task استفاده می‌کند.
    
    **مثال دستورات:**
    - "ایجاد ادمین جدید با ایمیل test@example.com و رمز 123456"
    - "Create a new admin with email admin@test.com"
    - "ساخت کاربر جدید"
    
    **دسترسی:** Admin و SuperAdmin
    """
    import time
    start_time = time.time()
    
    try:
        if not current_admin:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="احراز هویت لازم است"
            )
        
        logger.info(f"💬 Natural language command from {current_admin.email}: {request.command}")
        
        # استفاده از LLM برای تبدیل دستور زبان طبیعی به task description
        model_service = ModelService()
        
        # ساخت prompt برای تبدیل دستور زبان طبیعی به task description
        conversion_prompt = f"""
You are a task translator. Convert the following natural language command into a detailed, step-by-step task description for browser automation.

User's command (in Persian or English): {request.command}

Context:
- This is an admin panel at: {request.url}
- The user needs to login first (if credentials provided)
- After login, execute the command

Convert this command into a detailed task description that includes:
1. Login steps (if credentials provided)
2. Navigation steps
3. Form filling steps (if needed)
4. Submission steps
5. Verification steps

Respond ONLY with the task description in English, no explanations, no markdown.

Example:
If command is "ایجاد ادمین جدید با ایمیل test@example.com و رمز 123456"
Task description should be:
"Create a new admin user with the following details:
- Email: test@example.com
- Password: 123456
- Full Name: (use default or ask user)
- Role: Admin

You need to:
1. Navigate to {request.url}
2. Login with email: {request.login_email or 'provided credentials'} and password: {request.login_password or 'provided password'}
3. Navigate to admin management section
4. Click 'Add New Admin' button
5. Fill in the form with the admin details above
6. Select the role: Admin
7. Submit the form
8. Verify success"
"""
        
        # استفاده از LLM برای تبدیل
        try:
            llm = model_service.get_model(
                model_name="google/gemini-2.5-flash",  # استفاده از مدل سریع
                temperature=0.1,
                max_tokens=1000
            )
            
            from langchain_core.messages import HumanMessage
            human_message = HumanMessage(content=conversion_prompt)
            
            if hasattr(llm, 'ainvoke'):
                response = await llm.ainvoke([human_message])
            elif hasattr(llm, 'invoke'):
                response = await asyncio.to_thread(llm.invoke, [human_message])
            else:
                raise Exception("LLM model not supported")
            
            task_description = response.content if hasattr(response, 'content') else str(response)
            task_description = task_description.strip()
            
            logger.info(f"📝 Converted task description: {task_description[:200]}...")
            
        except Exception as e:
            logger.warning(f"⚠️ LLM conversion failed: {e}, using direct command")
            # Fallback: استفاده مستقیم از command
            task_description = f"""
Execute the following command in the admin panel:
{request.command}

Steps:
1. Navigate to {request.url}
2. Login (if credentials provided)
3. Execute the command: {request.command}
4. Verify success
"""
        
        # اجرای task با agentic_playwright_service
        result = await agentic_playwright_service.execute_task(
            task_description=task_description,
            login_email=request.login_email,
            login_password=request.login_password,
            url=request.url
        )
        
        execution_time = time.time() - start_time
        
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.error or "Task execution failed"
            )
        
        return BrowserTaskResponse(
            success=result.success,
            result=result.result,
            error=result.error,
            execution_time=execution_time,
            metadata={
                "service": "agentic_playwright_natural_language",
                "steps_taken": len(result.steps_taken) if result.steps_taken else 0,
                "screenshots": len(result.screenshots) if result.screenshots else 0,
                "original_command": request.command,
                "converted_task": task_description[:500]
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in natural language command execution: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"خطا در اجرای دستور زبان طبیعی: {str(e)}"
        )
