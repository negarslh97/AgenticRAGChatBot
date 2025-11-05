"""
Prompt Management Service
========================

این سرویس مسئولیت مدیریت پرامپت‌ها را بر عهده دارد:
- Loading prompt templates from files
- Prompt template validation
- Prompt parameter substitution
- Prompt caching and optimization
- Support for hierarchical prompt structure

Features:
- Support for prompt files in subdirectories
- Template variable substitution
- Prompt validation and error handling
- Caching for frequently used prompts
- Support for multiple prompt formats
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from jinja2 import Template, TemplateError

from app.core.logging_config import get_logger

logger = get_logger(__name__)


class PromptService:
    """
    Service for managing AI prompt templates
    
    این سرویس مسئولیت‌های زیر را بر عهده دارد:
    - بارگذاری پرامپت‌ها از فایل‌ها
    - اعتبارسنجی پرامپت‌ها
    - جایگزینی پارامترها در پرامپت‌ها
    - کش کردن پرامپت‌های استفاده شده
    - پشتیبانی از ساختار سلسله مراتبی پرامپت‌ها
    """
    
    def __init__(self, prompts_dir: Optional[Path] = None):
        if prompts_dir is None:
            # استفاده از مسیر پیش‌فرض
            from app.core.config import settings
            self.prompts_dir = Path(settings.prompts_dir_loaded)
        else:
            self.prompts_dir = prompts_dir
        
        self._prompt_cache: Dict[str, str] = {}
        self._template_cache: Dict[str, Template] = {}
        
        logger.debug(f"📝 PromptService initialized with directory: {self.prompts_dir}")
        
        # بررسی وجود دایرکتوری پرامپت‌ها
        if not self.prompts_dir.exists():
            logger.debug(f"⚠️ Prompts directory does not exist: {self.prompts_dir}")
            self.prompts_dir.mkdir(parents=True, exist_ok=True)
            logger.debug(f"📁 Created prompts directory: {self.prompts_dir}")
    
    def list_prompts(self) -> list[str]:
        """
        لیست تمام prompts موجود
        
        Returns:
            list[str]: لیست نام پرامپت‌ها
        """
        prompts = []
        
        # پیدا کردن فایل‌های txt در دایرکتوری اصلی
        for f in self.prompts_dir.glob("*.txt"):
            prompts.append(f.stem)
        
        # پیدا کردن فایل‌های txt در زیردایرکتوری‌ها
        for subdir in self.prompts_dir.iterdir():
            if subdir.is_dir():
                for f in subdir.glob("*.txt"):
                    # ذخیره نام کامل با مسیر نسبی
                    prompts.append(f"{subdir.name}/{f.stem}")
        
        logger.debug(f"📋 Available prompts: {prompts}")
        return prompts
    
    def get_prompt(self, prompt_name: str) -> str:
        """
        دریافت پرامپت با نام از فایل
        
        Args:
            prompt_name: نام پرامپت (ممکن است شامل مسیر نسبی باشد)
        
        Returns:
            str: محتوای پرامپت
        
        Raises:
            FileNotFoundError: اگر پرامپت پیدا نشود
            TemplateError: اگر پرامپت معتبر نباشد
        """
        # بررسی کش
        if prompt_name in self._prompt_cache:
            logger.debug(f"🎯 Using cached prompt: {prompt_name}")
            return self._prompt_cache[prompt_name]
        
        # خواندن از فایل
        prompt_path = self.prompts_dir / f"{prompt_name}.txt"
        
        # اگر فایل در مسیر اصلی پیدا نشد، در زیردایرکتوری‌ها جستجو کن
        if not prompt_path.exists():
            # بررسی آیا prompt_name شامل مسیر نسبی است (مثلاً "response_guides/specific")
            if "/" in prompt_name:
                subdir_name, file_name = prompt_name.split("/", 1)
                prompt_path = self.prompts_dir / subdir_name / f"{file_name}.txt"
            else:
                logger.debug(f"❌ Prompt file not found: {prompt_path}")
                raise FileNotFoundError(f"Prompt template not found: {prompt_name}")
        
        if not prompt_path.exists():
            logger.debug(f"❌ Prompt file not found: {prompt_path}")
            raise FileNotFoundError(f"Prompt template not found: {prompt_name}")
        
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                prompt_content = f.read()
            
            # اعتبارسنجی پرامپت
            self._validate_prompt(prompt_content, prompt_name)
            
            # کش کردن پرامپت
            self._prompt_cache[prompt_name] = prompt_content
            logger.debug(f"✅ Loaded prompt: {prompt_name} from {prompt_path}")
            
            return prompt_content
            
        except Exception as e:
            logger.debug(f"❌ Error loading prompt {prompt_name}: {e}")
            raise
    
    def render_prompt(self, prompt_name: str, **kwargs) -> str:
        """
        رندر کردن پرامپت با پارامترها
        
        Args:
            prompt_name: نام پرامپت
            **kwargs: پارامترهای جایگزین
        
        Returns:
            str: پرامپت رندر شده
        """
        prompt_content = self.get_prompt(prompt_name)
        
        # استفاده از Jinja2 برای رندر کردن پرامپت
        try:
            template = Template(prompt_content)
            rendered_prompt = template.render(**kwargs)
            return rendered_prompt
        except TemplateError as e:
            logger.debug(f"❌ Error rendering prompt {prompt_name}: {e}")
            # در صورت خطا، پرامپت اصلی را برگردان
            return prompt_content
    
    def _validate_prompt(self, prompt_content: str, prompt_name: str) -> None:
        """
        اعتبارسنجی پرامپت
        
        Args:
            prompt_content: محتوای پرامپت
            prompt_name: نام پرامپت
        
        Raises:
            ValueError: اگر پرامپت معتبر نباشد
        """
        if not prompt_content or not prompt_content.strip():
            raise ValueError(f"Prompt '{prompt_name}' is empty")
        
        # بررسی وجود placeholders ضروری در پرامپت‌های خاص
        if prompt_name in ["rag_response", "simple_rag_response"]:
            required_placeholders = ["{query}", "{context}"]
            for placeholder in required_placeholders:
                if placeholder not in prompt_content:
                    logger.debug(f"⚠️ Recommended placeholder '{placeholder}' not found in prompt '{prompt_name}'")
        
        if prompt_name == "conversational_response":
            if "{query}" not in prompt_content:
                logger.debug(f"⚠️ Required placeholder '{{query}}' not found in prompt '{prompt_name}'")
    
    def clear_cache(self):
        """پاک کردن کش پرامپت‌ها"""
        self._prompt_cache.clear()
        self._template_cache.clear()
        logger.debug("🗑️ Prompt cache cleared")
    
    def get_cache_info(self) -> Dict[str, int]:
        """دریافت اطلاعات کش"""
        return {
            "cached_prompts": len(self._prompt_cache),
            "cached_templates": len(self._template_cache)
        }
    
    def add_prompt_to_cache(self, prompt_name: str, prompt_content: str):
        """
        اضافه کردن پرامپت به کش
        
        Args:
            prompt_name: نام پرامپت
            prompt_content: محتوای پرامپت
        """
        self._prompt_cache[prompt_name] = prompt_content
        logger.debug(f"🎯 Added prompt to cache: {prompt_name}")
    
    def remove_prompt_from_cache(self, prompt_name: str):
        """
        حذف پرامپت از کش
        
        Args:
            prompt_name: نام پرامپت
        """
        if prompt_name in self._prompt_cache:
            del self._prompt_cache[prompt_name]
            logger.debug(f"🗑️ Removed prompt from cache: {prompt_name}")
    
    def create_prompt_file(self, prompt_name: str, content: str, subdirectory: Optional[str] = None):
        """
        ایجاد فایل پرامپت جدید
        
        Args:
            prompt_name: نام پرامپت
            content: محتوای پرامپت
            subdirectory: نام زیردایرکتوری (اختیاری)
        """
        try:
            if subdirectory:
                prompt_dir = self.prompts_dir / subdirectory
                prompt_dir.mkdir(parents=True, exist_ok=True)
                prompt_path = prompt_dir / f"{prompt_name}.txt"
            else:
                prompt_path = self.prompts_dir / f"{prompt_name}.txt"
            
            with open(prompt_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.debug(f"✅ Created prompt file: {prompt_path}")
            
            # پاک کردن کش برای اطمینان از استفاده از نسخه جدید
            self.clear_cache()
            
        except Exception as e:
            logger.debug(f"❌ Error creating prompt file {prompt_name}: {e}")
            raise
    
    def update_prompt_file(self, prompt_name: str, content: str, subdirectory: Optional[str] = None):
        """
        به‌روزرسانی فایل پرامپت موجود
        
        Args:
            prompt_name: نام پرامپت
            content: محتوای جدید پرامپت
            subdirectory: نام زیردایرکتوری (اختیاری)
        """
        try:
            if subdirectory:
                prompt_path = self.prompts_dir / subdirectory / f"{prompt_name}.txt"
            else:
                prompt_path = self.prompts_dir / f"{prompt_name}.txt"
            
            if not prompt_path.exists():
                raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
            
            with open(prompt_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.debug(f"✅ Updated prompt file: {prompt_path}")
            
            # پاک کردن کش برای اطمینان از استفاده از نسخه جدید
            self.clear_cache()
            
        except Exception as e:
            logger.debug(f"❌ Error updating prompt file {prompt_name}: {e}")
            raise
    
    def delete_prompt_file(self, prompt_name: str, subdirectory: Optional[str] = None):
        """
        حذف فایل پرامپت
        
        Args:
            prompt_name: نام پرامپت
            subdirectory: نام زیردایرکتوری (اختیاری)
        """
        try:
            if subdirectory:
                prompt_path = self.prompts_dir / subdirectory / f"{prompt_name}.txt"
            else:
                prompt_path = self.prompts_dir / f"{prompt_name}.txt"
            
            if prompt_path.exists():
                prompt_path.unlink()
                logger.debug(f"🗑️ Deleted prompt file: {prompt_path}")
                
                # پاک کردن کش برای اطمینان
                self.clear_cache()
            else:
                logger.debug(f"⚠️ Prompt file not found for deletion: {prompt_path}")
                
        except Exception as e:
            logger.debug(f"❌ Error deleting prompt file {prompt_name}: {e}")
            raise


# Global instance
prompt_service = PromptService()