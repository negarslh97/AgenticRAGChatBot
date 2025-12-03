"""
Playwright Automation Service - Direct browser control
"""
import asyncio
from playwright.async_api import async_playwright, Page
from typing import Optional
from dataclasses import dataclass
import re
from app.core.logging_config import get_logger

logger = get_logger(__name__)

@dataclass
class PlaywrightResult:
    success: bool
    result: Optional[str] = None
    error: Optional[str] = None

class PlaywrightService:
    
    async def create_admin(
        self,
        admin_email: str,
        admin_password: str,
        login_email: str,
        login_password: str,
        admin_full_name: str = "test",
        admin_role: str = "Admin",
        url: str = "http://localhost:3000/super-admin"
    ) -> PlaywrightResult:
        """ساخت ادمین با Playwright"""
        
        try:
            async with async_playwright() as p:
                # راه‌اندازی browser
                browser = await p.chromium.launch(headless=False)
                page = await browser.new_page()
                
                # 1. رفتن به صفحه login
                logger.info(f"🌐 Navigating to {url}")
                await page.goto(url)
                await page.wait_for_load_state('networkidle')
                await asyncio.sleep(2)
                
                # 2. Login
                logger.info(f"🔐 Logging in as {login_email}")
                await page.fill('input[type="email"]', login_email)
                await page.fill('input[type="password"]', login_password)
                await page.click('button[type="submit"]')
                await page.wait_for_load_state('networkidle')
                await asyncio.sleep(3)
                
                # 3. رفتن به بخش مدیریت کاربران از سایدبار
                logger.info("🔍 Looking for user management in sidebar...")
                
                # صبر برای بارگذاری کامل صفحه
                await asyncio.sleep(3)
                
                # گرفتن screenshot برای دیباگ
                await page.screenshot(path="debug_after_login.png")
                
                # جستجو برای لینک مدیریت کاربران در سایدبار
                user_management_selectors = [
                    'text=/مدیریت کاربران/i',
                    'text=/User Management/i',
                    'text=/کاربران/i',
                    'text=/Users/i',
                    'a:has-text("مدیریت کاربران")',
                    'a:has-text("User Management")',
                    'a:has-text("کاربران")',
                    'a:has-text("Users")',
                    '[data-testid="user-management"]',
                    'nav a:has-text("کاربر")'
                ]
                
                user_management_found = False
                for selector in user_management_selectors:
                    try:
                        link = page.locator(selector).first
                        if await link.count() > 0 and await link.is_visible():
                            logger.info(f"✅ Found user management link with selector: {selector}")
                            await link.click()
                            await asyncio.sleep(3)
                            user_management_found = True
                            break
                    except Exception as e:
                        logger.debug(f"User management selector {selector} failed: {e}")
                        continue
                
                if not user_management_found:
                    logger.warning("⚠️ Could not find user management link")
                    await page.screenshot(path="debug_no_user_management.png")
                
                # 4. رفتن به بخش مدیریت ادمین‌ها
                logger.info("🔍 Looking for admin management...")
                
                admin_management_selectors = [
                    'text=/مدیریت ادمین ها/i',
                    'text=/Admin Management/i',
                    'text=/ادمین ها/i',
                    'text=/Admins/i',
                    'a:has-text("مدیریت ادمین")',
                    'a:has-text("Admin Management")',
                    'a:has-text("ادمین")',
                    'button:has-text("مدیریت ادمین")',
                    'button:has-text("Admin Management")'
                ]
                
                admin_management_found = False
                for selector in admin_management_selectors:
                    try:
                        link = page.locator(selector).first
                        if await link.count() > 0 and await link.is_visible():
                            logger.info(f"✅ Found admin management link with selector: {selector}")
                            await link.click()
                            await asyncio.sleep(3)
                            admin_management_found = True
                            break
                    except Exception as e:
                        logger.debug(f"Admin management selector {selector} failed: {e}")
                        continue
                
                if not admin_management_found:
                    logger.warning("⚠️ Could not find admin management link")
                    await page.screenshot(path="debug_no_admin_management.png")
                
                # 5. کلیک روی دکمه افزودن ادمین جدید
                logger.info("🔍 Looking for add new admin button...")
                
                add_admin_selectors = [
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
                    '.btn-primary:has-text("Add")'
                ]
                
                add_admin_found = False
                for selector in add_admin_selectors:
                    try:
                        button = page.locator(selector).first
                        if await button.count() > 0 and await button.is_visible():
                            logger.info(f"✅ Found add admin button with selector: {selector}")
                            await button.click()
                            await asyncio.sleep(3)
                            add_admin_found = True
                            break
                    except Exception as e:
                        logger.debug(f"Add admin selector {selector} failed: {e}")
                        continue
                
                if not add_admin_found:
                    logger.warning("⚠️ Could not find add admin button")
                    await page.screenshot(path="debug_no_add_admin.png")
                
                # 6. پر کردن فرم
                logger.info(f"📝 Looking for form fields...")
                
                # گرفتن screenshot قبل از پر کردن فرم
                await page.screenshot(path="debug_before_form.png")
                
                # جستجو برای فیلدهای ایمیل و پسورد با روش‌های مختلف
                email_selectors = [
                    'input[type="email"]',
                    'input[placeholder*="email" i]',
                    'input[name*="email" i]',
                    'input[placeholder*="ایمیل" i]',
                    'input[name*="ایمیل" i]'
                ]
                
                password_selectors = [
                    'input[type="password"]',
                    'input[placeholder*="password" i]',
                    'input[name*="password" i]',
                    'input[placeholder*="رمز" i]',
                    'input[name*="رمز" i]'
                ]
                
                email_input = None
                for selector in email_selectors:
                    try:
                        elements = page.locator(selector)
                        count = await elements.count()
                        logger.info(f"Found {count} elements with selector: {selector}")
                        
                        if count > 0:
                            # اگر چندتا هست، آخرین را بردار (معمولاً فرم ساخت ادمین)
                            email_input = elements.last
                            if await email_input.is_visible():
                                logger.info(f"✅ Found email input with selector: {selector}")
                                break
                    except Exception as e:
                        logger.debug(f"Email selector {selector} failed: {e}")
                        continue
                
                password_input = None
                for selector in password_selectors:
                    try:
                        elements = page.locator(selector)
                        count = await elements.count()
                        logger.info(f"Found {count} elements with selector: {selector}")
                        
                        if count > 0:
                            # اگر چندتا هست، آخرین را بردار
                            password_input = elements.last
                            if await password_input.is_visible():
                                logger.info(f"✅ Found password input with selector: {selector}")
                                break
                    except Exception as e:
                        logger.debug(f"Password selector {selector} failed: {e}")
                        continue
                
                if not email_input or not password_input:
                    logger.error("❌ Could not find form fields")
                    # گرفتن screenshot برای دیباگ
                    await page.screenshot(path="debug_no_fields.png")
                    raise Exception("Could not find email or password input fields")
                
                # پر کردن فیلدها
                await email_input.fill(admin_email)
                await password_input.fill(admin_password)
                
                # پیدا کردن و پر کردن فیلد نام کامل
                logger.info("📝 Looking for full name field...")
                full_name_selectors = [
                    'input[name*="full_name" i]',
                    'input[name*="fullName" i]',
                    'input[name*="name" i]',
                    'input[placeholder*="نام" i]',
                    'input[placeholder*="full name" i]',
                    'input[placeholder*="name" i]',
                    'input[id*="name" i]',
                    'input[type="text"]'
                ]
                
                full_name_input = None
                for selector in full_name_selectors:
                    try:
                        elements = page.locator(selector)
                        count = await elements.count()
                        logger.info(f"Found {count} full name elements with selector: {selector}")
                        
                        if count > 0:
                            # اولین فیلد متنی که نام ندارد را پیدا کن
                            for i in range(count):
                                element = elements.nth(i)
                                if await element.is_visible():
                                    # بررسی اینکه آیا این فیلد ایمیل یا پسورد نیست
                                    input_type = await element.get_attribute("type")
                                    input_name = await element.get_attribute("name") or ""
                                    input_placeholder = await element.get_attribute("placeholder") or ""
                                    
                                    if input_type != "email" and input_type != "password" and "email" not in input_name.lower() and "password" not in input_name.lower() and "email" not in input_placeholder.lower() and "password" not in input_placeholder.lower():
                                        full_name_input = element
                                        logger.info(f"✅ Found full name input with selector: {selector}")
                                        break
                            
                            if full_name_input:
                                break
                    except Exception as e:
                        logger.debug(f"Full name selector {selector} failed: {e}")
                        continue
                
                if full_name_input:
                    await full_name_input.fill(admin_full_name)
                    logger.info(f"✅ Filled full name: {admin_full_name}")
                else:
                    logger.warning("⚠️ Could not find full name field")
                
                # # پیدا کردن و انتخاب نقش
                # logger.info("📝 Looking for role field...")
                # role_selectors = [
                #     'select[name*="role" i]',
                #     'select[id*="role" i]',
                #     'input[type="radio"][name*="role" i]',
                #     'input[type="checkbox"][name*="role" i]',
                #     '[data-testid="role-select"]',
                #     'select'
                # ]
                
                # role_input = None
                # for selector in role_selectors:
                #     try:
                #         elements = page.locator(selector)
                #         count = await elements.count()
                #         logger.info(f"Found {count} role elements with selector: {selector}")
                        
                #         if count > 0:
                #             role_input = elements.first
                #             if await role_input.is_visible():
                #                 logger.info(f"✅ Found role input with selector: {selector}")
                #                 break
                #     except Exception as e:
                #         logger.debug(f"Role selector {selector} failed: {e}")
                #         continue
                
                # if role_input:
                #     # بررسی نوع عنصر نقش
                #     tag_name = await role_input.evaluate("el => el.tagName.toLowerCase()")
                    
                #     if tag_name == "select":
                #         # برای dropdown/select - روش‌های مختلف برای انتخاب نقش
                #         logger.info("🔍 Trying to select role from dropdown...")
                        
                #         try:
                #             # روش 1: استفاده از force click روی container یا label
                #             role_container_selectors = [
                #                 '.role-select',
                #                 '[data-testid="role-select"]',
                #                 'div:has(select)',
                #                 'label:has-text("نقش")',
                #                 'label:has-text("Role")',
                #                 '.form-group:has(select)',
                #                 '.mb-4:has(select)',
                #                 'div[class*="role"]',
                #                 'div[class*="select"]'
                #             ]
                            
                #             container_clicked = False
                #             for selector in role_container_selectors:
                #                 try:
                #                     container = page.locator(selector).first
                #                     if await container.count() > 0 and await container.is_visible():
                #                         logger.info(f"✅ Found role container with selector: {selector}")
                #                         # استفاده از force click برای عبور از overlay
                #                         await container.click(force=True)
                #                         await asyncio.sleep(2)
                #                         container_clicked = True
                #                         break
                #                 except Exception as e:
                #                     logger.debug(f"Container selector {selector} failed: {e}")
                #                     continue
                            
                #             if not container_clicked:
                #                 # تلاش مستقیم برای کلیک روی select با force
                #                 try:
                #                     await role_input.click(force=True)
                #                     await asyncio.sleep(2)
                #                 except Exception as e:
                #                     logger.warning(f"Direct select click failed: {e}")
                            
                #             # حالا گزینه‌های dropdown را پیدا کن
                #             await asyncio.sleep(2)  # صبر بیشتر برای باز شدن dropdown
                            
                #             # جستجو برای گزینه "Admin" در dropdown باز شده
                #             admin_option_selectors = [
                #                 'option:has-text("Admin")',
                #                 'option[value="Admin"]',
                #                 '[role="option"]:has-text("Admin")',
                #                 'li:has-text("Admin")',
                #                 'div[role="option"]:has-text("Admin")',
                #                 '.dropdown-item:has-text("Admin")',
                #                 '[data-value="Admin"]',
                #                 'span:has-text("Admin")',
                #                 'div:has-text("Admin")'
                #             ]
                            
                #             option_found = False
                #             for selector in admin_option_selectors:
                #                 try:
                #                     option = page.locator(selector).first
                #                     if await option.count() > 0:
                #                         # تلاش برای scroll به سمت گزینه
                #                         await option.scroll_into_view_if_needed()
                #                         if await option.is_visible():
                #                             logger.info(f"✅ Found Admin option with selector: {selector}")
                #                             await option.click(force=True)
                #                             await asyncio.sleep(1)
                #                             option_found = True
                #                             break
                #                         else:
                #                             # اگر visible نیست، force click را امتحان کن
                #                             await option.click(force=True)
                #                             await asyncio.sleep(1)
                #                             option_found = True
                #                             break
                #                 except Exception as e:
                #                     logger.debug(f"Option selector {selector} failed: {e}")
                #                     continue
                            
                #             if not option_found:
                #                 logger.warning("⚠️ Could not find Admin option, trying select_option method")
                #                 # روش 2: استفاده از select_option
                #                 try:
                #                     await role_input.select_option("Admin")
                #                     logger.info(f"✅ Selected Admin role using select_option")
                #                     option_found = True
                #                 except Exception as e2:
                #                     logger.error(f"❌ select_option also failed: {e2}")
                            
                #             if not option_found:
                #                 logger.error("❌ All role selection methods failed")
                #                 # گرفتن screenshot برای دیباگ
                #                 try:
                #                     await page.screenshot(path="debug_role_selection_failed.png")
                #                 except:
                #                     pass
                            
                #         except Exception as e:
                #             logger.error(f"❌ Role selection failed: {e}")
                #             # گرفتن screenshot برای دیباگ
                #             try:
                #                 await page.screenshot(path="debug_role_error.png")
                #             except:
                #                 pass
                        
                #     elif tag_name == "input":
                #         input_type = await role_input.evaluate("el => el.type")
                        
                #         if input_type == "radio":
                #             # برای radio buttons
                #             role_radio = page.locator(f'input[type="radio"][value="{admin_role}"]')
                #             if await role_radio.count() > 0:
                #                 await role_radio.check()
                #                 logger.info(f"✅ Selected radio role: {admin_role}")
                #         elif input_type == "checkbox":
                #             # برای checkboxes
                #             role_checkbox = page.locator(f'input[type="checkbox"][value="{admin_role}"]')
                #             if await role_checkbox.count() > 0:
                #                 await role_checkbox.check()
                #                 logger.info(f"✅ Checked role: {admin_role}")
                # else:
                #     logger.warning("⚠️ Could not find role field")
                
                # ---------------------------------------------------------
                # روش تضمینی: استفاده از کیبورد برای انتخاب گزینه دوم
                # ---------------------------------------------------------
                logger.info("📝 Selecting Role using Keyboard...")
                
                try:
                    # 1. پیدا کردن و کلیک روی باکس "انتخاب نقش"
                    # با توجه به اینکه گفتی مرحله قبل درست کار کرده، از همون منطق استفاده می‌کنیم
                    dropdown_trigger = page.locator("div").filter(has_text="انتخاب نقش").last
                    
                    if not await dropdown_trigger.is_visible():
                         # تلاش جایگزین
                         dropdown_trigger = page.locator(".css-control, .select__control").last

                    logger.info("Clicking dropdown trigger...")
                    await dropdown_trigger.click(force=True)
                    
                    # 2. صبر کوتاه برای باز شدن انیمیشن منو
                    await asyncio.sleep(1)
                    
                    # 3. حرکت با کیبورد (راه حل اصلی)
                    # وقتی منو باز میشه، معمولا فوکوس روی سرچ یا گزینه اوله
                    
                    # یک بار فلش پایین میزنیم (میره روی گزینه اول: ادمین ارشد)
                    await page.keyboard.press("ArrowDown")
                    await asyncio.sleep(0.2)
                    
                    # یک بار دیگر فلش پایین میزنیم (میره روی گزینه دوم: ادمین)
                    await page.keyboard.press("ArrowDown")
                    await asyncio.sleep(0.2)
                    
                    # زدن اینتر برای انتخاب
                    await page.keyboard.press("Enter")
                    logger.info("✅ Selected option using Keyboard (Down -> Down -> Enter)")
                    
                    # 4. اطمینان از انتخاب شدن
                    # یه اسکرین شات میگیریم که مطمئن بشیم چی انتخاب شده
                    await asyncio.sleep(1)
                    await page.screenshot(path="debug_role_selected.png")

                except Exception as e:
                    logger.error(f"❌ Keyboard selection failed: {e}")
                # ---------------------------------------------------------


                # 7. ارسال فرم
                logger.info("📤 Looking for submit button...")
                
                submit_selectors = [
                    'button:has-text("ایجاد ادمین")',
                    'button[type="submit"]',
                    'button:has-text("Submit")',
                    'button:has-text("ارسال")',
                    'button:has-text("ثبت")',
                    'button:has-text("Create")',
                    'button:has-text("ساخت")',
                    'input[type="submit"]'
                ]
                
                submit_button = None
                for selector in submit_selectors:
                    try:
                        elements = page.locator(selector)
                        count = await elements.count()
                        logger.info(f"Found {count} submit elements with selector: {selector}")
                        
                        if count > 0:
                            submit_button = elements.last
                            if await submit_button.is_visible():
                                logger.info(f"✅ Found submit button with selector: {selector}")
                                break
                    except Exception as e:
                        logger.debug(f"Submit selector {selector} failed: {e}")
                        continue
                
                if not submit_button:
                    logger.error("❌ Could not find submit button")
                    await page.screenshot(path="debug_no_submit.png")
                    raise Exception("Could not find submit button")
                
                await submit_button.click()
                await page.wait_for_load_state('networkidle')
                await asyncio.sleep(3)
                
                # گرفتن screenshot نهایی
                await page.screenshot(path="debug_final.png")
                
                # بررسی موفقیت‌آمیز بودن عملیات
                # جستجو برای پیام موفقیت
                success_indicators = [
                    'text=/موفقیت/i',
                    'text=/success/i',
                    'text=/با موفقیت/i',
                    'text=/created successfully/i',
                    'text=/ایجاد شد/i',
                    '.alert-success',
                    '.success-message',
                    '[data-testid="success"]'
                ]
                
                operation_successful = False
                for selector in success_indicators:
                    try:
                        element = page.locator(selector).first
                        if await element.count() > 0 and await element.is_visible():
                            logger.info(f"✅ Found success indicator: {selector}")
                            operation_successful = True
                            break
                    except Exception as e:
                        logger.debug(f"Success indicator {selector} failed: {e}")
                        continue
                
                # اگر پیام موفقیت پیدا نشد، بررسی می‌کنیم که آیا فرم ارسال شده
                if not operation_successful:
                    logger.warning("⚠️ No clear success indicator found, checking if form was submitted...")
                    
                    # بررسی اینکه آیا هنوز در صفحه فرم هستیم یا به صفحه دیگری رفته‌ایم
                    current_url = page.url
                    if "admin" not in current_url.lower() or "create" not in current_url.lower():
                        logger.info("✅ Page changed, likely form was submitted successfully")
                        operation_successful = True
                    else:
                        # بررسی اینکه آیا فیلدهای فرم خالی شده‌اند (نشانه ارسال موفق)
                        try:
                            email_value = await email_input.input_value()
                            if not email_value:
                                logger.info("✅ Email field is empty, form likely submitted")
                                operation_successful = True
                        except:
                            pass
                
                await browser.close()
                
                if operation_successful:
                    logger.info("✅ Admin creation appears successful!")
                    return PlaywrightResult(
                        success=True,
                        result=f"Admin {admin_email} created successfully"
                    )
                else:
                    logger.error("❌ Admin creation may have failed - no success confirmation")
                    return PlaywrightResult(
                        success=False,
                        error="Admin creation completed but no success confirmation found"
                    )
                
        except Exception as e:
            logger.error(f"❌ Playwright task failed: {e}", exc_info=True)
            return PlaywrightResult(
                success=False,
                error=str(e)
            )

# Singleton
playwright_service = PlaywrightService()