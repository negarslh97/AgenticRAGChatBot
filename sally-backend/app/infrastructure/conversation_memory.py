"""
Conversation Memory Manager با استفاده از LangChain

این ماژول حافظه مکالمه را مدیریت می‌کند تا مدل بتواند بر اساس پیام‌های قبلی
پاسخ‌های بهتری ارائه دهد.

Features:
- نگهداری 10 پیام آخر (5 تبادل گفتگو)
- فرمت‌بندی مناسب برای LangChain
- خلاصه‌سازی هوشمند برای گفتگوهای طولانی
- پشتیبانی از streaming
"""

from typing import List, Dict, Optional, Any
from langchain.schema import HumanMessage, AIMessage, BaseMessage
from langchain.memory import ConversationBufferWindowMemory
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class ConversationMemoryManager:
    """
    مدیر حافظه مکالمه با LangChain
    
    این کلاس 10 پیام آخر را در حافظه نگه می‌دارد (5 تبادل گفتگو)
    و آن‌ها را به فرمت مناسب برای LangChain تبدیل می‌کند.
    """
    
    def __init__(self, max_messages: int = 10):
        """
        Args:
            max_messages: تعداد پیام‌های نگهداری شده (پیش‌فرض: 10)
        """
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


def format_history_for_prompt(messages: List[Dict[str, str]]) -> str:
    """
    فرمت‌بندی تاریخچه برای استفاده در prompt
    
    Args:
        messages: لیست پیام‌ها
        
    Returns:
        رشته فرمت شده
    """
    if not messages:
        return "هیچ تاریخچه‌ای موجود نیست. این اولین پیام است.\n\n"
    
    history_text = "\n**تاریخچه مکالمه:**\n"
    for msg in messages:
        role_fa = "کاربر" if msg["role"] == "user" else "سالی"
        history_text += f"{role_fa}: {msg['content']}\n"
    history_text += "\n"
    
    return history_text

