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


class QueryType(str, Enum):
    """نوع سوال - برای تعیین طول پاسخ"""
    SPECIFIC = "specific"        # سوال خاص - پاسخ کوتاه و مستقیم
    GENERAL = "general"          # سوال عمومی - پاسخ جامع
    EXPLANATION = "explanation"  # درخواست توضیح - پاسخ متوسط


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


def analyze_query_type(query: str) -> Dict[str, Any]:
    """
    تشخیص نوع سوال برای تعیین طول و سبک پاسخ
    
    Args:
        query: متن سوال کاربر
        
    Returns:
        Dict شامل query_type و توضیحات
    """
    query_lower = query.lower().strip()
    
    # الگوهای سوالات خاص (پاسخ کوتاه)
    specific_patterns = [
        r'\bچرا\b.*؟',  # چرا X است؟
        r'\bدلیل\b',    # دلیل چیست؟
        r'\bآیا\b.*؟',  # آیا X است؟
        r'\bکدام\b',    # کدام گزینه؟
        r'\bچند\b',     # چند تا؟
        r'\bکی\b',      # کی؟
        r'\bکجا\b',     # کجا؟
        r'\bچی\s+هست', # X چی هست؟
        r'\bچیست\b',    # X چیست؟
        r'\bتفاوت\b',   # تفاوت X و Y چیست؟
        r'\bمزیت\b',    # مزیت X چیست؟
        r'\bمعایب\b',   # معایب X؟
    ]
    
    # الگوهای سوالات عمومی (پاسخ جامع)
    general_patterns = [
        r'\bدر\s+مورد\b',           # در مورد X توضیح بده
        r'\bبرام\s+توضیح\b',        # برام توضیح بده
        r'\bمیدونی\b',              # چی میدونی؟
        r'\bمی\s*دانی\b',          # چه می‌دانی؟
        r'\bاطلاعات\b',             # اطلاعاتی بده
        r'\bهمه.*\bچیز',           # همه چیز رو بگو
        r'\bکامل.*\bتوضیح\b',      # کامل توضیح بده
        r'\bجامع\b',                # توضیح جامع
    ]
    
    # الگوهای درخواست توضیح (پاسخ متوسط)
    explanation_patterns = [
        r'\bچطور\b',    # چطور کار می‌کند؟
        r'\bچگونه\b',   # چگونه استفاده کنم؟
        r'\bنحوه\b',    # نحوه انجام X
        r'\bروش\b',     # روش انجام X
        r'\bمراحل\b',   # مراحل X چیست؟
    ]
    
    # بررسی الگوها
    is_specific = any(re.search(pattern, query) for pattern in specific_patterns)
    is_general = any(re.search(pattern, query) for pattern in general_patterns)
    is_explanation = any(re.search(pattern, query) for pattern in explanation_patterns)
    
    # تعیین نوع سوال
    if is_specific:
        query_type = QueryType.SPECIFIC
        query_type_fa = "خاص"
        response_style = "کوتاه و مستقیم"
        expected_length = "1-3 پاراگراف"
    elif is_general:
        query_type = QueryType.GENERAL
        query_type_fa = "عمومی"
        response_style = "جامع و کامل"
        expected_length = "5-10 پاراگراف"
    elif is_explanation:
        query_type = QueryType.EXPLANATION
        query_type_fa = "توضیحی"
        response_style = "متوسط با مراحل"
        expected_length = "3-5 پاراگراف"
    else:
        # پیش‌فرض: اگر سوال کوتاه است، خاص، وگرنه عمومی
        word_count = len(query.split())
        if word_count <= 8:
            query_type = QueryType.SPECIFIC
            query_type_fa = "خاص"
            response_style = "کوتاه و مستقیم"
            expected_length = "1-3 پاراگراف"
        else:
            query_type = QueryType.GENERAL
            query_type_fa = "عمومی"
            response_style = "جامع و کامل"
            expected_length = "5-10 پاراگراف"
    
    return {
        "query_type": query_type.value,
        "query_type_fa": query_type_fa,
        "response_style": response_style,
        "expected_length": expected_length,
        "is_specific": is_specific,
        "is_general": is_general,
        "is_explanation": is_explanation
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
