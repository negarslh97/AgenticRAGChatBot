#!/usr/bin/env python3
"""
Feedback Collector for Query Analyzer
مکانیزم جمع‌آوری بازخورد انسانی برای بهبود تحلیلگر سوالات
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

from app.utils.query_analyzer import QueryAnalysisResult

logger = logging.getLogger(__name__)


class FeedbackEntry:
    """ورودی بازخورد"""

    def __init__(self, query: str, original_result: QueryAnalysisResult,
                 corrected_result: Optional[QueryAnalysisResult] = None,
                 admin_id: Optional[str] = None, notes: Optional[str] = None):
        self.query = query
        self.original_result = original_result
        self.corrected_result = corrected_result
        self.admin_id = admin_id
        self.notes = notes
        self.timestamp = datetime.now()
        self.feedback_id = f"{int(self.timestamp.timestamp())}_{hash(query) % 10000}"

    def to_dict(self) -> Dict[str, Any]:
        """تبدیل به دیکشنری برای ذخیره"""
        return {
            "feedback_id": self.feedback_id,
            "query": self.query,
            "original_result": self.original_result.model_dump() if self.original_result else None,
            "corrected_result": self.corrected_result.model_dump() if self.corrected_result else None,
            "admin_id": self.admin_id,
            "notes": self.notes,
            "timestamp": self.timestamp.isoformat(),
            "is_corrected": self.corrected_result is not None
        }


class FeedbackCollector:
    """جمع‌آورنده بازخورد برای بهبود تحلیلگر"""

    def __init__(self, storage_file: str = "query_analyzer_feedback.json"):
        self.storage_file = Path(__file__).parent / storage_file
        self.feedback_entries: List[FeedbackEntry] = []
        self._load_feedback()

    def _load_feedback(self):
        """بارگذاری بازخوردهای ذخیره شده"""
        if self.storage_file.exists():
            try:
                with open(self.storage_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # تبدیل داده‌های ذخیره شده به FeedbackEntry
                    for entry_data in data.get("feedback_entries", []):
                        # بازسازی QueryAnalysisResult از داده‌ها
                        original_result = None
                        if entry_data.get("original_result"):
                            original_result = QueryAnalysisResult(**entry_data["original_result"])

                        corrected_result = None
                        if entry_data.get("corrected_result"):
                            corrected_result = QueryAnalysisResult(**entry_data["corrected_result"])

                        entry = FeedbackEntry(
                            query=entry_data["query"],
                            original_result=original_result,
                            corrected_result=corrected_result,
                            admin_id=entry_data.get("admin_id"),
                            notes=entry_data.get("notes")
                        )
                        entry.timestamp = datetime.fromisoformat(entry_data["timestamp"])
                        entry.feedback_id = entry_data["feedback_id"]

                        self.feedback_entries.append(entry)

                logger.info(f"✅ {len(self.feedback_entries)} ورودی بازخورد بارگذاری شد")

            except Exception as e:
                logger.error(f"❌ خطا در بارگذاری بازخورد: {e}")

    def _save_feedback(self):
        """ذخیره بازخوردهای جمع‌آوری شده"""
        try:
            data = {
                "feedback_entries": [entry.to_dict() for entry in self.feedback_entries],
                "last_updated": datetime.now().isoformat(),
                "total_entries": len(self.feedback_entries)
            }

            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            logger.info(f"💾 {len(self.feedback_entries)} ورودی بازخورد ذخیره شد")

        except Exception as e:
            logger.error(f"❌ خطا در ذخیره بازخورد: {e}")

    def add_feedback(self, query: str, original_result: QueryAnalysisResult,
                    corrected_result: Optional[QueryAnalysisResult] = None,
                    admin_id: Optional[str] = None, notes: Optional[str] = None) -> str:
        """
        اضافه کردن بازخورد جدید

        Args:
            query: سوال اصلی
            original_result: نتیجه تحلیل اصلی
            corrected_result: نتیجه اصلاح شده (اختیاری)
            admin_id: شناسه ادمین
            notes: یادداشت‌های اضافی

        Returns:
            feedback_id: شناسه بازخورد
        """
        entry = FeedbackEntry(query, original_result, corrected_result, admin_id, notes)
        self.feedback_entries.append(entry)
        self._save_feedback()

        logger.info(f"📝 بازخورد جدید اضافه شد: {entry.feedback_id}")
        return entry.feedback_id

    def get_feedback_stats(self) -> Dict[str, Any]:
        """دریافت آمار بازخورد"""
        total = len(self.feedback_entries)
        corrected = len([e for e in self.feedback_entries if e.corrected_result is not None])

        # آمار انواع خطا
        error_types = {
            "intent_errors": 0,
            "complexity_errors": 0,
            "rag_errors": 0
        }

        for entry in self.feedback_entries:
            if entry.corrected_result and entry.original_result:
                orig = entry.original_result
                corr = entry.corrected_result

                if orig.intent != corr.intent:
                    error_types["intent_errors"] += 1
                if orig.complexity != corr.complexity:
                    error_types["complexity_errors"] += 1
                if orig.needs_rag != corr.needs_rag:
                    error_types["rag_errors"] += 1

        return {
            "total_feedback": total,
            "corrected_feedback": corrected,
            "correction_rate": corrected / total if total > 0 else 0,
            "error_types": error_types,
            "most_recent": self.feedback_entries[-1].timestamp.isoformat() if self.feedback_entries else None
        }

    def get_uncorrected_feedback(self, limit: int = 10) -> List[Dict[str, Any]]:
        """دریافت بازخوردهای اصلاح نشده"""
        uncorrected = [e for e in self.feedback_entries if e.corrected_result is None]
        return [entry.to_dict() for entry in uncorrected[-limit:]]

    def get_training_data(self) -> List[Dict[str, Any]]:
        """دریافت داده‌های آموزشی از بازخوردهای اصلاح شده"""
        training_data = []

        for entry in self.feedback_entries:
            if entry.corrected_result:
                training_data.append({
                    "query": entry.query,
                    "expected_result": entry.corrected_result.model_dump(),
                    "original_result": entry.original_result.model_dump() if entry.original_result else None,
                    "feedback_id": entry.feedback_id
                })

        return training_data

    def export_for_fine_tuning(self, output_file: str = "fine_tuning_data.jsonl"):
        """اکسپورت داده‌ها برای fine-tuning مدل"""
        training_data = self.get_training_data()

        output_path = Path(__file__).parent / output_file

        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                for item in training_data:
                    # فرمت مناسب برای fine-tuning
                    fine_tune_entry = {
                        "messages": [
                            {
                                "role": "system",
                                "content": "شما یک تحلیلگر هوشمند سوالات هستید. سوال کاربر را تحلیل کرده و خروجی را در قالب JSON برگردانید."
                            },
                            {
                                "role": "user",
                                "content": item["query"]
                            },
                            {
                                "role": "assistant",
                                "content": json.dumps(item["expected_result"], ensure_ascii=False)
                            }
                        ]
                    }
                    f.write(json.dumps(fine_tune_entry, ensure_ascii=False) + '\n')

            logger.info(f"🎯 داده‌های fine-tuning در {output_path} ذخیره شد ({len(training_data)} نمونه)")

        except Exception as e:
            logger.error(f"❌ خطا در اکسپورت داده‌های fine-tuning: {e}")

    def clear_old_feedback(self, days: int = 30):
        """پاک کردن بازخوردهای قدیمی"""
        from datetime import timedelta

        cutoff_date = datetime.now() - timedelta(days=days)
        old_count = len(self.feedback_entries)

        self.feedback_entries = [
            entry for entry in self.feedback_entries
            if entry.timestamp > cutoff_date
        ]

        new_count = len(self.feedback_entries)
        removed = old_count - new_count

        if removed > 0:
            self._save_feedback()
            logger.info(f"🗑️ {removed} ورودی بازخورد قدیمی پاک شد")


# نمونه Singleton برای دسترسی آسان
feedback_collector = FeedbackCollector()