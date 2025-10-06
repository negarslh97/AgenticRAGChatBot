"""
اسکریپت ارزیابی دقت سیستم RAG

این اسکریپت دقت سیستم را با تست‌های مختلف ارزیابی می‌کند:
1. Retrieval accuracy (آیا documents صحیح پیدا می‌شوند؟)
2. Answer quality (آیا پاسخ‌ها صحیح و کامل هستند؟)
3. Confidence calibration (آیا confidence با کیفیت واقعی تطابق دارد؟)

نحوه استفاده:
    python scripts/evaluate_rag_accuracy.py
"""

import asyncio
import sys
from pathlib import Path
from typing import List, Dict, Any
import json
from datetime import datetime
import motor.motor_asyncio
from beanie import init_beanie

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.infrastructure.rag_service import SimpleRAGService
from app.core.logging_config import get_logger
from app.domain.entities import (
    KnowledgeBaseArticle, 
    Admin, 
    Customer, 
    GuestSession,
    Role, 
    Conversation, 
    Message,
    Ticket,
    Category
)
from app.core.config import settings

logger = get_logger(__name__)


# 📋 Test Cases - سوالاتی که پاسخشان را می‌دانیم
TEST_CASES = [
    {
        "id": 1,
        "query": "مدل فروش چیست؟",
        "category": "تعریف",
        "difficulty": "ساده",
        "expected_keywords": ["مدل فروش", "فاکتور", "تنظیمات"],
        "expected_articles": ["استقرار نرم افزار مدیریت فروش"],
        "min_rerank_score": 0.7,
        "min_confidence": 0.80
    },
    {
        "id": 2,
        "query": "چگونه مدل فروش تعریف کنم؟",
        "category": "راهنما",
        "difficulty": "متوسط",
        "expected_keywords": ["اطلاعات پایه", "تعریف", "فعال", "پیش فرض"],
        "expected_articles": ["استقرار نرم افزار مدیریت فروش"],
        "min_rerank_score": 0.6,
        "min_confidence": 0.75
    },
    # {
    #     "id": 3,
    #     "query": "تفاوت فاکتور فروش و پیش فاکتور چیست؟",
    #     "category": "مقایسه",
    #     "difficulty": "متوسط",
    #     "expected_keywords": ["فاکتور", "پیش فاکتور"],
    #     "expected_articles": ["استقرار نرم افزار مدیریت فروش"],
    #     "min_rerank_score": 0.5,
    #     "min_confidence": 0.70
    # },
    # {
    #     "id": 4,
    #     "query": "در مورد مدل های فروش توضیح بده",
    #     "category": "توضیح کامل",
    #     "difficulty": "پیچیده",
    #     "expected_keywords": ["مدل فروش", "معین", "بازاریاب", "نرخ فروش"],
    #     "expected_articles": ["استقرار نرم افزار مدیریت فروش"],
    #     "min_rerank_score": 0.5,
    #     "min_confidence": 0.65
    # },
    # {
    #     "id": 5,
    #     "query": "قوانین مالیاتی 2025",
    #     "category": "خارج از دامنه",
    #     "difficulty": "نامرتبط",
    #     "expected_keywords": [],
    #     "expected_articles": [],
    #     "min_rerank_score": 0.0,
    #     "min_confidence": 0.0,
    #     "should_fail": True  # انتظار داریم نتیجه خوبی ندهد
    # }
]


class RAGEvaluator:
    """کلاس ارزیابی سیستم RAG"""
    
    def __init__(self):
        self.rag_service = SimpleRAGService()
        self.results = []
        
    async def evaluate_retrieval(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """
        ارزیابی کیفیت بازیابی documents
        """
        query = test_case["query"]
        
        # بازیابی documents
        docs = await self.rag_service.retrieve_relevant_documents(query, is_public_only=True)
        
        if not docs:
            return {
                "status": "no_results",
                "top_score": 0.0,
                "relevant_docs_found": 0,
                "expected_docs_found": 0
            }
        
        # بررسی scores
        top_score = docs[0].get("score", 0) if docs else 0
        high_quality_docs = sum(1 for d in docs if d.get("score", 0) >= 0.6)
        
        # بررسی آیا مقالات مورد انتظار پیدا شده‌اند
        found_articles = set()
        for doc in docs[:5]:  # فقط top 5
            title = doc.get("article_title", "")
            found_articles.add(title)
        
        expected_found = 0
        for expected in test_case.get("expected_articles", []):
            if any(expected.lower() in article.lower() for article in found_articles):
                expected_found += 1
        
        return {
            "status": "success",
            "top_score": round(top_score, 3),
            "avg_score": round(sum(d.get("score", 0) for d in docs[:10]) / min(len(docs), 10), 3),
            "total_docs": len(docs),
            "high_quality_docs": high_quality_docs,
            "relevant_docs_found": len(found_articles),
            "expected_docs_found": expected_found,
            "expected_docs_total": len(test_case.get("expected_articles", [])),
            "top_articles": list(found_articles)[:3]
        }
    
    async def evaluate_answer(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """
        ارزیابی کیفیت پاسخ تولید شده
        """
        query = test_case["query"]
        
        try:
            # تولید پاسخ
            result = await self.rag_service.generate_response(query)
            
            answer = result.get("response", "")
            confidence = result.get("confidence", 0.0)
            sources = result.get("sources", [])
            confidence_analysis = result.get("confidence_analysis", {})
            
            # بررسی کلمات کلیدی
            keywords_found = 0
            for keyword in test_case.get("expected_keywords", []):
                if keyword.lower() in answer.lower():
                    keywords_found += 1
            
            # بررسی طول پاسخ
            answer_length = len(answer)
            
            return {
                "status": "success",
                "answer_length": answer_length,
                "confidence": confidence,
                "confidence_level": confidence_analysis.get("confidence_level", ""),
                "keywords_found": keywords_found,
                "keywords_total": len(test_case.get("expected_keywords", [])),
                "sources_count": len(sources),
                "answer_preview": answer[:200] + "..." if len(answer) > 200 else answer
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def evaluate_test_case(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """
        ارزیابی کامل یک test case
        """
        print(f"\n{'='*80}")
        print(f"🧪 Test Case #{test_case['id']}: {test_case['query']}")
        print(f"   Category: {test_case['category']} | Difficulty: {test_case['difficulty']}")
        print(f"{'='*80}")
        
        # 1. ارزیابی Retrieval
        print("\n📊 Evaluating Retrieval...")
        retrieval_result = await self.evaluate_retrieval(test_case)
        
        # 2. ارزیابی Answer
        print("💬 Evaluating Answer...")
        answer_result = await self.evaluate_answer(test_case)
        
        # 3. محاسبه امتیاز کلی
        score = self._calculate_overall_score(test_case, retrieval_result, answer_result)
        
        # 4. تعیین Pass/Fail
        passed = self._determine_pass_fail(test_case, retrieval_result, answer_result, score)
        
        result = {
            "test_case": test_case,
            "retrieval": retrieval_result,
            "answer": answer_result,
            "overall_score": score,
            "passed": passed,
            "timestamp": datetime.now().isoformat()
        }
        
        # نمایش نتیجه
        self._print_result(result)
        
        return result
    
    def _calculate_overall_score(
        self, 
        test_case: Dict[str, Any],
        retrieval: Dict[str, Any],
        answer: Dict[str, Any]
    ) -> float:
        """
        محاسبه امتیاز کلی (0-100)
        """
        if test_case.get("should_fail"):
            # برای test cases که باید fail شوند، امتیاز معکوس
            # امتیاز بالا = خوب است که نتیجه ضعیف داده
            if retrieval.get("top_score", 0) < 0.3 and answer.get("confidence", 1.0) < 0.5:
                return 100  # خوب است که شناسایی کرد نمی‌داند
            else:
                return 0  # بد است که اعتماد به نفس بالا داشت
        
        score = 0.0
        
        # 40% از امتیاز: Retrieval Quality
        if retrieval.get("status") == "success":
            top_score = retrieval.get("top_score", 0)
            expected_found = retrieval.get("expected_docs_found", 0)
            expected_total = retrieval.get("expected_docs_total", 1)
            
            score += top_score * 30  # 30% برای top score
            score += (expected_found / expected_total) * 10  # 10% برای پیدا کردن مقالات صحیح
        
        # 40% از امتیاز: Answer Quality
        if answer.get("status") == "success":
            keywords_found = answer.get("keywords_found", 0)
            keywords_total = answer.get("keywords_total", 1)
            answer_length = answer.get("answer_length", 0)
            
            score += (keywords_found / keywords_total) * 20  # 20% برای کلمات کلیدی
            score += min(answer_length / 200, 1.0) * 20  # 20% برای طول پاسخ
        
        # 20% از امتیاز: Confidence Calibration
        confidence = answer.get("confidence", 0)
        expected_confidence = test_case.get("min_confidence", 0.5)
        
        if confidence >= expected_confidence:
            score += 20
        else:
            score += (confidence / expected_confidence) * 20
        
        return round(min(score, 100), 2)
    
    def _determine_pass_fail(
        self,
        test_case: Dict[str, Any],
        retrieval: Dict[str, Any],
        answer: Dict[str, Any],
        score: float
    ) -> bool:
        """
        تعیین Pass یا Fail
        """
        if test_case.get("should_fail"):
            # برای test cases نامرتبط، باید confidence پایین باشد
            return answer.get("confidence", 1.0) < 0.5
        
        # شرایط Pass:
        passed = True
        
        # 1. Retrieval score کافی باشد
        if retrieval.get("top_score", 0) < test_case.get("min_rerank_score", 0.5):
            passed = False
        
        # 2. Confidence کافی باشد
        if answer.get("confidence", 0) < test_case.get("min_confidence", 0.5):
            passed = False
        
        # 3. حداقل یک مقاله مورد انتظار پیدا شده باشد
        if test_case.get("expected_articles") and retrieval.get("expected_docs_found", 0) == 0:
            passed = False
        
        # 4. امتیاز کلی بالای 60 باشد
        if score < 60:
            passed = False
        
        return passed
    
    def _print_result(self, result: Dict[str, Any]):
        """
        نمایش نتیجه به صورت خوانا
        """
        retrieval = result["retrieval"]
        answer = result["answer"]
        passed = result["passed"]
        score = result["overall_score"]
        
        print(f"\n📈 Results:")
        print(f"   Overall Score: {score}/100")
        print(f"   Status: {'✅ PASSED' if passed else '❌ FAILED'}")
        
        print(f"\n   📊 Retrieval:")
        print(f"      Top Score: {retrieval.get('top_score', 0):.3f}")
        print(f"      High Quality Docs: {retrieval.get('high_quality_docs', 0)}")
        print(f"      Expected Docs Found: {retrieval.get('expected_docs_found', 0)}/{retrieval.get('expected_docs_total', 0)}")
        
        print(f"\n   💬 Answer:")
        print(f"      Length: {answer.get('answer_length', 0)} chars")
        print(f"      Confidence: {answer.get('confidence', 0):.2f} ({answer.get('confidence_level', '')})")
        print(f"      Keywords Found: {answer.get('keywords_found', 0)}/{answer.get('keywords_total', 0)}")
        
        if answer.get("answer_preview"):
            print(f"\n   Preview: {answer['answer_preview']}")
    
    async def run_evaluation(self, test_cases: List[Dict[str, Any]] = None):
        """
        اجرای تمام تست‌ها
        """
        if test_cases is None:
            test_cases = TEST_CASES
        
        print(f"\n{'='*80}")
        print(f"🚀 Starting RAG System Evaluation")
        print(f"   Total Test Cases: {len(test_cases)}")
        print(f"   Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}")
        
        results = []
        for test_case in test_cases:
            result = await self.evaluate_test_case(test_case)
            results.append(result)
            await asyncio.sleep(1)  # فاصله بین تست‌ها
        
        # خلاصه نتایج
        self._print_summary(results)
        
        # ذخیره نتایج
        self._save_results(results)
        
        return results
    
    def _print_summary(self, results: List[Dict[str, Any]]):
        """
        نمایش خلاصه نتایج
        """
        print(f"\n{'='*80}")
        print(f"📊 Evaluation Summary")
        print(f"{'='*80}")
        
        total = len(results)
        passed = sum(1 for r in results if r["passed"])
        failed = total - passed
        
        avg_score = sum(r["overall_score"] for r in results) / total if total > 0 else 0
        avg_confidence = sum(r["answer"].get("confidence", 0) for r in results) / total if total > 0 else 0
        avg_top_score = sum(r["retrieval"].get("top_score", 0) for r in results) / total if total > 0 else 0
        
        print(f"\n✅ Tests Passed: {passed}/{total} ({passed/total*100:.1f}%)")
        print(f"❌ Tests Failed: {failed}/{total} ({failed/total*100:.1f}%)")
        print(f"\n📈 Average Metrics:")
        print(f"   Overall Score: {avg_score:.2f}/100")
        print(f"   Confidence: {avg_confidence:.2f}")
        print(f"   Top Rerank Score: {avg_top_score:.3f}")
        
        # تفکیک بر اساس دشواری
        print(f"\n📊 By Difficulty:")
        difficulties = set(r["test_case"]["difficulty"] for r in results)
        for diff in difficulties:
            diff_results = [r for r in results if r["test_case"]["difficulty"] == diff]
            diff_passed = sum(1 for r in diff_results if r["passed"])
            print(f"   {diff}: {diff_passed}/{len(diff_results)} passed")
        
        # Failed tests
        if failed > 0:
            print(f"\n❌ Failed Tests:")
            for r in results:
                if not r["passed"]:
                    print(f"   - Test #{r['test_case']['id']}: {r['test_case']['query']}")
                    print(f"     Score: {r['overall_score']}/100")
                    print(f"     Confidence: {r['answer'].get('confidence', 0):.2f}")
    
    def _save_results(self, results: List[Dict[str, Any]]):
        """
        ذخیره نتایج در فایل
        """
        output_file = f"evaluation_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 Results saved to: {output_file}")


async def initialize_database():
    """
    Initialize MongoDB connection
    """
    print("🔗 Initializing database connection...")
    
    try:
        # Create Motor client
        client = motor.motor_asyncio.AsyncIOMotorClient(settings.database_url)
        
        # Get database
        db_name = settings.database_url.split("/")[-1] if "/" in settings.database_url else "SallyChatBot"
        database = client[db_name]
        
        # Initialize Beanie
        await init_beanie(
            database=database,
            document_models=[
                KnowledgeBaseArticle,
                Admin,
                Customer,
                GuestSession,
                Role,
                Conversation,
                Message,
                Ticket,
                Category
            ]
        )
        
        print("✅ Database initialized")
        return client
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        raise


async def main():
    """
    تابع اصلی
    """
    # Initialize database first
    db_client = None
    try:
        db_client = await initialize_database()
        
        # Run evaluation
        evaluator = RAGEvaluator()
        await evaluator.run_evaluation()
        
    except Exception as e:
        print(f"❌ Evaluation failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Close database connection
        if db_client:
            db_client.close()
            print("\n🔌 Database connection closed")


if __name__ == "__main__":
    asyncio.run(main())

