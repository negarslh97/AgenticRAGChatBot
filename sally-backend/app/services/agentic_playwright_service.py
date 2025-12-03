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
from io import BytesIO
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from playwright.async_api import async_playwright, Page
from PIL import Image
import json

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
                raise Exception("Failed to take screenshot")
            
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
- click: Click on a button, link, or clickable element
- fill: Fill in an input field (text, email, password, etc.)
- select: Select an option from a dropdown
- wait: Wait for something to appear or load
- navigate: Navigate to a different page (use page.goto())
- submit: Submit a form
- scroll: Scroll the page
- done: Task is complete

RESPONSE FORMAT (MUST BE VALID JSON, NO MARKDOWN CODE BLOCKS):
{{
    "action": "click|fill|select|wait|navigate|submit|scroll|done",
    "element_description": "Description of element to interact with (in Persian or English)",
    "element_type": "button|input|link|select|text|other",
    "element_text": "Visible text on the element (if any)",
    "input_value": "Value to fill (only if action is 'fill')",
    "selector_hint": "CSS selector hint (optional, e.g., 'button', 'input[type=email]')",
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
                # Navigate to a URL - فقط اگر URL معتبر باشد
                url_to_navigate = element_description or ai_decision.get("url", "")
                
                # بررسی اینکه آیا این یک URL معتبر است یا فقط متن
                url_pattern = re.compile(
                    r'^https?://'  # شروع با http:// یا https://
                    r'|^/'  # یا مسیر نسبی
                )
                
                # اگر URL معتبر نیست، skip کن و wait (AI باید دوباره فکر کند)
                if not url_to_navigate or not url_pattern.match(url_to_navigate.strip()):
                    logger.warning(f"⚠️ Invalid URL for navigate: {url_to_navigate}. Skipping - AI should use click instead.")
                    # به جای خطا، wait می‌کنیم تا AI دوباره فکر کند
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
                select_found = False
                
                try:
                    # روش 1: پیدا کردن dropdown trigger (React Select)
                    dropdown_trigger = None
                    
                    # جستجو برای dropdown trigger با روش‌های مختلف
                    trigger_selectors = [
                        'div:has-text("انتخاب نقش")',
                        'div:has-text("Select Role")',
                        'div:has-text("نقش")',
                        '.css-control',
                        '.select__control',
                        '[class*="select"]',
                        '[class*="Select"]',
                        'div[role="combobox"]',
                    ]
                    
                    for selector in trigger_selectors:
                        try:
                            elements = page.locator(selector)
                            count = await elements.count()
                            if count > 0:
                                # استفاده از آخرین dropdown (معمولاً فرم جدید)
                                dropdown_trigger = elements.last
                                if await dropdown_trigger.is_visible():
                                    logger.info(f"✅ Found dropdown trigger with selector: {selector}")
                                    break
                        except Exception as e:
                            logger.debug(f"Trigger selector failed: {selector} - {e}")
                            continue
                    
                    # اگر selector_hint داریم، از آن استفاده کن
                    if not dropdown_trigger and selector_hint:
                        try:
                            elements = page.locator(selector_hint)
                            count = await elements.count()
                            if count > 0:
                                dropdown_trigger = elements.last
                        except:
                            pass
                    
                    if dropdown_trigger:
                        # کلیک روی dropdown trigger
                        logger.info("Clicking dropdown trigger...")
                        await dropdown_trigger.click(force=True)
                        await asyncio.sleep(1)  # صبر برای باز شدن dropdown
                        
                        # روش 2: استفاده از keyboard navigation (مثل playwright_service)
                        # این روش برای React Select بهتر کار می‌کند
                        target_option = input_value or element_text or element_description
                        
                        # اگر target_option "Admin" یا "ادمین" است، از keyboard navigation استفاده کن
                        if target_option and ("admin" in target_option.lower() or "ادمین" in target_option):
                            logger.info("Using keyboard navigation for role selection...")
                            
                            # ArrowDown دو بار برای رفتن به گزینه دوم (Admin)
                            await page.keyboard.press("ArrowDown")
                            await asyncio.sleep(0.2)
                            await page.keyboard.press("ArrowDown")
                            await asyncio.sleep(0.2)
                            
                            # Enter برای انتخاب
                            await page.keyboard.press("Enter")
                            await asyncio.sleep(0.5)
                            
                            select_found = True
                            logger.info("✅ Selected role using keyboard navigation (Down -> Down -> Enter)")
                        else:
                            # روش 3: جستجو برای option و کلیک
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
                            
                            # اگر option پیدا نشد، از keyboard navigation استفاده کن
                            if not option_found:
                                logger.info("Option not found, using keyboard navigation...")
                                await page.keyboard.press("ArrowDown")
                                await asyncio.sleep(0.2)
                                await page.keyboard.press("ArrowDown")
                                await asyncio.sleep(0.2)
                                await page.keyboard.press("Enter")
                                await asyncio.sleep(0.5)
                                select_found = True
                                logger.info("✅ Selected using keyboard navigation fallback")
                    else:
                        # روش 4: استفاده از select_option برای select معمولی HTML
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
                
                except Exception as e:
                    logger.error(f"❌ Select action failed: {e}", exc_info=True)
                    result["error"] = f"Select failed: {str(e)}"
                
                if select_found:
                    await asyncio.sleep(1)
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
                    # جستجو بر اساس نوع input
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
                                input_element = elements.last
                                if await input_element.is_visible():
                                    # بررسی اینکه آیا این input قبلاً پر نشده
                                    current_value = await input_element.input_value()
                                    if not current_value or current_value == input_value:
                                        await input_element.fill(input_value)
                                        input_found = True
                                        logger.info(f"✅ Filled using selector: {selector}")
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
                # پیدا کردن دکمه submit (با تاکید بر دکمه "ایجاد ادمین")
                submit_selectors = [
                    # دکمه‌های خاص برای ایجاد ادمین (اولویت اول)
                    'button:has-text("ایجاد ادمین")',
                    'button:has-text("Create Admin")',
                    'button:has-text("ایجاد ادمین جدید")',
                    'button:has-text("Add New Admin")',
                    'text=/ایجاد ادمین/i',
                    'text=/Create Admin/i',
                    # دکمه‌های عمومی submit
                    'button[type="submit"]',
                    'button:has-text("Submit")',
                    'button:has-text("ارسال")',
                    'button:has-text("ثبت")',
                    'button:has-text("ایجاد")',
                    'button:has-text("Create")',
                    'button:has-text("ساخت")',
                    'input[type="submit"]'
                ]
                
                submit_found = False
                submit_button = None
                
                # جستجو با تمام selectorها
                for selector in submit_selectors:
                    try:
                        elements = page.locator(selector)
                        count = await elements.count()
                        logger.debug(f"Found {count} submit elements with selector: {selector}")
                        
                        if count > 0:
                            # استفاده از آخرین دکمه (معمولاً دکمه فرم جدید)
                            submit_button = elements.last
                            
                            if await submit_button.is_visible():
                                # گرفتن متن دکمه برای لاگ
                                try:
                                    button_text = await submit_button.text_content()
                                    logger.info(f"✅ Found submit button: '{button_text}' with selector: {selector}")
                                except:
                                    logger.info(f"✅ Found submit button with selector: {selector}")
                                
                                # scroll into view
                                await submit_button.scroll_into_view_if_needed()
                                await asyncio.sleep(0.3)
                                
                                # کلیک
                                await submit_button.click()
                                submit_found = True
                                logger.info(f"✅ Clicked submit button")
                                break
                            else:
                                # اگر visible نیست، امتحان force click
                                try:
                                    await submit_button.click(force=True)
                                    submit_found = True
                                    logger.info(f"✅ Clicked submit button (force)")
                                    break
                                except:
                                    continue
                    except Exception as e:
                        logger.debug(f"Submit selector failed: {selector} - {e}")
                        continue
                
                # اگر پیدا نشد، جستجوی پیشرفته در تمام دکمه‌ها
                if not submit_found:
                    logger.warning("⚠️ Standard submit selectors failed, searching all buttons...")
                    
                    try:
                        all_buttons = page.locator('button')
                        button_count = await all_buttons.count()
                        logger.debug(f"Found {button_count} total buttons on page")
                        
                        # جستجو برای دکمه‌هایی که متنشان شامل کلمات کلیدی است
                        keywords = ["ایجاد ادمین", "Create Admin", "ایجاد", "Create", "Submit", "ارسال", "ثبت"]
                        
                        for i in range(button_count):
                            try:
                                button = all_buttons.nth(i)
                                if await button.is_visible():
                                    button_text = await button.text_content()
                                    button_text_clean = (button_text or "").strip()
                                    
                                    # بررسی اینکه آیا این دکمه submit است
                                    if any(keyword in button_text_clean for keyword in keywords):
                                        # بررسی اینکه disabled نیست
                                        is_disabled = await button.is_disabled()
                                        if not is_disabled:
                                            logger.info(f"✅ Found submit button by text search: '{button_text_clean}'")
                                            await button.scroll_into_view_if_needed()
                                            await asyncio.sleep(0.3)
                                            await button.click()
                                            submit_found = True
                                            break
                            except Exception as e:
                                logger.debug(f"Button {i} check failed: {e}")
                                continue
                    except Exception as e:
                        logger.error(f"❌ Advanced button search failed: {e}")
                
                if submit_found:
                    # صبر برای ارسال فرم
                    await page.wait_for_load_state('networkidle')
                    await asyncio.sleep(3)  # صبر بیشتر برای اطمینان از ثبت
                    result["success"] = True
                    logger.info("✅ Form submitted successfully")
                else:
                    result["error"] = "Could not find submit button"
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
        
        steps_taken = []
        screenshots = []
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=False)
                page = await browser.new_page()
                
                # Task description برای AI
                task_description = f"""
Create a new admin user with the following details:
- Email: {admin_email}
- Password: {admin_password}
- Full Name: {admin_full_name}
- Role: {admin_role}

You need to:
1. Navigate to {url}
2. Login with email: {login_email} and password: {login_password}
3. Navigate to admin management section
4. Click "Add New Admin" button
5. Fill in the form with the admin details above
6. Select the role: {admin_role}
7. Submit the form
8. Verify success
"""
                
                logger.info(f"🤖 Starting Agentic Admin Creation")
                logger.info(f"📋 Task: {task_description[:200]}...")
                
                iteration = 0
                task_complete = False
                
                while iteration < self.max_iterations and not task_complete:
                    iteration += 1
                    logger.info(f"\n🔄 Iteration {iteration}/{self.max_iterations}")
                    
                    # تحلیل صفحه با AI
                    ai_decision = await self._analyze_page_with_ai(
                        page=page,
                        task_description=task_description,
                        previous_actions=steps_taken
                    )
                    
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
                
                # گرفتن screenshot نهایی
                final_screenshot = await self._take_screenshot(page, "final")
                if final_screenshot:
                    screenshots.append(final_screenshot)
                
                await browser.close()
                
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
                
        except Exception as e:
            logger.error(f"❌ Agentic Playwright task failed: {e}", exc_info=True)
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

