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
        prompts = [f.stem for f in PROMPTS_DIR.glob("*.txt")]
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

