"""
سیستم Logging پیشرفته برای SallyBot

این ماژول شامل:
- Structured Logging
- JSON Formatting برای production
- Log Rotation
- Different Log Levels
- Context Managers
- Performance Tracking
"""

import logging
import sys
import json
import time
from datetime import datetime
from pathlib import Path
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from typing import Dict, Any, Optional
from contextvars import ContextVar
import traceback


# Context variables for request tracking
request_id_var: ContextVar[str] = ContextVar('request_id', default='')
user_id_var: ContextVar[str] = ContextVar('user_id', default='')
user_type_var: ContextVar[str] = ContextVar('user_type', default='')


class StructuredFormatter(logging.Formatter):
    """
    Formatter برای تولید لاگ‌های structured به فرمت JSON
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON"""
        
        # استخراج اطلاعات پایه
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # اضافه کردن اطلاعات context
        request_id = request_id_var.get()
        if request_id:
            log_data["request_id"] = request_id
            
        user_id = user_id_var.get()
        if user_id:
            log_data["user_id"] = user_id
            
        user_type = user_type_var.get()
        if user_type:
            log_data["user_type"] = user_type
        
        # اضافه کردن exception اگر وجود دارد
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": traceback.format_exception(*record.exc_info)
            }
        
        # اضافه کردن extra fields
        if hasattr(record, 'extra_data'):
            log_data.update(record.extra_data)
        
        return json.dumps(log_data, ensure_ascii=False)


class ColoredFormatter(logging.Formatter):
    """
    Formatter با رنگ برای خروجی console در development
    """
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
    }
    RESET = '\033[0m'
    BOLD = '\033[1m'
    
    # Emoji icons
    ICONS = {
        'DEBUG': '🔍',
        'INFO': '✅',
        'WARNING': '⚠️',
        'ERROR': '❌',
        'CRITICAL': '🔥',
    }
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors and emojis"""
        
        # Get color for level
        color = self.COLORS.get(record.levelname, '')
        icon = self.ICONS.get(record.levelname, '')
        
        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        
        # Build colored message
        colored_level = f"{color}{self.BOLD}{icon} {record.levelname}{self.RESET}"
        location = f"{record.module}.{record.funcName}:{record.lineno}"
        
        # Add context if available
        context_parts = []
        request_id = request_id_var.get()
        if request_id:
            context_parts.append(f"req:{request_id[:8]}")
        
        user_id = user_id_var.get()
        if user_id:
            context_parts.append(f"user:{user_id[:8]}")
        
        context_str = f"[{', '.join(context_parts)}]" if context_parts else ""
        
        # Format base message
        message = f"{timestamp} {colored_level} {context_str} [{location}] {record.getMessage()}"
        
        # Add exception if present
        if record.exc_info:
            message += "\n" + "".join(traceback.format_exception(*record.exc_info))
        
        return message


class PerformanceLogger:
    """
    Context manager برای اندازه‌گیری و لاگ performance
    """
    
    def __init__(self, logger: logging.Logger, operation: str, **kwargs):
        self.logger = logger
        self.operation = operation
        self.extra_data = kwargs
        self.start_time = None
        self.end_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        self.logger.info(
            f"🚀 Starting: {self.operation}",
            extra={'extra_data': {**self.extra_data, 'operation': self.operation}}
        )
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        duration = (self.end_time - self.start_time) * 1000  # Convert to milliseconds
        
        extra_data = {
            **self.extra_data,
            'operation': self.operation,
            'duration_ms': round(duration, 2),
            'success': exc_type is None
        }
        
        if exc_type is None:
            self.logger.info(
                f"✅ Completed: {self.operation} (took {duration:.2f}ms)",
                extra={'extra_data': extra_data}
            )
        else:
            extra_data['error'] = str(exc_val)
            self.logger.error(
                f"❌ Failed: {self.operation} (took {duration:.2f}ms) - {exc_val}",
                extra={'extra_data': extra_data},
                exc_info=True
            )
        
        return False  # Don't suppress exceptions


def setup_logging(
    app_name: str = "sallybot",
    log_level: str = "INFO",
    log_dir: str = "logs",
    enable_json: bool = False,
    enable_console: bool = True,
    enable_file: bool = True
) -> None:
    """
    راه‌اندازی سیستم logging برای کل application
    
    Args:
        app_name: نام application
        log_level: سطح logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: مسیر ذخیره فایل‌های لاگ
        enable_json: استفاده از JSON formatter برای فایل‌ها
        enable_console: نمایش لاگ در console
        enable_file: ذخیره لاگ در فایل
    """
    
    # Create logs directory
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler با رنگ و emoji
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(ColoredFormatter())
        root_logger.addHandler(console_handler)
    
    # File handlers
    if enable_file:
        # Main log file با rotation
        main_log_file = log_path / f"{app_name}.log"
        main_handler = RotatingFileHandler(
            main_log_file,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding='utf-8'
        )
        main_handler.setLevel(logging.INFO)
        
        if enable_json:
            main_handler.setFormatter(StructuredFormatter())
        else:
            main_handler.setFormatter(
                logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - [%(module)s.%(funcName)s:%(lineno)d] - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                )
            )
        root_logger.addHandler(main_handler)
        
        # Error log file (فقط ERROR و بالاتر)
        error_log_file = log_path / f"{app_name}_errors.log"
        error_handler = RotatingFileHandler(
            error_log_file,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        
        if enable_json:
            error_handler.setFormatter(StructuredFormatter())
        else:
            error_handler.setFormatter(
                logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - [%(module)s.%(funcName)s:%(lineno)d] - %(message)s\n%(exc_info)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                )
            )
        root_logger.addHandler(error_handler)
        
        # Performance log file
        perf_log_file = log_path / f"{app_name}_performance.log"
        perf_handler = TimedRotatingFileHandler(
            perf_log_file,
            when='midnight',
            interval=1,
            backupCount=7,
            encoding='utf-8'
        )
        perf_handler.setLevel(logging.INFO)
        if enable_json:
            perf_handler.setFormatter(StructuredFormatter())
        else:
            perf_handler.setFormatter(
                logging.Formatter(
                    '%(asctime)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                )
            )
        
        # فقط لاگ‌های performance را به این handler اضافه کن
        perf_logger = logging.getLogger('performance')
        perf_logger.addHandler(perf_handler)
        perf_logger.propagate = False
    
    # Suppress noisy loggers
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    logging.getLogger('openai').setLevel(logging.WARNING)
    logging.getLogger('weaviate').setLevel(logging.WARNING)
    
    root_logger.info(f"🎯 Logging system initialized - Level: {log_level}, JSON: {enable_json}")


def get_logger(name: str) -> logging.Logger:
    """
    دریافت logger با نام مشخص
    
    Args:
        name: نام logger (معمولا __name__)
    
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def set_request_context(request_id: str, user_id: Optional[str] = None, user_type: Optional[str] = None):
    """
    تنظیم context برای request جاری
    
    Args:
        request_id: شناسه یکتای request
        user_id: شناسه کاربر (اختیاری)
        user_type: نوع کاربر (اختیاری)
    """
    request_id_var.set(request_id)
    if user_id:
        user_id_var.set(user_id)
    if user_type:
        user_type_var.set(user_type)


def clear_request_context():
    """پاک کردن context فعلی"""
    request_id_var.set('')
    user_id_var.set('')
    user_type_var.set('')


# Helper function for structured logging
def log_with_context(logger: logging.Logger, level: str, message: str, **kwargs):
    """
    لاگ کردن با context و extra data
    
    Args:
        logger: Logger instance
        level: سطح لاگ (debug, info, warning, error, critical)
        message: پیام لاگ
        **kwargs: داده‌های اضافی
    """
    log_func = getattr(logger, level.lower())
    log_func(message, extra={'extra_data': kwargs})

