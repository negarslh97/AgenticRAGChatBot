"""
Query Router - تشخیص هوشمند نوع سوال
🎯 هدف: تشخیص اینکه آیا سوال نیاز به RAG دارد یا یک گفتگوی محاوره‌ای ساده است

این ماژول قبل از اجرای پایپلاین سنگین RAG، سوال را تحلیل می‌کند و مسیر مناسب را انتخاب می‌کند:
- conversational: سوالات محاوره‌ای، سلام، تشکر، معرفی نام → RAG bypass
- factual: سوالات تخصصی که نیاز به جستجو در پایگاه دانش دارند → RAG اجرا می‌شود
"""

from enum import Enum
from typing import Dict, Any, Optional
import logging
from app.infrastructure.langchain_utils import langchain_service

logger = logging.getLogger(__name__)


class QueryIntent(str, Enum):
    """نوع هدف سوال کاربر"""
    CONVERSATIONAL = "conversational"  # گفتگوی محاوره‌ای - بدون نیاز به RAG
    FACTUAL = "factual"               # سوال تخصصی - نیاز به RAG
    GREETING = "greeting"             # سلام و احوال‌پرسی
    GRATITUDE = "gratitude"           # تشکر
    INTRODUCTION = "introduction"      # معرفی خود


class QueryRouter:
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
        logger.info(f"🔍 Query Router analyzing: '{query[:100]}...'")
        
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
        این کار هزینه و latency را برای سوالات رایج به صفر می‌رساند.
        """
        query_lower = query.strip().lower()
        
        # 🎯 الگوهای محاوره‌ای
        conversational_patterns = [
            # معرفی
            "اسم من", "نام من", "من هستم", "من ... هستم",
            "my name is", "i am", "i'm",
            
            # تشکر
            "ممنون", "متشکر", "مرسی", "تشکر",
            "thank", "thanks", "thx",
            
            # سلام
            "سلام", "درود", "صبح بخیر", "عصر بخیر", "شب بخیر",
            "hello", "hi", "hey", "good morning", "good evening",
            
            # احوال‌پرسی
            "حالت چطور", "چطوری", "خوبی",
            "how are you", "what's up", "how do you do",
            
            # خداحافظی
            "خداحافظ", "بای", "فعلا",
            "bye", "goodbye", "see you"
        ]
        
        for pattern in conversational_patterns:
            if pattern in query_lower:
                return {
                    "intent": QueryIntent.CONVERSATIONAL.value,
                    "confidence": 1.0,
                    "needs_rag": False,
                    "reason": f"الگوی محاوره‌ای شناسایی شد: '{pattern}'"
                }
        
        # 🎯 الگوهای واضح تخصصی
        factual_indicators = [
            "چگونه", "چطور", "چیست", "چیه",
            "how to", "what is", "where is", "why",
            "راهنما", "آموزش", "مستندات",
            "فاکتور", "مدل فروش", "حسابداری", "خرید", "فروش"
        ]
        
        for indicator in factual_indicators:
            if indicator in query_lower:
                return {
                    "intent": QueryIntent.FACTUAL.value,
                    "confidence": 1.0,
                    "needs_rag": True,
                    "reason": f"الگوی تخصصی شناسایی شد: '{indicator}'"
                }
        
        # 🎯 سوالات کوتاه (کمتر از 4 کلمه) معمولاً محاوره‌ای هستند
        words = query_lower.split()
        if len(words) <= 3 and len(query_lower) < 20:
            # اما اگر علامت سوال دارد، احتمالاً factual است
            if '؟' not in query and '?' not in query:
                return {
                    "intent": QueryIntent.CONVERSATIONAL.value,
                    "confidence": 0.8,
                    "needs_rag": False,
                    "reason": "جمله کوتاه بدون علامت سوال - احتمالاً محاوره‌ای"
                }
        
        # اگر هیچ الگویی match نکرد، None برگردان (برای استفاده از LLM)
        return None


# 🔥 Singleton instance
query_router = QueryRouter()

