"""
Custom Callbacks برای monitoring و logging عملیات LangChain
"""

import time
import contextvars
from typing import Any, Dict, List, Optional
from uuid import UUID
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

from app.core.logging_config import get_logger, PerformanceLogger

logger = get_logger(__name__)

# Context variables for per-request tracking
current_request_token_usage: contextvars.ContextVar[Optional[Dict[str, int]]] = contextvars.ContextVar(
    'current_request_token_usage',
    default=None
)

current_request_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    'current_request_id',
    default=None
)

current_request_cost: contextvars.ContextVar[Optional[float]] = contextvars.ContextVar(
    'current_request_cost',
    default=None
)


class DetailedLoggingCallback(BaseCallbackHandler):
    """
    Callback برای logging دقیق تمام مراحل LangChain
    """
    
    def __init__(self):
        super().__init__()
        self.start_times = {}
        self.token_usage = {}
    
    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        **kwargs: Any
    ) -> None:
        """Log when LLM starts"""
        run_id = kwargs.get('run_id')
        self.start_times[run_id] = time.time()
        
        logger.info(
            f"🤖 LLM Request Started",
            extra={
                'extra_data': {
                    'run_id': str(run_id),
                    'model': serialized.get('name', 'unknown'),
                    'prompts_count': len(prompts),
                    'prompt_preview': prompts[0][:200] if prompts else None
                }
            }
        )
    
    def on_llm_end(
        self,
        response: LLMResult,
        **kwargs: Any
    ) -> None:
        """Log when LLM completes"""
        run_id = kwargs.get('run_id')
        start_time = self.start_times.get(run_id)

        if start_time:
            duration_ms = (time.time() - start_time) * 1000
            del self.start_times[run_id]
        else:
            duration_ms = None

        # Extract token usage if available
        token_usage = {}
        if response.llm_output:
            token_usage = response.llm_output.get('token_usage', {})

        # Store token usage in context variable for per-request access
        if token_usage:
            current_request_token_usage.set(token_usage)

            # Calculate and store cost if we have token usage
            # This is a simplified calculation - you might want to use actual pricing
            cost = calculate_request_cost(token_usage)
            if cost is not None:
                current_request_cost.set(cost)

        logger.info(
            f"✅ LLM Request Completed",
            extra={
                'extra_data': {
                    'run_id': str(run_id),
                    'duration_ms': round(duration_ms, 2) if duration_ms else None,
                    'generations_count': len(response.generations),
                    'token_usage': token_usage
                }
            }
        )
    
    def on_llm_error(
        self,
        error: Exception,
        **kwargs: Any
    ) -> None:
        """Log when LLM encounters an error"""
        run_id = kwargs.get('run_id')
        
        logger.error(
            f"❌ LLM Request Failed",
            exc_info=True,
            extra={
                'extra_data': {
                    'run_id': str(run_id),
                    'error_type': type(error).__name__,
                    'error_message': str(error)
                }
            }
        )
    
    def on_chain_start(
        self,
        serialized: Dict[str, Any],
        inputs: Dict[str, Any],
        **kwargs: Any
    ) -> None:
        """Log when chain starts"""
        run_id = kwargs.get('run_id')
        self.start_times[run_id] = time.time()
        
        logger.info(
            f"🔗 Chain Started",
            extra={
                'extra_data': {
                    'run_id': str(run_id),
                    'chain_type': serialized.get('name', 'unknown'),
                    'inputs_keys': list(inputs.keys())
                }
            }
        )
    
    def on_chain_end(
        self,
        outputs: Dict[str, Any],
        **kwargs: Any
    ) -> None:
        """Log when chain completes"""
        run_id = kwargs.get('run_id')
        start_time = self.start_times.get(run_id)
        
        if start_time:
            duration_ms = (time.time() - start_time) * 1000
            del self.start_times[run_id]
        else:
            duration_ms = None
        
        logger.info(
            f"✅ Chain Completed",
            extra={
                'extra_data': {
                    'run_id': str(run_id),
                    'duration_ms': round(duration_ms, 2) if duration_ms else None,
                    'outputs_keys': list(outputs.keys())
                }
            }
        )
    
    def on_chain_error(
        self,
        error: Exception,
        **kwargs: Any
    ) -> None:
        """Log when chain encounters an error"""
        run_id = kwargs.get('run_id')
        
        logger.error(
            f"❌ Chain Failed",
            exc_info=True,
            extra={
                'extra_data': {
                    'run_id': str(run_id),
                    'error_type': type(error).__name__,
                    'error_message': str(error)
                }
            }
        )
    
    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        **kwargs: Any
    ) -> None:
        """Log when tool starts"""
        run_id = kwargs.get('run_id')
        self.start_times[run_id] = time.time()
        
        logger.info(
            f"🔧 Tool Execution Started",
            extra={
                'extra_data': {
                    'run_id': str(run_id),
                    'tool_name': serialized.get('name', 'unknown'),
                    'input_preview': input_str[:200]
                }
            }
        )
    
    def on_tool_end(
        self,
        output: str,
        **kwargs: Any
    ) -> None:
        """Log when tool completes"""
        run_id = kwargs.get('run_id')
        start_time = self.start_times.get(run_id)
        
        if start_time:
            duration_ms = (time.time() - start_time) * 1000
            del self.start_times[run_id]
        else:
            duration_ms = None
        
        logger.info(
            f"✅ Tool Execution Completed",
            extra={
                'extra_data': {
                    'run_id': str(run_id),
                    'duration_ms': round(duration_ms, 2) if duration_ms else None,
                    'output_preview': output[:200]
                }
            }
        )
    
    def on_tool_error(
        self,
        error: Exception,
        **kwargs: Any
    ) -> None:
        """Log when tool encounters an error"""
        run_id = kwargs.get('run_id')
        
        logger.error(
            f"❌ Tool Execution Failed",
            exc_info=True,
            extra={
                'extra_data': {
                    'run_id': str(run_id),
                    'error_type': type(error).__name__,
                    'error_message': str(error)
                }
            }
        )
    
    def on_retriever_start(
        self,
        serialized: Dict[str, Any],
        query: str,
        **kwargs: Any
    ) -> None:
        """Log when retriever starts"""
        run_id = kwargs.get('run_id')
        self.start_times[run_id] = time.time()
        
        logger.info(
            f"🔍 Retriever Search Started",
            extra={
                'extra_data': {
                    'run_id': str(run_id),
                    'query': query[:200]
                }
            }
        )
    
    def on_retriever_end(
        self,
        documents,
        **kwargs: Any
    ) -> None:
        """Log when retriever completes"""
        run_id = kwargs.get('run_id')
        start_time = self.start_times.get(run_id)
        
        if start_time:
            duration_ms = (time.time() - start_time) * 1000
            del self.start_times[run_id]
        else:
            duration_ms = None
        
        logger.info(
            f"✅ Retriever Search Completed",
            extra={
                'extra_data': {
                    'run_id': str(run_id),
                    'duration_ms': round(duration_ms, 2) if duration_ms else None,
                    'documents_count': len(documents)
                }
            }
        )
    
    def on_retriever_error(
        self,
        error: Exception,
        **kwargs: Any
    ) -> None:
        """Log when retriever encounters an error"""
        run_id = kwargs.get('run_id')
        
        logger.error(
            f"❌ Retriever Search Failed",
            exc_info=True,
            extra={
                'extra_data': {
                    'run_id': str(run_id),
                    'error_type': type(error).__name__,
                    'error_message': str(error)
                }
            }
        )


class TokenUsageCallback(BaseCallbackHandler):
    """
    Callback برای tracking استفاده از token و محاسبه هزینه
    """
    
    # هزینه‌های تقریبی (باید بر اساس provider واقعی تنظیم شود)
    PRICING = {
        'gpt-4': {'input': 0.03, 'output': 0.06},  # per 1K tokens
        'gpt-3.5-turbo': {'input': 0.0015, 'output': 0.002},
        'default': {'input': 0.001, 'output': 0.002}
    }
    
    def __init__(self):
        super().__init__()
        self.total_tokens = 0
        self.total_cost = 0.0
        self.requests_count = 0
    
    def on_llm_end(
        self,
        response: LLMResult,
        **kwargs: Any
    ) -> None:
        """Track token usage"""
        if response.llm_output:
            token_usage = response.llm_output.get('token_usage', {})
            
            if token_usage:
                prompt_tokens = token_usage.get('prompt_tokens', 0)
                completion_tokens = token_usage.get('completion_tokens', 0)
                total_tokens = token_usage.get('total_tokens', 0)
                
                self.total_tokens += total_tokens
                self.requests_count += 1
                
                # محاسبه هزینه تقریبی
                model_name = response.llm_output.get('model_name', 'default')
                pricing = self.PRICING.get(model_name, self.PRICING['default'])
                
                cost = (
                    (prompt_tokens / 1000) * pricing['input'] +
                    (completion_tokens / 1000) * pricing['output']
                )
                self.total_cost += cost
                
                logger.info(
                    f"💰 Token Usage",
                    extra={
                        'extra_data': {
                            'model': model_name,
                            'prompt_tokens': prompt_tokens,
                            'completion_tokens': completion_tokens,
                            'total_tokens': total_tokens,
                            'estimated_cost_usd': round(cost, 6),
                            'cumulative_tokens': self.total_tokens,
                            'cumulative_cost_usd': round(self.total_cost, 4),
                            'requests_count': self.requests_count
                        }
                    }
                )
    
    def get_stats(self) -> Dict[str, Any]:
        """دریافت آمار کلی"""
        return {
            'total_tokens': self.total_tokens,
            'total_cost_usd': round(self.total_cost, 4),
            'requests_count': self.requests_count,
            'avg_tokens_per_request': round(self.total_tokens / self.requests_count, 2) if self.requests_count > 0 else 0
        }


class PerformanceCallback(BaseCallbackHandler):
    """
    Callback برای monitoring performance
    """
    
    def __init__(self):
        super().__init__()
        self.perf_logger = get_logger('performance')
        self.slow_threshold_ms = 3000  # 3 seconds
    
    def on_llm_end(
        self,
        response: LLMResult,
        **kwargs: Any
    ) -> None:
        """Check for slow LLM calls"""
        run_id = kwargs.get('run_id')
        
        # این اطلاعات باید از DetailedLoggingCallback دریافت شود
        # برای سادگی فعلا فقط log می‌کنیم
        pass


# Global callback instances
detailed_callback = DetailedLoggingCallback()
token_callback = TokenUsageCallback()
performance_callback = PerformanceCallback()


def get_default_callbacks() -> List[BaseCallbackHandler]:
    """
    دریافت لیست callbacks پیش‌فرض

    Returns:
        لیست callback handlers
    """
    return [
        detailed_callback,
        token_callback,
        performance_callback
    ]


def get_current_request_token_usage() -> Optional[Dict[str, int]]:
    """
    دریافت مصرف توکن درخواست فعلی از context variable

    Returns:
        Dict containing token usage or None if not available
    """
    try:
        token_usage = current_request_token_usage.get()
        if token_usage:
            return {
                'prompt_tokens': token_usage.get('prompt_tokens', 0),
                'completion_tokens': token_usage.get('completion_tokens', 0),
                'total_tokens': token_usage.get('total_tokens', 0)
            }
    except LookupError:
        pass
    return None


def get_current_request_id() -> Optional[str]:
    """Get the current request ID from context variable"""
    try:
        return current_request_id.get()
    except LookupError:
        return None


def set_current_request_id(request_id: str):
    """Set the current request ID in context variable"""
    current_request_id.set(request_id)


def get_current_request_cost() -> Optional[float]:
    """Get the current request cost from context variable"""
    try:
        return current_request_cost.get()
    except LookupError:
        return None


def set_current_request_cost(cost: float):
    """Set the current request cost in context variable"""
    current_request_cost.set(cost)


def calculate_request_cost(token_usage: Dict[str, int]) -> Optional[float]:
    """
    Calculate the estimated cost of a request based on token usage.

    This is a simplified calculation. In production, you should use actual pricing
    from your LLM provider and consider different models/pricing tiers.
    """
    try:
        # Simplified pricing (example rates - update with actual pricing)
        # These are example rates for GPT-4o (as of 2024)
        input_cost_per_1k = 0.005  # $0.005 per 1K input tokens
        output_cost_per_1k = 0.015  # $0.015 per 1K output tokens

        input_tokens = token_usage.get('prompt_tokens', 0)
        output_tokens = token_usage.get('completion_tokens', 0)

        input_cost = (input_tokens / 1000) * input_cost_per_1k
        output_cost = (output_tokens / 1000) * output_cost_per_1k

        total_cost = input_cost + output_cost
        return round(total_cost, 6)  # Round to 6 decimal places

    except Exception as e:
        logger.warning(f"Could not calculate request cost: {e}")
        return None


def reset_current_request_context():
    """Reset all current request context variables"""
    current_request_token_usage.set(None)
    current_request_id.set(None)
    current_request_cost.set(None)

