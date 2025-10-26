"""
Query Analyzer - تحلیلگر هوشمند سوالات
ادغام شده از query_analyzer.py و query_intent.py
"""

import re
import logging
import time
from enum import Enum
from typing import Dict, Any, Optional, List
from async_lru import alru_cache
from pydantic import BaseModel, Field
from app.infrastructure.langchain_utils import langchain_service
from app.utils.analyzer_config import (
    CONVERSATIONAL_PATTERNS, INTRODUCTION_PATTERNS, FACTUAL_INDICATORS,
    COMPLEXITY_KEYWORDS, SPECIFIC_PATTERNS, GENERAL_PATTERNS, EXPLANATION_PATTERNS,
    TITLE_CLEANUP_WORDS
)

logger = logging.getLogger(__name__)


class QueryIntent(str, Enum):
    """نوع هدف سوال کاربر"""
    CONVERSATIONAL = "conversational"  # گفتگوی محاوره‌ای - بدون نیاز به RAG
    FACTUAL = "factual"               # سوال تخصصی - نیاز به RAG
    MIXED = "mixed"                   # سوال ترکیبی - نیاز به RAG


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


class QueryAnalysisResult(BaseModel):
    """ساختار جامع تحلیل سوال کاربر"""
    intent: QueryIntent = Field(..., description="هدف اصلی سوال (محاوره‌ای، تخصصی یا ترکیبی)")
    needs_rag: bool = Field(..., description="آیا برای پاسخ به این سوال نیاز به جستجو در پایگاه دانش (RAG) است؟")
    complexity: QueryComplexity = Field(..., description="میزان پیچیدگی سوال")
    summary: str = Field(..., description="خلاصه‌ای یک خطی از درخواست اصلی کاربر")
    keywords: List[str] = Field(default_factory=list, description="کلمات کلیدی استخراج شده از سوال (برای جستجو)")
    confidence: float = Field(..., description="میزان اطمینان از تحلیل")
    reason: str = Field(..., description="توضیح دلیل تحلیل")
    query_type: Optional[QueryType] = Field(None, description="نوع سوال برای تعیین سبک پاسخ")
    analysis: Optional[Dict[str, Any]] = Field(None, description="جزئیات تحلیل پیچیدگی و نوع")


class QueryAnalyzer:
    """
    تحلیلگر هوشمند سوالات - یکپارچه شده

    این کلاس هر دو وظیفه تشخیص هدف و تحلیل پیچیدگی را انجام می‌دهد.
    """

    def __init__(self):
        self.langchain_service = langchain_service
        self._load_compiled_patterns()

        # آمار عملکرد
        self.stats = {
            "total_analyses": 0,
            "cache_hits": 0,
            "llm_calls": 0,
            "fallback_calls": 0,
            "average_response_time": 0.0,
            "intent_distribution": {
                "conversational": 0,
                "factual": 0,
                "mixed": 0
            },
            "complexity_distribution": {
                "simple": 0,
                "moderate": 0,
                "complex": 0
            }
        }

        # پرامپت برای تحلیل تک‌مرحله‌ای با LLM
        self.single_pass_prompt = """شما یک تحلیلگر هوشمند سوالات هستید. وظیفه شما این است که سوال کاربر را تحلیل کرده و خروجی را دقیقاً در قالب JSON برگردانید.

**فرمت خروجی اجباری:**
{{
  "intent": "conversational|factual|mixed",
  "needs_rag": true|false,
  "complexity": "simple|moderate|complex",
  "summary": "خلاصه سوال",
  "keywords": ["کلمه1", "کلمه2"],
  "confidence": 0.0-1.0,
  "reason": "توضیح تحلیل"
}}

**قوانین تحلیل:**
- intent: "conversational" برای سلام/تشکر، "factual" برای سوالات تخصصی، "mixed" برای ترکیبی
- needs_rag: true فقط برای factual و mixed
- complexity:
  - "simple": سوال مستقیم تک‌جوابی (مثال: "قیمت چنده؟")
  - "moderate": سوال چندمرحله‌ای (مثال: "چطور بایگانی کنم؟")
  - "complex": سوال چندبخشی ترکیبی (مثال: "بایگانی و گزارش تولید")

سوال کاربر: "{query}"

**پاسخ فقط JSON خالص بدون هیچ متن اضافی:**"""

    def _load_compiled_patterns(self):
        """کامپایل کردن تمام الگوهای Regex برای کارایی بهتر"""
        logger.info("🔧 کامپایل کردن الگوهای Regex برای QueryAnalyzer...")

        # الگوهای محاوره‌ای
        self.compiled_conversational = {}
        for category, patterns in CONVERSATIONAL_PATTERNS.items():
            self.compiled_conversational[category] = [re.compile(p) for p in patterns]

        # سایر الگوها
        self.compiled_introduction = [re.compile(p) for p in INTRODUCTION_PATTERNS]
        self.compiled_factual = [re.compile(p) for p in FACTUAL_INDICATORS]

        # الگوهای تحلیل نوع
        self.compiled_specific = [re.compile(p) for p in SPECIFIC_PATTERNS]
        self.compiled_general = [re.compile(p) for p in GENERAL_PATTERNS]
        self.compiled_explanation = [re.compile(p) for p in EXPLANATION_PATTERNS]

        logger.info("✅ الگوهای Regex کامپایل شدند")

    def _normalize_query(self, query: str) -> str:
        """نرمال‌سازی متن سوال"""
        return re.sub(r'\s+', ' ', query.strip().lower())

    @alru_cache(maxsize=1000)
    async def analyze(self, query: str, conversation_history: Optional[list] = None) -> QueryAnalysisResult:
        """
        تحلیل جامع سوال کاربر با استفاده از LLM تک‌مرحله‌ای

        Args:
            query: متن سوال کاربر
            conversation_history: تاریخچه مکالمه (اختیاری)

        Returns:
            QueryAnalysisResult: تحلیل کامل در قالب Pydantic model
        """
        start_time = time.time()
        logger.info(f"🔍 تحلیل تک‌مرحله‌ای سوال: '{query[:100]}...'")

        # بررسی cache hit
        is_cache_hit = hasattr(self.analyze, '_cache') and query in self.analyze._cache
        if is_cache_hit:
            self.stats["cache_hits"] += 1

        try:
            # استفاده از پرامپت تک‌مرحله‌ای با مدل اختصاصی intent
            from app.core.config import settings
            intent_model = settings.intent_model_loaded or settings.rag_model_loaded

            prompt = self.single_pass_prompt.format(query=query)

            response = await self.langchain_service.generate_rag_response(
                query=query,
                context=prompt,
                conversation_history=conversation_history or [],
                custom_model=intent_model,
                custom_temperature=0.1,  # دقت بالا
                query_type="specific"  # پاسخ کوتاه
            )

            self.stats["llm_calls"] += 1

            # پاکسازی پاسخ JSON - بهبود استخراج JSON از پاسخ
            import json
            import re

            # ابتدا تلاش برای استخراج JSON کامل
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                try:
                    result_dict = json.loads(json_str)
                except json.JSONDecodeError as e:
                    logger.warning(f"JSON decode error: {e}, trying to fix...")
                    # اگر JSON نامعتبر بود، تلاش برای پاکسازی
                    json_str = re.sub(r'[^\x00-\x7F]+', '', json_str)  # حذف کاراکترهای غیر ASCII
                    json_str = re.sub(r',\s*}', '}', json_str)  # حذف کاماهای اضافی
                    json_str = re.sub(r',\s*]', ']', json_str)
                    # پاکسازی نقل قول‌های اضافی
                    json_str = re.sub(r'""(\w+)""', r'"\1"', json_str)
                    json_str = re.sub(r'"(\w+)":', r'"\1":', json_str)
                    try:
                        result_dict = json.loads(json_str)
                    except json.JSONDecodeError:
                        logger.error(f"Failed to parse JSON even after cleanup: {json_str}")
                        raise ValueError(f"Invalid JSON response: {json_str}")
            else:
                # اگر JSON پیدا نشد، از fallback استفاده کن
                logger.error(f"No JSON found in response: {response}")
                raise ValueError("No JSON found in response")

            # اطمینان از مقادیر معتبر
            if result_dict.get('intent') not in [e.value for e in QueryIntent]:
                result_dict['intent'] = QueryIntent.FACTUAL.value

            if result_dict.get('complexity') not in [e.value for e in QueryComplexity]:
                result_dict['complexity'] = QueryComplexity.SIMPLE.value

            # تعیین query_type بر اساس complexity
            if result_dict.get('complexity') == QueryComplexity.SIMPLE.value:
                result_dict['query_type'] = QueryType.SPECIFIC.value
            elif result_dict.get('complexity') == QueryComplexity.COMPLEX.value:
                result_dict['query_type'] = QueryType.GENERAL.value
            else:
                result_dict['query_type'] = QueryType.EXPLANATION.value

            # اطمینان از وجود فیلدهای ضروری
            result_dict.setdefault('summary', query[:100])
            result_dict.setdefault('keywords', [])
            result_dict.setdefault('confidence', 0.8)
            result_dict.setdefault('reason', 'تحلیل تک‌مرحله‌ای LLM')

            result = QueryAnalysisResult(**result_dict)

            # بروزرسانی آمار
            self._update_stats(result, start_time, is_cache_hit, True, False)

            return result

        except Exception as e:
            logger.error(f"❌ خطا در تحلیل تک‌مرحله‌ای: {e}")
            # بازگشت به تحلیل fallback
            result = await self._fallback_analyze(query)

            # بروزرسانی آمار برای fallback
            self._update_stats(result, start_time, is_cache_hit, False, True)

            return result

    def _update_stats(self, result: QueryAnalysisResult, start_time: float,
                     is_cache_hit: bool, is_llm_call: bool, is_fallback: bool):
        """بروزرسانی آمار عملکرد"""
        response_time = time.time() - start_time

        self.stats["total_analyses"] += 1

        if is_cache_hit:
            self.stats["cache_hits"] += 1
        elif is_llm_call:
            self.stats["llm_calls"] += 1
        elif is_fallback:
            self.stats["fallback_calls"] += 1

        # بروزرسانی میانگین زمان پاسخ
        total_time = self.stats["average_response_time"] * (self.stats["total_analyses"] - 1)
        self.stats["average_response_time"] = (total_time + response_time) / self.stats["total_analyses"]

        # بروزرسانی توزیع intent
        intent = result.intent.value
        if intent in self.stats["intent_distribution"]:
            self.stats["intent_distribution"][intent] += 1

        # بروزرسانی توزیع complexity
        complexity = result.complexity.value
        if complexity in self.stats["complexity_distribution"]:
            self.stats["complexity_distribution"][complexity] += 1

    def get_performance_stats(self) -> Dict[str, Any]:
        """دریافت آمار عملکرد تحلیلگر"""
        stats = self.stats.copy()

        # محاسبه نرخ cache hit
        if stats["total_analyses"] > 0:
            stats["cache_hit_rate"] = stats["cache_hits"] / stats["total_analyses"]
            stats["llm_call_rate"] = stats["llm_calls"] / stats["total_analyses"]
            stats["fallback_rate"] = stats["fallback_calls"] / stats["total_analyses"]
        else:
            stats["cache_hit_rate"] = 0.0
            stats["llm_call_rate"] = 0.0
            stats["fallback_rate"] = 0.0

        return stats

    def log_performance_summary(self):
        """لاگ کردن خلاصه عملکرد"""
        stats = self.get_performance_stats()

        logger.info("📊 آمار عملکرد QueryAnalyzer:")
        logger.info(f"  کل تحلیل‌ها: {stats['total_analyses']}")
        logger.info(f"  نرخ cache hit: {stats['cache_hit_rate']:.2%}")
        logger.info(f"  نرخ فراخوانی LLM: {stats['llm_call_rate']:.2%}")
        logger.info(f"  نرخ fallback: {stats['fallback_rate']:.2%}")
        logger.info(f"  میانگین زمان پاسخ: {stats['average_response_time']:.3f}s")
        logger.info(f"  توزیع intent: {stats['intent_distribution']}")
        logger.info(f"  توزیع complexity: {stats['complexity_distribution']}")

    async def _fallback_analyze(self, query: str) -> QueryAnalysisResult:
        """
        تحلیل fallback در صورت خطا در تحلیل اصلی
        """
        logger.info("🔄 استفاده از تحلیل fallback...")

        normalized_query = self._normalize_query(query)

        # تشخیص سریع هدف
        intent_result = self._classify_intent_quick(normalized_query)

        if intent_result is None:
            intent_result = await self._classify_intent_llm(query, [])

        # اگر محاوره‌ای بود
        if not intent_result["needs_rag"]:
            return QueryAnalysisResult(
                intent=QueryIntent.CONVERSATIONAL,
                needs_rag=False,
                complexity=QueryComplexity.SIMPLE,
                summary=query[:100],
                keywords=[],
                confidence=intent_result["confidence"],
                reason=intent_result["reason"]
            )

        # اگر تخصصی بود، تحلیل پیچیدگی
        complexity_result = self._analyze_complexity(normalized_query)
        type_result = self._analyze_type(normalized_query)

        return QueryAnalysisResult(
            intent=QueryIntent.FACTUAL,
            needs_rag=True,
            complexity=QueryComplexity(complexity_result["complexity"]),
            summary=query[:100],
            keywords=[],
            confidence=0.7,
            reason="تحلیل fallback",
            query_type=QueryType(type_result["query_type"]),
            analysis={
                "complexity": complexity_result,
                "type": type_result
            }
        )

    def _classify_intent_quick(self, normalized_query: str) -> Optional[Dict[str, Any]]:
        """
        تشخیص سریع هدف سوال بر اساس الگوهای Regex

        Returns:
            None اگر نیاز به LLM باشد
        """
        # بررسی الگوهای محاوره‌ای دقیق
        for category, patterns in self.compiled_conversational.items():
            for pattern in patterns:
                if pattern.match(normalized_query):
                    return {
                        "intent": QueryIntent.CONVERSATIONAL.value,
                        "confidence": 1.0,
                        "needs_rag": False,
                        "reason": f"الگوی محاوره‌ای دقیق شناسایی شد ({category})"
                    }

        # بررسی الگوهای معرفی
        for pattern in self.compiled_introduction:
            if pattern.search(normalized_query):
                return {
                    "intent": QueryIntent.CONVERSATIONAL.value,
                    "confidence": 1.0,
                    "needs_rag": False,
                    "reason": "الگوی معرفی شناسایی شد"
                }

        # بررسی الگوهای تخصصی
        for pattern in self.compiled_factual:
            if pattern.search(normalized_query):
                return {
                    "intent": QueryIntent.FACTUAL.value,
                    "confidence": 1.0,
                    "needs_rag": True,
                    "reason": "الگوی تخصصی شناسایی شد"
                }

        # بررسی سوالات کوتاه بدون علامت سوال
        words = normalized_query.split()
        if len(words) <= 2 and len(normalized_query) < 15:
            if '؟' not in normalized_query and '?' not in normalized_query:
                return {
                    "intent": QueryIntent.CONVERSATIONAL.value,
                    "confidence": 0.7,
                    "needs_rag": False,
                    "reason": "جمله بسیار کوتاه بدون علامت سوال"
                }

        # اگر هیچ الگویی match نکرد، نیاز به LLM داریم
        return None

    async def _classify_intent_llm(self, query: str, conversation_history: Optional[list] = None) -> Dict[str, Any]:
        """
        تشخیص هدف سوال با استفاده از LLM
        """
        try:
            prompt = self.router_prompt.format(query=query)

            response = await self.langchain_service.generate_rag_response(
                query=query,
                context=prompt,
                conversation_history=conversation_history or [],
                custom_temperature=0.1,  # دقت بالا
                query_type="specific"  # پاسخ کوتاه
            )

            response_lower = response.strip().lower()

            if "conversational" in response_lower:
                return {
                    "intent": QueryIntent.CONVERSATIONAL.value,
                    "confidence": 0.9,
                    "needs_rag": False,
                    "reason": "تشخیص LLM: سوال محاوره‌ای"
                }
            else:
                return {
                    "intent": QueryIntent.FACTUAL.value,
                    "confidence": 0.9,
                    "needs_rag": True,
                    "reason": "تشخیص LLM: سوال تخصصی"
                }

        except Exception as e:
            logger.error(f"❌ خطا در تشخیص هدف با LLM: {e}")
            # در صورت خطا، به عنوان factual در نظر بگیر (safer)
            return {
                "intent": QueryIntent.FACTUAL.value,
                "confidence": 0.5,
                "needs_rag": True,
                "reason": "خطا در تشخیص - به صورت پیش‌فرض به RAG ارسال می‌شود"
            }

    def _analyze_complexity(self, normalized_query: str) -> Dict[str, Any]:
        """
        تحلیل سطح پیچیدگی سوال
        """
        word_count = len(normalized_query.split())
        score = 0
        reasons = []

        # ۱. طول سوال
        if word_count <= 5:
            score += 0
            reasons.append("سوال کوتاه")
        elif word_count <= 15:
            score += 1
            reasons.append("سوال متوسط")
        else:
            score += 2
            reasons.append("سوال طولانی")

        # ۲. کلمات کلیدی پیچیده
        complex_count = sum(1 for keyword in COMPLEXITY_KEYWORDS["complex"]
                           if keyword in normalized_query)
        if complex_count > 0:
            score += complex_count
            reasons.append(f"{complex_count} کلمه پیچیده")

        # ۳. چندبخشی بودن
        multi_part_count = sum(1 for keyword in COMPLEXITY_KEYWORDS["multi_part"]
                              if keyword in normalized_query)
        if multi_part_count >= 2:
            score += 2
            reasons.append("سوال چندبخشی")

        # ۴. درخواست جزئیات
        detail_count = sum(1 for keyword in COMPLEXITY_KEYWORDS["detail_requests"]
                           if keyword in normalized_query)
        if detail_count > 0:
            score += 1
            reasons.append("درخواست جزئیات")

        # ۵. علامت سوال متعدد
        question_marks = normalized_query.count('؟') + normalized_query.count('?')
        if question_marks > 1:
            score += 1
            reasons.append("چند سوال")

        # تعیین complexity
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

    def _analyze_type(self, normalized_query: str) -> Dict[str, Any]:
        """
        تحلیل نوع سوال برای تعیین سبک پاسخ
        """
        # بررسی الگوها
        is_specific = any(p.search(normalized_query) for p in self.compiled_specific)
        is_general = any(p.search(normalized_query) for p in self.compiled_general)
        is_explanation = any(p.search(normalized_query) for p in self.compiled_explanation)

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
            word_count = len(normalized_query.split())
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

    def generate_conversation_title(self, first_message: str, max_length: int = 50) -> str:
        """
        تولید عنوان خودکار برای مکالمه از اولین پیام
        """
        # پاکسازی
        title = first_message.strip()

        # حذف علامت‌های سوال
        title = title.replace('؟', '').replace('?', '')

        # حذف کلمات اضافی
        for word in TITLE_CLEANUP_WORDS:
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


# نمونه Singleton برای دسترسی آسان
query_analyzer = QueryAnalyzer()
