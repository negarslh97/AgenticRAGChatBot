"""
Prompt Management Module
========================

این ماژول برای مدیریت متمرکز prompts استفاده می‌شود.
"""

from pathlib import Path
from typing import Dict
import logging

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent


class PromptManager:
    """
    مدیر prompts - برای loading و caching template های prompt
    
    مزایا:
    - جداسازی prompts از logic کد
    - امکان version control آسان برای prompts
    - تست A/B راحت‌تر
    - نگهداری و ویرایش ساده‌تر
    """
    
    def __init__(self):
        self._cache: Dict[str, str] = {}
        logger.info(f"📋 PromptManager initialized with prompts directory: {PROMPTS_DIR}")
    
    def get_prompt(self, prompt_name: str, use_cache: bool = True) -> str:
        """
        دریافت یک prompt template
        
        Args:
            prompt_name: نام فایل prompt (بدون پسوند)
            use_cache: استفاده از cache یا خواندن مجدد از فایل
        
        Returns:
            محتوای prompt template
        """
        # بررسی cache
        if use_cache and prompt_name in self._cache:
            logger.debug(f"♻️ Using cached prompt: {prompt_name}")
            return self._cache[prompt_name]
        
        # خواندن از فایل
        prompt_path = PROMPTS_DIR / f"{prompt_name}.txt"
        
        # اگر فایل در مسیر اصلی پیدا نشد، در زیردایرکتوری‌ها جستجو کن
        if not prompt_path.exists():
            # بررسی آیا prompt_name شامل مسیر نسبی است (مثلاً "response_guides/specific")
            if "/" in prompt_name:
                subdir_name, file_name = prompt_name.split("/", 1)
                prompt_path = PROMPTS_DIR / subdir_name / f"{file_name}.txt"
            else:
                logger.error(f"❌ Prompt file not found: {prompt_path}")
                raise FileNotFoundError(f"Prompt template not found: {prompt_name}")
        
        if not prompt_path.exists():
            logger.error(f"❌ Prompt file not found: {prompt_path}")
            raise FileNotFoundError(f"Prompt template not found: {prompt_name}")
        
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # ذخیره در cache
            self._cache[prompt_name] = content
            logger.info(f"✅ Loaded prompt template: {prompt_name}")
            
            return content
            
        except Exception as e:
            logger.error(f"❌ Error loading prompt {prompt_name}: {e}")
            raise
    
    def reload_prompt(self, prompt_name: str) -> str:
        """
        بارگذاری مجدد یک prompt (بدون استفاده از cache)
        
        مفید برای development و hot-reload
        """
        logger.info(f"🔄 Reloading prompt: {prompt_name}")
        return self.get_prompt(prompt_name, use_cache=False)
    
    def clear_cache(self):
        """پاک کردن تمام cache"""
        self._cache.clear()
        logger.info("🗑️ Prompt cache cleared")
    
    def list_prompts(self):
        """لیست تمام prompts موجود"""
        prompts = []
        
        # پیدا کردن فایل‌های txt در دایرکتوری اصلی
        for f in PROMPTS_DIR.glob("*.txt"):
            prompts.append(f.stem)
        
        # پیدا کردن فایل‌های txt در زیردایرکتوری‌ها
        for subdir in PROMPTS_DIR.iterdir():
            if subdir.is_dir():
                for f in subdir.glob("*.txt"):
                    # ذخیره نام کامل با مسیر نسبی
                    prompts.append(f"{subdir.name}/{f.stem}")
        
        logger.info(f"📋 Available prompts: {prompts}")
        return prompts


# Global instance
prompt_manager = PromptManager()


# Convenience functions
def get_prompt(prompt_name: str) -> str:
    """دریافت یک prompt template"""
    return prompt_manager.get_prompt(prompt_name)


def reload_prompt(prompt_name: str) -> str:
    """بارگذاری مجدد یک prompt"""
    return prompt_manager.reload_prompt(prompt_name)

