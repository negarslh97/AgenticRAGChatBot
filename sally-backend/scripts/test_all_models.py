#!/usr/bin/env python3
"""
تست جامع همه مدل‌های موجود در سیستم
برای بررسی عملکرد و پاسخگویی هر مدل به سوال "مدل فروش چیه؟"
"""

import asyncio
import json
import time
import logging
from typing import Dict, List, Any
from pathlib import Path

# تنظیمات لاگ
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# اضافه کردن مسیر پکیج‌ها
import sys
sys.path.append(str(Path(__file__).parent.parent))

from app.infrastructure.langchain_orchestrator import LangChainOrchestrator, RequestContext
from app.infrastructure.model_factory import ModelFactory, ModelConfig, ModelProvider, ModelType
from app.core.config import settings

class ModelTester:
    def __init__(self):
        self.orchestrator = LangChainOrchestrator()
        self.test_results = []
        
    async def test_model(self, model_id: str, model_name: str, provider: str) -> Dict[str, Any]:
        """تست یک مدل خاص با سوال استاندارد"""
        logger.info(f"🧪 Testing model: {model_id} ({model_name}) - Provider: {provider}")
        
        start_time = time.time()
        
        try:
            # ایجاد درخواست تست
            request_context = RequestContext(
                query="مدل فروش چیه؟",
                query_type="general",
                response_style="detailed",
                max_tokens=1000,
                streaming=False,
                custom_model=model_id
            )
            
            # پردازش درخواست
            result = await self.orchestrator.process_request(
                query="مدل فروش چیه؟",
                custom_model=model_id
            )
            
            processing_time = time.time() - start_time
            
            # تحلیل پاسخ
            response_analysis = self._analyze_response(result.content)
            
            test_result = {
                "model_id": model_id,
                "model_name": model_name,
                "provider": provider,
                "success": True,
                "processing_time": processing_time,
                "response_length": len(result.content),
                "tokens_used": result.tokens_used,
                "response_quality": response_analysis,
                "response_preview": result.content[:200] + "..." if len(result.content) > 200 else result.content,
                "full_response": result.content,
                "error": None,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
            logger.info(f"✅ Model {model_id} tested successfully in {processing_time:.2f}s")
            return test_result
            
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = str(e)
            
            logger.error(f"❌ Model {model_id} failed: {error_msg}")
            
            return {
                "model_id": model_id,
                "model_name": model_name,
                "provider": provider,
                "success": False,
                "processing_time": processing_time,
                "response_length": 0,
                "tokens_used": 0,
                "response_quality": None,
                "response_preview": None,
                "full_response": None,
                "error": error_msg,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
    
    def _analyze_response(self, response: str) -> Dict[str, Any]:
        """تحلیل کیفیت پاسخ"""
        analysis = {
            "length": len(response),
            "word_count": len(response.split()),
            "has_arabic": any('\u0600' <= char <= '\u06FF' for char in response),
            "has_english": any(char.isascii() for char in response),
            "has_numbers": any(char.isdigit() for char in response),
            "has_special_chars": any(not char.isalnum() and not char.isspace() for char in response),
            "quality_score": 0
        }
        
        # محاسبه امتیاز کیفیت
        score = 0
        
        # امتیاز طول پاسخ (50-1000 کلمه ایده‌آل)
        if 50 <= analysis["word_count"] <= 1000:
            score += 25
        elif analysis["word_count"] > 0:
            score += 10
        
        # امتیاز زبان فارسی
        if analysis["has_arabic"]:
            score += 25
        
        # امتیاز محتوایی (پاسخ واقعی به سوال)
        if any(keyword in response.lower() for keyword in ["فروش", "مدل", "business", "model", "revenue"]):
            score += 25
        
        # امتیاز ساختاری
        if analysis["has_special_chars"] and '.' in response:
            score += 15
        
        analysis["quality_score"] = min(score, 100)
        
        return analysis
    
    async def test_all_models(self) -> List[Dict[str, Any]]:
        """تست همه مدل‌های موجود"""
        logger.info("🚀 Starting comprehensive model testing...")
        
        # دریافت لیست مدل‌ها
        models = self.orchestrator.list_models()
        logger.info(f"📋 Found {len(models)} models to test")
        
        # تست هر مدل
        for model_info in models:
            # بررسی ساختار مدل
            if isinstance(model_info, dict):
                # اصلاح: factory از "name" استفاده می‌کند نه "id"
                model_id = model_info.get("name", model_info.get("id", "unknown"))
                model_name = model_info.get("name", model_info.get("model_name", "Unknown Model"))
                provider = model_info.get("provider", model_info.get("provider_name", "unknown"))
            else:
                # اگر model_info یک رشته است
                model_id = str(model_info)
                model_name = str(model_info)
                provider = "unknown"
            
            # تست مدل
            result = await self.test_model(model_id, model_name, provider)
            self.test_results.append(result)
            
            # کوچک تأخیر بین تست‌ها برای جلوگیری از محدودیت‌ها
            await asyncio.sleep(1)
        
        logger.info(f"✅ Completed testing {len(self.test_results)} models")
        return self.test_results
    
    def generate_report(self) -> str:
        """تولید گزارش جامع از نتایج تست"""
        if not self.test_results:
            return "No test results available"
        
        # محاسبات آماری
        total_models = len(self.test_results)
        successful_models = len([r for r in self.test_results if r["success"]])
        failed_models = total_models - successful_models
        
        avg_processing_time = sum(r["processing_time"] for r in self.test_results if r["success"]) / successful_models if successful_models > 0 else 0
        
        # گروه‌بندی بر اساس provider
        provider_stats = {}
        for result in self.test_results:
            provider = result["provider"]
            if provider not in provider_stats:
                provider_stats[provider] = {"total": 0, "successful": 0, "failed": 0}
            
            provider_stats[provider]["total"] += 1
            if result["success"]:
                provider_stats[provider]["successful"] += 1
            else:
                provider_stats[provider]["failed"] += 1
        
        # تولید گزارش
        report = f"""
# 📊 گزارش جامع تست مدل‌ها

## 📈 خلاصه آماری
- **تعداد کل مدل‌ها**: {total_models}
- **موفق**: {successful_models} ({successful_models/total_models*100:.1f}%)
- **ناموفق**: {failed_models} ({failed_models/total_models*100:.1f}%)
- **میانگین زمان پردازش**: {avg_processing_time:.2f} ثانیه

## 🏭 عملکرد بر اساس Provider
"""
        
        for provider, stats in provider_stats.items():
            success_rate = stats["successful"] / stats["total"] * 100
            report += f"- **{provider}**: {stats['successful']}/{stats['total']} موفق ({success_rate:.1f}%)\n"
        
        report += "\n## 🏆 بهترین مدل‌ها (بر اساس کیفیت و سرعت)\n"
        
        # مرتب‌سازی مدل‌های موفق بر اساس کیفیت و سرعت
        successful_results = [r for r in self.test_results if r["success"]]
        successful_results.sort(key=lambda x: (x["response_quality"]["quality_score"], -x["processing_time"]), reverse=True)
        
        for i, result in enumerate(successful_results[:10], 1):
            report += f"{i}. **{result['model_name']}** ({result['provider']})\n"
            report += f"   - امتیاز کیفیت: {result['response_quality']['quality_score']}/100\n"
            report += f"   - زمان پردازش: {result['processing_time']:.2f}s\n"
            report += f"   - طول پاسخ: {result['response_quality']['word_count']} کلمه\n"
            report += f"   - پیش‌نمایش: {result['response_preview']}\n\n"
        
        report += "## ❌ مدل‌های ناموفق\n"
        for result in self.test_results:
            if not result["success"]:
                report += f"- **{result['model_name']}** ({result['provider']}): {result['error']}\n"
        
        return report
    
    def save_results(self, filename: str = "model_test_results.json"):
        """ذخیره نتایج در فایل JSON"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.test_results, f, ensure_ascii=False, indent=2)
        logger.info(f"📄 Results saved to {filename}")

async def main():
    """اجرای تست جامع"""
    print("🚀 شروع تست جامع همه مدل‌ها...")
    print("📝 سوال تست: 'مدل فروش چیه؟'")
    print("=" * 60)
    
    tester = ModelTester()
    
    # اجرای تست
    results = await tester.test_all_models()
    
    # تولید گزارش
    report = tester.generate_report()
    print(report)
    
    # ذخیره نتایج
    tester.save_results()
    
    # نمایش بهترین مدل‌ها
    print("\n" + "=" * 60)
    print("🏆 بهترین مدل‌ها برای سوال 'مدل فروش چیه؟':")
    
    successful_results = [r for r in results if r["success"]]
    successful_results.sort(key=lambda x: x["response_quality"]["quality_score"], reverse=True)
    
    for i, result in enumerate(successful_results[:5], 1):
        print(f"{i}. {result['model_name']} ({result['provider']}) - امتیاز: {result['response_quality']['quality_score']}/100")

if __name__ == "__main__":
    asyncio.run(main())