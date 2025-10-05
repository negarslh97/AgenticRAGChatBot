"""
تحلیلگر سوالات برای تشخیص پیچیدگی
"""
from enum import Enum
from typing import Dict, Any
import re


class QueryComplexity(str, Enum):
    """سطوح پیچیدگی سوال"""
    SIMPLE = "simple"      # ساده - یک سوال واضح
    MODERATE = "moderate"  # متوسط - نیاز به کمی جستجو
    COMPLEX = "complex"    # پیچیده - چند بخشی، نیاز به تجزیه


def analyze_query_complexity(query: str) -> Dict[str, Any]:
    """
    تشخیص سطح پیچیدگی سوال
    
    Args:
        query: متن سوال کاربر
        
    Returns:
        Dict شامل complexity و دلیل
    """
    query_lower = query.lower().strip()
    word_count = len(query.split())
    
    # شمارش کلمات کلیدی پیچیدگی
    complexity_indicators = {
        # کلمات پیچیده
        "complex_keywords": [
            "چطور", "چگونه", "چه طور", "نحوه", "روش",
            "مراحل", "قدم", "ابتدا", "سپس", "بعد",
            "و همچنین", "علاوه بر", "در کنار"
        ],
        # سوالات چندبخشی
        "multi_part": ["و", "همچنین", "ضمناً", "علاوه"],
        # درخواست جزئیات
        "detail_requests": [
            "دقیق", "کامل", "با جزئیات", "تمام",
            "همه", "تمامی", "کلیه"
        ]
    }
    
    # امتیازدهی
    score = 0
    reasons = []
    
    # 1. طول سوال
    if word_count <= 5:
        score += 0
        reasons.append("سوال کوتاه")
    elif word_count <= 15:
        score += 1
        reasons.append("سوال متوسط")
    else:
        score += 2
        reasons.append("سوال طولانی")
    
    # 2. کلمات کلیدی پیچیده
    complex_count = sum(1 for keyword in complexity_indicators["complex_keywords"] 
                       if keyword in query_lower)
    if complex_count > 0:
        score += complex_count
        reasons.append(f"{complex_count} کلمه پیچیده")
    
    # 3. چندبخشی بودن
    multi_part_count = sum(1 for keyword in complexity_indicators["multi_part"] 
                          if keyword in query_lower)
    if multi_part_count >= 2:
        score += 2
        reasons.append("سوال چندبخشی")
    
    # 4. درخواست جزئیات
    detail_count = sum(1 for keyword in complexity_indicators["detail_requests"] 
                      if keyword in query_lower)
    if detail_count > 0:
        score += 1
        reasons.append("درخواست جزئیات")
    
    # 5. علامت سوال متعدد
    question_marks = query.count('؟') + query.count('?')
    if question_marks > 1:
        score += 1
        reasons.append("چند سوال")
    
    # تعیین complexity براساس امتیاز
    if score <= 2:
        complexity = QueryComplexity.SIMPLE
        complexity_fa = "ساده"
    elif score <= 5:
        complexity = QueryComplexity.MODERATE
        complexity_fa = "متوسط"
    else:
        complexity = QueryComplexity.COMPLEX
        complexity_fa = "پیچیده"
    
    return {
        "complexity": complexity.value,
        "complexity_fa": complexity_fa,
        "score": score,
        "word_count": word_count,
        "reasons": reasons,
        "description": f"سوال {complexity_fa} با امتیاز {score}"
    }


def generate_conversation_title(first_message: str, max_length: int = 50) -> str:
    """
    تولید عنوان خودکار برای مکالمه از اولین پیام
    
    Args:
        first_message: اولین پیام کاربر
        max_length: حداکثر طول عنوان
        
    Returns:
        عنوان مناسب
    """
    # پاکسازی
    title = first_message.strip()
    
    # حذف علامت‌های سوال
    title = title.replace('؟', '').replace('?', '')
    
    # حذف کلمات اضافی
    remove_words = ['لطفا', 'لطفاً', 'ممنون', 'متشکرم', 'سلام', 'درود']
    for word in remove_words:
        title = title.replace(word, '')
    
    # حذف فضاهای اضافی
    title = ' '.join(title.split())
    
    # محدود کردن طول
    if len(title) > max_length:
        title = title[:max_length] + '...'
    
    # اگر خیلی کوتاه شد، از پیام اصلی استفاده کن
    if len(title) < 5:
        title = first_message[:max_length] + '...' if len(first_message) > max_length else first_message
    
    return title.strip()
