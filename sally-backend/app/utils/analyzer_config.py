"""
Query Analyzer Configuration
تنظیمات و کلمات کلیدی برای تحلیلگر سوالات
"""

from typing import Dict, List
from pydantic import BaseModel, Field


class AnalyzerSettings(BaseModel):
    """تنظیمات تحلیلگر سوالات با اعتبارسنجی Pydantic"""
    conversational_patterns: Dict[str, List[str]] = Field(..., description="الگوهای تشخیص محاورات")
    introduction_patterns: List[str] = Field(..., description="الگوهای معرفی")
    factual_indicators: List[str] = Field(..., description="کلمات کلیدی سوالات تخصصی")
    complexity_keywords: Dict[str, List[str]] = Field(..., description="کلمات کلیدی پیچیدگی")
    specific_patterns: List[str] = Field(..., description="الگوهای سوالات خاص")
    general_patterns: List[str] = Field(..., description="الگوهای سوالات عمومی")
    explanation_patterns: List[str] = Field(..., description="الگوهای سوالات توضیحی")
    title_cleanup_words: List[str] = Field(..., description="کلمات پاکسازی عنوان")


# ===========================================
# الگوهای Regex برای تشخیص هدف سوال
# ===========================================

CONVERSATIONAL_PATTERNS: Dict[str, List[str]] = {
    "greetings": [
        r'^سلام$', r'^درود$', r'^سلام\s*(علیکم)?$',
        r'^صبح بخیر$', r'^عصر بخیر$', r'^شب بخیر$',
        r'^hello$', r'^hi$', r'^hey$'
    ],
    "thanks": [
        r'^ممنون(م)?$', r'^متشکر(م)?$', r'^مرسی$', r'^تشکر$',
        r'^خیلی\s+ممنون(م)?$', r'^بسیار\s+متشکر(م)?$',
        r'^thank\s*you$', r'^thanks$', r'^thx$'
    ],
    "farewell": [
        r'^خداحافظ$', r'^خدا\s+حافظ$', r'^بای$', r'^فعلا$',
        r'^bye$', r'^goodbye$', r'^see\s+you$'
    ],
    "wellbeing": [
        r'^چطوری(\s+هستی)?$', r'^خوبی$', r'^حالت\s+چطوره?$',
        r'^how\s+are\s+you(\s+doing)?$', r'^what\'?s\s+up$'
    ]
}

INTRODUCTION_PATTERNS: List[str] = [
    r'اسم\s+من\s+\S+\s+(است|هست)',
    r'نام\s+من\s+\S+\s+(است|هست)',
    r'من\s+\S+\s+هستم',
    r'my\s+name\s+is\s+\S+',
    r'i\'?m\s+\S+',
    r'i\s+am\s+\S+'
]

FACTUAL_INDICATORS: List[str] = [
    r'\bچگونه\b', r'\bچطور\b', r'\bچیست\b', r'\bچیه\b',
    r'\bچرا\b', r'\bکجا\b', r'\bکی\b', r'\bکدام\b',
    r'\bhow\s+to\b', r'\bwhat\s+is\b', r'\bwhere\s+is\b', r'\bwhy\b',
    r'\bراهنما\b', r'\bآموزش\b', r'\bمستندات\b',
    r'\bفاکتور\b', r'\bمدل\s+فروش\b', r'\bحسابداری\b',
    r'\bخرید\b', r'\bفروش\b', r'\bبایگانی\b'
]

# ===========================================
# کلمات کلیدی برای تحلیل پیچیدگی
# ===========================================

COMPLEXITY_KEYWORDS: Dict[str, List[str]] = {
    "complex": [
        "چطور", "چگونه", "چه طور", "نحوه", "روش",
        "مراحل", "قدم", "ابتدا", "سپس", "بعد",
        "و همچنین", "علاوه بر", "در کنار"
    ],
    "multi_part": ["و", "همچنین", "ضمناً", "علاوه"],
    "detail_requests": [
        "دقیق", "کامل", "با جزئیات", "تمام",
        "همه", "تمامی", "کلیه"
    ]
}

# ===========================================
# الگوهای تحلیل نوع سوال
# ===========================================

SPECIFIC_PATTERNS: List[str] = [
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

GENERAL_PATTERNS: List[str] = [
    r'\bدر\s+مورد\b',           # در مورد X توضیح بده
    r'\bبرام\s+توضیح\b',        # برام توضیح بده
    r'\bمیدونی\b',              # چی میدونی؟
    r'\bمی\s*دانی\b',          # چه می‌دانی؟
    r'\bاطلاعات\b',             # اطلاعاتی بده
    r'\bهمه.*\bچیز',           # همه چیز رو بگو
    r'\bکامل.*\bتوضیح\b',      # کامل توضیح بده
    r'\bجامع\b',                # توضیح جامع
]

EXPLANATION_PATTERNS: List[str] = [
    r'\bچطور\b',    # چطور کار می‌کند؟
    r'\bچگونه\b',   # چگونه استفاده کنم؟
    r'\bنحوه\b',    # نحوه انجام X
    r'\bروش\b',     # روش انجام X
    r'\bمراحل\b',   # مراحل X چیست؟
]

# ===========================================
# کلمات برای پاکسازی عنوان
# ===========================================

TITLE_CLEANUP_WORDS: List[str] = [
    'لطفا', 'لطفاً', 'ممنون', 'متشکرم', 'سلام', 'درود'
]

# نمونه تنظیمات پیش‌فرض
default_config = AnalyzerSettings(
    conversational_patterns=CONVERSATIONAL_PATTERNS,
    introduction_patterns=INTRODUCTION_PATTERNS,
    factual_indicators=FACTUAL_INDICATORS,
    complexity_keywords=COMPLEXITY_KEYWORDS,
    specific_patterns=SPECIFIC_PATTERNS,
    general_patterns=GENERAL_PATTERNS,
    explanation_patterns=EXPLANATION_PATTERNS,
    title_cleanup_words=TITLE_CLEANUP_WORDS
)

# ===========================================
# الگوهای Regex برای تشخیص هدف سوال
# ===========================================

CONVERSATIONAL_PATTERNS: Dict[str, List[str]] = {
    "greetings": [
        r'^سلام$', r'^درود$', r'^سلام\s*(علیکم)?$',
        r'^صبح بخیر$', r'^عصر بخیر$', r'^شب بخیر$',
        r'^hello$', r'^hi$', r'^hey$'
    ],
    "thanks": [
        r'^ممنون(م)?$', r'^متشکر(م)?$', r'^مرسی$', r'^تشکر$',
        r'^خیلی\s+ممنون(م)?$', r'^بسیار\s+متشکر(م)?$',
        r'^thank\s*you$', r'^thanks$', r'^thx$'
    ],
    "farewell": [
        r'^خداحافظ$', r'^خدا\s+حافظ$', r'^بای$', r'^فعلا$',
        r'^bye$', r'^goodbye$', r'^see\s+you$'
    ],
    "wellbeing": [
        r'^چطوری(\s+هستی)?$', r'^خوبی$', r'^حالت\s+چطوره?$',
        r'^how\s+are\s+you(\s+doing)?$', r'^what\'?s\s+up$'
    ]
}

INTRODUCTION_PATTERNS: List[str] = [
    r'اسم\s+من\s+\S+\s+(است|هست)',
    r'نام\s+من\s+\S+\s+(است|هست)',
    r'من\s+\S+\s+هستم',
    r'my\s+name\s+is\s+\S+',
    r'i\'?m\s+\S+',
    r'i\s+am\s+\S+'
]

FACTUAL_INDICATORS: List[str] = [
    r'\bچگونه\b', r'\bچطور\b', r'\bچیست\b', r'\bچیه\b',
    r'\bچرا\b', r'\bکجا\b', r'\bکی\b', r'\bکدام\b',
    r'\bhow\s+to\b', r'\bwhat\s+is\b', r'\bwhere\s+is\b', r'\bwhy\b',
    r'\bراهنما\b', r'\bآموزش\b', r'\bمستندات\b',
    r'\bفاکتور\b', r'\bمدل\s+فروش\b', r'\bحسابداری\b',
    r'\bخرید\b', r'\bفروش\b', r'\bبایگانی\b'
]

# ===========================================
# کلمات کلیدی برای تحلیل پیچیدگی
# ===========================================

COMPLEXITY_KEYWORDS: Dict[str, List[str]] = {
    "complex": [
        "چطور", "چگونه", "چه طور", "نحوه", "روش",
        "مراحل", "قدم", "ابتدا", "سپس", "بعد",
        "و همچنین", "علاوه بر", "در کنار"
    ],
    "multi_part": ["و", "همچنین", "ضمناً", "علاوه"],
    "detail_requests": [
        "دقیق", "کامل", "با جزئیات", "تمام",
        "همه", "تمامی", "کلیه"
    ]
}

# ===========================================
# الگوهای تحلیل نوع سوال
# ===========================================

SPECIFIC_PATTERNS: List[str] = [
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

GENERAL_PATTERNS: List[str] = [
    r'\bدر\s+مورد\b',           # در مورد X توضیح بده
    r'\bبرام\s+توضیح\b',        # برام توضیح بده
    r'\bمیدونی\b',              # چی میدونی؟
    r'\bمی\s*دانی\b',          # چه می‌دانی؟
    r'\bاطلاعات\b',             # اطلاعاتی بده
    r'\bهمه.*\bچیز',           # همه چیز رو بگو
    r'\bکامل.*\bتوضیح\b',      # کامل توضیح بده
    r'\bجامع\b',                # توضیح جامع
]

EXPLANATION_PATTERNS: List[str] = [
    r'\bچطور\b',    # چطور کار می‌کند؟
    r'\bچگونه\b',   # چگونه استفاده کنم؟
    r'\bنحوه\b',    # نحوه انجام X
    r'\bروش\b',     # روش انجام X
    r'\bمراحل\b',   # مراحل X چیست؟
]

# ===========================================
# کلمات برای پاکسازی عنوان
# ===========================================

TITLE_CLEANUP_WORDS: List[str] = [
    'لطفا', 'لطفاً', 'ممنون', 'متشکرم', 'سلام', 'درود'
]