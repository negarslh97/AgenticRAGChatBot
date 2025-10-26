"""
Query Intent - تشخیص هوشمند نوع سوال
🎯 هدف: تشخیص اینکه آیا سوال نیاز به RAG دارد یا یک گفتگوی محاوره‌ای ساده است

این ماژول قبل از اجرای پایپلاین سنگین RAG، سوال را تحلیل می‌کند و مسیر مناسب را انتخاب می‌کند:
- conversational: سوالات محاوره‌ای، سلام، تشکر، معرفی نام → RAG bypass
- factual: سوالات تخصصی که نیاز به جستجو در پایگاه دانش دارند → RAG اجرا می‌شود

⚠️ IMPORTANT: از regex برای تطبیق دقیق استفاده می‌کند تا False Positive نداشته باشیم
"""

from enum import Enum
from typing import Dict, Any, Optional
import logging
import re  # ✅ اضافه شد برای regex
from app.infrastructure.langchain_utils import langchain_service

logger = logging.getLogger(__name__)


class QueryIntent(str, Enum):
    """نوع هدف سوال کاربر"""
    CONVERSATIONAL = "conversational"  # گفتگوی محاوره‌ای - بدون نیاز به RAG
    FACTUAL = "factual"               # سوال تخصصی - نیاز به RAG
    GREETING = "greeting"             # سلام و احوال‌پرسی
    GRATITUDE = "gratitude"           # تشکر
    INTRODUCTION = "introduction"      # معرفی خود


class QueryIntent:
    """
    Query Router - مسیریابی هوشمند سوالات
    
    این کلاس با استفاده از یک LLM کوچک و سریع (Gemini Flash یا مشابه)
    تشخیص می‌دهد که آیا سوال نیاز به جستجو در پایگاه دانش دارد یا خیر.
    """
    
    def __init__(self):
        self.langchain_service = langchain_service
        
        # 🎯 پرامپت برای تشخیص نوع سوال
        self.router_prompt = """شما یک طبقه‌بند هوشمند سوالات هستید. وظیفه شما تشخیص نوع سوال کاربر است.

**دسته‌بندی‌ها:**

1. **conversational** (گفتگوی محاوره‌ای):
   - معرفی خود: "اسم من ... است"، "من ... هستم"
   - تشکر: "ممنون"، "متشکرم"، "خیلی ممنون"
   - سلام و احوال‌پرسی: "سلام"، "درود"، "چطوری؟"، "حالت چطوره؟"
   - جملات شخصی که به پایگاه دانش مربوط نیست

2. **factual** (سوال تخصصی):
   - سوالاتی که به اطلاعات محصول/سرویس نیاز دارد
   - سوالات "چگونه"، "چطور"، "چیست"، "کجا"، "چرا" در مورد مستندات
   - درخواست راهنمایی یا آموزش
   - سوالات فنی

**سوال کاربر:**
{query}

**دستورالعمل:**
فقط یک کلمه پاسخ دهید: "conversational" یا "factual"

**پاسخ:**"""

    async def classify_query(self, query: str, conversation_history: Optional[list] = None) -> Dict[str, Any]:
        """
        طبقه‌بندی سوال کاربر
        
        Args:
            query: سوال کاربر
            conversation_history: تاریخچه مکالمه (برای context بهتر)
            
        Returns:
            {
                "intent": "conversational" | "factual",
                "confidence": 0.0-1.0,
                "needs_rag": True/False,
                "reason": "دلیل تصمیم‌گیری"
            }
        """
        logger.info(f"🔍 Query Intent analyzing: '{query[:100]}...'")
        
        try:
            # 🎯 تشخیص سریع الگوهای رایج (بدون فراخوانی LLM)
            quick_result = self._quick_pattern_match(query)
            if quick_result:
                logger.info(f"⚡ Quick match: {quick_result['intent']} (Pattern-based)")
                return quick_result
            
            # 🤖 استفاده از LLM برای تشخیص پیچیده‌تر
            prompt = self.router_prompt.format(query=query)
            
            # استفاده از مدل سریع و ارزان برای routing
            response = await self.langchain_service.generate_rag_response(
                query=query,
                context=prompt,
                conversation_history=[],
                custom_temperature=0.1,  # دقت بالا
                query_type="specific"  # پاسخ کوتاه
            )
            
            # پردازش پاسخ
            response_lower = response.strip().lower()
            
            if "conversational" in response_lower:
                intent = QueryIntent.CONVERSATIONAL
                needs_rag = False
                reason = "سوال محاوره‌ای - نیازی به جستجو در پایگاه دانش نیست"
            else:
                intent = QueryIntent.FACTUAL
                needs_rag = True
                reason = "سوال تخصصی - نیاز به جستجو در پایگاه دانش"
            
            result = {
                "intent": intent.value,
                "confidence": 0.9,
                "needs_rag": needs_rag,
                "reason": reason
            }
            
            logger.info(f"✅ Query classified as: {intent.value} (needs_rag={needs_rag})")
            return result
            
        except Exception as e:
            logger.error(f"❌ Query routing failed: {e}", exc_info=True)
            # در صورت خطا، به عنوان factual در نظر بگیر (safer)
            return {
                "intent": QueryIntent.FACTUAL.value,
                "confidence": 0.5,
                "needs_rag": True,
                "reason": "خطا در تشخیص - به صورت پیش‌فرض به RAG ارسال می‌شود"
            }
    
    def _quick_pattern_match(self, query: str) -> Optional[Dict[str, Any]]:
        """
        تشخیص سریع بر اساس الگوهای رایج (بدون نیاز به LLM)
        
        ⚠️ CRITICAL: از regex برای تطبیق دقیق استفاده می‌کند تا False Positive نداشته باشیم
        """
        query_lower = query.strip().lower()
        query_normalized = re.sub(r'\s+', ' ', query_lower)  # normalize spaces
        
        # 🎯 الگوهای EXACT محاوره‌ای (باید کل پیام match شود)
        # این الگوها فقط وقتی match می‌شوند که کل پیام فقط شامل آن‌ها باشد
        exact_conversational_patterns = [
            # سلام
            r'^سلام$', r'^درود$', r'^سلام\s*(علیکم)?$',
            r'^صبح بخیر$', r'^عصر بخیر$', r'^شب بخیر$',
            r'^hello$', r'^hi$', r'^hey$',
            
            # تشکر
            r'^ممنون(م)?$', r'^متشکر(م)?$', r'^مرسی$', r'^تشکر$',
            r'^خیلی\s+ممنون(م)?$', r'^بسیار\s+متشکر(م)?$',
            r'^thank\s*you$', r'^thanks$', r'^thx$',
            
            # خداحافظی
            r'^خداحافظ$', r'^خدا\s+حافظ$', r'^بای$', r'^فعلا$',
            r'^bye$', r'^goodbye$', r'^see\s+you$',
            
            # احوال‌پرسی
            r'^چطوری(\s+هستی)?$', r'^خوبی$', r'^حالت\s+چطوره?$',
            r'^how\s+are\s+you(\s+doing)?$', r'^what\'?s\s+up$',
        ]
        
        for pattern in exact_conversational_patterns:
            if re.match(pattern, query_normalized):
                return {
                    "intent": QueryIntent.CONVERSATIONAL.value,
                    "confidence": 1.0,
                    "needs_rag": False,
                    "reason": f"الگوی محاوره‌ای دقیق شناسایی شد"
                }
        
        # 🎯 الگوهای معرفی (می‌تواند در دل جمله باشد)
        introduction_patterns = [
            r'اسم\s+من\s+\S+\s+(است|هست)',
            r'نام\s+من\s+\S+\s+(است|هست)',
            r'من\s+\S+\s+هستم',
            r'my\s+name\s+is\s+\S+',
            r'i\'?m\s+\S+',
            r'i\s+am\s+\S+'
        ]
        
        for pattern in introduction_patterns:
            if re.search(pattern, query_normalized):
                return {
                    "intent": QueryIntent.CONVERSATIONAL.value,
                    "confidence": 1.0,
                    "needs_rag": False,
                    "reason": "الگوی معرفی شناسایی شد"
                }
        
        # 🎯 الگوهای واضح تخصصی (اولویت بالا)
        factual_indicators = [
            r'\bچگونه\b', r'\bچطور\b', r'\bچیست\b', r'\bچیه\b',
            r'\bچرا\b', r'\bکجا\b', r'\bکی\b', r'\bکدام\b',
            r'\bhow\s+to\b', r'\bwhat\s+is\b', r'\bwhere\s+is\b', r'\bwhy\b',
            r'\bراهنما\b', r'\bآموزش\b', r'\bمستندات\b',
            r'\bفاکتور\b', r'\bمدل\s+فروش\b', r'\bحسابداری\b',
            r'\bخرید\b', r'\bفروش\b', r'\bبایگانی\b'
        ]
        
        for pattern in factual_indicators:
            if re.search(pattern, query_normalized):
                return {
                    "intent": QueryIntent.FACTUAL.value,
                    "confidence": 1.0,
                    "needs_rag": True,
                    "reason": f"الگوی تخصصی شناسایی شد"
                }
        
        # 🎯 سوالات کوتاه (کمتر از 3 کلمه) بدون علامت سوال
        words = query_normalized.split()
        if len(words) <= 2 and len(query_normalized) < 15:
            # اگر علامت سوال دارد، احتمالاً factual است
            if '؟' not in query and '?' not in query:
                return {
                    "intent": QueryIntent.CONVERSATIONAL.value,
                    "confidence": 0.7,
                    "needs_rag": False,
                    "reason": "جمله بسیار کوتاه بدون علامت سوال"
                }
        
        # اگر هیچ الگویی match نکرد، None برگردان (برای استفاده از LLM)
        return None


# 🔥 Singleton instance
query_intent = QueryIntent()

