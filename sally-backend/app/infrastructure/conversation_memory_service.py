# conversation_memory_service.py

"""
Conversation Memory Service
===========================

این سرویس مسئولیت مدیریت حافظه مکالمات را بر عهده دارد:
- Conversation history formatting
- Context window management
- Message filtering and prioritization
- Memory optimization and cleanup
- Support for different conversation formats

Features:
- Efficient conversation history formatting
- Context window size optimization
- Message filtering based on relevance
- Memory usage optimization
- Support for multiple conversation formats
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from langchain.schema import HumanMessage, AIMessage, BaseMessage
from langchain.memory import ConversationBufferWindowMemory

from app.core.logging_config import get_logger
from app.core.config import settings

logger = get_logger(__name__)


class ConversationMemoryService:
    """
    Service for managing conversation memory and history
    
    این سرویس مسئولیت‌های زیر را بر عهده دارد:
    - فرمت‌بندی تاریخچه مکالمات
    - مدیریت پنجره بافت (context window)
    - فیلتر کردن پیام‌ها بر اساس اهمیت
    - بهینه‌سازی استفاده از حافظه
    - پشتیبانی از فرمت‌های مختلف مکالمه
    """
    
    def __init__(self, max_history_length: int = None, max_context_length: int = None):
        """
        مقداردهی اولیه سرویس حافظه مکالمه
        
        Args:
            max_history_length: حداکثر تعداد پیام‌های تاریخچه
            max_context_length: حداکثر طول بافت (به کاراکتر)
        """
        # Use settings values if not provided, with fallbacks
        self.max_history_length = max_history_length or getattr(settings, 'agentic_history_messages_count', 20)
        self.max_context_length = max_context_length or 4000
        
        logger.debug(f"🧠 ConversationMemoryService initialized (max_history: {self.max_history_length}, max_context: {self.max_context_length})")
    
    def format_history_for_prompt(self, conversation_history: List[Dict[str, str]], max_messages: Optional[int] = None) -> str:
        """
        فرمت‌بندی تاریخچه مکالمه برای استفاده در پرامپت
        
        Args:
            conversation_history: لیست تاریخچه مکالمات
            max_messages: حداکثر تعداد پیام‌ها (اختیاری)
        
        Returns:
            str: تاریخچه مکالمه فرمت شده
        """
        if not conversation_history:
            logger.debug("📚 No conversation history provided")
            return "هیچ تاریخچه‌ای موجود نیست. این اولین پیام است.\n\n"
        
        # محدود کردن تعداد پیام‌ها
        max_messages = max_messages or self.max_history_length
        recent_messages = conversation_history[-max_messages:]
        
        logger.debug(f"📚 Formatting conversation history: {len(recent_messages)} messages (from {len(conversation_history)} total)")
        
        formatted_history = "**تاریخچه مکالمه:**\n"
        
        for i, msg in enumerate(recent_messages, 1):
            # پشتیبانی از فرمت‌های مختلف ورودی
            role = self._extract_role(msg)
            content = self._extract_content(msg)
            
            if role and content:
                role_fa = self._translate_role(role)
                formatted_history += f"{i}. {role_fa}: {content}\n"
            else:
                logger.debug(f"⚠️ Invalid message format at index {i}: {msg}")
        
        formatted_history += "\n"
        
        logger.debug(f"✅ Formatted history length: {len(formatted_history)} characters")
        return formatted_history
    
    def _extract_role(self, message: Any) -> Optional[str]:
        """
        استخراج نقش پیام از فرمت‌های مختلف
        
        Args:
            message: پیام (می‌تواند tuple, dict, یا object باشد)
        
        Returns:
            Optional[str]: نقش پیام
        """
        if isinstance(message, tuple) and len(message) >= 2:
            return message[0]  # فرمت: ('user', 'content')
        elif isinstance(message, dict):
            return message.get("role")  # فرمت: {'role': 'user', 'content': 'content'}
        elif hasattr(message, 'role'):
            return message.role  # فرمت: object with role attribute
        elif hasattr(message, 'sender_type'):
            return message.sender_type  # فرمت: object with sender_type attribute
        
        return None
    
    def _extract_content(self, message: Any) -> Optional[str]:
        """
        استخراج محتوای پیام از فرمت‌های مختلف
        
        Args:
            message: پیام (می‌تواند tuple, dict، یا object باشد)
        
        Returns:
            Optional[str]: محتوای پیام
        """
        if isinstance(message, tuple) and len(message) >= 2:
            return message[1]  # فرمت: ('user', 'content')
        elif isinstance(message, dict):
            return message.get("content")  # فرمت: {'role': 'user', 'content': 'content'}
        elif hasattr(message, 'content'):
            return message.content  # فرمت: object with content attribute
        elif hasattr(message, 'message'):
            return message.message  # فرمت: object with message attribute
        
        return None
    
    def _translate_role(self, role: str) -> str:
        """
        ترجمه نقش پیام به فارسی
        
        Args:
            role: نقش پیام به انگلیسی
        
        Returns:
            str: نقش پیام به فارسی
        """
        role_mapping = {
            "user": "کاربر",
            "assistant": "سالی",
            "system": "سیستم",
            "ai": "سالی",
            "customer": "مشتری",
            "admin": "ادمین",
            "super_admin": "ادمین ارشد",
            "guest": "مهمان"
        }
        
        return role_mapping.get(role.lower(), role)
    
    def optimize_context_window(self, context: str, conversation_history: List[Dict[str, str]], query: str) -> Tuple[str, List[Dict[str, str]]]:
        """
        بهینه‌سازی پنجره بافت برای جلوگیری از overflow
        
        Args:
            context: بافت فعلی
            conversation_history: تاریخچه مکالمه
            query: سوال کاربر
        
        Returns:
            tuple: (context_optimized, history_optimized)
        """
        # محاسبه طول کل
        total_length = len(context) + len(query)
        if conversation_history:
            history_text = self.format_history_for_prompt(conversation_history)
            total_length += len(history_text)
        
        logger.debug(f"📏 Total context length: {total_length} characters (max: {self.max_context_length})")
        
        if total_length <= self.max_context_length:
            logger.debug("✅ Context is within limits")
            return context, conversation_history
        
        # بهینه‌سازی با کاهش طول‌ها
        optimized_context = self._optimize_text_length(context, self.max_context_length // 2)
        remaining_length = self.max_context_length // 2
        
        # بهینه‌سازی تاریخچه مکالمه
        optimized_history = self._optimize_history_length(conversation_history, remaining_length)
        
        logger.debug(f"🔧 Context optimized: {len(context)} → {len(optimized_context)}")
        logger.debug(f"🔧 History optimized: {len(conversation_history)} → {len(optimized_history)}")
        
        return optimized_context, optimized_history
    
    def _optimize_text_length(self, text: str, max_length: int) -> str:
        """
        بهینه‌سازی طول متن
        
        Args:
            text: متن اصلی
            max_length: حداکثر طول مجاز
        
        Returns:
            str: متن بهینه‌سازی شده
        """
        if len(text) <= max_length:
            return text
        
        # ساده‌ترین راه: برش متن از انتها
        optimized_text = text[:max_length]
        
        # اطمینان از اینکه متن در یک کلمه تمام نمی‌شود
        last_space = optimized_text.rfind(' ')
        if last_space > max_length * 0.9:  # اگر در 90% آخر فضا باشد
            optimized_text = optimized_text[:last_space]
        
        logger.debug(f"🔧 Text optimized: {len(text)} → {len(optimized_text)}")
        return optimized_text
    
    def _optimize_history_length(self, conversation_history: List[Dict[str, str]], max_length: int) -> List[Dict[str, str]]:
        """
        بهینه‌سازی طول تاریخچه مکالمه
        
        Args:
            conversation_history: تاریخچه اصلی
            max_length: حداکثر طول مجاز (به کاراکتر)
        
        Returns:
            List[Dict[str, str]]: تاریخچه بهینه‌سازی شده
        """
        if not conversation_history:
            return []
        
        # شروع از پیام‌های جدیدتر و اضافه کردن به عقب
        optimized_history = []
        current_length = 0
        
        for msg in reversed(conversation_history):
            if current_length >= max_length:
                break
            
            msg_content = self._extract_content(msg) or ""
            msg_length = len(msg_content)
            
            if current_length + msg_length <= max_length:
                optimized_history.insert(0, msg)
                current_length += msg_length
            else:
                # اضافه کردن بخشی از پیام
                remaining_space = max_length - current_length
                partial_content = msg_content[:remaining_space]
                
                partial_msg = msg.copy() if isinstance(msg, dict) else list(msg)
                if isinstance(partial_msg, dict):
                    partial_msg["content"] = partial_content
                else:
                    partial_msg[1] = partial_content
                
                optimized_history.insert(0, partial_msg)
                break
        
        return optimized_history
    
    def filter_conversation_by_relevance(self, conversation_history: List[Dict[str, str]], query: str, min_relevance_score: float = 0.3) -> List[Dict[str, str]]:
        """
        فیلتر کردن مکالمات بر اساس ارتباط با سوال فعلی
        
        Args:
            conversation_history: تاریخچه مکالمه
            query: سوال فعلی کاربر
            min_relevance_score: حداقل امتیاز ارتباط
        
        Returns:
            List[Dict[str, str]]: مکالمات مرتبط
        """
        if not conversation_history:
            return []
        
        # ساده‌ترین پیاده‌سازی: استفاده از کلمات کلیدی مشترک
        query_words = set(query.lower().split())
        relevant_messages = []
        
        for msg in conversation_history:
            content = self._extract_content(msg) or ""
            content_words = set(content.lower().split())
            
            # محاسبه امتیاز ارتباط بر اساس کلمات مشترک
            common_words = query_words.intersection(content_words)
            relevance_score = len(common_words) / max(len(query_words), 1)
            
            if relevance_score >= min_relevance_score:
                relevant_messages.append(msg)
                logger.debug(f"🎯 Message relevant (score: {relevance_score:.2f}): {content[:50]}...")
            else:
                logger.debug(f"⚠️ Message not relevant (score: {relevance_score:.2f}): {content[:50]}...")
        
        logger.debug(f"🔍 Filtered conversation: {len(conversation_history)} → {len(relevant_messages)} relevant messages")
        return relevant_messages
    
    def get_conversation_summary(self, conversation_history: List[Dict[str, str]], max_summary_length: int = 500) -> str:
        """
        ایجاد خلاصه از مکالمه
        
        Args:
            conversation_history: تاریخچه مکالمه
            max_summary_length: حداکثر طول خلاصه
        
        Returns:
            str: خلاصه مکالمه
        """
        if not conversation_history:
            return "هیچ مکالمه‌ای وجود ندارد."
        
        # ساده‌ترین پیاده‌سازی: ترکیب پیام‌های کلیدی
        key_messages = []
        total_messages = len(conversation_history)
        
        # انتخاب پیام‌های کلیدی (هر 3 پیام یک پیام کلیدی)
        for i in range(0, total_messages, max(1, total_messages // 5)):
            msg = conversation_history[i]
            content = self._extract_content(msg) or ""
            role = self._translate_role(self._extract_role(msg) or "")
            
            if content:
                key_messages.append(f"{role}: {content[:100]}...")
        
        summary = "خلاصه مکالمه:\n" + "\n".join(key_messages)
        
        if len(summary) > max_summary_length:
            summary = summary[:max_summary_length] + "..."
        
        logger.debug(f"📝 Generated conversation summary: {len(summary)} characters")
        return summary
    
    def cleanup_old_messages(self, conversation_history: List[Dict[str, str]], max_age_hours: int = 24) -> List[Dict[str, str]]:
        """
        پاک کردن پیام‌های قدیمی
        
        Args:
            conversation_history: تاریخچه مکالمه
            max_age_hours: حداکثر سن پیام‌ها (به ساعت)
        
        Returns:
            List[Dict[str, str]]: تاریخچه تمیز شده
        """
        if not conversation_history:
            return []
        
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        cleaned_history = []
        
        for msg in conversation_history:
            # بررسی سن پیام (اگر اطلاعات زمانی موجود باشد)
            if hasattr(msg, 'created_at'):
                msg_time = msg.created_at
                if msg_time >= cutoff_time:
                    cleaned_history.append(msg)
            else:
                # اگر اطلاعات زمانی موجود نباشد، پیام را نگه می‌داریم
                cleaned_history.append(msg)
        
        removed_count = len(conversation_history) - len(cleaned_history)
        if removed_count > 0:
            logger.debug(f"🧹 Cleaned up {removed_count} old messages")
        
        return cleaned_history
    
    def get_memory_usage_stats(self, conversation_history: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        دریافت آمار استفاده از حافظه
        
        Args:
            conversation_history: تاریخچه مکالمه
        
        Returns:
            Dict[str, Any]: آمار حافظه
        """
        if not conversation_history:
            return {
                "total_messages": 0,
                "total_characters": 0,
                "average_message_length": 0,
                "memory_usage_mb": 0
            }
        
        total_characters = sum(len(self._extract_content(msg) or "") for msg in conversation_history)
        average_length = total_characters / len(conversation_history)
        
        # تخمین استفاده از حافظه (به مگابایت)
        memory_usage_mb = (total_characters * 2) / (1024 * 1024)  # فرض 2 byte per character
        
        return {
            "total_messages": len(conversation_history),
            "total_characters": total_characters,
            "average_message_length": average_length,
            "memory_usage_mb": memory_usage_mb
        }


# Global instance
conversation_memory_service = ConversationMemoryService()


# 🔥 Enhanced LangChain Integration
class ConversationMemoryManager:
    """
    مدیر حافظه مکالمه با LangChain
    
    این کلاس 10 پیام آخر را در حافظه نگه می‌دارد (5 تبادل گفتگو)
    و آن‌ها را به فرمت مناسب برای LangChain تبدیل می‌کند.
    """
    
    def __init__(self, max_messages: int = None):
        """
        Args:
            max_messages: تعداد پیام‌های نگهداری شده (پیش‌فرض: از settings یا 10)
        """
        # Use settings value if not provided
        if max_messages is None:
            max_messages = getattr(settings, 'agentic_history_messages_count', 10) * 2
        
        self.max_messages = max_messages
        # استفاده از ConversationBufferWindowMemory برای نگهداری تعداد محدودی پیام
        self.memory = ConversationBufferWindowMemory(
            k=max_messages // 2,  # تعداد exchanges (هر exchange = user + assistant)
            return_messages=True,
            memory_key="chat_history"
        )
        logger.info(f"🧠 Conversation Memory initialized with max {max_messages} messages")
    
    def add_user_message(self, content: str):
        """
        اضافه کردن پیام کاربر به حافظه
        
        Args:
            content: محتوای پیام کاربر
        """
        self.memory.chat_memory.add_user_message(content)
        logger.debug(f"👤 User message added to memory: {content[:50]}...")
    
    def add_ai_message(self, content: str):
        """
        اضافه کردن پیام AI به حافظه
        
        Args:
            content: محتوای پیام AI
        """
        self.memory.chat_memory.add_ai_message(content)
        logger.debug(f"🤖 AI message added to memory: {content[:50]}...")
    
    def load_history_from_list(self, messages: List[Dict[str, str]]):
        """
        بارگذاری تاریخچه از لیست پیام‌ها
        
        Args:
            messages: لیست پیام‌ها به فرمت [{"role": "user"/"assistant", "content": "..."}]
        """
        # پاک کردن حافظه فعلی
        self.memory.clear()
        
        # اضافه کردن پیام‌های جدید (فقط 10 تا آخر)
        recent_messages = messages[-self.max_messages:] if len(messages) > self.max_messages else messages
        
        for msg in recent_messages:
            if msg["role"] == "user":
                self.memory.chat_memory.add_user_message(msg["content"])
            elif msg["role"] == "assistant":
                self.memory.chat_memory.add_ai_message(msg["content"])
        
        logger.info(f"📚 Loaded {len(recent_messages)} messages into memory")
    
    def get_messages(self) -> List[BaseMessage]:
        """
        دریافت پیام‌های موجود در حافظه به فرمت LangChain
        
        Returns:
            لیست پیام‌های LangChain (HumanMessage, AIMessage)
        """
        return self.memory.chat_memory.messages
    
    def get_formatted_history(self, format_type: str = "text") -> str:
        """
        دریافت تاریخچه به فرمت متنی
        
        Args:
            format_type: نوع فرمت ("text", "markdown")
            
        Returns:
            رشته متنی تاریخچه مکالمه
        """
        messages = self.get_messages()
        
        if not messages:
            return "هیچ تاریخچه‌ای موجود نیست. این اولین پیام است.\n\n"
        
        history_text = "\n**تاریخچه مکالمه:**\n"
        
        for msg in messages:
            if isinstance(msg, HumanMessage):
                role_fa = "کاربر"
            elif isinstance(msg, AIMessage):
                role_fa = "سالی"
            else:
                role_fa = "سیستم"
            
            if format_type == "markdown":
                history_text += f"**{role_fa}:** {msg.content}\n\n"
            else:
                history_text += f"{role_fa}: {msg.content}\n"
        
        history_text += "\n"
        return history_text
    
    def get_history_dict_list(self) -> List[Dict[str, str]]:
        """
        دریافت تاریخچه به فرمت لیست دیکشنری
        
        Returns:
            لیست پیام‌ها به فرمت [{"role": "user"/"assistant", "content": "..."}]
        """
        messages = self.get_messages()
        history_list = []
        
        for msg in messages:
            if isinstance(msg, HumanMessage):
                history_list.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                history_list.append({"role": "assistant", "content": msg.content})
        
        return history_list
    
    def clear(self):
        """پاک کردن حافظه"""
        self.memory.clear()
        logger.info("🧹 Memory cleared")
    
    def get_message_count(self) -> int:
        """دریافت تعداد پیام‌های موجود در حافظه"""
        return len(self.memory.chat_memory.messages)
    
    def is_empty(self) -> bool:
        """بررسی خالی بودن حافظه"""
        return len(self.memory.chat_memory.messages) == 0
    
    def summarize_if_needed(self) -> Optional[str]:
        """
        خلاصه‌سازی گفتگو در صورت طولانی بودن
        
        این متد در آینده می‌تواند با LLM خلاصه‌سازی کند
        Returns:
            خلاصه گفتگو (در صورت نیاز)
        """
        if self.get_message_count() >= self.max_messages:
            logger.info("📝 Conversation is getting long, might need summarization")
            # TODO: پیاده‌سازی خلاصه‌سازی با LLM
            return None
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        تبدیل حافظه به دیکشنری برای ذخیره‌سازی
        
        Returns:
            دیکشنری شامل تمام پیام‌ها
        """
        return {
            "max_messages": self.max_messages,
            "messages": self.get_history_dict_list(),
            "message_count": self.get_message_count()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationMemoryManager":
        """
        ساخت instance از دیکشنری
        
        Args:
            data: دیکشنری حاوی اطلاعات حافظه
            
        Returns:
            instance جدید ConversationMemoryManager
        """
        manager = cls(max_messages=data.get("max_messages", 10))
        if "messages" in data:
            manager.load_history_from_list(data["messages"])
        return manager
    
    def __repr__(self) -> str:
        return f"<ConversationMemoryManager: {self.get_message_count()} messages>"
    
    def __len__(self) -> int:
        return self.get_message_count()


# 🔥 Helper Functions

def create_memory_from_messages(messages: List[Dict[str, str]], max_messages: int = 10) -> ConversationMemoryManager:
    """
    ساخت سریع ConversationMemoryManager از لیست پیام‌ها
    
    Args:
        messages: لیست پیام‌ها به فرمت [{"role": "user"/"assistant", "content": "..."}]
        max_messages: تعداد حداکثر پیام‌ها
        
    Returns:
        instance آماده ConversationMemoryManager
    """
    memory = ConversationMemoryManager(max_messages=max_messages)
    memory.load_history_from_list(messages)
    return memory