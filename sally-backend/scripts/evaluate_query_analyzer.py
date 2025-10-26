#!/usr/bin/env python3
"""
Query Analyzer Evaluation Script
ارزیابی عملکرد تحلیلگر سوالات جدید
"""

import asyncio
import json
import logging
from typing import List, Dict, Any
from pathlib import Path

# تنظیم logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# اضافه کردن مسیر پروژه به PYTHONPATH
import sys
sys.path.append(str(Path(__file__).parent.parent))

from app.utils.query_analyzer import query_analyzer, QueryAnalysisResult


class QueryAnalyzerEvaluator:
    """ارزیابی عملکرد تحلیلگر سوالات"""

    def __init__(self):
        self.test_cases = self._load_test_cases()

    def _load_test_cases(self) -> List[Dict[str, Any]]:
        """بارگذاری مجموعه داده ارزیابی گسترده"""
        return [
            # سوالات محاوره‌ای - ۵ کیس
            {
                "query": "سلام",
                "expected": {
                    "intent": "conversational",
                    "needs_rag": False,
                    "complexity": "simple"
                }
            },
            {
                "query": "ممنونم",
                "expected": {
                    "intent": "conversational",
                    "needs_rag": False,
                    "complexity": "simple"
                }
            },
            {
                "query": "اسم من علی است",
                "expected": {
                    "intent": "conversational",
                    "needs_rag": False,
                    "complexity": "simple"
                }
            },
            {
                "query": "چطوری؟",
                "expected": {
                    "intent": "conversational",
                    "needs_rag": False,
                    "complexity": "simple"
                }
            },
            {
                "query": "خداحافظ",
                "expected": {
                    "intent": "conversational",
                    "needs_rag": False,
                    "complexity": "simple"
                }
            },

            # سوالات تخصصی ساده - ۵ کیس
            {
                "query": "چطور فاکتور خرید را بایگانی کنم؟",
                "expected": {
                    "intent": "factual",
                    "needs_rag": True,
                    "complexity": "simple"
                }
            },
            {
                "query": "قیمت محصول چنده؟",
                "expected": {
                    "intent": "factual",
                    "needs_rag": True,
                    "complexity": "simple"
                }
            },
            {
                "query": "چگونه می‌توانم وارد سیستم شوم؟",
                "expected": {
                    "intent": "factual",
                    "needs_rag": True,
                    "complexity": "simple"
                }
            },
            {
                "query": "آیا امکان تغییر رمز عبور وجود دارد؟",
                "expected": {
                    "intent": "factual",
                    "needs_rag": True,
                    "complexity": "simple"
                }
            },
            {
                "query": "کجا می‌توانم گزارش‌ها را مشاهده کنم؟",
                "expected": {
                    "intent": "factual",
                    "needs_rag": True,
                    "complexity": "simple"
                }
            },

            # سوالات ترکیبی - ۵ کیس
            {
                "query": "سلام، چطور می‌تونم فاکتور خرید رو بایگانی کنم؟",
                "expected": {
                    "intent": "mixed",
                    "needs_rag": True,
                    "complexity": "simple"
                }
            },
            {
                "query": "ممنون، حالا بگید چطور گزارش تولید کنم؟",
                "expected": {
                    "intent": "mixed",
                    "needs_rag": True,
                    "complexity": "simple"
                }
            },
            {
                "query": "درود، امکان تغییر تنظیمات وجود داره؟",
                "expected": {
                    "intent": "mixed",
                    "needs_rag": True,
                    "complexity": "simple"
                }
            },
            {
                "query": "سلام، قیمت محصول چنده؟",
                "expected": {
                    "intent": "mixed",
                    "needs_rag": True,
                    "complexity": "simple"
                }
            },
            {
                "query": "خداحافظ، ولی اول بگید چطور پشتیبان بگیرم؟",
                "expected": {
                    "intent": "mixed",
                    "needs_rag": True,
                    "complexity": "simple"
                }
            },

            # سوالات پیچیده - ۵ کیس
            {
                "query": "چطور می‌توانم فاکتور خرید را بایگانی کنم و سپس گزارش مالی ماهانه را تولید نمایم؟",
                "expected": {
                    "intent": "factual",
                    "needs_rag": True,
                    "complexity": "complex"
                }
            },
            {
                "query": "چگونه می‌توانم ابتدا محصول را ثبت کنم، سپس قیمت‌گذاری انجام دهم و در نهایت گزارش فروش تولید نمایم؟",
                "expected": {
                    "intent": "factual",
                    "needs_rag": True,
                    "complexity": "complex"
                }
            },
            {
                "query": "آیا می‌توانم همزمان با بایگانی فاکتورها، گزارش‌های مالی را تولید کرده و تنظیمات سیستم را تغییر دهم؟",
                "expected": {
                    "intent": "factual",
                    "needs_rag": True,
                    "complexity": "complex"
                }
            },
            {
                "query": "مراحل کامل از ثبت محصول تا تولید گزارش نهایی شامل چه گام‌هایی است؟",
                "expected": {
                    "intent": "factual",
                    "needs_rag": True,
                    "complexity": "complex"
                }
            },
            {
                "query": "چطور می‌توانم ابتدا کاربران را مدیریت کنم، سپس محصولات را دسته‌بندی نموده و در نهایت آمار فروش را تحلیل نمایم؟",
                "expected": {
                    "intent": "factual",
                    "needs_rag": True,
                    "complexity": "complex"
                }
            },

            # سوالات متوسط - ۵ کیس
            {
                "query": "مراحل بایگانی فاکتور خرید به چه صورت است؟",
                "expected": {
                    "intent": "factual",
                    "needs_rag": True,
                    "complexity": "moderate"
                }
            },
            {
                "query": "چگونه می‌توانم گزارش فروش ماهانه تولید کنم؟",
                "expected": {
                    "intent": "factual",
                    "needs_rag": True,
                    "complexity": "moderate"
                }
            },
            {
                "query": "روش‌های مختلف پشتیبان‌گیری از داده‌ها چیست؟",
                "expected": {
                    "intent": "factual",
                    "needs_rag": True,
                    "complexity": "moderate"
                }
            },
            {
                "query": "مراحل تنظیم دسترسی کاربران به چه صورت است؟",
                "expected": {
                    "intent": "factual",
                    "needs_rag": True,
                    "complexity": "moderate"
                }
            },
            {
                "query": "چطور می‌توانم محصولات را دسته‌بندی کنم؟",
                "expected": {
                    "intent": "factual",
                    "needs_rag": True,
                    "complexity": "moderate"
                }
            },

            # سوالات مرزی - ۵ کیس
            {
                "query": "سلام، ممنون",
                "expected": {
                    "intent": "conversational",
                    "needs_rag": False,
                    "complexity": "simple"
                }
            },
            {
                "query": "این محصول چقدره؟",
                "expected": {
                    "intent": "factual",
                    "needs_rag": True,
                    "complexity": "simple"
                }
            },
            {
                "query": "چطور می‌توانم فاکتور را بایگانی کنم و گزارش تولید کنم؟",
                "expected": {
                    "intent": "factual",
                    "needs_rag": True,
                    "complexity": "moderate"
                }
            },
            {
                "query": "سلام، چطور می‌توانم فاکتور را بایگانی کنم و گزارش تولید کنم؟",
                "expected": {
                    "intent": "mixed",
                    "needs_rag": True,
                    "complexity": "moderate"
                }
            },
            {
                "query": "آیا امکان بایگانی فاکتور و تولید گزارش همزمان وجود دارد؟",
                "expected": {
                    "intent": "factual",
                    "needs_rag": True,
                    "complexity": "moderate"
                }
            }
        ]

    async def evaluate(self) -> Dict[str, Any]:
        """اجرای ارزیابی کامل"""
        logger.info("🚀 شروع ارزیابی تحلیلگر سوالات...")

        results = []
        total_cases = len(self.test_cases)

        for i, test_case in enumerate(self.test_cases, 1):
            logger.info(f"📊 ارزیابی کیس {i}/{total_cases}: {test_case['query'][:50]}...")

            try:
                # اجرای تحلیل
                result = await query_analyzer.analyze(test_case["query"])

                # تبدیل به dict برای مقایسه
                result_dict = result.model_dump()

                # ارزیابی دقت
                accuracy = self._calculate_accuracy(result_dict, test_case["expected"])

                results.append({
                    "query": test_case["query"],
                    "expected": test_case["expected"],
                    "actual": result_dict,
                    "accuracy": accuracy,
                    "success": True
                })

            except Exception as e:
                logger.error(f"❌ خطا در ارزیابی کیس {i}: {e}")
                results.append({
                    "query": test_case["query"],
                    "expected": test_case["expected"],
                    "actual": None,
                    "accuracy": 0.0,
                    "success": False,
                    "error": str(e)
                })

        # محاسبه آمار کلی
        stats = self._calculate_stats(results)

        logger.info("✅ ارزیابی کامل شد")
        logger.info(f"📈 دقت کلی: {stats['overall_accuracy']:.2%}")
        logger.info(f"🎯 دقت intent: {stats['intent_accuracy']:.2%}")
        logger.info(f"🔍 دقت needs_rag: {stats['rag_accuracy']:.2%}")
        logger.info(f"⚡ دقت complexity: {stats['complexity_accuracy']:.2%}")

        return {
            "stats": stats,
            "results": results,
            "total_cases": total_cases
        }

    def _calculate_accuracy(self, actual: Dict[str, Any], expected: Dict[str, Any]) -> float:
        """محاسبه دقت برای یک کیس تست"""
        scores = []

        # دقت intent
        if actual.get("intent") == expected.get("intent"):
            scores.append(1.0)
        else:
            scores.append(0.0)

        # دقت needs_rag
        if actual.get("needs_rag") == expected.get("needs_rag"):
            scores.append(1.0)
        else:
            scores.append(0.0)

        # دقت complexity
        if actual.get("complexity") == expected.get("complexity"):
            scores.append(1.0)
        else:
            scores.append(0.0)

        return sum(scores) / len(scores)

    def _calculate_stats(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """محاسبه آمار کلی"""
        successful_results = [r for r in results if r["success"]]

        if not successful_results:
            return {
                "overall_accuracy": 0.0,
                "intent_accuracy": 0.0,
                "rag_accuracy": 0.0,
                "complexity_accuracy": 0.0,
                "success_rate": 0.0
            }

        # دقت کلی
        overall_accuracy = sum(r["accuracy"] for r in successful_results) / len(successful_results)

        # دقت هر بخش
        intent_correct = sum(1 for r in successful_results
                           if r["actual"]["intent"] == r["expected"]["intent"])
        rag_correct = sum(1 for r in successful_results
                         if r["actual"]["needs_rag"] == r["expected"]["needs_rag"])
        complexity_correct = sum(1 for r in successful_results
                               if r["actual"]["complexity"] == r["expected"]["complexity"])

        total_successful = len(successful_results)

        return {
            "overall_accuracy": overall_accuracy,
            "intent_accuracy": intent_correct / total_successful,
            "rag_accuracy": rag_correct / total_successful,
            "complexity_accuracy": complexity_correct / total_successful,
            "success_rate": len(successful_results) / len(results)
        }

    def save_results(self, evaluation_results: Dict[str, Any], output_file: str = "evaluation_results.json"):
        """ذخیره نتایج ارزیابی"""
        output_path = Path(__file__).parent / output_file

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(evaluation_results, f, ensure_ascii=False, indent=2)

        logger.info(f"💾 نتایج ارزیابی در {output_path} ذخیره شد")


async def main():
    """تابع اصلی"""
    evaluator = QueryAnalyzerEvaluator()

    try:
        results = await evaluator.evaluate()
        evaluator.save_results(results)

        # نمایش خلاصه
        stats = results["stats"]
        print("\n" + "="*50)
        print("📊 نتایج ارزیابی تحلیلگر سوالات")
        print("="*50)
        print(f"دقت کلی: {stats['overall_accuracy']:.2%}")
        print(f"دقت تشخیص هدف: {stats['intent_accuracy']:.2%}")
        print(f"دقت تشخیص نیاز به RAG: {stats['rag_accuracy']:.2%}")
        print(f"دقت تشخیص پیچیدگی: {stats['complexity_accuracy']:.2%}")
        print(f"نرخ موفقیت: {stats['success_rate']:.2%}")
        print(f"کل کیس‌های تست: {results['total_cases']}")

    except Exception as e:
        logger.error(f"❌ خطا در اجرای ارزیابی: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())