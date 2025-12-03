"""
Browser Automation Service با پشتیبانی کامل Windows
راه‌حل NotImplementedError و CDP connection issues
"""

import asyncio
import time
import sys
import threading
from typing import Optional, Any
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from browser_use import Agent, Browser
from langchain_openai import ChatOpenAI

from app.core.logging_config import get_logger, PerformanceLogger

logger = get_logger(__name__)


class BrowserChatOpenAI(ChatOpenAI):
    """
    کلاس سفارشی ChatOpenAI که فیلدهای provider و model را برای سازگاری با browser-use دارد
    """
    model_config = {"extra": "allow"}  # اجازه فیلدهای اضافی
    provider: str = "openai"
    
    @property
    def model(self) -> str:
        return self.model_name


@dataclass
class BrowserTaskResult:
    """نتیجه اجرای task"""
    success: bool
    result: Optional[str] = None
    error: Optional[str] = None
    execution_time: float = 0.0
    metadata: dict = None


class WindowsBrowserRunner:
    """
    کلاس مخصوص اجرای browser در Windows
    همه چیز در یک thread جداگانه با ProactorEventLoop
    """
    
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=1)
    
    async def _find_existing_tab(self, cdp_endpoint: str, target_url_pattern: str = "localhost:3000") -> Optional[str]:
        """
        پیدا کردن tab موجود از طریق CDP endpoint
        
        Args:
            cdp_endpoint: آدرس CDP (مثلاً http://127.0.0.1:9222)
            target_url_pattern: بخشی از URL که باید در tab باشد
            
        Returns:
            WebSocket URL tab مورد نظر یا None
        """
        try:
            import httpx
            
            list_url = f"{cdp_endpoint}/json/list"
            logger.info(f"🔍 Finding existing tab at: {list_url}")
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(list_url)
                
                if response.status_code != 200:
                    logger.warning(f"Could not get page list: status {response.status_code}")
                    return None
                
                pages = response.json()
                logger.info(f"📑 Found {len(pages)} open tabs")
                
                # پیدا کردن tab با URL مورد نظر
                for page in pages:
                    page_url = page.get('url', '')
                    page_type = page.get('type', '')
                    ws_url = page.get('webSocketDebuggerUrl', '')
                    
                    logger.info(f"  📄 Tab: {page_url[:60]}... (type: {page_type})")
                    
                    # فقط page ها را بررسی کن (نه service worker ها و...)
                    if page_type == 'page' and target_url_pattern in page_url:
                        logger.info(f"✅ Found target tab: {page_url}")
                        return ws_url
                
                # اگر tab مورد نظر پیدا نشد، اولین page را برگردان
                for page in pages:
                    if page.get('type') == 'page' and page.get('webSocketDebuggerUrl'):
                        logger.warning(f"⚠️ Target URL not found, using first available tab: {page.get('url', '')[:60]}")
                        return page.get('webSocketDebuggerUrl')
                
                logger.warning("⚠️ No suitable tab found")
                return None
                
        except Exception as e:
            logger.warning(f"⚠️ Error finding existing tab: {e}")
            return None
    
    def _run_in_new_event_loop(self, coro):
        """
        اجرای coroutine در یک event loop جدید (ProactorEventLoop)
        """
        # ساخت event loop جدید
        if sys.platform == 'win32':
            # در Windows حتماً ProactorEventLoop
            loop = asyncio.ProactorEventLoop()
        else:
            loop = asyncio.new_event_loop()
        
        asyncio.set_event_loop(loop)
        
        try:
            return loop.run_until_complete(coro)
        finally:
            try:
                # پاکسازی کامل
                pending = asyncio.all_tasks(loop)
                for task in pending:
                    task.cancel()
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            except Exception as e:
                logger.warning(f"Cleanup warning: {e}")
            finally:
                loop.close()
        
    async def _execute_task_async(
        self,
        task_description: str,
        llm,
        url: Optional[str] = None,
        cdp_url: Optional[str] = None,
        use_current_page: bool = False,
        max_steps: int = 30,
        login_email: Optional[str] = None,
        login_password: Optional[str] = None,
    ) -> str:
        """
        اجرای task با browser - این در thread جداگانه با ProactorEventLoop اجرا میشه
        """
        browser = None
        
        try:
            logger.info("🌐 Creating browser instance...")
            
            # ساخت browser - در نسخه جدید browser-use، Browser بدون آرگومان ساخته می‌شود
            # تنظیمات از طریق متغیرهای محیطی اعمال می‌شوند
            import os
            
            # اگر CDP URL داده شده یا use_current_page=True، از مرورگر موجود استفاده کن
            if cdp_url or use_current_page:
                # اگر فقط use_current_page داده شده، از CDP پیش‌فرض استفاده کن
                actual_cdp_url = cdp_url or "http://127.0.0.1:9222"
                logger.info(f"🔗 Connecting to existing browser at: {actual_cdp_url}")
                
                # بررسی وجود tab موجود
                target_url = url or "localhost:3000"
                ws_url = await self._find_existing_tab(actual_cdp_url, target_url)
                
                if ws_url:
                    logger.info(f"✅ Found existing tab: {ws_url}")
                    logger.info("📌 Will use existing tab - no new tabs will be opened")
                else:
                    logger.warning("⚠️ No existing tab found matching target URL")
                    if use_current_page:
                        logger.warning("⚠️ use_current_page=True but no matching tab found - will use first available tab")
                
                # browser-use: استفاده از CDP endpoint
                # تنظیمات CDP از طریق متغیرهای محیطی اعمال می‌شوند
                os.environ["BROWSER_USE_EXISTING"] = "true"
                os.environ["BROWSER_CDP_URL"] = actual_cdp_url
                logger.info("✅ Browser configured to use existing browser/tab")
            else:
                # اگر از مرورگر جدید استفاده می‌کنیم، متغیرهای محیطی را پاک می‌کنیم
                os.environ.pop("BROWSER_USE_EXISTING", None)
                os.environ.pop("BROWSER_CDP_URL", None)
            
            # ساخت Browser بدون آرگومان config
            browser = Browser()
            
            # اگر login لازم بود و use_current_page=False (یعنی tab جدید باز شده)
            if login_email and login_password and not use_current_page:
                logger.info(f"🔐 Will login and execute task as one combined operation...")
                
                # ترکیب login + task در یک prompt
                combined_task = f"""
                You are a browser automation assistant. Complete these steps carefully:

                STEP 1 - LOGIN:
                1. You are now on the login page: {url or 'http://localhost:3000/super-admin'}
                2. WAIT 5 SECONDS for the page to fully load
                3. Look carefully at the page - find the email/username input field
                4. Type this email into the field: {login_email}
                5. Find the password input field
                6. Type this password: {login_password}
                7. Find and click the login/submit button
                8. WAIT 5 SECONDS after clicking to ensure login completes
                9. Verify you see the admin dashboard

                STEP 2 - MAIN TASK:
                After successful login, do this task:
                {task_description}

                IMPORTANT RULES:
                - Wait 5 seconds after each major action (page load, button click)
                - Read all visible text on the page carefully
                - If you cannot find an element, wait 3 more seconds and try again
                - The interface may be in Persian (فارسی) or English
                - Look for common patterns: input fields, buttons, links
                - Complete BOTH steps before finishing
                """
                
                enhanced_task = combined_task
                
                # لاگ‌های تشخیصی برای بررسی وضعیت browser
                logger.info("🔍 DIAGNOSTIC: About to create single combined agent")
                logger.info(f"🔍 DIAGNOSTIC: Browser object ID: {id(browser)}")
                logger.info(f"🔍 DIAGNOSTIC: Browser type: {type(browser)}")
                
            elif use_current_page:
                # اگر از tab موجود استفاده می‌کنیم، navigate نکن
                enhanced_task = f"""
                ⚠️ CRITICAL: You are using an EXISTING browser tab. DO NOT navigate or open new tabs.
                
                YOUR TASK: {task_description}
                
                IMPORTANT INSTRUCTIONS:
                1. You are already on the correct page - DO NOT navigate anywhere
                2. Wait 2 seconds for page to fully load
                3. Look at the CURRENT page carefully - read all visible text
                4. Find the relevant buttons, forms, or links on THIS page
                5. Complete the task using elements on THIS page only
                6. Fill forms and click submit buttons
                7. Wait for success/error messages
                
                DO NOT:
                - Navigate to any URL
                - Open new tabs
                - Refresh the page
                - Click back/forward buttons
                - Leave the current page
                
                Work ONLY with what you see on the current page.
                """
            elif login_email:
                # این بخش دیگر استفاده نمی‌شود چون با حالت بالا ترکیب شده
                logger.warning("⚠️ This login_email branch should not be reached with combined approach")
                enhanced_task = task_description
            else:
                enhanced_task = task_description
            
            # اجرای task اصلی
            logger.info("📋 Executing main task...")
            
            # صبر برای React
            await asyncio.sleep(3)

            # لاگ‌های تشخیصی قبل از ساخت agent
            logger.info("🔍 DIAGNOSTIC: Creating agent...")
            logger.info(f"🔍 DIAGNOSTIC: Browser still valid: {browser is not None}")
            
            main_agent = Agent(
                task=enhanced_task,
                llm=llm,
                browser=browser,
                max_steps=max_steps,
            )
            
            logger.info("🔍 DIAGNOSTIC: Agent created, about to run...")
            # logger.info(f"🔍 DIAGNOSTIC: Agent browser object ID: {id(main_agent.browser)}")

            history = await main_agent.run()
            
            logger.info("🔍 DIAGNOSTIC: Agent run completed")
            logger.info(f"🔍 DIAGNOSTIC: Task completed successfully: {history.is_done() if history else 'No history'}")
            
            # استخراج نتیجه
            if history and history.is_done():
                result = history.final_result()
                logger.info(f"✅ Task completed: {result}")
                return result or "Task completed successfully"
            else:
                logger.warning("⚠️ Task completed with issues")
                return "Task completed with issues"
                
        except Exception as e:
            logger.error(f"❌ Browser task failed: {e}", exc_info=True)
            raise
        
        finally:
            # بستن browser - ایمن‌سازی برای نسخه‌های مختلف browser-use
            if browser:
                try:
                    logger.info("🔍 DIAGNOSTIC: About to close browser...")
                    logger.info(f"🔍 DIAGNOSTIC: Browser object ID at cleanup: {id(browser)}")
                    logger.info(f"🔍 DIAGNOSTIC: Browser type at cleanup: {type(browser)}")
                    
                    # بررسی وجود متد close
                    if hasattr(browser, 'close'):
                        logger.info("🔍 DIAGNOSTIC: Browser has close() method, calling it...")
                        await browser.close()
                        logger.info("🔒 Browser closed")
                    # اگر در نسخه جدید نامش stop شده باشد
                    elif hasattr(browser, 'stop'):
                        logger.info("🔍 DIAGNOSTIC: Browser has stop() method, calling it...")
                        await browser.stop()
                        logger.info("🔒 Browser stopped")
                    else:
                        logger.warning("⚠️ Browser object has no close/stop method")
                        
                    logger.info("🔍 DIAGNOSTIC: Browser cleanup completed")
                except Exception as e:
                    logger.error(f"🔍 DIAGNOSTIC: Browser cleanup failed: {e}", exc_info=True)
    
    def execute_task_sync(
        self,
        task_description: str,
        llm,
        url: Optional[str] = None,
        cdp_url: Optional[str] = None,
        use_current_page: bool = False,
        max_steps: int = 20,
        login_email: Optional[str] = None,
        login_password: Optional[str] = None,
    ) -> str:
        """
        اجرای task به صورت synchronous
        این متد در thread جداگانه با ProactorEventLoop اجرا میشه
        """
        logger.info("🪟 Running browser task in separate thread with ProactorEventLoop")
                
        # اجرا در thread جداگانه
        future = self.executor.submit(
            self._run_in_new_event_loop,
            self._execute_task_async(
                task_description=task_description,
                llm=llm,
                url=url,
                cdp_url=cdp_url,
                use_current_page=use_current_page,
                max_steps=max_steps,
                login_email=login_email,
                login_password=login_password,
            )
        )
        
        # منتظر نتیجه
        return future.result()


class BrowserAutomationService:
    """
    سرویس اصلی Browser Automation
    """
    
    def __init__(self):
        self.windows_runner = WindowsBrowserRunner()
        self._is_windows = sys.platform == 'win32'
    
    def _get_llm(self, model_name: Optional[str] = None) -> Any:
        """ساخت LLM"""
        
        try:
            from app.core.config import settings
            
            api_key = settings.embedder_api_key_loaded
            if not api_key:
                raise ValueError("OpenAI API key not configured")
            
            # استفاده از مدل قوی‌تر با Vision
            model = "gpt-4o"
            logger.info(f"🤖 Using OpenAI {model}")
            
            llm = BrowserChatOpenAI(
                model=model,
                model_name=model,
                api_key=api_key,
                temperature=0.0,
                provider="openai",
            )
            
            logger.info("✅ LLM configured for browser-use")
            
            return llm
            
        except Exception as e:
            logger.error(f"❌ Failed to create LLM: {e}")
            raise

    async def execute_task(
        self,
        task_description: str,
        url: Optional[str] = None,
        model_name: Optional[str] = None,
        max_steps: int = 20,
        cdp_url: Optional[str] = None,
        use_current_page: bool = False,
        login_email: Optional[str] = None,
        login_password: Optional[str] = None,
    ) -> BrowserTaskResult:
        """
        اجرای task با مدیریت کامل Windows
        """
        start_time = time.time()
        
        try:
            logger.info(f"🚀 Starting browser task: {task_description[:100]}...")
            
            # ساخت LLM
            llm = self._get_llm(model_name)
            
            # اجرا بر اساس سیستم‌عامل
            if self._is_windows:
                logger.info("🪟 Detected Windows - using ProactorEventLoop")
                
                # اجرا در thread جداگانه (synchronous)
                result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    self.windows_runner.execute_task_sync,
                    task_description,
                    llm,
                    url,
                    cdp_url,
                    use_current_page,
                    max_steps,
                    login_email,
                    login_password,
                )
            else:
                # Linux/Mac - اجرای مستقیم
                logger.info("🐧 Detected Linux/Mac - using default event loop")
                result = await self.windows_runner._execute_task_async(
                    task_description=task_description,
                llm=llm,
                    url=url,
                    cdp_url=cdp_url,
                    use_current_page=use_current_page,
                    max_steps=max_steps,
                    login_email=login_email,
                    login_password=login_password,
                )
            
            execution_time = time.time() - start_time
            
            return BrowserTaskResult(
                success=True,
                result=result,
                execution_time=execution_time,
                metadata={
                    "task": task_description,
                    "url": url,
                    "cdp_url": cdp_url,
                    "use_current_page": use_current_page,
                    "login_used": login_email is not None,
                    "os": "Windows" if self._is_windows else "Linux/Mac",
                }
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"❌ Task failed: {e}", exc_info=True)
            
            return BrowserTaskResult(
                success=False,
                error=str(e),
                execution_time=execution_time,
            )


# Singleton instance
browser_automation_service = BrowserAutomationService()