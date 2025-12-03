"""
🤖 Agentic Playwright Service - استفاده از Vision AI برای دقت بالاتر

این سرویس از Vision Language Models برای:
- دیدن صفحه (screenshot)
- تحلیل و تصمیم‌گیری هوشمند
- اجرای اقدامات دقیق‌تر
- مدیریت خطا و retry

مزایا نسبت به playwright_service.py:
✅ دقت بالاتر در پیدا کردن عناصر
✅ مقاوم در برابر تغییرات UI
✅ پشتیبانی از فارسی و انگلیسی
✅ تصمیم‌گیری هوشمند در شرایط پیچیده
"""

import asyncio
import base64
import re
import sys
from io import BytesIO
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from playwright.async_api import async_playwright, Page
from PIL import Image
import json
from concurrent.futures import ThreadPoolExecutor

from app.core.logging_config import get_logger
from app.services.model_service import ModelService

logger = get_logger(__name__)
model_service = ModelService()

@dataclass
class AgenticPlaywrightResult:
    """نتیجه اجرای Agentic Playwright"""
    success: bool
    result: Optional[str] = None
    error: Optional[str] = None
    steps_taken: List[Dict[str, Any]] = None
    screenshots: List[str] = None


class AgenticPlaywrightService:
    """
    🤖 Agentic Playwright Service
    
    استفاده از Vision AI برای خودکارسازی دقیق‌تر مرورگر
    """
    
    # لیست مدل‌های Vision-capable در OpenRouter
    VISION_CAPABLE_MODELS = [
        # Google Gemini (پشتیبانی کامل از Vision)
        "google/gemini-2.5-flash",
        
        # OpenAI (پشتیبانی کامل از Vision)
        "gpt-4o",
        
        # Amazon Nova (پشتیبانی از Vision)
        "amazon/nova-2-lite-v1"
    ]
    
    def __init__(self, vision_model: str = "google/gemini-2.5-flash"):
        """
        Initialize Agentic Playwright Service
        
        Args:
            vision_model: نام مدل Vision 
                - OpenRouter: "google/gemini-2.5-flash"
                - OpenRouter: "amazon/nova-2-lite-v1"
                - OpenAI: "gpt-4o"
        """
        # بررسی اینکه مدل از Vision پشتیبانی می‌کند
        if vision_model not in self.VISION_CAPABLE_MODELS:
            logger.warning(
                f"⚠️ Model {vision_model} may not support vision. "
                f"Recommended models: {', '.join(self.VISION_CAPABLE_MODELS[:5])}"
            )
        
        self.vision_model = vision_model
        self.max_iterations = 20  # حداکثر تعداد تکرار
        self.screenshot_paths = []
        
    async def _get_vision_model(self):
        """دریافت مدل Vision از ModelService (پشتیبانی از OpenRouter و OpenAI)"""
        try:
            # استفاده از ModelService موجود که خودش provider را تشخیص می‌دهد
            model = model_service.get_model(
                model_name=self.vision_model,
                temperature=0.1,  # دقت بالا
                max_tokens=2000,
                streaming=False
            )
            logger.info(f"✅ Vision model loaded: {self.vision_model}")
            return model
        except Exception as e:
            logger.error(f"❌ Failed to get vision model: {e}")
            raise
    
    async def _take_screenshot(self, page: Page, step_name: str) -> str:
        """گرفتن screenshot و ذخیره"""
        try:
            # بررسی اینکه page هنوز باز است
            if page.is_closed():
                logger.warning("⚠️ Page is closed, cannot take screenshot")
                return ""
            
            # بررسی اینکه browser هنوز باز است
            try:
                # تست اینکه آیا می‌توانیم به page دسترسی داشته باشیم
                await page.evaluate("() => document.title")
            except Exception as e:
                logger.warning(f"⚠️ Page is not accessible: {e}")
                return ""
            
            screenshot_bytes = await page.screenshot(full_page=False)
            screenshot_path = f"debug_agentic_{step_name}.png"
            
            with open(screenshot_path, "wb") as f:
                f.write(screenshot_bytes)
            
            self.screenshot_paths.append(screenshot_path)
            logger.info(f"📸 Screenshot saved: {screenshot_path}")
            return screenshot_path
        except Exception as e:
            logger.error(f"❌ Failed to take screenshot: {e}")
            return ""
    
    def _encode_image_to_base64(self, image_path: str) -> Optional[str]:
        """تبدیل تصویر به base64 برای ارسال به Vision API"""
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            logger.error(f"❌ Failed to encode image: {e}")
            return None
    
    async def _analyze_page_with_ai(
        self,
        page: Page,
        task_description: str,
        previous_actions: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        تحلیل صفحه با Vision AI و دریافت دستور بعدی
        
        Returns:
            Dict با keys: action, element_description, confidence, reasoning
        """
        try:
            # گرفتن screenshot
            screenshot_path = await self._take_screenshot(page, "analysis")
            if not screenshot_path:
                # اگر screenshot ناموفق بود، یک fallback decision برگردان
                logger.warning("⚠️ Screenshot failed, returning wait action")
                return {
                    "action": "wait",
                    "element_description": "Waiting for page to load",
                    "confidence": 0.3,
                    "reasoning": "Screenshot failed, waiting before retry"
                }
            
            # گرفتن accessibility tree (برای اطلاعات بیشتر)
            try:
                accessibility_tree = await page.accessibility.snapshot()
            except:
                accessibility_tree = None
            
            # گرفتن URL فعلی
            current_url = page.url
            
            # ساخت prompt برای Vision AI
            previous_context = ""
            if previous_actions:
                previous_context = "\n\nاقدامات قبلی:\n"
                for i, action in enumerate(previous_actions[-5:], 1):  # آخرین 5 اقدام
                    previous_context += f"{i}. {action.get('action', 'unknown')}: {action.get('description', '')}\n"
            
            prompt = f"""
You are an AI assistant helping to automate browser tasks using Playwright.

CURRENT TASK: {task_description}

CURRENT PAGE URL: {current_url}

{previous_context}

INSTRUCTIONS:
1. Analyze the screenshot carefully
2. Identify what needs to be done next to complete the task
3. Determine the best action to take
4. Provide specific instructions for finding and interacting with elements
5. RESPOND WITH ONLY VALID JSON - NO MARKDOWN, NO EXPLANATIONS

AVAILABLE ACTIONS:
- click: Click on a button, link, or clickable element (NOT for dropdown options - use "select" instead)
- fill: Fill in an input field (text, email, password, etc.)
- select: Select an option from a dropdown menu (USE THIS for role selection, not "click")
- wait: Wait for something to appear or load
- navigate: Navigate to a different page (use page.goto())
- submit: Submit a form (CRITICAL: Use this IMMEDIATELY after all form fields are filled)
- scroll: Scroll the page
- done: Task is complete

CRITICAL SUBMIT RULES:
- After filling ALL form fields (email, password, full name, role), you MUST use "submit" action IMMEDIATELY
- DO NOT wait, scroll, or do any other action after all fields are filled - SUBMIT RIGHT AWAY
- Look for buttons with text like "ایجاد ادمین", "Create Admin", "ثبت", "Submit", "ایجاد", "Create"
- The submit button is usually at the bottom of the form, often purple/blue colored
- If you see a form with all fields filled, the NEXT action MUST be "submit"

IMPORTANT: For dropdown menus (like role selection), ALWAYS use "select" action, NOT "click". 
The "select" action will handle opening the dropdown and selecting the option automatically.

WORKFLOW FOR FORM FILLING:
1. Fill email field → action: "fill"
2. Fill password field → action: "fill"
3. Fill full name field → action: "fill"
4. Select role from dropdown → action: "select"
5. IMMEDIATELY submit the form → action: "submit" (DO THIS RIGHT AFTER STEP 4, NO WAITING)

RESPONSE FORMAT (MUST BE VALID JSON, NO MARKDOWN CODE BLOCKS):
{{
    "action": "click|fill|select|wait|navigate|submit|scroll|done",
    "element_description": "Description of element to interact with (in Persian or English)",
    "element_type": "button|input|link|select|text|other",
    "element_text": "Visible text on the element (if any)",
    "input_value": "Value to fill (only if action is 'fill')",
    "selector_hint": "CSS selector hint (optional, e.g., 'button', 'input[type=email]')",
    "coordinates": [x, y] (optional, estimated pixel coordinates if you can see the element position),
    "reasoning": "Why this action is needed",
    "confidence": 0.0-1.0,
    "next_step_hint": "What should happen after this action"
}}

CRITICAL REQUIREMENTS:
- You MUST respond with ONLY valid JSON, no markdown code blocks, no explanations before or after
- Start your response directly with {{ and end with }}
- Be very specific about element identification
- Consider both Persian (فارسی) and English text
- If multiple similar elements exist, describe how to distinguish the target
- If you can estimate pixel coordinates [x, y] of the element from the screenshot, include them in "coordinates" field (optional but helpful)
- If the task is complete, use action "done"
- Confidence should reflect how sure you are about the action
- For "navigate" action, provide the URL in element_description
"""
            
            # ارسال به Vision Model
            model = await self._get_vision_model()
            
            # برای Vision API (OpenRouter یا OpenAI)
            image_base64 = self._encode_image_to_base64(screenshot_path)
            
            if not image_base64:
                raise Exception("Failed to encode image")
            
            # ساخت پیام برای Vision API
            from langchain_core.messages import HumanMessage
            
            # ساخت محتوای پیام با تصویر (فرمت OpenAI-compatible که OpenRouter هم پشتیبانی می‌کند)
            message_content = [
                {
                    "type": "text",
                    "text": prompt
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{image_base64}"
                    }
                }
            ]
            
            human_message = HumanMessage(content=message_content)
            
            # فراخوانی مدل (پشتیبانی از OpenRouter و OpenAI)
            try:
                # استفاده از LangChain model که از ModelService آمده
                if hasattr(model, 'ainvoke'):
                    response = await model.ainvoke([human_message])
                elif hasattr(model, 'invoke'):
                    response = await asyncio.to_thread(model.invoke, [human_message])
                else:
                    # Fallback: استفاده مستقیم از OpenAI-compatible API
                    from app.core.config import settings
                    import openai
                    
                    # تشخیص provider از نام مدل
                    is_openrouter = any(x in self.vision_model.lower() for x in [
                        "google/", "anthropic/", "x-ai/", "meta-llama/", 
                        "mistralai/", "deepseek/", "qwen/"
                    ])
                    
                    if is_openrouter:
                        # استفاده از OpenRouter
                        api_key = settings.openai_api_key_loaded
                        base_url = settings.openai_base_url_loaded or "https://openrouter.ai/api/v1"
                    else:
                        # استفاده از OpenAI
                        api_key = settings.embedder_api_key_loaded or settings.openai_api_key_loaded
                        base_url = settings.embedder_openai_base_url_loaded or "https://api.openai.com/v1"
                    
                    if not api_key:
                        raise Exception("API key not configured")
                    
                    client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url)
                    response_obj = await client.chat.completions.create(
                        model=self.vision_model,
                        messages=[
                            {
                                "role": "user",
                                "content": message_content
                            }
                        ],
                        max_tokens=2000,
                        temperature=0.1
                    )
                    response_text = response_obj.choices[0].message.content
                    # ساخت یک response object شبیه LangChain
                    class MockResponse:
                        def __init__(self, content):
                            self.content = content
                    response = MockResponse(response_text)
                    
            except Exception as e:
                logger.error(f"❌ Model invocation failed: {e}", exc_info=True)
                raise Exception(f"Failed to call vision model: {str(e)}")
            
            # استخراج JSON از پاسخ
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            # پاک کردن whitespace و markdown code blocks
            response_text = response_text.strip()
            
            # حذف markdown code blocks اگر وجود دارد
            if response_text.startswith('```'):
                # پیدا کردن اولین { بعد از ```
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}')
                if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                    response_text = response_text[start_idx:end_idx+1]
            
            # تلاش برای استخراج JSON از پاسخ
            ai_decision = None
            try:
                # روش 1: اگر پاسخ JSON خالص است
                if response_text.strip().startswith('{'):
                    ai_decision = json.loads(response_text)
                else:
                    # روش 2: پیدا کردن JSON در متن (با regex پیشرفته‌تر)
                    # پیدا کردن اولین { تا آخرین } (با پشتیبانی از nested braces)
                    json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
                    json_matches = re.findall(json_pattern, response_text, re.DOTALL)
                    
                    if json_matches:
                        # استفاده از طولانی‌ترین match
                        json_match = max(json_matches, key=len)
                        ai_decision = json.loads(json_match)
                    else:
                        # روش 3: پیدا کردن JSON با شمارش braces
                        start_idx = response_text.find('{')
                        if start_idx != -1:
                            brace_count = 0
                            end_idx = start_idx
                            for i in range(start_idx, len(response_text)):
                                if response_text[i] == '{':
                                    brace_count += 1
                                elif response_text[i] == '}':
                                    brace_count -= 1
                                    if brace_count == 0:
                                        end_idx = i
                                        break
                            
                            if brace_count == 0:
                                json_str = response_text[start_idx:end_idx+1]
                                ai_decision = json.loads(json_str)
                            else:
                                raise ValueError("Unbalanced JSON braces")
                        else:
                            raise ValueError("No JSON found in response")
                            
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"⚠️ Failed to parse JSON: {e}")
                logger.debug(f"Response text: {response_text[:500]}")
                
                # Fallback: ساخت تصمیم ساده از متن
                # تلاش برای استخراج action از متن
                action = "wait"
                if "click" in response_text.lower():
                    action = "click"
                elif "fill" in response_text.lower() or "input" in response_text.lower():
                    action = "fill"
                elif "submit" in response_text.lower():
                    action = "submit"
                elif "navigate" in response_text.lower() or "goto" in response_text.lower():
                    action = "navigate"
                elif "done" in response_text.lower() or "complete" in response_text.lower():
                    action = "done"
                
                ai_decision = {
                    "action": action,
                    "element_description": response_text[:200],
                    "reasoning": response_text[:300],
                    "confidence": 0.3
                }
            
            logger.info(f"🤖 AI Decision: {ai_decision.get('action')} - {ai_decision.get('reasoning', '')[:100]}")
            
            return ai_decision
            
        except Exception as e:
            logger.error(f"❌ Failed to analyze page with AI: {e}", exc_info=True)
            return {
                "action": "wait",
                "element_description": f"Error: {str(e)}",
                "confidence": 0.0,
                "reasoning": str(e)
            }
    
    async def _execute_action(
        self,
        page: Page,
        ai_decision: Dict[str, Any],
        previous_actions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        اجرای اقدام بر اساس تصمیم AI
        
        Returns:
            Dict با نتیجه اجرا
        """
        action = ai_decision.get("action", "").lower()
        element_description = ai_decision.get("element_description", "")
        element_type = ai_decision.get("element_type", "")
        element_text = ai_decision.get("element_text", "")
        selector_hint = ai_decision.get("selector_hint", "")
        input_value = ai_decision.get("input_value", "")
        coordinates = ai_decision.get("coordinates")  # [x, y] از Vision AI
        
        result = {
            "success": False,
            "action": action,
            "description": element_description,
            "error": None
        }
        
        try:
            if action == "done":
                result["success"] = True
                result["description"] = "Task completed"
                return result
            
            elif action == "wait":
                await asyncio.sleep(2)
                result["success"] = True
                return result
            
            elif action == "scroll":
                await page.evaluate("window.scrollBy(0, 500)")
                await asyncio.sleep(1)
                result["success"] = True
                return result
            
            elif action == "navigate":
                # Navigate to a URL - استخراج URL از متن
                url_to_navigate = element_description or ai_decision.get("url", "")
                
                # استخراج URL از متن (مثلاً "Navigate to http://localhost:3000/super-admin")
                url_match = re.search(r'https?://[^\s]+', url_to_navigate)
                if url_match:
                    url_to_navigate = url_match.group()
                elif url_to_navigate.strip().startswith('http://') or url_to_navigate.strip().startswith('https://'):
                    url_to_navigate = url_to_navigate.strip()
                elif url_to_navigate.strip().startswith('/'):
                    # مسیر نسبی - استفاده از base URL
                    current_url = page.url
                    base_url = '/'.join(current_url.split('/')[:3]) if current_url else "http://localhost:3000"
                    url_to_navigate = base_url + url_to_navigate.strip()
                else:
                    # اگر URL معتبر نیست، skip کن و wait (AI باید دوباره فکر کند)
                    logger.warning(f"⚠️ Invalid URL for navigate: {url_to_navigate}. Skipping - AI should use click instead.")
                    await asyncio.sleep(1)
                    result["success"] = False
                    result["error"] = f"Invalid URL (not a real URL): {url_to_navigate}"
                    return result
                
                # Navigate به URL معتبر
                try:
                    await page.goto(url_to_navigate)
                    await page.wait_for_load_state('networkidle')
                    await asyncio.sleep(2)
                    result["success"] = True
                    logger.info(f"✅ Navigated to: {url_to_navigate}")
                except Exception as e:
                    result["error"] = f"Failed to navigate: {str(e)}"
                    logger.warning(f"⚠️ {result['error']}")
                return result
            
            elif action == "select":
                # Select an option from dropdown (پشتیبانی از React Select با keyboard navigation)
                # استفاده از روش تضمینی playwright_service.py
                select_found = False
                
                try:
                    logger.info("📝 Selecting Role using Keyboard (guaranteed method)...")
                    
                    # روش 1: پیدا کردن dropdown trigger با روش تضمینی (مثل playwright_service)
                    dropdown_trigger = None
                    
                    # اول از همه، روش اصلی playwright_service را امتحان می‌کنیم
                    try:
                        # استفاده از filter با has_text (مثل playwright_service)
                        dropdown_trigger = page.locator("div").filter(has_text="انتخاب نقش").last
                        # بررسی visibility
                        count = await dropdown_trigger.count()
                        if count > 0:
                            visible = await dropdown_trigger.is_visible()
                            if visible:
                                logger.info("✅ Found dropdown trigger using filter method")
                            else:
                                dropdown_trigger = None
                        else:
                            dropdown_trigger = None
                    except Exception as e:
                        logger.debug(f"Filter method failed: {e}")
                        dropdown_trigger = None
                    
                    # اگر پیدا نشد، از selectorهای جایگزین استفاده کن
                    if not dropdown_trigger or not await dropdown_trigger.is_visible():
                        logger.info("Trying alternative selectors...")
                        trigger_selectors = [
                            '.css-control',
                            '.select__control',
                            'div:has-text("انتخاب نقش")',
                            'div:has-text("Select Role")',
                            'div:has-text("نقش")',
                            '[class*="select"]',
                            '[class*="Select"]',
                            'div[role="combobox"]',
                        ]
                        
                        for selector in trigger_selectors:
                            try:
                                elements = page.locator(selector)
                                count = await elements.count()
                                if count > 0:
                                    dropdown_trigger = elements.last
                                    if await dropdown_trigger.is_visible():
                                        logger.info(f"✅ Found dropdown trigger with selector: {selector}")
                                        break
                            except Exception as e:
                                logger.debug(f"Trigger selector failed: {selector} - {e}")
                                continue
                    
                    # اگر selector_hint داریم، از آن استفاده کن
                    if (not dropdown_trigger or not await dropdown_trigger.is_visible()) and selector_hint:
                        try:
                            elements = page.locator(selector_hint)
                            count = await elements.count()
                            if count > 0:
                                dropdown_trigger = elements.last
                                if await dropdown_trigger.is_visible():
                                    logger.info(f"✅ Found dropdown trigger using selector_hint: {selector_hint}")
                        except Exception as e:
                            logger.debug(f"selector_hint failed: {e}")
                    
                    if dropdown_trigger and await dropdown_trigger.is_visible():
                        # کلیک روی dropdown trigger (با force برای اطمینان)
                        logger.info("Clicking dropdown trigger...")
                        await dropdown_trigger.click(force=True)
                        
                        # صبر برای باز شدن انیمیشن منو (مثل playwright_service)
                        await asyncio.sleep(1)
                        
                        # استفاده از keyboard navigation (روش تضمینی)
                        # این روش برای React Select بهتر کار می‌کند
                        target_option = input_value or element_text or element_description
                        
                        # اگر target_option "Admin" یا "ادمین" است یا خالی است، از keyboard navigation استفاده کن
                        # (معمولاً گزینه دوم Admin است)
                        use_keyboard = True
                        if target_option and ("admin" not in target_option.lower() and "ادمین" not in target_option):
                            # اگر گزینه دیگری است، ابتدا سعی می‌کنیم با selector پیدا کنیم
                            option_selectors = [
                                f'[role="option"]:has-text("{target_option}")',
                                f'div[role="option"]:has-text("{target_option}")',
                                f'li:has-text("{target_option}")',
                                f'.select-item:has-text("{target_option}")',
                                f'[data-value*="{target_option.lower()}"]',
                            ]
                            
                            option_found = False
                            for opt_selector in option_selectors:
                                try:
                                    options = page.locator(opt_selector)
                                    count = await options.count()
                                    if count > 0:
                                        option = options.first
                                        if await option.is_visible():
                                            await option.scroll_into_view_if_needed()
                                            await option.click()
                                            option_found = True
                                            select_found = True
                                            logger.info(f"✅ Selected option using selector: {opt_selector}")
                                            break
                                except Exception as e:
                                    logger.debug(f"Option selector failed: {opt_selector} - {e}")
                                    continue
                            
                            if not option_found:
                                logger.info("Option not found with selectors, using keyboard navigation...")
                                use_keyboard = True
                            else:
                                use_keyboard = False
                        
                        # استفاده از keyboard navigation (روش تضمینی)
                        if use_keyboard:
                            logger.info("Using keyboard navigation for role selection...")
                            
                            # یک بار فلش پایین میزنیم (میره روی گزینه اول: ادمین ارشد)
                            await page.keyboard.press("ArrowDown")
                            await asyncio.sleep(0.2)
                            
                            # یک بار دیگر فلش پایین میزنیم (میره روی گزینه دوم: ادمین)
                            await page.keyboard.press("ArrowDown")
                            await asyncio.sleep(0.2)
                            
                            # زدن اینتر برای انتخاب
                            await page.keyboard.press("Enter")
                            await asyncio.sleep(0.5)
                            
                            select_found = True
                            logger.info("✅ Selected role using keyboard navigation (Down -> Down -> Enter)")
                    else:
                        # روش جایگزین: استفاده از select_option برای select معمولی HTML
                        if selector_hint:
                            try:
                                select_element = page.locator(selector_hint).last
                                if await select_element.is_visible():
                                    if input_value:
                                        await select_element.select_option(input_value)
                                        select_found = True
                                        logger.info(f"✅ Selected option using select_option: {input_value}")
                            except Exception as e:
                                logger.debug(f"select_option failed: {e}")
                        
                        if not select_found:
                            logger.warning("⚠️ Could not find dropdown trigger, trying direct keyboard navigation...")
                            # آخرین تلاش: استفاده مستقیم از keyboard
                            try:
                                await page.keyboard.press("ArrowDown")
                                await asyncio.sleep(0.2)
                                await page.keyboard.press("ArrowDown")
                                await asyncio.sleep(0.2)
                                await page.keyboard.press("Enter")
                                await asyncio.sleep(0.5)
                                select_found = True
                                logger.info("✅ Selected using direct keyboard navigation")
                            except Exception as e:
                                logger.debug(f"Direct keyboard navigation failed: {e}")
                
                except Exception as e:
                    logger.error(f"❌ Select action failed: {e}", exc_info=True)
                    result["error"] = f"Select failed: {str(e)}"
                
                if select_found:
                    await asyncio.sleep(1)  # صبر برای اطمینان از انتخاب شدن
                    result["success"] = True
                else:
                    result["error"] = f"Could not find or select dropdown: {element_description}"
                    logger.warning(f"⚠️ {result['error']}")
                
                return result
            
            elif action == "click":
                # پیدا کردن عنصر با روش‌های مختلف (بهبود یافته)
                element_found = False
                
                # روش 1: استفاده از selector hint
                if selector_hint:
                    try:
                        elements = page.locator(selector_hint)
                        count = await elements.count()
                        if count > 0:
                            element = elements.first
                            if await element.is_visible():
                                await element.click()
                                element_found = True
                                logger.info(f"✅ Clicked using selector: {selector_hint}")
                    except Exception as e:
                        logger.debug(f"Selector hint failed: {e}")
                
                # روش 2: جستجو بر اساس متن (بهبود یافته با regex و case-insensitive)
                if not element_found and element_text:
                    # تمیز کردن متن
                    clean_text = element_text.strip()
                    
                    # لیست selectorهای پیشرفته‌تر (مثل playwright_service)
                    selectors = [
                        # دقیق
                        f'text="{clean_text}"',
                        f'text=/{re.escape(clean_text)}/i',
                        # دکمه‌ها
                        f'button:has-text("{clean_text}")',
                        f'button:has-text(/{re.escape(clean_text)}/i)',
                        # لینک‌ها
                        f'a:has-text("{clean_text}")',
                        f'a:has-text(/{re.escape(clean_text)}/i)',
                        # div و span
                        f'div:has-text("{clean_text}")',
                        f'span:has-text("{clean_text}")',
                        # aria-label
                        f'[aria-label*="{clean_text}" i]',
                        # data-testid
                        f'[data-testid*="{clean_text.lower().replace(" ", "-")}"]',
                        # class-based
                        f'.btn:has-text("{clean_text}")',
                        f'.button:has-text("{clean_text}")',
                    ]
                    
                    # برای دکمه "افزودن ادمین جدید" - selectorهای خاص
                    if "افزودن" in clean_text or "add" in clean_text.lower() or "admin" in clean_text.lower():
                        selectors.extend([
                            'text=/افزودن ادمین جدید/i',
                            'text=/Add New Admin/i',
                            'text=/Add Admin/i',
                            'text=/افزودن/i',
                            'text=/Add/i',
                            'button:has-text("افزودن ادمین")',
                            'button:has-text("Add Admin")',
                            'button:has-text("افزودن")',
                            'button:has-text("Add")',
                            '[data-testid="add-admin"]',
                            '.btn-primary:has-text("افزودن")',
                            '.btn-primary:has-text("Add")',
                            'button.btn-primary',
                            'button[class*="add"]',
                            'button[class*="create"]',
                        ])
                    
                    for selector in selectors:
                        try:
                            elements = page.locator(selector)
                            count = await elements.count()
                            if count > 0:
                                # امتحان کردن همه عناصر پیدا شده
                                for i in range(count):
                                    element = elements.nth(i)
                                    try:
                                        if await element.is_visible():
                                            # scroll into view
                                            await element.scroll_into_view_if_needed()
                                            await asyncio.sleep(0.3)
                                            await element.click()
                                            element_found = True
                                            logger.info(f"✅ Clicked using text selector: {selector} (element {i+1}/{count})")
                                            break
                                    except Exception as e:
                                        logger.debug(f"Element {i} click failed: {e}")
                                        continue
                                
                                if element_found:
                                    break
                        except Exception as e:
                            logger.debug(f"Text selector failed: {selector} - {e}")
                            continue
                
                # روش 3: جستجو بر اساس element_description (اگر element_text نبود)
                if not element_found and element_description and not element_text:
                    # استخراج کلمات کلیدی از description
                    keywords = []
                    if "افزودن" in element_description or "add" in element_description.lower():
                        keywords.extend(["افزودن", "Add", "add"])
                    if "ادمین" in element_description or "admin" in element_description.lower():
                        keywords.extend(["ادمین", "Admin", "admin"])
                    if "دکمه" in element_description or "button" in element_description.lower():
                        keywords.extend(["button"])
                    
                    for keyword in keywords[:3]:  # فقط 3 کلمه اول
                        try:
                            selector = f'button:has-text("{keyword}")'
                            elements = page.locator(selector)
                            count = await elements.count()
                            if count > 0:
                                element = elements.first
                                if await element.is_visible():
                                    await element.scroll_into_view_if_needed()
                                    await element.click()
                                    element_found = True
                                    logger.info(f"✅ Clicked using keyword: {keyword}")
                                    break
                        except Exception as e:
                            logger.debug(f"Keyword selector failed: {e}")
                            continue
                
                # روش 4: جستجو بر اساس نوع عنصر
                if not element_found:
                    type_selectors = {
                        "button": "button",
                        "link": "a",
                        "input": "input",
                        "select": "select"
                    }
                    
                    base_selector = type_selectors.get(element_type, "button")  # پیش‌فرض button
                    try:
                        elements = page.locator(base_selector)
                        count = await elements.count()
                        if count > 0:
                            # اگر چند دکمه داریم، سعی می‌کنیم دکمه مناسب را پیدا کنیم
                            for i in range(min(count, 10)):  # حداکثر 10 دکمه اول
                                element = elements.nth(i)
                                try:
                                    text = await element.text_content()
                                    if text and (
                                        "افزودن" in text or "add" in text.lower() or
                                        "ادمین" in text or "admin" in text.lower()
                                    ):
                                        if await element.is_visible():
                                            await element.scroll_into_view_if_needed()
                                            await element.click()
                                            element_found = True
                                            logger.info(f"✅ Clicked using type and text match: {text[:30]}")
                                            break
                                except:
                                    continue
                            
                            # اگر پیدا نشد، آخرین دکمه را امتحان کن
                            if not element_found and count > 0:
                                element = elements.last
                                if await element.is_visible():
                                    await element.scroll_into_view_if_needed()
                                    await element.click()
                                    element_found = True
                                    logger.info(f"✅ Clicked using last {element_type}")
                    except Exception as e:
                        logger.debug(f"Type selector failed: {e}")
                
                # روش 5: استفاده از مختصات (coordinates) از Vision AI (Level 4 Agentic)
                # این روش زمانی استفاده می‌شود که selectorها کار نکردند اما AI مختصات را تخمین زده
                if not element_found and coordinates:
                    try:
                        if isinstance(coordinates, list) and len(coordinates) >= 2:
                            x, y = int(coordinates[0]), int(coordinates[1])
                            logger.info(f"🎯 Trying coordinates from Vision AI: ({x}, {y})")
                            
                            # بررسی اینکه مختصات در محدوده صفحه است
                            viewport_size = page.viewport_size
                            if viewport_size:
                                if 0 <= x <= viewport_size['width'] and 0 <= y <= viewport_size['height']:
                                    await page.mouse.click(x, y)
                                    element_found = True
                                    logger.info(f"✅ Clicked using coordinates: ({x}, {y})")
                                else:
                                    logger.warning(f"⚠️ Coordinates out of bounds: ({x}, {y}), viewport: {viewport_size}")
                            else:
                                # اگر viewport_size موجود نبود، امتحان کن
                                await page.mouse.click(x, y)
                                element_found = True
                                logger.info(f"✅ Clicked using coordinates (no viewport check): ({x}, {y})")
                    except Exception as e:
                        logger.debug(f"Coordinate click failed: {e}")
                
                # روش 6: Fallback برای dropdown - اگر element پیدا نشد و description شامل "role" یا "dropdown" است
                if not element_found and element_description:
                    desc_lower = element_description.lower()
                    # بررسی اینکه آیا این یک dropdown است
                    is_dropdown = any(keyword in desc_lower for keyword in [
                        "role", "نقش", "dropdown", "select", "option", 
                        "انتخاب", "گزینه", "منوی", "dropdown"
                    ])
                    
                    if is_dropdown:
                        logger.info("🔄 Detected dropdown in click action, trying select method...")
                        # استفاده از منطق select برای dropdown
                        try:
                            # پیدا کردن dropdown trigger
                            dropdown_trigger = None
                            try:
                                dropdown_trigger = page.locator("div").filter(has_text="انتخاب نقش").last
                                count = await dropdown_trigger.count()
                                if count > 0 and await dropdown_trigger.is_visible():
                                    logger.info("✅ Found dropdown trigger using filter method")
                            except:
                                pass
                            
                            # اگر پیدا نشد، از selectorهای جایگزین استفاده کن
                            if not dropdown_trigger or not await dropdown_trigger.is_visible():
                                trigger_selectors = [
                                    '.css-control',
                                    '.select__control',
                                    'div:has-text("انتخاب نقش")',
                                    'div:has-text("Select Role")',
                                    'div:has-text("نقش")',
                                    '[class*="select"]',
                                    'div[role="combobox"]',
                                ]
                                
                                for selector in trigger_selectors:
                                    try:
                                        elements = page.locator(selector)
                                        count = await elements.count()
                                        if count > 0:
                                            dropdown_trigger = elements.last
                                            if await dropdown_trigger.is_visible():
                                                logger.info(f"✅ Found dropdown trigger: {selector}")
                                                break
                                    except:
                                        continue
                            
                            if dropdown_trigger and await dropdown_trigger.is_visible():
                                # کلیک روی dropdown trigger
                                await dropdown_trigger.click(force=True)
                                await asyncio.sleep(1)
                                
                                # استفاده از keyboard navigation برای انتخاب Admin (گزینه دوم)
                                await page.keyboard.press("ArrowDown")
                                await asyncio.sleep(0.2)
                                await page.keyboard.press("ArrowDown")
                                await asyncio.sleep(0.2)
                                await page.keyboard.press("Enter")
                                await asyncio.sleep(0.5)
                                
                                element_found = True
                                logger.info("✅ Selected role using dropdown fallback method")
                        except Exception as e:
                            logger.debug(f"Dropdown fallback failed: {e}")
                
                if element_found:
                    await asyncio.sleep(2)  # صبر برای بارگذاری
                    result["success"] = True
                else:
                    result["error"] = f"Could not find element: {element_description}"
                    logger.warning(f"⚠️ {result['error']}")
                    # گرفتن screenshot برای دیباگ
                    try:
                        await page.screenshot(path=f"debug_click_failed_{len(previous_actions)}.png")
                    except:
                        pass
            
            elif action == "fill":
                # پیدا کردن input field
                input_found = False
                
                if selector_hint:
                    try:
                        elements = page.locator(selector_hint)
                        count = await elements.count()
                        if count > 0:
                            input_element = elements.last  # معمولاً آخرین input فرم جدید است
                            if await input_element.is_visible():
                                await input_element.fill(input_value)
                                input_found = True
                                logger.info(f"✅ Filled using selector: {selector_hint}")
                    except Exception as e:
                        logger.debug(f"Selector hint failed: {e}")
                
                if not input_found:
                    # جستجو بر اساس نوع input و element_description
                    input_selectors = []
                    desc_lower = element_description.lower()
                    
                    # اگر element_description شامل "email" یا "ایمیل" است
                    if "email" in desc_lower or "ایمیل" in element_description:
                        input_selectors = [
                            'input[type="email"]',
                            'input[placeholder*="email" i]',
                            'input[placeholder*="ایمیل" i]',
                            'input[name*="email" i]',
                            'input[id*="email" i]',
                        ]
                    # اگر element_description شامل "password" یا "رمز" است
                    elif "password" in desc_lower or "رمز" in element_description:
                        input_selectors = [
                            'input[type="password"]',
                            'input[placeholder*="password" i]',
                            'input[placeholder*="رمز" i]',
                            'input[name*="password" i]',
                            'input[id*="password" i]',
                        ]
                    # جستجوی عمومی
                    else:
                        input_selectors = [
                            'input[type="email"]',
                            'input[type="password"]',
                            'input[type="text"]',
                            'input[placeholder*="email" i]',
                            'input[placeholder*="password" i]',
                            'input[placeholder*="ایمیل" i]',
                            'input[placeholder*="رمز" i]',
                            'input[name*="email" i]',
                            'input[name*="password" i]',
                        ]
                    
                    for selector in input_selectors:
                        try:
                            elements = page.locator(selector)
                            count = await elements.count()
                            if count > 0:
                                # استفاده از اولین input خالی (نه آخرین)
                                for i in range(count):
                                    input_element = elements.nth(i)
                                    if await input_element.is_visible():
                                        # بررسی اینکه آیا این input قبلاً پر نشده
                                        try:
                                            current_value = await input_element.input_value()
                                            if not current_value or current_value == input_value:
                                                await input_element.fill(input_value)
                                                input_found = True
                                                logger.info(f"✅ Filled using selector: {selector} (element {i+1}/{count})")
                                                break
                                        except:
                                            # اگر input_value() کار نکرد، امتحان کن
                                            try:
                                                await input_element.fill(input_value)
                                                input_found = True
                                                logger.info(f"✅ Filled using selector: {selector} (element {i+1}/{count})")
                                                break
                                            except:
                                                continue
                                
                                if input_found:
                                    break
                        except Exception as e:
                            logger.debug(f"Input selector failed: {e}")
                            continue
                
                if input_found:
                    await asyncio.sleep(0.5)
                    result["success"] = True
                else:
                    result["error"] = f"Could not find input field: {element_description}"
                    logger.warning(f"⚠️ {result['error']}")
            
            elif action == "submit":
                # بررسی اینکه آیا صفحه reload شده یا نه
                current_url_before = page.url
                logger.info(f"📍 Current URL before submit: {current_url_before}")
                
                # ====== مرحله ۰: بررسی مقادیر فرم قبل از submit ======
                logger.info("🔍 Verifying form values before submit...")
                form_values = await page.evaluate("""
                    () => {
                        const inputs = document.querySelectorAll('input[type="email"], input[type="password"], input[type="text"]');
                        const values = {};
                        inputs.forEach((input, i) => {
                            if (input.offsetParent !== null) {  // visible
                                values[`input_${i}_${input.type}`] = input.value || '(empty)';
                            }
                        });
                        return values;
                    }
                """)
                logger.info(f"📋 Form values: {form_values}")
                
                # ====== مرحله ۱: اول با Playwright Native Click (بهترین روش برای React) ======
                submit_found = False
                submit_button = None
                
                # سلکتورهای دکمه submit داخل Modal (اولویت به Modal)
                modal_submit_selectors = [
                    # دکمه‌های داخل Modal/Dialog (با class/role مشخص)
                    '[role="dialog"] button:has-text("ایجاد ادمین")',
                    '.modal button:has-text("ایجاد ادمین")',
                    '[class*="modal"] button:has-text("ایجاد ادمین")',
                    '[class*="dialog"] button:has-text("ایجاد ادمین")',
                    # دکمه‌های type=submit داخل Modal
                    '[role="dialog"] button[type="submit"]',
                    '.modal button[type="submit"]',
                    # دکمه‌های با gradient/primary style (معمولاً دکمه اصلی فرم)
                    'button[class*="gradient"]:has-text("ایجاد")',
                    'button[class*="primary"]:has-text("ایجاد")',
                    # دکمه‌های ایجاد ادمین (عمومی)
                    'button:has-text("ایجاد ادمین")',
                    'button:has-text("Create Admin")',
                ]
                
                logger.info("🎯 Trying Playwright native click FIRST (best for React)...")
                
                for selector in modal_submit_selectors:
                    try:
                        elements = page.locator(selector)
                        count = await elements.count()
                        
                        if count > 0:
                            logger.info(f"🔍 Found {count} elements with selector: {selector}")
                            
                            # پیدا کردن دکمه visible و enabled
                            for idx in range(count):
                                btn = elements.nth(idx)
                                try:
                                    is_visible = await btn.is_visible()
                                    is_disabled = await btn.is_disabled()
                                    btn_text = await btn.text_content()
                                    btn_text = (btn_text or "").strip()
                                    
                                    logger.info(f"   Button {idx+1}: '{btn_text}' (visible: {is_visible}, disabled: {is_disabled})")
                                    
                                    # فقط دکمه ایجاد را بزن، نه افزودن
                                    if "افزودن" in btn_text and "ایجاد" not in btn_text:
                                        logger.info(f"   ⏭️ Skipping 'افزودن' button (opens modal, not submit)")
                                        continue
                                    
                                    if is_visible and not is_disabled:
                                        # Scroll to button
                                        await btn.scroll_into_view_if_needed()
                                        await asyncio.sleep(0.3)
                                        
                                        # تلاش برای کلیک با Playwright
                                        try:
                                            logger.info(f"🖱️ Clicking button with Playwright: '{btn_text}'")
                                            await btn.click(timeout=5000)
                                            logger.info(f"✅ Playwright click successful on: '{btn_text}'")
                                            submit_found = True
                                            submit_button = btn
                                            break
                                        except Exception as click_err:
                                            logger.warning(f"⚠️ Normal click failed: {click_err}, trying force click...")
                                            try:
                                                await btn.click(force=True, timeout=5000)
                                                logger.info(f"✅ Playwright force click successful on: '{btn_text}'")
                                                submit_found = True
                                                submit_button = btn
                                                break
                                            except Exception as force_err:
                                                logger.warning(f"⚠️ Force click also failed: {force_err}")
                                except Exception as e:
                                    logger.debug(f"   Error checking button {idx}: {e}")
                            
                            if submit_found:
                                break
                    except Exception as e:
                        logger.debug(f"Selector failed: {selector} - {e}")
                
                # ====== مرحله ۲: اگر Playwright کار نکرد، JavaScript Click با شبیه‌سازی React Events ======
                if not submit_found:
                    logger.info("🔧 Playwright click didn't work, trying JavaScript with React event simulation...")
                    try:
                        js_click_result = await page.evaluate("""
                            () => {
                                // پیدا کردن دکمه ایجاد ادمین (نه افزودن!)
                                const allButtons = Array.from(document.querySelectorAll('button'));
                                
                                // فیلتر کردن: فقط دکمه‌هایی که "ایجاد" دارند اما "افزودن" ندارند
                                const submitButtons = allButtons.filter(btn => {
                                    const text = (btn.textContent || '').trim();
                                    const isVisible = btn.offsetParent !== null;
                                    const isDisabled = btn.disabled;
                                    
                                    // باید "ایجاد" داشته باشد و نباید "افزودن" داشته باشد
                                    const isCreateButton = text.includes('ایجاد') && !text.includes('افزودن');
                                    
                                    return isVisible && !isDisabled && isCreateButton;
                                });
                                
                                if (submitButtons.length === 0) {
                                    return { success: false, error: 'No submit button found' };
                                }
                                
                                const btn = submitButtons[0];
                                const text = (btn.textContent || '').trim();
                                
                                // Scroll into view
                                btn.scrollIntoView({ behavior: 'instant', block: 'center' });
                                
                                // Focus the button first
                                btn.focus();
                                
                                // شبیه‌سازی کامل events برای React
                                // 1. Pointer events
                                const pointerDown = new PointerEvent('pointerdown', {
                                    bubbles: true, cancelable: true, pointerType: 'mouse'
                                });
                                const pointerUp = new PointerEvent('pointerup', {
                                    bubbles: true, cancelable: true, pointerType: 'mouse'
                                });
                                
                                // 2. Mouse events
                                const mouseDown = new MouseEvent('mousedown', {
                                    bubbles: true, cancelable: true, view: window, button: 0
                                });
                                const mouseUp = new MouseEvent('mouseup', {
                                    bubbles: true, cancelable: true, view: window, button: 0
                                });
                                const click = new MouseEvent('click', {
                                    bubbles: true, cancelable: true, view: window, button: 0
                                });
                                
                                // Dispatch events in correct order
                                btn.dispatchEvent(pointerDown);
                                btn.dispatchEvent(mouseDown);
                                btn.dispatchEvent(pointerUp);
                                btn.dispatchEvent(mouseUp);
                                btn.dispatchEvent(click);
                                
                                return { 
                                    success: true, 
                                    method: 'javascript_react_events', 
                                    text: text
                                };
                            }
                        """)
                        
                        if js_click_result and js_click_result.get('success'):
                            logger.info(f"✅ JavaScript click with React events successful! Button: '{js_click_result.get('text')}'")
                            submit_found = True
                        else:
                            logger.warning(f"⚠️ JavaScript method failed: {js_click_result}")
                    except Exception as e:
                        logger.warning(f"⚠️ JavaScript method failed: {e}")
                
                # ====== مرحله ۳: جستجو با selectorهای عمومی ======
                if not submit_found:
                    logger.info("🔍 Searching for submit button with fallback selectors...")
                    
                    # تعریف سلکتورهای fallback
                    submit_selectors = [
                        'button:has-text("ایجاد ادمین")',
                        'button:has-text("Create Admin")',
                        'button[type="submit"]',
                        'button:has-text("Submit")',
                        'button:has-text("ارسال")',
                        'button:has-text("ثبت")',
                        'button:has-text("ایجاد")',
                        'button:has-text("Create")',
                        'input[type="submit"]'
                    ]
                    
                    for selector in submit_selectors:
                        try:
                            elements = page.locator(selector)
                            count = await elements.count()
                            logger.info(f"🔍 Found {count} elements with selector: {selector}")
                            
                            if count > 0:
                                # امتحان همه دکمه‌ها (نه فقط آخرین)
                                for idx in range(count):
                                    submit_button = elements.nth(idx)
                                    
                                    # بررسی visibility و disabled state
                                    try:
                                        is_visible = await submit_button.is_visible()
                                        is_disabled = await submit_button.is_disabled()
                                        
                                        # گرفتن متن دکمه برای لاگ
                                        try:
                                            button_text = await submit_button.text_content()
                                            button_text_clean = (button_text or "").strip()
                                            logger.info(f"🔍 Checking button {idx+1}/{count}: '{button_text_clean}' (visible: {is_visible}, disabled: {is_disabled})")
                                        except:
                                            logger.info(f"🔍 Checking button {idx+1}/{count} (visible: {is_visible}, disabled: {is_disabled})")
                                        
                                        # اگر disabled است، صبر کن تا enabled شود
                                        if is_disabled:
                                            logger.info(f"⏳ Button is disabled, waiting for it to be enabled...")
                                            for wait_attempt in range(10):  # حداکثر 10 ثانیه صبر
                                                await asyncio.sleep(1)
                                                is_still_disabled = await submit_button.is_disabled()
                                                if not is_still_disabled:
                                                    logger.info(f"✅ Button is now enabled after {wait_attempt+1} seconds")
                                                    is_disabled = False
                                                    break
                                                # اگر هنوز disabled است، امتحان JavaScript click
                                                if wait_attempt >= 3:  # بعد از 3 ثانیه
                                                    try:
                                                        await submit_button.evaluate("btn => { if (!btn.disabled) btn.click(); }")
                                                        is_still_disabled = await submit_button.is_disabled()
                                                        if not is_still_disabled:
                                                            logger.info(f"✅ Button enabled and clicked via JavaScript after {wait_attempt+1} seconds")
                                                            submit_found = True
                                                            break
                                                    except:
                                                        pass
                                        
                                        if is_visible and not is_disabled:
                                            # scroll into view
                                            await submit_button.scroll_into_view_if_needed()
                                            await asyncio.sleep(0.5)
                                            
                                            # بررسی مجدد بعد از scroll
                                            is_still_visible = await submit_button.is_visible()
                                            is_still_disabled = await submit_button.is_disabled()
                                            
                                            if is_still_visible and not is_still_disabled:
                                                # تلاش برای کلیک با روش‌های مختلف
                                                try:
                                                    button_text_display = button_text_clean if 'button_text_clean' in locals() else 'unknown'
                                                    logger.info(f"🖱️ Attempting to click button: '{button_text_display}'")
                                                    
                                                    # علامت‌گذاری که دکمه submit کلیک شده
                                                    await page.evaluate("window.__submitButtonClicked = true;")
                                                    
                                                    # روش 1: کلیک عادی
                                                    try:
                                                        await submit_button.click(timeout=10000)
                                                        submit_found = True
                                                        logger.info(f"✅ Clicked submit button successfully!")
                                                        break
                                                    except Exception as click_error:
                                                        logger.warning(f"⚠️ Normal click failed: {click_error}, trying force click...")
                                                        
                                                        # روش 2: Force click
                                                        try:
                                                            await submit_button.click(force=True, timeout=10000)
                                                            submit_found = True
                                                            logger.info(f"✅ Clicked submit button (force)")
                                                            break
                                                        except Exception as force_error:
                                                            logger.warning(f"⚠️ Force click also failed: {force_error}, trying JavaScript...")
                                                            
                                                            # روش 3: JavaScript click
                                                            try:
                                                                await submit_button.evaluate("btn => { btn.scrollIntoView({behavior: 'smooth', block: 'center'}); btn.click(); }")
                                                                submit_found = True
                                                                logger.info(f"✅ Clicked submit button (JavaScript)")
                                                                break
                                                            except Exception as js_error:
                                                                logger.warning(f"⚠️ JavaScript click also failed: {js_error}")
                                                                continue
                                                except Exception as e:
                                                    logger.warning(f"⚠️ All click methods failed: {e}")
                                                    continue
                                            else:
                                                logger.debug(f"Button not ready after scroll (visible: {is_still_visible}, disabled: {is_still_disabled})")
                                                continue
                                        elif not is_visible:
                                            # اگر visible نیست، امتحان force click
                                            try:
                                                await submit_button.scroll_into_view_if_needed()
                                                await asyncio.sleep(0.5)
                                                await submit_button.click(force=True, timeout=10000)
                                                submit_found = True
                                                logger.info(f"✅ Clicked submit button (force, not visible)")
                                                break
                                            except Exception as e:
                                                logger.debug(f"Force click failed: {e}")
                                                continue
                                    except Exception as check_error:
                                        logger.debug(f"Error checking button {idx+1}: {check_error}")
                                        continue
                                
                                if submit_found:
                                    break
                        except Exception as e:
                            logger.debug(f"Submit selector failed: {selector} - {e}")
                            continue
                
                # اگر پیدا نشد، جستجوی پیشرفته در تمام دکمه‌ها
                if not submit_found:
                    logger.warning("⚠️ Standard submit selectors failed, searching all buttons...")
                    
                    try:
                        all_buttons = page.locator('button')
                        button_count = await all_buttons.count()
                        logger.info(f"🔍 Found {button_count} total buttons on page")
                        
                        # جستجو برای دکمه‌هایی که متنشان شامل کلمات کلیدی است
                        keywords = [
                            "ایجاد ادمین جدید", "Add New Admin",  # اولویت اول
                            "ایجاد ادمین", "Create Admin",  # اولویت دوم
                            "افزودن ادمین جدید", "Add New Admin",  # اولویت سوم
                            "ایجاد", "Create", "Submit", "ارسال", "ثبت"  # اولویت چهارم
                        ]
                        
                        # جستجو با اولویت‌بندی
                        for priority, keyword_group in enumerate(keywords, 1):
                            if submit_found:
                                break
                            
                            logger.info(f"🔍 Searching with priority {priority}: '{keyword_group}'")
                            for i in range(button_count):
                                try:
                                    button = all_buttons.nth(i)
                                    is_visible = await button.is_visible()
                                    
                                    if is_visible:
                                        button_text = await button.text_content()
                                        button_text_clean = (button_text or "").strip()
                                        
                                        # بررسی اینکه آیا این دکمه submit است (با اولویت)
                                        if keyword_group in button_text_clean:
                                            # بررسی اینکه disabled نیست
                                            is_disabled = await button.is_disabled()
                                            
                                            logger.info(f"🔍 Found candidate button {i+1}/{button_count}: '{button_text_clean}' (disabled: {is_disabled})")
                                            
                                            # اگر disabled است، صبر کن
                                            if is_disabled:
                                                logger.info(f"⏳ Button is disabled, waiting...")
                                                for wait_attempt in range(3):
                                                    await asyncio.sleep(1)
                                                    is_still_disabled = await button.is_disabled()
                                                    if not is_still_disabled:
                                                        logger.info(f"✅ Button enabled after {wait_attempt+1} seconds")
                                                        break
                                            
                                            is_still_disabled = await button.is_disabled()
                                            if not is_still_disabled:
                                                logger.info(f"✅ Attempting to click button: '{button_text_clean}'")
                                                await button.scroll_into_view_if_needed()
                                                await asyncio.sleep(0.5)
                                                
                                                # تلاش برای کلیک
                                                try:
                                                    await button.click(timeout=10000)
                                                    submit_found = True
                                                    logger.info(f"✅ Clicked submit button: '{button_text_clean}'")
                                                    break
                                                except Exception as click_error:
                                                    logger.warning(f"⚠️ Normal click failed: {click_error}, trying force...")
                                                    try:
                                                        await button.click(force=True, timeout=10000)
                                                        submit_found = True
                                                        logger.info(f"✅ Clicked submit button (force): '{button_text_clean}'")
                                                        break
                                                    except Exception as force_error:
                                                        logger.warning(f"⚠️ Force click also failed: {force_error}")
                                                        # امتحان JavaScript click
                                                        try:
                                                            await button.evaluate("btn => btn.click()")
                                                            submit_found = True
                                                            logger.info(f"✅ Clicked submit button (JavaScript): '{button_text_clean}'")
                                                            break
                                                        except:
                                                            continue
                                except Exception as e:
                                    logger.debug(f"Button {i} check failed: {e}")
                                    continue
                            
                            if submit_found:
                                break
                    except Exception as e:
                        logger.error(f"❌ Advanced button search failed: {e}", exc_info=True)
                
                # روش آخر: استفاده از keyboard Enter یا JavaScript (اگر دکمه پیدا نشد یا کلیک نشد)
                if not submit_found:
                    logger.warning("⚠️ Could not click submit button with selectors, trying alternative methods...")
                    
                    # روش 1: استفاده از JavaScript برای پیدا کردن و کلیک دکمه (قوی‌ترین روش)
                    try:
                        logger.info("🔧 Trying JavaScript to find and click submit button...")
                        js_result = await page.evaluate("""
                            () => {
                                // اولویت 1: دکمه‌های با متن دقیق
                                const priorityKeywords = [
                                    'ایجاد ادمین جدید',
                                    'Add New Admin',
                                    'ایجاد ادمین',
                                    'Create Admin',
                                    'افزودن ادمین جدید'
                                ];
                                
                                const allButtons = Array.from(document.querySelectorAll('button'));
                                
                                // جستجو با اولویت
                                for (let keyword of priorityKeywords) {
                                    for (let btn of allButtons) {
                                        const text = (btn.textContent || btn.innerText || '').trim();
                                        const isVisible = btn.offsetParent !== null;
                                        const isDisabled = btn.disabled || btn.hasAttribute('disabled');
                                        
                                        if (isVisible && !isDisabled && text.includes(keyword)) {
                                            // scroll to button
                                            btn.scrollIntoView({ behavior: 'smooth', block: 'center' });
                                            
                                            // کلیک با dispatchEvent برای اطمینان
                                            const clickEvent = new MouseEvent('click', {
                                                bubbles: true,
                                                cancelable: true,
                                                view: window
                                            });
                                            btn.dispatchEvent(clickEvent);
                                            
                                            // همچنین کلیک مستقیم
                                            btn.click();
                                            
                                            return { success: true, method: 'priority_keyword', text: text };
                                        }
                                    }
                                }
                                
                                // اولویت 2: دکمه‌های submit
                                for (let btn of allButtons) {
                                    if (btn.type === 'submit' && btn.offsetParent !== null && !btn.disabled) {
                                        btn.scrollIntoView({ behavior: 'smooth', block: 'center' });
                                        btn.click();
                                        return { success: true, method: 'submit_type', text: (btn.textContent || '').trim() };
                                    }
                                }
                                
                                // اولویت 3: دکمه‌های با کلمات کلیدی عمومی
                                const generalKeywords = ['ایجاد', 'Create', 'Submit', 'ثبت', 'ارسال'];
                                for (let keyword of generalKeywords) {
                                    for (let btn of allButtons) {
                                        const text = (btn.textContent || btn.innerText || '').trim();
                                        if (btn.offsetParent !== null && !btn.disabled && text.includes(keyword)) {
                                            btn.scrollIntoView({ behavior: 'smooth', block: 'center' });
                                            btn.click();
                                            return { success: true, method: 'general_keyword', text: text };
                                        }
                                    }
                                }
                                
                                // اولویت 4: فرم submit
                                const forms = document.querySelectorAll('form');
                                if (forms.length > 0) {
                                    const lastForm = forms[forms.length - 1];
                                    const submitBtn = lastForm.querySelector('button[type="submit"]');
                                    if (submitBtn && submitBtn.offsetParent !== null && !submitBtn.disabled) {
                                        submitBtn.scrollIntoView({ behavior: 'smooth', block: 'center' });
                                        submitBtn.click();
                                        return { success: true, method: 'form_submit', text: (submitBtn.textContent || '').trim() };
                                    }
                                    // اگر دکمه submit نبود، خود فرم را submit کن
                                    lastForm.submit();
                                    return { success: true, method: 'form_submit_direct' };
                                }
                                
                                return { success: false, error: 'No button or form found' };
                            }
                        """)
                        
                        if js_result and js_result.get('success'):
                            logger.info(f"✅ JavaScript click successful! Method: {js_result.get('method')}, Button text: {js_result.get('text', 'N/A')}")
                            await asyncio.sleep(2)
                            submit_found = True
                        else:
                            logger.warning(f"⚠️ JavaScript click failed: {js_result.get('error', 'Unknown error')}")
                    except Exception as e:
                        logger.error(f"❌ JavaScript submit failed: {e}", exc_info=True)
                    
                    # روش 2: استفاده از keyboard Enter (اگر JavaScript کار نکرد)
                    if not submit_found:
                        try:
                            logger.info("⌨️ Trying keyboard Enter...")
                            # پیدا کردن آخرین input یا textarea
                            try:
                                last_input = page.locator('input, textarea').last
                                if await last_input.is_visible():
                                    await last_input.focus()
                                    await asyncio.sleep(0.5)
                            except:
                                pass
                            
                            # استفاده از Enter برای submit فرم
                            await page.keyboard.press("Enter")
                            await asyncio.sleep(2)
                            submit_found = True
                            logger.info("✅ Submitted form using keyboard Enter")
                        except Exception as e:
                            logger.debug(f"Keyboard Enter failed: {e}")
                    
                    # روش 3: استفاده از coordinate-based clicking (اگر AI coordinates داده)
                    if not submit_found and ai_decision.get("coordinates"):
                        try:
                            logger.info("📍 Trying coordinate-based click...")
                            coords = ai_decision.get("coordinates")
                            x, y = coords[0], coords[1]
                            await page.mouse.click(x, y)
                            await asyncio.sleep(2)
                            submit_found = True
                            logger.info(f"✅ Clicked at coordinates ({x}, {y})")
                        except Exception as e:
                            logger.debug(f"Coordinate click failed: {e}")
                
                if submit_found:
                    # صبر کوتاه برای بررسی نتیجه click
                    await asyncio.sleep(1)
                    
                    # ====== بررسی ارور validation HTML5 ======
                    validation_error = await page.evaluate("""
                        () => {
                            // بررسی HTML5 validation errors
                            const invalidInputs = document.querySelectorAll('input:invalid');
                            if (invalidInputs.length > 0) {
                                const errors = [];
                                invalidInputs.forEach(inp => {
                                    errors.push({
                                        type: inp.type,
                                        name: inp.name || inp.placeholder,
                                        validationMessage: inp.validationMessage
                                    });
                                });
                                return { hasError: true, errors: errors };
                            }
                            
                            // بررسی پیام‌های ارور visible در صفحه
                            const errorTexts = ['Please fill out this field', 'فیلد الزامی', 'required'];
                            for (let text of errorTexts) {
                                if (document.body.innerText.includes(text)) {
                                    return { hasError: true, message: text };
                                }
                            }
                            
                            return { hasError: false };
                        }
                    """)
                    
                    if validation_error and validation_error.get('hasError'):
                        logger.warning(f"⚠️ Form validation failed! Errors: {validation_error}")
                        logger.warning("⚠️ Form fields might be empty or invalid - need to refill")
                        result["error"] = f"Form validation error: {validation_error}"
                        result["success"] = False
                        return result
                    
                    # بررسی اینکه آیا صفحه reload شده یا نه
                    try:
                        current_url_after = page.url
                        if current_url_after != current_url_before:
                            logger.warning(f"⚠️ Page reloaded! URL changed from {current_url_before} to {current_url_after}")
                            logger.warning("⚠️ This might have cleared the form fields")
                            # اگر reload شد، باید دوباره فیلدها را پر کنیم
                            result["error"] = "Page reloaded before submit - form fields may be cleared"
                            result["success"] = False
                            return result
                    except:
                        pass
                    
                    # صبر برای ارسال فرم و بررسی موفقیت
                    logger.info("⏳ Waiting for form submission to complete...")
                    
                    # صبر برای تغییرات صفحه
                    try:
                        # صبر برای navigation یا تغییرات DOM (اما نه reload کامل)
                        await page.wait_for_load_state('networkidle', timeout=15000)
                        logger.info("✅ Page loaded (networkidle)")
                    except:
                        logger.warning("⚠️ networkidle timeout, checking for success indicators...")
                    
                    # صبر بیشتر برای اطمینان از ثبت
                    await asyncio.sleep(3)
                    
                    # بررسی موفقیت: جستجو برای پیام موفقیت یا تغییر URL
                    success_indicators = [
                        'text=/success/i',
                        'text=/موفق/i',
                        'text=/created/i',
                        'text=/ایجاد شد/i',
                        'text=/ثبت شد/i',
                    ]
                    
                    success_found = False
                    for indicator in success_indicators:
                        try:
                            elements = page.locator(indicator)
                            count = await elements.count()
                            if count > 0:
                                success_found = True
                                logger.info(f"✅ Success indicator found: {indicator}")
                                break
                        except:
                            continue
                    
                    # گرفتن screenshot برای بررسی نتیجه
                    try:
                        await page.screenshot(path="debug_after_submit.png")
                        logger.info("📸 Screenshot saved: debug_after_submit.png")
                    except:
                        pass
                    
                    if success_found:
                        logger.info("✅ Form submitted successfully - success message detected!")
                    else:
                        logger.info("✅ Form submitted successfully - button clicked (no success message detected)")
                    
                    result["success"] = True
                else:
                    result["error"] = "Could not find or click submit button"
                    logger.warning(f"⚠️ {result['error']}")
                    # گرفتن screenshot برای دیباگ
                    try:
                        await page.screenshot(path="debug_submit_not_found.png")
                    except:
                        pass
            
            else:
                # اگر action ناشناخته است، لاگ کن و wait کن
                result["error"] = f"Unknown action: {action}"
                logger.warning(f"⚠️ {result['error']}")
                # Fallback: wait برای اینکه AI فرصت دوباره فکر کند
                await asyncio.sleep(1)
                result["success"] = False  # صریحاً False
            
            return result
            
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"❌ Error executing action: {e}")
            return result
    
    def _run_in_proactor_loop(self, coro):
        """
        اجرای coroutine در ProactorEventLoop برای Windows
        این متد باید در thread جداگانه صدا زده شود
        """
        if sys.platform == 'win32':
            loop = asyncio.ProactorEventLoop()
        else:
            loop = asyncio.new_event_loop()
        
        asyncio.set_event_loop(loop)
        
        try:
            logger.info("🔄 Starting ProactorEventLoop for Playwright...")
            result = loop.run_until_complete(coro)
            logger.info("✅ ProactorEventLoop completed successfully")
            return result
        except Exception as e:
            logger.error(f"❌ Error in ProactorEventLoop: {e}", exc_info=True)
            raise
        finally:
            try:
                # پاکسازی tasks
                pending = asyncio.all_tasks(loop)
                if pending:
                    logger.info(f"🧹 Cleaning up {len(pending)} pending tasks...")
                    for task in pending:
                        task.cancel()
                    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            except Exception as e:
                logger.warning(f"⚠️ Cleanup warning: {e}")
            finally:
                try:
                    loop.close()
                    logger.info("🔒 Event loop closed")
                except:
                    pass
    
    def _create_admin_sync_wrapper(self, *args, **kwargs):
        """
        Wrapper function برای اجرای create_admin در thread جداگانه
        این function sync است و می‌تواند به run_in_executor داده شود
        """
        coro = self._create_admin_internal(*args, **kwargs)
        return self._run_in_proactor_loop(coro)
    
    def _execute_task_sync_wrapper(self, *args, **kwargs):
        """
        Wrapper function برای اجرای execute_task در thread جداگانه
        این function sync است و می‌تواند به run_in_executor داده شود
        """
        coro = self._execute_task_internal(*args, **kwargs)
        return self._run_in_proactor_loop(coro)
    
    async def execute_task(
        self,
        task_description: str,
        login_email: Optional[str] = None,
        login_password: Optional[str] = None,
        url: str = "http://localhost:3000/super-admin"
    ) -> AgenticPlaywrightResult:
        """
        اجرای یک task عمومی با استفاده از Agentic AI
        
        این متد می‌تواند هر task description را بگیرد و اجرا کند
        """
        # در Windows، باید در thread جداگانه با ProactorEventLoop اجرا شود
        if sys.platform == 'win32':
            logger.info("🪟 Windows detected - running execute_task in separate thread with ProactorEventLoop")
            # استفاده از run_in_executor برای جلوگیری از block شدن
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                self._execute_task_sync_wrapper,
                task_description,
                login_email,
                login_password,
                url
            )
        else:
            return await self._execute_task_internal(task_description, login_email, login_password, url)
    
    async def _execute_task_internal(
        self,
        task_description: str,
        login_email: Optional[str] = None,
        login_password: Optional[str] = None,
        url: str = "http://localhost:3000/super-admin"
    ) -> AgenticPlaywrightResult:
        """
        اجرای داخلی task (بدون مدیریت Windows)
        """
        steps_taken = []
        screenshots = []
        browser = None
        page = None
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=False)
                page = await browser.new_page()
                
                # اگر login credentials داده شده، ابتدا لاگین کن
                if login_email and login_password:
                    logger.info(f"🔐 Logging in first...")
                    try:
                        await page.goto(url)
                        await page.wait_for_load_state('networkidle')
                        await asyncio.sleep(2)
                        
                        # پیدا کردن فیلدهای login
                        email_input = page.locator('input[type="email"]')
                        password_input = page.locator('input[type="password"]')
                        submit_button = page.locator('button[type="submit"]')
                        
                        if await email_input.count() > 0 and await password_input.count() > 0:
                            await email_input.fill(login_email)
                            await password_input.fill(login_password)
                            await submit_button.click()
                            await page.wait_for_load_state('networkidle')
                            await asyncio.sleep(3)
                            logger.info("✅ Login successful")
                        else:
                            logger.warning("⚠️ Could not find login fields, continuing anyway...")
                    except Exception as e:
                        logger.warning(f"⚠️ Login failed: {e}, continuing anyway...")
                else:
                    # اگر login credentials داده نشده، فقط به URL برو
                    logger.info(f"🌐 Navigating to {url}")
                    await page.goto(url)
                    await page.wait_for_load_state('networkidle')
                    await asyncio.sleep(2)
                
                logger.info(f"🤖 Starting Agentic Task Execution")
                logger.info(f"📋 Task: {task_description[:200]}...")
                
                iteration = 0
                task_complete = False
                last_url = None
                
                while iteration < self.max_iterations and not task_complete:
                    iteration += 1
                    logger.info(f"\n🔄 Iteration {iteration}/{self.max_iterations}")
                    
                    # بررسی اینکه آیا صفحه reload شده یا نه
                    try:
                        current_url = page.url
                        if last_url and current_url != last_url:
                            logger.warning(f"⚠️ Page URL changed! Previous: {last_url}, Current: {current_url}")
                            logger.warning("⚠️ This might indicate a page reload - form fields may be cleared")
                            # صبر برای بارگذاری کامل صفحه
                            await page.wait_for_load_state('networkidle', timeout=10000)
                            await asyncio.sleep(2)
                        last_url = current_url
                    except:
                        pass
                    
                    # تحلیل صفحه با AI
                    ai_decision = await self._analyze_page_with_ai(
                        page=page,
                        task_description=task_description,
                        previous_actions=steps_taken
                    )
                    
                    # بررسی اینکه آیا AI یک navigate action پیشنهاد داده که باعث reload می‌شود
                    if ai_decision.get("action") == "navigate":
                        nav_url = ai_decision.get("url", "") or ai_decision.get("element_description", "")
                        current_url = page.url
                        # اگر URL فعلی همان URL navigate است، skip کن
                        if nav_url and (current_url in nav_url or nav_url in current_url):
                            logger.warning(f"⚠️ AI suggested navigate to current URL, skipping to prevent reload")
                            ai_decision["action"] = "wait"
                            ai_decision["element_description"] = "Already on correct page"
                    
                    # بررسی اینکه آیا کار تمام شده
                    if ai_decision.get("action") == "done":
                        task_complete = True
                        logger.info("✅ AI determined task is complete")
                        break
                    
                    # اجرای اقدام
                    action_result = await self._execute_action(
                        page=page,
                        ai_decision=ai_decision,
                        previous_actions=steps_taken
                    )
                    
                    # بررسی مجدد URL بعد از action
                    try:
                        new_url = page.url
                        if last_url and new_url != last_url:
                            logger.warning(f"⚠️ Page reloaded after action! URL changed from {last_url} to {new_url}")
                            logger.warning("⚠️ Form fields may have been cleared")
                        last_url = new_url
                    except:
                        pass
                    
                    # ذخیره نتیجه
                    step_info = {
                        "iteration": iteration,
                        "action": action_result.get("action"),
                        "description": action_result.get("description"),
                        "success": action_result.get("success"),
                        "error": action_result.get("error"),
                        "ai_confidence": ai_decision.get("confidence", 0.0),
                        "ai_reasoning": ai_decision.get("reasoning", "")
                    }
                    steps_taken.append(step_info)
                    
                    # اگر خطا رخ داد
                    if not action_result.get("success"):
                        logger.warning(f"⚠️ Action failed: {action_result.get('error')}")
                        # ادامه می‌دهیم - AI ممکن است راه دیگری پیدا کند
                    
                    # صبر کوتاه بین اقدامات
                    await asyncio.sleep(1)
                
                # بررسی موفقیت
                success = task_complete or len([s for s in steps_taken if s.get("success")]) >= 3
                
                # گرفتن screenshot نهایی
                try:
                    if not page.is_closed():
                        final_screenshot = await self._take_screenshot(page, "final")
                        if final_screenshot:
                            screenshots.append(final_screenshot)
                except Exception as e:
                    logger.warning(f"⚠️ Could not take final screenshot: {e}")
                
                # بستن browser
                try:
                    await browser.close()
                    logger.info("🔒 Browser closed successfully")
                except Exception as e:
                    logger.warning(f"⚠️ Browser may already be closed or error occurred: {e}")
                
                if success:
                    logger.info("✅ Agentic task completed successfully!")
                    return AgenticPlaywrightResult(
                        success=True,
                        result=f"Task completed successfully using AI",
                        steps_taken=steps_taken,
                        screenshots=screenshots
                    )
                else:
                    logger.warning("⚠️ Task may not be complete")
                    return AgenticPlaywrightResult(
                        success=False,
                        error="Task completed but success not confirmed",
                        steps_taken=steps_taken,
                        screenshots=screenshots
                    )
                
        except KeyboardInterrupt:
            logger.warning("⚠️ Task interrupted by user")
            try:
                if 'browser' in locals() and browser:
                    await browser.close()
            except:
                pass
            return AgenticPlaywrightResult(
                success=False,
                error="Task interrupted by user",
                steps_taken=steps_taken,
                screenshots=screenshots
            )
        except asyncio.CancelledError:
            logger.warning("⚠️ Task was cancelled")
            try:
                if 'browser' in locals() and browser:
                    await browser.close()
            except:
                pass
            return AgenticPlaywrightResult(
                success=False,
                error="Task was cancelled",
                steps_taken=steps_taken,
                screenshots=screenshots
            )
        except Exception as e:
            logger.error(f"❌ Agentic Playwright task failed: {e}", exc_info=True)
            try:
                if 'browser' in locals() and browser:
                    await browser.close()
            except:
                pass
            return AgenticPlaywrightResult(
                success=False,
                error=str(e),
                steps_taken=steps_taken,
                screenshots=screenshots
            )
    
    async def create_admin(
        self,
        admin_email: str,
        admin_password: str,
        login_email: str,
        login_password: str,
        admin_full_name: str = "test",
        admin_role: str = "Admin",
        url: str = "http://localhost:3000/super-admin"
    ) -> AgenticPlaywrightResult:
        """
        ساخت ادمین با استفاده از Agentic AI
        
        این متد از Vision AI استفاده می‌کند تا:
        1. صفحه را ببیند و تحلیل کند
        2. تصمیم بگیرد چه کاری انجام دهد
        3. اقدامات را اجرا کند
        4. نتیجه را بررسی کند
        """
        # در Windows، باید در thread جداگانه با ProactorEventLoop اجرا شود
        if sys.platform == 'win32':
            logger.info("🪟 Windows detected - running create_admin in separate thread with ProactorEventLoop")
            # استفاده از run_in_executor برای جلوگیری از block شدن
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                self._create_admin_sync_wrapper,
                admin_email,
                admin_password,
                login_email,
                login_password,
                admin_full_name,
                admin_role,
                url
            )
        else:
            return await self._create_admin_internal(
                admin_email, admin_password, login_email, login_password,
                admin_full_name, admin_role, url
            )
    
    async def _create_admin_internal(
        self,
        admin_email: str,
        admin_password: str,
        login_email: str,
        login_password: str,
        admin_full_name: str = "test",
        admin_role: str = "Admin",
        url: str = "http://localhost:3000/super-admin"
    ) -> AgenticPlaywrightResult:
        """
        اجرای داخلی create_admin (بدون مدیریت Windows)
        """
        steps_taken = []
        screenshots = []
        browser = None
        page = None
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=False)
                page = await browser.new_page()
                
                # ابتدا navigate به URL (قبل از شروع loop)
                logger.info(f"🌐 Navigating to {url} first...")
                try:
                    await page.goto(url)
                    await page.wait_for_load_state('networkidle')
                    await asyncio.sleep(2)
                    logger.info("✅ Initial navigation completed")
                except Exception as e:
                    logger.warning(f"⚠️ Initial navigation failed: {e}")
                
                # Task description برای AI
                task_description = f"""
Create a new admin user with the following details:
- Email: {admin_email}
- Password: {admin_password}
- Full Name: {admin_full_name}
- Role: {admin_role}

You are currently on: {url}

You need to:
1. Login with email: {login_email} and password: {login_password}
2. Navigate to admin management section
3. Click "Add New Admin" button
4. Fill in the form with the admin details above
5. Select the role: {admin_role}
6. Submit the form
7. Verify success

Note: You are already on the login page, so start by filling the login form.
"""
                
                logger.info(f"🤖 Starting Agentic Admin Creation")
                logger.info(f"📋 Task: {task_description[:200]}...")
                
                iteration = 0
                task_complete = False
                last_url = None
                
                while iteration < self.max_iterations and not task_complete:
                    iteration += 1
                    logger.info(f"\n🔄 Iteration {iteration}/{self.max_iterations}")
                    
                    # بررسی اینکه آیا صفحه باز است
                    try:
                        if page.is_closed():
                            logger.error("❌ Page is closed! Cannot continue.")
                            break
                    except:
                        pass
                    
                    # بررسی اینکه آیا صفحه reload شده یا نه
                    try:
                        current_url = page.url
                        if last_url and current_url != last_url:
                            logger.warning(f"⚠️ Page URL changed! Previous: {last_url}, Current: {current_url}")
                            logger.warning("⚠️ This might indicate a page reload - form fields may be cleared")
                            # صبر برای بارگذاری کامل صفحه
                            await page.wait_for_load_state('networkidle', timeout=10000)
                            await asyncio.sleep(2)
                        last_url = current_url
                    except Exception as url_check_error:
                        logger.warning(f"⚠️ Error checking URL: {url_check_error}")
                        try:
                            if page.is_closed():
                                logger.error("❌ Page is closed! Cannot continue.")
                                break
                        except:
                            pass
                    
                    # بررسی اینکه آیا همه فیلدها پر شده‌اند و باید submit کنیم
                    recent_actions = steps_taken[-5:] if len(steps_taken) >= 5 else steps_taken
                    filled_fields = [s for s in recent_actions if s.get("action") == "fill"]
                    selected_role = [s for s in recent_actions if s.get("action") == "select" and ("role" in str(s.get("description", "")).lower() or "نقش" in str(s.get("description", "")))]
                    
                    # اگر همه فیلدها پر شده و نقش انتخاب شده، فوراً submit کنیم
                    if len(filled_fields) >= 3 and len(selected_role) >= 1:
                        # بررسی اینکه آیا قبلاً submit کرده‌ایم
                        submitted = [s for s in recent_actions if s.get("action") == "submit"]
                        if not submitted:
                            logger.info("🚀 All form fields filled and role selected - forcing submit action!")
                            ai_decision = {
                                "action": "submit",
                                "element_description": "ایجاد ادمین",
                                "confidence": 1.0,
                                "reasoning": "All form fields are filled, must submit now"
                            }
                        else:
                            # اگر قبلاً submit کرده‌ایم، با AI ادامه بده
                            ai_decision = await self._analyze_page_with_ai(
                                page=page,
                                task_description=task_description,
                                previous_actions=steps_taken
                            )
                    else:
                        # تحلیل صفحه با AI
                        ai_decision = await self._analyze_page_with_ai(
                            page=page,
                            task_description=task_description,
                            previous_actions=steps_taken
                        )
                    
                    # بررسی اینکه آیا AI یک navigate action پیشنهاد داده که باعث reload می‌شود
                    if ai_decision.get("action") == "navigate":
                        nav_url = ai_decision.get("url", "") or ai_decision.get("element_description", "")
                        current_url = page.url
                        # اگر URL فعلی همان URL navigate است، skip کن
                        if nav_url and (current_url in nav_url or nav_url in current_url):
                            logger.warning(f"⚠️ AI suggested navigate to current URL, skipping to prevent reload")
                            ai_decision["action"] = "wait"
                            ai_decision["element_description"] = "Already on correct page"
                    
                    # بررسی اینکه آیا کار تمام شده
                    if ai_decision.get("action") == "done":
                        task_complete = True
                        logger.info("✅ AI determined task is complete")
                        break
                    
                    # بررسی اینکه آیا صفحه باز است قبل از اجرای action
                    try:
                        if page.is_closed():
                            logger.error("❌ Page is closed before action execution! Cannot continue.")
                            break
                    except Exception as check_error:
                        logger.warning(f"⚠️ Error checking if page is closed: {check_error}")
                        # اگر نمی‌توانیم بررسی کنیم، ادامه بده
                    
                    # اجرای اقدام با try-catch برای جلوگیری از بسته شدن صفحه
                    try:
                        action_result = await self._execute_action(
                            page=page,
                            ai_decision=ai_decision,
                            previous_actions=steps_taken
                        )
                    except Exception as action_error:
                        logger.error(f"❌ Error executing action: {action_error}", exc_info=True)
                        # بررسی اینکه آیا صفحه بسته شده
                        try:
                            if page.is_closed():
                                logger.error("❌ Page closed due to action error!")
                                break
                        except:
                            pass
                        # ادامه با یک action ناموفق
                        action_result = {
                            "action": ai_decision.get("action"),
                            "description": ai_decision.get("element_description", ""),
                            "success": False,
                            "error": str(action_error)
                        }
                    
                    # بررسی مجدد URL بعد از action و اینکه صفحه باز است
                    try:
                        if page.is_closed():
                            logger.error("❌ Page closed after action execution!")
                            break
                        
                        new_url = page.url
                        if last_url and new_url != last_url:
                            logger.warning(f"⚠️ Page reloaded after action! URL changed from {last_url} to {new_url}")
                            logger.warning("⚠️ Form fields may have been cleared")
                        last_url = new_url
                    except Exception as url_error:
                        logger.warning(f"⚠️ Error checking URL after action: {url_error}")
                        try:
                            if page.is_closed():
                                logger.error("❌ Page is closed! Cannot continue.")
                                break
                        except:
                            pass
                    
                    # ذخیره نتیجه
                    step_info = {
                        "iteration": iteration,
                        "action": action_result.get("action"),
                        "description": action_result.get("description"),
                        "success": action_result.get("success"),
                        "error": action_result.get("error"),
                        "ai_confidence": ai_decision.get("confidence", 0.0),
                        "ai_reasoning": ai_decision.get("reasoning", "")
                    }
                    steps_taken.append(step_info)
                    
                    # اگر خطا رخ داد
                    if not action_result.get("success"):
                        logger.warning(f"⚠️ Action failed: {action_result.get('error')}")
                        # ادامه می‌دهیم - AI ممکن است راه دیگری پیدا کند
                    
                    # صبر کوتاه بین اقدامات
                    await asyncio.sleep(1)
                
                # بررسی موفقیت - بهبود منطق
                success = False
                
                if task_complete:
                    success = True
                elif len(steps_taken) > 0:
                    # بررسی آخرین اقدامات
                    last_steps = steps_taken[-3:] if len(steps_taken) >= 3 else steps_taken
                    
                    # اگر آخرین اقدام submit موفق بود
                    if any(step.get("action") == "submit" and step.get("success") for step in last_steps):
                        success = True
                    # یا اگر چند اقدام موفق پشت سر هم داشتیم
                    elif len([s for s in last_steps if s.get("success")]) >= 2:
                        # بررسی اینکه آیا به صفحه جدیدی رفته‌ایم
                        try:
                            final_url = page.url
                            if "admin" in final_url.lower() and "create" not in final_url.lower():
                                success = True
                        except:
                            pass
                
                # گرفتن screenshot نهایی (فقط اگر browser هنوز باز است)
                try:
                    if not page.is_closed():
                        final_screenshot = await self._take_screenshot(page, "final")
                        if final_screenshot:
                            screenshots.append(final_screenshot)
                except Exception as e:
                    logger.warning(f"⚠️ Could not take final screenshot: {e}")
                
                # بستن browser (فقط اگر هنوز باز است)
                try:
                    # تلاش برای بستن browser
                    await browser.close()
                    logger.info("🔒 Browser closed successfully")
                except Exception as e:
                    # اگر browser قبلاً بسته شده یا خطایی رخ داده
                    logger.warning(f"⚠️ Browser may already be closed or error occurred: {e}")
                
                if success:
                    logger.info("✅ Agentic admin creation completed successfully!")
                    return AgenticPlaywrightResult(
                        success=True,
                        result=f"Admin {admin_email} created successfully using AI",
                        steps_taken=steps_taken,
                        screenshots=screenshots
                    )
                else:
                    logger.warning("⚠️ Task may not be complete")
                    return AgenticPlaywrightResult(
                        success=False,
                        error="Task completed but success not confirmed",
                        steps_taken=steps_taken,
                        screenshots=screenshots
                    )
                
        except KeyboardInterrupt:
            logger.warning("⚠️ Task interrupted by user")
            # بستن browser در صورت interrupt
            try:
                if 'browser' in locals() and browser:
                    await browser.close()
            except:
                pass
            return AgenticPlaywrightResult(
                success=False,
                error="Task interrupted by user",
                steps_taken=steps_taken,
                screenshots=screenshots
            )
        except asyncio.CancelledError:
            logger.warning("⚠️ Task was cancelled")
            # بستن browser در صورت cancel
            try:
                if 'browser' in locals() and browser:
                    await browser.close()
            except:
                pass
            return AgenticPlaywrightResult(
                success=False,
                error="Task was cancelled",
                steps_taken=steps_taken,
                screenshots=screenshots
            )
        except Exception as e:
            logger.error(f"❌ Agentic Playwright task failed: {e}", exc_info=True)
            # بستن browser در صورت خطا
            try:
                if 'browser' in locals() and browser:
                    await browser.close()
            except:
                pass
            return AgenticPlaywrightResult(
                success=False,
                error=str(e),
                steps_taken=steps_taken,
                screenshots=screenshots
            )


# Singleton با مدل پیش‌فرض Vision-capable
agentic_playwright_service = AgenticPlaywrightService(
    vision_model="google/gemini-2.5-flash"  # مدل رایگان با Vision
)