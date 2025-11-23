"""
Advanced Agentic RAG System with LangGraph
==========================================

این ماژول یک سیستم RAG پیشرفته عامل‌محور با قابلیت‌های زیر ارائه می‌دهد:

1. **Multi-Agent Workflow**: گره‌های مختلف برای Planning, Research, Analysis, Synthesis
2. **Tree-Aware Search**: استفاده از ساختار درختی Markdown در Weaviate
3. **Query Decomposition**: تقسیم سوالات پیچیده به زیرسوالات
4. **Self-Reflection**: بررسی و بهبود کیفیت پاسخ‌ها
5. **Dynamic Routing**: مسیریابی هوشمند بر اساس نوع سوال
6. **Context Aggregation**: جمع‌آوری و ترکیب اطلاعات از منابع مختلف
"""

from typing import Dict, Any, List, Optional, Tuple, Annotated
from typing_extensions import TypedDict
from enum import Enum
import operator
import uuid
import re
from datetime import datetime
import json

from app.core.logging_config import get_logger, PerformanceLogger
from app.core.config import settings
from app.infrastructure.model_factory import model_factory

logger = get_logger(__name__)

try:
    from langgraph.graph import StateGraph, END
    from langgraph.prebuilt import ToolExecutor
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    logger.warning("⚠️ LangGraph not installed. Advanced Agentic RAG will not be available.")

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.tools import tool
try:
    from pydantic import BaseModel, Field
except ImportError:
    from pydantic.v1 import BaseModel, Field


class AgentAction(str, Enum):
    """انواع اقدامات Agent"""
    PLAN = "plan"                    # برنامه‌ریزی استراتژی
    SEARCH = "search"                # جستجوی اطلاعات
    TREE_SEARCH = "tree_search"      # جستجوی درختی
    ANALYZE = "analyze"              # تحلیل نتایج
    SYNTHESIZE = "synthesize"        # ترکیب اطلاعات
    REFLECT = "reflect"              # بازبینی و ارزیابی
    DECOMPOSE = "decompose"          # تقسیم سوال
    AGGREGATE = "aggregate"          # جمع‌آوری نتایج
    USE_TOOLS = "use_tools"          # استفاده از ابزارهای خارجی


# 🔥 Input Schemas برای ابزارهای LangChain
class WebSearchInput(BaseModel):
    """ورودی ابزار جستجوی وب"""
    query: str = Field(description="عبارت جستجوی وب (باید دقیق و مرتبط باشد)")
    max_results: int = Field(default=3, description="حداکثر تعداد نتایج")


class CalculatorInput(BaseModel):
    """ورودی ابزار ماشین حساب"""
    expression: str = Field(description="عبارت ریاضی برای محاسبه (مثال: '2 + 3 * 4' یا 'sqrt(16)')")


class DateTimeInput(BaseModel):
    """ورودی ابزار تاریخ/زمان"""
    timezone: str = Field(default="Asia/Tehran", description="منطقه زمانی")


# 🔥 LangChain Tools برای Agentic RAG
@tool("web_search", args_schema=WebSearchInput)
async def web_search_tool(query: str, max_results: int = 3) -> str:
    """
    جستجوی اطلاعات جدید و به‌روز از وب برای موضوعات عمومی.

    این ابزار برای دریافت اطلاعات جاری، اخبار، و موضوعات عمومی از وب استفاده می‌شود.
    """
    try:
        import requests

        # جستجوی ساده DuckDuckGo
        search_url = f"https://api.duckduckgo.com/?q={query}&format=json&no_html=1"

        response = requests.get(search_url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            answer = data.get("Answer", "")
            if not answer:
                answer = data.get("AbstractText", "No direct answer found")

            return answer[:500]  # محدود به 500 کاراکتر
        else:
            return f"Web search simulation: Results for '{query}' would be shown here."

    except Exception as e:
        logger.warning(f"Web search failed: {e}")
        return f"Web search unavailable: {str(e)}"


@tool("calculate", args_schema=CalculatorInput)
async def calculate_tool(expression: str) -> str:
    """
    انجام محاسبات ریاضی ساده.

    این ابزار برای محاسبات پایه ریاضی، جذر، توان، و عملیات ساده استفاده می‌شود.
    """
    try:
        # جایگزینی عملیات فارسی
        expression = expression.replace("×", "*").replace("÷", "/")

        # محاسبات امن
        if "sqrt(" in expression:
            import math
            num = float(re.search(r'sqrt\((\d+(?:\.\d+)?)\)', expression).group(1))
            return str(math.sqrt(num))
        elif "^" in expression:
            base, exp = expression.split("^")
            return str(float(base.strip()) ** float(exp.strip()))
        else:
            # استفاده از eval با محدودیت‌های امنیتی
            allowed_chars = "0123456789.+-*/()"
            if all(c in allowed_chars for c in expression):
                result = eval(expression)
                return str(result)
            else:
                return "Unsupported operation"

    except Exception as e:
        return f"Error: {str(e)}"


@tool("get_current_datetime", args_schema=DateTimeInput)
async def datetime_tool(timezone: str = "Asia/Tehran") -> str:
    """
    دریافت زمان و تاریخ فعلی.

    این ابزار برای دریافت زمان و تاریخ جاری در منطقه زمانی مشخص استفاده می‌شود.
    """
    try:
        from datetime import datetime
        import pytz

        tz = pytz.timezone(timezone)
        now = datetime.now(tz)

        return now.strftime('%Y-%m-%d %H:%M:%S %Z')

    except Exception as e:
        logger.warning(f"Datetime tool failed: {e}")
        return f"Error getting datetime: {str(e)}"


# لیست ابزارهای LangChain
LANGCHAIN_TOOLS = [web_search_tool, calculate_tool, datetime_tool]


class QueryComplexity(str, Enum):
    """میزان پیچیدگی سوال"""
    SIMPLE = "simple"                # سوال ساده - نیاز به یک جستجو
    MODERATE = "moderate"            # سوال متوسط - نیاز به چند جستجو
    COMPLEX = "complex"              # سوال پیچیده - نیاز به تجزیه و تحلیل


class TreeNode(TypedDict):
    """نمایش یک گره از درخت Markdown"""
    node_id: str
    title: str
    level: int
    content: str
    parent_id: str
    path: str
    article_id: str
    score: float
    # 🔥 اضافه شده برای RERANKING
    raw_content: str
    full_article_content: str
    rerank_score: Optional[float] = None


class AgenticRAGState(TypedDict):
    """
    State برای Agentic RAG Workflow
    """
    # ورودی اصلی
    query: str
    user_id: Optional[str]
    session_id: str
    conversation_history: List[Dict[str, str]]
    
    # تحلیل Query
    query_complexity: Optional[QueryComplexity]
    decomposed_queries: List[str]
    current_subquery_index: int
    
    # نتایج جستجو
    search_results: Annotated[List[TreeNode], operator.add]
    tree_context: Dict[str, Any]  # برای نگه‌داری context درختی
    
    # تحلیل و ترکیب
    analyzed_results: List[Dict[str, Any]]
    partial_answers: Annotated[List[str], operator.add]
    
    # پاسخ نهایی
    final_response: Optional[str]
    confidence_score: float
    sources: List[Dict[str, Any]]
    
    # مدیریت workflow
    current_action: Optional[AgentAction]
    action_history: Annotated[List[AgentAction], operator.add]
    reflection_notes: Annotated[List[str], operator.add]
    
    # خطاها و تلاش‌های مجدد
    errors: Annotated[List[str], operator.add]
    retry_count: int
    max_retries: int
    needs_fallback: bool  # 🔥 برای مدیریت fallback


class AdvancedAgenticRAG:
    """
    سیستم RAG پیشرفته عامل‌محور با LangGraph
    """
    
    def __init__(self, orchestrator, rag_service, weaviate_connector=None):
        self.orchestrator = orchestrator
        self.rag_service = rag_service
        self.weaviate_connector = weaviate_connector
        self.graph = None
        
        # 🔥 Configuration validation
        self._validate_configuration()
        
        if LANGGRAPH_AVAILABLE:
            self._build_graph()
            logger.info("🤖 AdvancedAgenticRAG initialized with multi-agent workflow")
        else:
            logger.warning("⚠️ LangGraph not available, using fallback mode")
    
    def _validate_configuration(self):
        """
        🔥 Validate critical configuration settings
        """
        validation_errors = []
        
        # Validate model configurations
        if not settings.chat_model_loaded:
            validation_errors.append("chat_model_loaded is not configured")
        
        if not settings.rag_model_loaded:
            validation_errors.append("rag_model_loaded is not configured")
        
        # Validate hybrid model strategy if enabled
        if settings.use_hybrid_model_strategy:
            if not settings.agentic_fast_model:
                validation_errors.append("agentic_fast_model is required when hybrid strategy is enabled")
            if not settings.agentic_power_model:
                validation_errors.append("agentic_power_model is required when hybrid strategy is enabled")
        
        # Validate Weaviate configuration if tree search is enabled
        if not settings.weaviate_url_loaded:
            logger.warning("⚠️ Weaviate URL not configured - tree search will be disabled")
        else:
            logger.info("✅ Weaviate URL configured")
        
        # Weaviate API key is optional for many deployments
        weaviate_api_key = settings.weaviate_api_key_loaded
        if weaviate_api_key is not None and weaviate_api_key.strip():
            logger.info("✅ Weaviate API key configured")
        else:
            # API key is empty or not configured - this is fine for unauthenticated Weaviate
            logger.info("ℹ️ Weaviate API key not configured (using unauthenticated mode)")
        
        # Validate embedder configuration
        if not settings.embedder_api_key_loaded:
            validation_errors.append("embedder_api_key_loaded is not configured")
        
        if not settings.embedder_model_loaded:
            validation_errors.append("embedder_model_loaded is not configured")
        
        # Log validation results
        if validation_errors:
            logger.error("❌ Configuration validation failed:")
            for error in validation_errors:
                logger.error(f"   - {error}")
            raise ValueError(f"Configuration validation failed: {', '.join(validation_errors)}")
        else:
            logger.info("✅ Configuration validation passed")
            logger.info("🌳 Tree search enabled (Weaviate connection working)")
    
    def _build_graph(self):
        """ساخت workflow graph پیشرفته"""
        
        workflow = StateGraph(AgenticRAGState)
        
        # اضافه کردن گره‌های اصلی
        workflow.add_node("analyze_query", self.analyze_query)
        workflow.add_node("decompose_query", self.decompose_query)
        workflow.add_node("plan_strategy", self.plan_strategy)
        workflow.add_node("tree_search", self.tree_search)
        workflow.add_node("simple_search", self.simple_search)  # 🔥 گره fallback
        workflow.add_node("parallel_subquery_search", self.parallel_subquery_search)
        workflow.add_node("multi_hop_search", self.multi_hop_search)  # 🔥 Multi-hop Retrieval
        workflow.add_node("use_external_tools", self.use_external_tools)  # 🔥 Function Calling
        workflow.add_node("aggregate_context", self.aggregate_context)
        workflow.add_node("analyze_results", self.analyze_results)
        workflow.add_node("synthesize_answer", self.synthesize_answer)
        workflow.add_node("reflect_on_answer", self.reflect_on_answer)
        workflow.add_node("process_subquery", self.process_subquery)
        
        # تعریف نقطه شروع
        workflow.set_entry_point("analyze_query")
        
        # مسیریابی بر اساس پیچیدگی
        workflow.add_conditional_edges(
            "analyze_query",
            self.route_by_complexity,
            {
                "simple": "tree_search",
                "moderate": "plan_strategy",
                "complex": "decompose_query"
            }
        )
        
        # مسیر برای سوالات پیچیده - پردازش موازی زیرسوالات
        workflow.add_edge("decompose_query", "parallel_subquery_search")
        workflow.add_edge("parallel_subquery_search", "aggregate_context")
        
        # مسیر برای سوالات متوسط
        workflow.add_edge("plan_strategy", "tree_search")
        
        # 🔥 مسیریابی بعد از tree_search با multi-hop و fallback
        workflow.add_conditional_edges(
            "tree_search",
            self.should_use_multi_hop,
            {
                "multi_hop": "multi_hop_search",
                "simple": "aggregate_context",
                "fallback": "simple_search"
            }
        )
        
        # مسیر multi-hop
        workflow.add_edge("multi_hop_search", "aggregate_context")

        # مسیر external tools
        workflow.add_edge("use_external_tools", "aggregate_context")

        # مسیر fallback
        workflow.add_edge("simple_search", "aggregate_context")

        # مسیریابی بعد از aggregate_context
        workflow.add_conditional_edges(
            "aggregate_context",
            self.should_use_external_tools,
            {
                "use_tools": "use_external_tools",
                "synthesize": "analyze_results"
            }
        )
        workflow.add_edge("analyze_results", "synthesize_answer")
        workflow.add_edge("synthesize_answer", "reflect_on_answer")
        
        # تصمیم نهایی
        workflow.add_conditional_edges(
            "reflect_on_answer",
            self.should_retry_or_finish,
            {
                "retry": "plan_strategy",
                "finish": END
            }
        )
        
        self.graph = workflow.compile()
        logger.info("✅ Advanced Agentic RAG workflow compiled successfully")
    
    async def analyze_query(self, state: AgenticRAGState) -> AgenticRAGState:
        """
        تحلیل اولیه سوال و تعیین پیچیدگی
        """
        with PerformanceLogger(logger, "analyze_query"):
            logger.info(f"🔍 Analyzing query complexity: {state['query'][:100]}")
            logger.info(f"📊 Query length: {len(state['query'])} characters")
            
            # بررسی تاریخچه مکالمه
            if state.get("conversation_history") and len(state["conversation_history"]) > 0:
                logger.info(f"💬 Found {len(state['conversation_history'])} previous messages in conversation")
            
            try:
                # آماده‌سازی context از تاریخچه
                history_context = ""
                if state.get("conversation_history"):
                    recent_messages = state["conversation_history"][-settings.agentic_history_messages_count:]  # پیام‌های آخر از تنظیمات
                    history_context = "\n\nتاریخچه مکالمه:\n"
                    for msg in recent_messages:
                        role = msg.get("role", "user")
                        content = msg.get("content", "")[:100]
                        history_context += f"- {role}: {content}\n"
                
                prompt = ChatPromptTemplate.from_template("""
                تحلیل کن که این سوال چقدر پیچیده است:
                
                سوال فعلی: {query}
                {history_context}
                
                معیارها:
                - simple: سوال مستقیم که با یک جستجو قابل پاسخ است
                - moderate: سوال که نیاز به چند جستجو یا مقایسه دارد
                - complex: سوال پیچیده که نیاز به تجزیه به زیرسوالات دارد
                
                اگر سوال فعلی به مکالمه قبلی اشاره دارد (مثل "آیا"، "این"، "آن")، آن را در نظر بگیر.
                
                فقط یکی از این کلمات را برگردان: simple, moderate, complex
                """)
                
                # 🔥 استفاده از Hybrid Model Strategy
                model_to_use = self._get_fast_model() if settings.use_hybrid_model_strategy else settings.chat_model_loaded
                logger.info(f"🤖 Agentic RAG - Using FAST model: {model_to_use}")
                
                from app.services.model_service import model_service
                model = model_service.get_model(
                    model_to_use,
                    max_tokens=10,
                    temperature=0.1
                )
                
                chain = prompt | model | StrOutputParser()
                result = await chain.ainvoke({
                    "query": state["query"],
                    "history_context": history_context
                })
                
                complexity = result.strip().lower()
                
                try:
                    state["query_complexity"] = QueryComplexity(complexity)
                except ValueError:
                    state["query_complexity"] = QueryComplexity.SIMPLE
                
                logger.info(f"✅ Query complexity: {state['query_complexity'].value}")
                logger.info(f"🤖 Using model: {model_to_use} for complexity analysis")
                state["action_history"].append(AgentAction.PLAN)
                
            except Exception as e:
                logger.error(f"❌ Query analysis failed: {e}")
                state["query_complexity"] = QueryComplexity.SIMPLE
                state["errors"].append(f"analysis_error:{str(e)}")
            
            return state
    
    async def decompose_query(self, state: AgenticRAGState) -> AgenticRAGState:
        """
        تقسیم سوال پیچیده به زیرسوالات
        """
        with PerformanceLogger(logger, "decompose_query"):
            logger.info(f"🔨 Decomposing complex query: {state['query'][:100]}")
            
            try:
                prompt = ChatPromptTemplate.from_template("""
                این سوال پیچیده را به زیرسوالات ساده‌تر تقسیم کن:
                
                سوال اصلی: {query}
                
                هر زیرسوال را در یک خط جداگانه بنویس و با عدد شماره‌گذاری کن.
                فقط زیرسوالات مهم و ضروری را بنویس (حداکثر 3 تا).
                """)
                
                # 🔥 استفاده از Fast Model برای decomposition
                fast_model = self._get_fast_model()
                
                from app.services.model_service import model_service
                model = model_service.get_model(
                    fast_model,
                    max_tokens=200,
                    temperature=0.1
                )
                
                chain = prompt | model | StrOutputParser()
                result = await chain.ainvoke({"query": state["query"]})
                
                # استخراج زیرسوالات از نتیجه
                lines = result.strip().split('\n')
                subqueries = []
                for line in lines:
                    # حذف شماره‌گذاری و فضاهای خالی
                    clean_line = line.strip()
                    if clean_line and any(char.isalpha() for char in clean_line):
                        # حذف شماره اول خط
                        import re
                        clean_line = re.sub(r'^\d+[\.\-\)]\s*', '', clean_line)
                        subqueries.append(clean_line)
                
                state["decomposed_queries"] = subqueries[:settings.agentic_max_subqueries]  # حداکثر زیرسوالات از تنظیمات
                state["current_subquery_index"] = 0
                
                logger.info(f"✅ Query decomposed into {len(state['decomposed_queries'])} subqueries:")
                for i, sq in enumerate(state["decomposed_queries"], 1):
                    logger.info(f"   {i}. {sq[:80]}...")
                
                state["action_history"].append(AgentAction.DECOMPOSE)
                
            except Exception as e:
                logger.error(f"❌ Query decomposition failed: {e}")
                state["decomposed_queries"] = [state["query"]]
                state["current_subquery_index"] = 0
                state["errors"].append(f"decomposition_error:{str(e)}")
            
            return state
    
    async def process_subquery(self, state: AgenticRAGState) -> AgenticRAGState:
        """
        پردازش زیرسوال فعلی
        """
        idx = state["current_subquery_index"]
        
        if idx < len(state["decomposed_queries"]):
            current_subquery = state["decomposed_queries"][idx]
            logger.info(f"🔄 Processing subquery {idx + 1}/{len(state['decomposed_queries'])}: {current_subquery[:60]}...")
            
            # ذخیره query فعلی برای استفاده در tree_search
            state["query"] = current_subquery
            state["current_subquery_index"] = idx + 1
        
        return state
    
    def check_more_subqueries(self, state: AgenticRAGState) -> str:
        """
        بررسی اینکه آیا زیرسوال دیگری برای پردازش وجود دارد
        """
        if state["current_subquery_index"] < len(state["decomposed_queries"]):
            logger.info(f"➡️ More subqueries to process")
            return "continue"
        else:
            logger.info(f"✅ All subqueries processed")
            return "done"
    
    async def parallel_subquery_search(self, state: AgenticRAGState) -> AgenticRAGState:
        """
        🔥 پردازش موازی زیرسوالات برای افزایش سرعت
        
        این متد تمام زیرسوالات را به صورت موازی پردازش کرده و نتایج را جمع‌آوری می‌کند
        """
        with PerformanceLogger(logger, "parallel_subquery_search"):
            logger.info(f"🚀 Processing {len(state['decomposed_queries'])} subqueries in parallel")
            
            try:
                import asyncio
                
                # ایجاد لیست وظایف برای پردازش موازی
                tasks = []
                for subquery in state["decomposed_queries"]:
                    task = self._process_single_subquery(subquery)
                    tasks.append(task)
                
                # اجرای موازی تمام وظایف
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # جمع‌آوری نتایج
                successful_results = []
                failed_subqueries = []
                
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        failed_subqueries.append({
                            "subquery": state["decomposed_queries"][i],
                            "error": str(result)
                        })
                        logger.error(f"❌ Subquery {i+1} failed: {result}")
                    else:
                        successful_results.extend(result)
                        logger.info(f"✅ Subquery {i+1} completed successfully")
                
                # افزودن نتایج موفق به state
                state["search_results"].extend(successful_results)
                
                # لاگ نتایج
                logger.info(f"📊 Parallel search completed:")
                logger.info(f"   ✅ Successful: {len(successful_results)} results")
                logger.info(f"   ❌ Failed: {len(failed_subqueries)} subqueries")
                
                if failed_subqueries:
                    state["errors"].extend([f"parallel_subquery_error:{err['error']}" for err in failed_subqueries])
                
                state["action_history"].append(AgentAction.SEARCH)
                
            except Exception as e:
                logger.error(f"❌ Parallel subquery search failed: {e}")
                state["errors"].append(f"parallel_search_error:{str(e)}")
                # fallback به پردازش ترتیبی
                logger.warning(f"🔄 Falling back to sequential processing")
                for subquery in state["decomposed_queries"]:
                    sequential_results = await self._process_single_subquery(subquery)
                    state["search_results"].extend(sequential_results)
            
            return state
    
    async def _process_single_subquery(self, subquery: str) -> List[TreeNode]:
        """
        پردازش یک زیرسوال به صورت مستقل
        
        Args:
            subquery: زیرسوال برای پردازشن
            
        Returns:
            لیست نتایج جستجو برای این زیرسوال
        """
        try:
            # ایجاد state موقت برای این زیرسوال
            temp_state: AgenticRAGState = {
                "query": subquery,
                "user_id": None,
                "session_id": str(uuid.uuid4()),
                "conversation_history": [],
                "query_complexity": QueryComplexity.SIMPLE,
                "decomposed_queries": [],
                "current_subquery_index": 0,
                "search_results": [],
                "tree_context": {},
                "analyzed_results": [],
                "partial_answers": [],
                "final_response": None,
                "confidence_score": 0.0,
                "sources": [],
                "current_action": None,
                "action_history": [],
                "reflection_notes": [],
                "errors": [],
                "retry_count": 0,
                "max_retries": 1,
                "needs_fallback": False
            }
            
            # اجرای جستجوی درختی برای این زیرسوال
            await self.tree_search(temp_state)
            
            return temp_state["search_results"]
            
        except Exception as e:
            logger.error(f"❌ Failed to process subquery '{subquery[:50]}...': {e}")
            raise e
    
    async def plan_strategy(self, state: AgenticRAGState) -> AgenticRAGState:
        """
        برنامه‌ریزی استراتژی جستجو
        """
        with PerformanceLogger(logger, "plan_strategy"):
            logger.info(f"📋 Planning search strategy")
            
            try:
                prompt = ChatPromptTemplate.from_template("""
                برای پاسخ به این سوال، چه استراتژی جستجویی پیشنهاد می‌کنی؟
                
                سوال: {query}
                پیچیدگی: {complexity}
                
                توصیه‌های مختصر برای جستجوی بهتر بده:
                - چه کلیدواژه‌هایی را جستجو کنیم؟
                - آیا نیاز به جستجوی درختی (سلسله مراتبی) داریم؟
                - آیا باید منابع مختلف را مقایسه کنیم؟
                
                پاسخ خود را در 2-3 خط خلاصه کن.
                """)
                
                # 🔥 استفاده از Fast Model برای planning
                fast_model = self._get_fast_model()
                
                from app.services.model_service import model_service
                model = model_service.get_model(
                    fast_model,
                    max_tokens=150,
                    temperature=0.1
                )
                
                chain = prompt | model | StrOutputParser()
                strategy = await chain.ainvoke({
                    "query": state["query"],
                    "complexity": state["query_complexity"].value
                })
                
                logger.info(f"✅ Strategy planned: {strategy[:100]}...")
                state["reflection_notes"].append(f"Strategy: {strategy}")
                state["action_history"].append(AgentAction.PLAN)
                
            except Exception as e:
                logger.error(f"❌ Strategy planning failed: {e}")
                state["errors"].append(f"planning_error:{str(e)}")
            
            return state
    
    async def tree_search(self, state: AgenticRAGState) -> AgenticRAGState:
        """
        جستجوی درختی هوشمند در Weaviate

        این متد از ساختار سلسله مراتبی markdown استفاده می‌کند:
        - جستجو در گره‌های markdown
        - پیدا کردن والدین و فرزندان مرتبط
        - استخراج context کامل از درخت

        🔥 با fallback به simple_search در صورت خطا
        """
        with PerformanceLogger(logger, "tree_search"):
            logger.info(f"🌳 Performing tree-aware search for: {state['query'][:100]}")
            logger.info(f"🔍 Search limit: {settings.agentic_search_limit} nodes")
            
            try:
                # جستجوی vector در Weaviate
                results = await self._search_weaviate_tree(state["query"])
                
                if results:
                    logger.info(f"✅ Found {len(results)} relevant nodes")
                    scores = [f"{r.get('score', 0):.3f}" for r in results[:3]]
                    logger.info(f"📊 Top scores: {scores}")

                    # غنی‌سازی با context درختی
                    enriched_results = await self._enrich_with_tree_context(results)
                    logger.info(f"🔗 Enriched with {len(enriched_results)} total nodes (including parents)")

                    state["search_results"].extend(enriched_results)

                    # ذخیره context درختی برای استفاده بعدی
                    if not state.get("tree_context"):
                        state["tree_context"] = {}

                    for result in enriched_results:
                        article_id = result.get("article_id")
                        if article_id:
                            if article_id not in state["tree_context"]:
                                state["tree_context"][article_id] = []
                            state["tree_context"][article_id].append(result)

                    logger.info(f"📊 Tree context includes {len(state['tree_context'])} articles")
                else:
                    logger.warning(f"⚠️ No results found for query")
                    # 🔥 اگر نتیجه‌ای پیدا نشد، fallback flag را تنظیم کن
                    state["errors"].append("tree_search_no_results")
                
                state["action_history"].append(AgentAction.TREE_SEARCH)
                
            except Exception as e:
                logger.error(f"❌ Tree search failed: {e}")
                logger.warning(f"🔄 Will fallback to simple search")
                # 🔥 علامت‌گذاری برای fallback
                state["errors"].append(f"tree_search_failed:{str(e)}")
                state["needs_fallback"] = True
            
            return state
    
    async def simple_search(self, state: AgenticRAGState) -> AgenticRAGState:
        """
        جستجوی ساده با استفاده از RAG service معمولی
        
        🔥 این گره به عنوان fallback برای tree_search استفاده می‌شود
        """
        with PerformanceLogger(logger, "simple_search"):
            logger.info(f"🔍 Performing simple RAG search (fallback mode)")
            
            try:
                # استفاده از rag_service موجود برای جستجوی ساده
                if self.rag_service:
                    documents = await self.rag_service.retrieve_relevant_documents(
                        state["query"],
                        is_public_only=False
                    )
                    
                    if documents:
                        logger.info(f"✅ Found {len(documents)} documents via fallback")
                        
                        # تبدیل به فرمت TreeNode
                        for doc in documents:
                            node = TreeNode(
                                node_id=doc.get("node_id", ""),
                                title=doc.get("title", ""),
                                level=1,
                                content=doc.get("content", ""),
                                parent_id="-1",
                                path=doc.get("path", ""),
                                article_id=doc.get("id", ""),
                                score=doc.get("score", 0.5)
                            )
                            state["search_results"].append(node)
                    else:
                        logger.warning("⚠️ Simple search also returned no results")
                
                state["action_history"].append(AgentAction.SEARCH)
                
            except Exception as e:
                logger.error(f"❌ Simple search also failed: {e}")
                state["errors"].append(f"simple_search_error:{str(e)}")
            
            return state
    
    async def _search_weaviate_tree(self, query: str, limit: int = 5) -> List[TreeNode]:
        """
        جستجوی vector در ساختار درختی Weaviate
        
        🔥 ENHANCED: استفاده از near_text و اضافه کردن reranking
        """
        try:
            # استفاده از Connection Manager
            from app.infrastructure.connection_manager import weaviate_client
            with weaviate_client() as client:
                # جستجو در collection
                from app.core.weaviate_utils import get_weaviate_collection_name
                collection_name = get_weaviate_collection_name()
                collection = client.collections.get(collection_name)
                
                # 🔥 استفاده از near_text به جای near_vector (مثل RAG معمولی)
                search_response = collection.query.near_text(
                    query=query,
                    limit=limit,
                    return_metadata=['distance', 'certainty']
                )
                
                results = []
                for obj in search_response.objects:
                    # آماده‌سازی محتوای کامل برای reranking
                    node_content = obj.properties.get("content", "")
                    full_content = obj.properties.get("full_content", "")
                    
                    # ترکیب محتوا برای reranking (مثل RAG معمولی)
                    combined_content = f"Title: {obj.properties.get('title', '')}\nContent: {node_content}"
                    if full_content:
                        combined_content += f"\n\nFull Article: {full_content}..."
                    
                    node = TreeNode(
                        node_id=obj.properties.get("node_id", ""),
                        title=obj.properties.get("title", ""),
                        level=obj.properties.get("level", 1),
                        content=combined_content,  # محتوای ترکیبی
                        parent_id=obj.properties.get("parent_id", ""),
                        path=obj.properties.get("path", ""),
                        article_id=obj.properties.get("article_id", ""),
                        score=obj.metadata.certainty if hasattr(obj.metadata, 'certainty') else 0.5,
                        raw_content=node_content,  # 🔥 برای reranking
                        full_article_content=full_content  # 🔥 برای reranking
                    )
                    results.append(node)
                
                # 🔥 RERANKING اضافه شده (مثل RAG معمولی)
                logger.info(f"🎯 Applying RERANKING to {len(results)} results...")
                reranked_results = await self._rerank_documents(query, results, top_k=limit)
                logger.info(f"✅ RERANKING completed. Top {len(reranked_results)} results selected.")
                
                return reranked_results
            # client به صورت خودکار بسته می‌شود
            
        except Exception as e:
            logger.error(f"❌ Weaviate tree search error: {e}")
            return []
    
    async def _enrich_with_tree_context(self, nodes: List[TreeNode]) -> List[TreeNode]:
        """
        غنی‌سازی نتایج با context درختی (والدین و فرزندان)
        
        🔥 OPTIMIZED: استفاده از batch query برای جلوگیری از مشکل N+1
        """
        try:
            enriched_nodes = []
            
            # 🔥 OPTIMIZATION 1: جمع‌آوری تمام parent_id های یکتا
            parent_ids = set()
            for node in nodes:
                if node["parent_id"] and node["parent_id"] != "-1":
                    parent_ids.add(node["parent_id"])
            
            # 🔥 OPTIMIZATION 2: فقط یک درخواست به Weaviate برای گرفتن تمام parents
            parents_map = {}
            if parent_ids:
                logger.info(f"📊 Fetching {len(parent_ids)} parent nodes in single batch query...")
                parents_map = await self._fetch_nodes_by_ids(list(parent_ids))
                logger.info(f"✅ Fetched {len(parents_map)} parent nodes from Weaviate in a single query.")
            
            # 🔥 OPTIMIZATION 3: حلقه بدون درخواست اضافی
            for node in nodes:
                # افزودن node اصلی
                enriched_nodes.append(node)
                
                # اگر node والد دارد، آن را از map بگیر
                if node["parent_id"] and node["parent_id"] != "-1":
                    parent = parents_map.get(node["parent_id"])
                    if parent:
                        parent["score"] = node["score"] * 0.7  # score کمتر برای والد
                        enriched_nodes.append(parent)
                        
                        logger.info(f"   🔗 Added parent node: {parent['title'][:50]}")
            
            return enriched_nodes
            
        except Exception as e:
            logger.error(f"❌ Tree context enrichment error: {e}")
            return nodes
    
    async def _fetch_nodes_by_ids(self, node_ids: List[str]) -> Dict[str, TreeNode]:
        """
        دریافت چندین گره با استفاده از node_ids (batch query)
        
        🔥 OPTIMIZED: برای جلوگیری از N+1 Query Problem
        
        Args:
            node_ids: لیست node_id ها
        
        Returns:
            Dictionary mapping node_id to TreeNode
        """
        try:
            from app.infrastructure.connection_manager import weaviate_client
            from weaviate.classes.query import Filter
            
            nodes_map = {}
            
            if not node_ids:
                return nodes_map
            
            with weaviate_client() as client:
                from app.core.weaviate_utils import get_weaviate_collection_name
                collection_name = get_weaviate_collection_name()
                collection = client.collections.get(collection_name)
                
                # 🔥 استفاده از contains_any برای batch query
                response = collection.query.fetch_objects(
                    filters=Filter.by_property("node_id").contains_any(node_ids),
                    limit=len(node_ids)  # حداکثر به اندازه تعداد IDs
                )
                
                # ساخت map از نتایج
                for obj in response.objects:
                    node_id = obj.properties.get("node_id", "")
                    if node_id:
                        nodes_map[node_id] = TreeNode(
                            node_id=node_id,
                            title=obj.properties.get("title", ""),
                            level=obj.properties.get("level", 1),
                            content=obj.properties.get("content", ""),
                            parent_id=obj.properties.get("parent_id", ""),
                            path=obj.properties.get("path", ""),
                            article_id=obj.properties.get("article_id", ""),
                            score=0.5,
                            raw_content=obj.properties.get("content", ""),  # 🔥 اضافه شده
                            full_article_content=obj.properties.get("full_content", "")  # 🔥 اضافه شده
                        )
                
                return nodes_map
            
        except Exception as e:
            logger.error(f"❌ Batch node fetch error: {e}")
            return {}
    
    async def _fetch_node_by_id(self, node_id: str) -> Optional[TreeNode]:
        """
        دریافت یک گره با استفاده از node_id
        
        Note: این متد برای backward compatibility نگه داشته شده.
        برای performance بهتر از _fetch_nodes_by_ids استفاده کنید.
        """
        nodes_map = await self._fetch_nodes_by_ids([node_id])
    
    async def _rerank_documents(self, query: str, documents: List[TreeNode], top_k: int = 15) -> List[TreeNode]:
        """
        Rerank documents using external Reranker API (Colab) with fallback to local scoring.
        
        🔥 این متد از RAG service معمولی کپی شده است
        """
        # 🎯 تلاش برای استفاده از API خارجی
        reranker_api_url = settings.RERANKER_API_URL
        if reranker_api_url:
            try:
                import requests
                logger.debug(f"🚀 Reranking {len(documents)} documents with external API...")
                
                # 1️⃣ آماده‌سازی داده‌ها
                doc_contents = [doc.get("raw_content", doc.get("content", "")) for doc in documents]
                
                # 2️⃣ ساخت payload برای API
                payload = {
                    "query": query,
                    "documents": doc_contents
                }
                
                # 3️⃣ ارسال درخواست به API
                response = requests.post(
                    reranker_api_url,
                    json=payload,
                    timeout=settings.reranker_timeout
                )
                
                # 4️⃣ بررسی موفقیت
                response.raise_for_status()
                
                # 5️⃣ دریافت امتیازات
                result = response.json()
                scores = result.get("scores", [])
                
                if len(scores) != len(documents):
                    raise ValueError(f"Score count mismatch: got {len(scores)}, expected {len(documents)}")
                
                # 6️⃣ اعمال امتیازات جدید
                for idx, (doc, score) in enumerate(zip(documents, scores)):
                    doc["rerank_score"] = float(score)
                    doc["score"] = float(score)  # بروزرسانی score اصلی
                
                # 7️⃣ مرتب‌سازی بر اساس امتیازات جدید
                documents.sort(key=lambda x: x.get("rerank_score", -999), reverse=True)
                
                logger.debug(f"✅ API Reranking completed. Top score: {documents[0]['score']:.4f}")
                
                return documents[:top_k]
                
            except requests.exceptions.Timeout:
                logger.debug("❌ Reranker API timeout - falling back to local scoring")
            except requests.exceptions.ConnectionError:
                logger.debug("❌ Reranker API connection failed - falling back to local scoring")
            except Exception as e:
                logger.debug(f"❌ Reranker API error: {e} - falling back to local scoring")
        
        # 🔄 Fallback: scoring محلی
        logger.debug(f"⚙️ Using fallback local scoring for {len(documents)} documents...")
        
        try:
            import requests
            query_lower = query.lower()
            query_keywords = set(query_lower.split())
            
            for doc in documents:
                # شروع با vector score از Weaviate
                vector_score = doc.get("score", 0.5)
                
                # Keyword matching score
                content_lower = doc.get("raw_content", "").lower()
                title_lower = doc.get("title", "").lower()
                
                # تعداد کلمات مشترک
                content_keywords = set(content_lower.split())
                keyword_overlap = len(query_keywords & content_keywords)
                keyword_score = min(keyword_overlap / max(len(query_keywords), 1), 1.0)
                
                # Title matching
                title_score = 0.0
                for keyword in query_keywords:
                    if len(keyword) > 2 and keyword in title_lower:
                        title_score += 0.2
                title_score = min(title_score, 1.0)
                
                # ترکیب امتیازات: 60% vector, 25% keyword, 15% title
                combined_score = (0.60 * vector_score) + (0.25 * keyword_score) + (0.15 * title_score)
                
                doc["rerank_score"] = combined_score
                doc["score"] = combined_score
            
            # مرتب‌سازی
            documents.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)
            
            logger.debug(f"✅ Fallback reranking completed. Top score: {documents[0]['score']:.4f}")
            
            return documents[:top_k]
            
        except Exception as e:
            logger.debug(f"❌ Fallback reranking failed: {e}")
            # آخرین راه: برگرداندن documents با ترتیب اصلی
            documents.sort(key=lambda x: x.get("score", 0), reverse=True)
            return documents[:top_k]
        return nodes_map.get(node_id)
    
    async def aggregate_context(self, state: AgenticRAGState) -> AgenticRAGState:
        """
        جمع‌آوری و ترکیب context از نتایج مختلف
        """
        with PerformanceLogger(logger, "aggregate_context"):
            logger.info(f"🔗 Aggregating context from search results")
            
            try:
                results = state["search_results"]
                
                if not results:
                    logger.warning("⚠️ No search results to aggregate")
                    return state
                
                # گروه‌بندی بر اساس مقاله
                articles = {}
                for result in results:
                    article_id = result.get("article_id", "unknown")
                    if article_id not in articles:
                        articles[article_id] = []
                    articles[article_id].append(result)
                
                # مرتب‌سازی نتایج در هر مقاله بر اساس path (ترتیب درختی)
                for article_id in articles:
                    articles[article_id].sort(key=lambda x: x.get("path", ""))
                
                logger.info(f"✅ Aggregated {len(results)} nodes from {len(articles)} articles")
                state["action_history"].append(AgentAction.AGGREGATE)
                
            except Exception as e:
                logger.error(f"❌ Context aggregation failed: {e}")
                state["errors"].append(f"aggregation_error:{str(e)}")
            
            return state
    
    async def analyze_results(self, state: AgenticRAGState) -> AgenticRAGState:
        """
        تحلیل نتایج جستجو
        """
        with PerformanceLogger(logger, "analyze_results"):
            logger.info(f"🔬 Analyzing search results")
            
            try:
                results = state["search_results"]
                
                if not results:
                    logger.warning("⚠️ No results to analyze")
                    state["analyzed_results"] = []
                    return state
                
                analyzed = []
                for result in results[:5]:  # فقط top 5
                    analysis = {
                        "title": result.get("title", ""),
                        "path": result.get("path", ""),
                        "relevance": result.get("score", 0),
                        "level": result.get("level", 1),
                        "content_preview": result.get("content", "")[:200]
                    }
                    analyzed.append(analysis)
                
                state["analyzed_results"] = analyzed
                logger.info(f"✅ Analyzed {len(analyzed)} results")
                state["action_history"].append(AgentAction.ANALYZE)
                
            except Exception as e:
                logger.error(f"❌ Results analysis failed: {e}")
                state["errors"].append(f"analysis_error:{str(e)}")
            
            return state
    
    async def synthesize_answer(self, state: AgenticRAGState) -> AgenticRAGState:
        """
        ترکیب اطلاعات و تولید پاسخ نهایی با در نظر گرفتن تاریخچه
        """
        with PerformanceLogger(logger, "synthesize_answer"):
            logger.info(f"💡 Synthesizing final answer using {len(state['search_results'])} search results")
            
            try:
                # 🔥 ENHANCED: استفاده از تعداد بیشتر نتایج (افزایش از 5 به 8)
                results_to_use = state["search_results"][:8]  # افزایش تعداد نتایج
                
                # آماده‌سازی context از نتایج جستجو
                # 🔥 SMALL-TO-BIG RETRIEVAL (Phase 1): استفاده از full content با منطق بهتر
                context_parts = []
                total_content_length = 0
                max_context_length = 8000  # افزایش از 6000 به 8000 کاراکتر
                
                for idx, result in enumerate(results_to_use, 1):
                    # 🎯 استفاده از full content اگر موجود و مناسب باشد
                    full_content = result.get('full_article_content', '')
                    chunk_content = result.get('content', '')
                    title = result.get('title', '')
                    path = result.get('path', '')
                    
                    # منطق بهتر برای انتخاب محتوا:
                    # 1. اگر full content موجود است و کمتر از 2000 کاراکتر است، از آن استفاده کن
                    # 2. اگر بزرگتر از 2000 است، 1500 کاراکتر اولش را بگیر
                    # 3. اگر full content نداریم، chunk content را بگیر (افزایش از 1500 به 2000)
                    
                    if full_content and len(full_content) <= 2000:
                        content_to_use = full_content
                        logger.info(f"   📄 Result {idx}: Using FULL content ({len(full_content)} chars)")
                    elif full_content and len(full_content) > 2000:
                        content_to_use = full_content[:1500]  # محدودیت برای full content بزرگ
                        logger.info(f"   📄 Result {idx}: Using TRUNCATED full content ({len(content_to_use)} chars)")
                    else:
                        content_to_use = chunk_content[:2000]  # افزایش از 1500 به 2000 کاراکتر
                        logger.info(f"   📄 Result {idx}: Using extended chunk content ({len(content_to_use)} chars)")
                    
                    # بررسی کل طول context (حداکثر 8000 کاراکتر)
                    content_with_formatting = f"""
مسیر: {path}
عنوان: {title}
محتوا: {content_to_use}
---
"""
                    
                    if total_content_length + len(content_with_formatting) > max_context_length:
                        remaining_length = max_context_length - total_content_length
                        if remaining_length > 100:  # اگر فضای کافی موجود است
                            content_to_use = content_to_use[:remaining_length - 200]  # فضای رزرو برای formatting
                            content_with_formatting = f"""
مسیر: {path}
عنوان: {title}
محتوا: {content_to_use}...
---
"""
                            logger.info(f"   ⚠️ Result {idx}: Truncated to fit context limit (total: {total_content_length + len(content_with_formatting)} chars)")
                        else:
                            logger.info(f"   ⏭️ Result {idx}: Skipped to avoid context overflow")
                            continue
                    
                    context_parts.append(content_with_formatting)
                    total_content_length += len(content_with_formatting)
                
                context = "\n".join(context_parts)
                logger.info(f"📊 Total context length: {len(context)} characters ({len(context_parts)} sources included)")
                
                # آماده‌سازی تاریخچه مکالمه
                history_text = ""
                conversation_history = state.get("conversation_history", [])
                is_first_message = not conversation_history or len(conversation_history) == 0
                
                if is_first_message:
                    logger.info("👋 First message detected (Agentic RAG) - Bot will introduce itself")
                    history_text = "\n\n[هیچ تاریخچه‌ای وجود ندارد - این اولین پیام است]\n\n---\n"
                elif len(conversation_history) > 0:
                    logger.info(f"💬 Including conversation history ({len(conversation_history)} messages)")
                    history_text = "\n\nتاریخچه مکالمه:\n"
                    # افزایش تعداد پیام‌های تاریخچه از 5 به 7
                    recent_messages = conversation_history[-7:]
                    for msg in recent_messages:
                        role = "کاربر" if msg.get("role") == "user" else "دستیار"
                        content = msg.get("content", "")
                        history_text += f"{role}: {content}\n"
                    history_text += "\n---\n"
                
                # اگر زیرسوالات داشتیم، سوال اصلی را از state اولیه بگیر
                original_query = state.get("query")
                if state.get("decomposed_queries"):
                    # ترکیب همه زیرسوالات در prompt
                    subqueries_text = "\n".join([f"- {sq}" for sq in state["decomposed_queries"]])
                    query_text = f"""
{history_text}
سوال اصلی: {original_query}

زیرسوالات بررسی شده:
{subqueries_text}
"""
                else:
                    query_text = history_text + original_query
                
                # 🔥 تولید پاسخ با context کامل - استفاده از Power Model
                power_model = self._get_power_model()
                logger.info(f"🎯 Using power model for synthesis: {power_model}")
                
                result = await self.orchestrator.process_request(
                    query=query_text,
                    context=context,
                    custom_model=power_model
                )
                response = result.content
                
                state["final_response"] = response
                state["confidence_score"] = self._calculate_confidence(state)
                
                # 🔥 ENHANCED: استخراج منابع بیشتر (افزایش از 3 به 5)
                sources = []
                for result in state["search_results"][:5]:  # افزایش تعداد sources
                    sources.append({
                        "title": result.get("title", ""),
                        "path": result.get("path", ""),
                        "score": result.get("score", 0),
                        "article_id": result.get("article_id", "")
                    })
                state["sources"] = sources
                
                logger.info(f"✅ Answer synthesized (confidence: {state['confidence_score']:.2f})")
                logger.info(f"📝 Response length: {len(state['final_response'])} characters")
                logger.info(f"📚 Sources extracted: {len(state['sources'])} (enhanced selection)")
                logger.info(f"🔍 Context details: {len(context_parts)} sources, {len(context)} chars total")
                state["action_history"].append(AgentAction.SYNTHESIZE)
                
            except Exception as e:
                logger.error(f"❌ Answer synthesis failed: {e}")
                state["final_response"] = "متأسفانه نمی‌توانم پاسخی تولید کنم."
                state["confidence_score"] = 0.0
                state["errors"].append(f"synthesis_error:{str(e)}")
            
            return state
    
    async def reflect_on_answer(self, state: AgenticRAGState) -> AgenticRAGState:
        """
        بازبینی و ارزیابی کیفیت پاسخ
        """
        with PerformanceLogger(logger, "reflect_on_answer"):
            logger.info(f"🤔 Reflecting on answer quality")
            
            try:
                if not state["final_response"]:
                    state["reflection_notes"].append("No response generated")
                    state["confidence_score"] = 0.0
                    return state
                
                # بررسی‌های خودکار
                checks = []
                
                # 1. بررسی طول پاسخ
                if len(state["final_response"]) < 50:
                    checks.append("Response too short")
                    state["confidence_score"] *= 0.7
                
                # 2. بررسی وجود منابع
                if not state["sources"]:
                    checks.append("No sources found")
                    state["confidence_score"] *= 0.8
                
                # 3. بررسی تعداد نتایج
                if len(state["search_results"]) < 2:
                    checks.append("Limited search results")
                    state["confidence_score"] *= 0.9
                
                if checks:
                    state["reflection_notes"].extend(checks)
                    logger.warning(f"⚠️ Quality issues: {', '.join(checks)}")
                else:
                    logger.info(f"✅ Answer quality looks good")
                
                state["action_history"].append(AgentAction.REFLECT)
                
            except Exception as e:
                logger.error(f"❌ Reflection failed: {e}")
                state["errors"].append(f"reflection_error:{str(e)}")
            
            return state
    
    def _get_fast_model(self) -> str:
        """
        دریافت مدل سریع برای وظایف ساده
        
        🔥 Unified Model Strategy: برای کاهش هزینه و افزایش سرعت
        """
        # Use ModelFactory for fast model selection
        try:
            fast_model = model_factory.get_optimal_model("chat")
            logger.info(f"⚡ Agentic RAG - Using FAST model: {fast_model}")
            return fast_model
        except Exception as e:
            logger.warning(f"⚠️ ModelFactory fast model selection failed: {e}")
            return self._select_model_by_strategy("fast")
    
    def _get_power_model(self) -> str:
        """
        دریافت مدل قدرتمند برای وظایف پیچیده
        
        🔥 Unified Model Strategy: برای کیفیت بالاتر در وظایف مهم
        """
        # Use ModelFactory for power model selection
        try:
            power_model = model_factory.get_optimal_model("rag")
            logger.info(f"🚀 Agentic RAG - Using POWER model: {power_model}")
            return power_model
        except Exception as e:
            logger.warning(f"⚠️ ModelFactory power model selection failed: {e}")
            return self._select_model_by_strategy("power")
    
    def _select_model_by_strategy(self, strategy: str) -> str:
        """
        🆕 Unified model selection logic based on strategy and system requirements using ModelFactory
        
        Args:
            strategy: "fast", "power", or "balanced"
            
        Returns:
            Selected model name
            
        Strategy Documentation:
        - fast: Prioritizes speed and cost efficiency for simple tasks
        - power: Prioritizes quality and capability for complex tasks
        - balanced: Uses hybrid approach for moderate complexity tasks
        """
        try:
            # Map strategy to task type for ModelFactory
            strategy_mapping = {
                "fast": "chat",      # Fast tasks use chat models
                "power": "rag",      # Complex tasks use RAG models
                "balanced": "rag"    # Balanced approach uses RAG models
            }
            
            task_type = strategy_mapping.get(strategy, "rag")
            
            # Get optimal model from ModelFactory
            selected_model = model_factory.get_optimal_model(task_type)
            
            # Log the selection
            self._log_model_selection(strategy, selected_model, f"ModelFactory selected optimal model for {task_type} task")
            
            return selected_model
            
        except Exception as e:
            logger.warning(f"⚠️ ModelFactory selection failed for strategy '{strategy}', using fallback: {e}")
            # Fallback to original logic
            if strategy == "fast":
                if settings.use_hybrid_model_strategy and settings.agentic_fast_model:
                    selected_model = settings.agentic_fast_model
                    self._log_model_selection("fast", selected_model, "Hybrid strategy - Fast model configured")
                else:
                    selected_model = settings.chat_model_loaded
                    self._log_model_selection("fast", selected_model, "Using chat model as fallback")
                    
            elif strategy == "power":
                if settings.use_hybrid_model_strategy and settings.agentic_power_model:
                    selected_model = settings.agentic_power_model
                    self._log_model_selection("power", selected_model, "Hybrid strategy - Power model configured")
                else:
                    selected_model = settings.rag_model_loaded
                    self._log_model_selection("power", selected_model, "Using RAG model as fallback")
                    
            else:  # balanced
                if settings.use_hybrid_model_strategy:
                    selected_model = settings.agentic_power_model if settings.agentic_power_model else settings.rag_model_loaded
                    self._log_model_selection("balanced", selected_model, "Hybrid strategy - Balanced approach")
                else:
                    selected_model = settings.rag_model_loaded
                    self._log_model_selection("balanced", selected_model, "Using RAG model for balanced approach")
            
            return selected_model
    
    def _log_model_selection(self, strategy: str, model_name: str, reason: str):
        """
        🆕 Log model selection with detailed reasoning for transparency
        
        Args:
            strategy: The strategy used for selection
            model_name: The selected model name
            reason: The reason for selection
        """
        logger.info(f"🎯 Model Selection Strategy: {strategy.upper()}")
        logger.info(f"🤖 Selected Model: {model_name}")
        logger.info(f"📋 Reason: {reason}")
        
        # Log model capabilities and limitations
        if "gpt-4" in model_name.lower():
            logger.info("🔥 Model Capabilities: High reasoning, complex tasks, detailed analysis")
        elif "gpt-3.5" in model_name.lower() or "gpt-4o-mini" in model_name.lower():
            logger.info("🔥 Model Capabilities: Fast responses, cost-effective, good for simple tasks")
        elif "gemini" in model_name.lower():
            logger.info("🔥 Model Capabilities: Multi-modal, creative tasks, good context understanding")
        else:
            logger.info("🔥 Model Capabilities: Standard AI capabilities")
    
    def _calculate_confidence(self, state: AgenticRAGState) -> float:
        """
        محاسبه confidence score بر اساس کیفیت نتایج
        """
        base_confidence = 0.5
        
        # افزایش بر اساس تعداد نتایج
        results_count = len(state["search_results"])
        if results_count >= 5:
            base_confidence += 0.2
        elif results_count >= 3:
            base_confidence += 0.15
        elif results_count >= 1:
            base_confidence += 0.1
        
        # افزایش بر اساس میانگین score نتایج
        if state["search_results"]:
            avg_score = sum(r.get("score", 0) for r in state["search_results"]) / len(state["search_results"])
            base_confidence += avg_score * 0.2
        
        # کاهش بر اساس خطاها
        if state.get("errors"):
            base_confidence *= 0.8
        
        return min(base_confidence, 1.0)
    
    def should_use_fallback(self, state: AgenticRAGState) -> str:
        """
        تصمیم‌گیری برای استفاده از fallback
        
        🔥 اگر tree_search شکست خورد یا نتیجه‌ای پیدا نکرد، به simple_search هدایت می‌شود
        """
        # بررسی flag نیاز به fallback
        if state.get("needs_fallback", False):
            logger.info("🔄 Tree search failed, using fallback to simple search")
            return "use_fallback"
        
        # بررسی اینکه آیا نتیجه‌ای پیدا شده یا نه
        if not state["search_results"] or len(state["search_results"]) == 0:
            logger.info("🔄 No results from tree search, using fallback")
            return "use_fallback"
        
        logger.info("✅ Tree search successful, continuing normally")
        return "continue"
    
    def route_by_complexity(self, state: AgenticRAGState) -> str:
        """
        مسیریابی بر اساس پیچیدگی سوال
        """
        complexity = state.get("query_complexity", QueryComplexity.SIMPLE)
        
        if complexity == QueryComplexity.SIMPLE:
            logger.info("➡️ Routing to direct tree search (simple query)")
            return "simple"
        elif complexity == QueryComplexity.MODERATE:
            logger.info("➡️ Routing to strategy planning (moderate query)")
            return "moderate"
        else:
            logger.info("➡️ Routing to query decomposition (complex query)")
            return "complex"
    
    def should_retry_or_finish(self, state: AgenticRAGState) -> str:
        """
        تصمیم برای retry یا اتمام
        """
        # اگر confidence خیلی پایین و تعداد retry کمتر از max است
        if state["confidence_score"] < 0.3 and state["retry_count"] < state["max_retries"]:
            state["retry_count"] += 1
            logger.info(f"🔄 Low confidence ({state['confidence_score']:.2f}), retrying... (attempt {state['retry_count']})")
            return "retry"
        
        logger.info(f"✅ Finishing workflow (confidence: {state['confidence_score']:.2f})")
        return "finish"

    def should_use_multi_hop(self, state: AgenticRAGState) -> str:
        """
        🔥 تصمیم‌گیری برای استفاده از Multi-hop Retrieval

        استراتژی:
        - اگر سوال نیاز به چندین مرحله جستجو دارد (multi-hop)
        - اگر نتایج اولیه کافی نیستند و سوال نیاز به entities مرتبط دارد
        - اگر سوال comparative یا analytical است
        """
        query = state.get("query", "").lower()
        search_results = state.get("search_results", [])
        query_complexity = state.get("query_complexity", QueryComplexity.SIMPLE)

        # بررسی الگوهای multi-hop
        multi_hop_indicators = [
            "چرا", "چگونه", "مقایسه", "تفاوت", "ارتباط", "تأثیر",
            "نحوه", "چه زمانی", "کجا", "کی", "چه کسی", "چرا",
            "who was", "what is the relationship", "how does",
            "compare", "difference between", "impact of"
        ]

        # اگر سوال پیچیده است یا نشانگرهای multi-hop دارد
        if query_complexity == QueryComplexity.COMPLEX or any(indicator in query for indicator in multi_hop_indicators):
            # بررسی اینکه آیا نتایج اولیه کافی هستند
            if len(search_results) < 3 or state.get("needs_more_context", False):
                logger.info("🔗 Using multi-hop retrieval for complex/analytical query")
                return "multi_hop"
            else:
                logger.info("📄 Using simple aggregation (sufficient initial results)")
                return "simple"
        elif not search_results or len(search_results) == 0:
            logger.info("🔄 No results found, using fallback search")
            return "fallback"
        else:
            logger.info("📄 Using simple aggregation")
            return "simple"

    async def multi_hop_search(self, state: AgenticRAGState) -> AgenticRAGState:
        """
        🔥 Multi-hop Retrieval: جستجوی چندمرحله‌ای

        استراتژی:
        1. استخراج entities/concepts کلیدی از نتایج اولیه
        2. جستجوی ثانویه بر اساس entities استخراج شده
        3. ترکیب اطلاعات از چندین hop
        """
        with PerformanceLogger(logger, "multi_hop_search"):
            logger.info("🔍 Starting multi-hop retrieval process")

            initial_results = state["search_results"]
            query = state["query"]

            # Hop 1: استخراج entities کلیدی از نتایج اولیه
            logger.info("🎯 Hop 1: Extracting key entities from initial results")
            key_entities = await self._extract_key_entities(initial_results, query)

            if not key_entities:
                logger.info("⚠️ No key entities found, skipping multi-hop")
                return state

            logger.info(f"📋 Found {len(key_entities)} key entities: {key_entities[:5]}")

            # Hop 2: جستجوی ثانویه بر اساس entities
            logger.info("🔍 Hop 2: Performing secondary search based on entities")
            secondary_results = []

            for entity in key_entities[:5]:  # محدود به 5 entity برتر
                try:
                    # ساخت query جدید بر اساس entity
                    entity_query = f"{query} {entity}"
                    logger.debug(f"   🔎 Searching for: '{entity_query}'")

                    # جستجوی entity در Weaviate
                    entity_results = await self._search_weaviate_by_entity(entity_query)

                    # اضافه کردن entity به نتایج
                    for result in entity_results:
                        result["hop"] = 2
                        result["related_entity"] = entity
                        secondary_results.append(result)

                except Exception as e:
                    logger.warning(f"⚠️ Failed to search for entity '{entity}': {e}")
                    continue

            # ترکیب نتایج از هر دو hop
            all_results = initial_results + secondary_results
            logger.info(f"📊 Combined results: {len(initial_results)} initial + {len(secondary_results)} secondary = {len(all_results)} total")

            # حذف duplicate ها بر اساس node_id
            seen_node_ids = set()
            unique_results = []
            for result in all_results:
                node_id = result.get("node_id")
                if node_id and node_id not in seen_node_ids:
                    seen_node_ids.add(node_id)
                    unique_results.append(result)
                elif not node_id:
                    unique_results.append(result)

            state["search_results"] = unique_results
            state["multi_hop_performed"] = True
            state["hop_count"] = 2

            logger.info(f"✅ Multi-hop search completed: {len(unique_results)} unique results")
            return state

    async def _extract_key_entities(self, results: List[TreeNode], original_query: str) -> List[str]:
        """
        استخراج entities/concepts کلیدی از نتایج جستجو
        """
        try:
            # ترکیب محتوای نتایج برای استخراج entities
            combined_content = ""
            for result in results[:5]:  # استفاده از 5 نتیجه برتر
                content = result.get("content", "")
                combined_content += content[:500] + " "  # محدود به 500 کاراکتر per result

            # استفاده از LLM برای استخراج entities
            from app.infrastructure.model_factory import model_factory

            entity_extraction_prompt = f"""
            Analyze this content and extract 3-5 key entities, concepts, or proper nouns that are most relevant to the query.

            Query: {original_query}

            Content:
            {combined_content[:1500]}

            Return only a comma-separated list of entities (no explanations):
            """

            llm = model_factory.create_model("fast")
            response = await llm.agenerate([entity_extraction_prompt])

            if hasattr(response, 'content'):
                entities_text = response.content
            elif isinstance(response, list) and response:
                entities_text = response[0].content if hasattr(response[0], 'content') else str(response[0])

            # پردازش پاسخ و استخراج entities
            entities = []
            for entity in entities_text.split(','):
                entity = entity.strip()
                if entity and len(entity) > 1:  # حداقل 2 کاراکتر
                    entities.append(entity)

            return entities[:5]  # حداکثر 5 entity

        except Exception as e:
            logger.warning(f"⚠️ Entity extraction failed: {e}")
            return []

    async def _search_weaviate_by_entity(self, entity_query: str) -> List[Dict[str, Any]]:
        """
        جستجوی entity-specific در Weaviate
        """
        try:
            from app.infrastructure.connection_manager import weaviate_client
            from app.core.weaviate_utils import get_weaviate_collection_name

            with weaviate_client() as client:
                collection_name = get_weaviate_collection_name()
                collection = client.collections.get(collection_name)

                # جستجوی entity با limit کمتر
                response = collection.query.near_text(
                    query=entity_query,
                    limit=3  # محدود به 3 نتیجه per entity
                )

                entity_results = []
                for obj in response.objects:
                    entity_results.append({
                        "node_id": obj.properties.get("node_id"),
                        "title": obj.properties.get("title"),
                        "content": obj.properties.get("raw_content", obj.properties.get("content", "")),
                        "score": obj.metadata.certainty if hasattr(obj.metadata, 'certainty') else 0.5,
                        "path": obj.properties.get("path"),
                        "source": "weaviate_entity_search"
                    })

                return entity_results

        except Exception as e:
            logger.warning(f"⚠️ Entity search failed for '{entity_query}': {e}")
            return []

    def should_use_external_tools(self, state: AgenticRAGState) -> str:
        """
        🔥 تصمیم‌گیری برای استفاده از ابزارهای خارجی

        استراتژی:
        - اگر سوال نیاز به اطلاعات به‌روز وب دارد
        - اگر سوال شامل محاسبات است
        - اگر سوال درباره زمان/تاریخ فعلی است
        - اگر اطلاعات داخلی کافی نیست
        """
        query = state.get("query", "").lower()
        aggregated_results = state.get("aggregated_context", {})
        confidence = state.get("confidence_score", 1.0)

        # نشانگرهای نیاز به ابزارهای خارجی
        web_search_indicators = [
            "اخبار", "به‌روز", "جدیدترین", "امسال", "حالا", "کنون",
            "news", "current", "latest", "today", "now"
        ]

        calculation_indicators = [
            "محاسبه", "حساب", "ریاضی", "جمع", "تفريق", "ضرب", "تقسیم",
            "calculate", "math", "sum", "multiply", "divide"
        ]

        datetime_indicators = [
            "زمان", "تاریخ", "ساعت", "امروز", "دیروز", "فردا",
            "time", "date", "today", "yesterday", "tomorrow"
        ]

        # بررسی نیاز به web search
        if any(indicator in query for indicator in web_search_indicators):
            logger.info("🌐 Using web search for current information")
            return "use_tools"

        # بررسی نیاز به محاسبات
        if any(indicator in query for indicator in calculation_indicators):
            logger.info("🔢 Using calculator for mathematical queries")
            return "use_tools"

        # بررسی نیاز به datetime
        if any(indicator in query for indicator in datetime_indicators):
            logger.info("🕒 Using datetime tool for time-related queries")
            return "use_tools"

        # اگر confidence پایین است و اطلاعات کافی نداریم
        if confidence < 0.6 and len(aggregated_results.get("sources", [])) < 2:
            logger.info("📊 Low confidence, using external tools for additional information")
            return "use_tools"

        logger.info("📝 Proceeding to synthesis (sufficient internal information)")
        return "synthesize"

    async def use_external_tools(self, state: AgenticRAGState) -> AgenticRAGState:
        """
        🔥 Function Calling: استفاده از ابزارهای LangChain

        استراتژی:
        1. LLM با ابزارها bind می‌شود
        2. LLM تصمیم می‌گیرد کدام ابزار را استفاده کند
        3. ابزارها به صورت خودکار اجرا می‌شوند
        4. نتایج به context اضافه می‌شود
        """
        with PerformanceLogger(logger, "use_external_tools"):
            logger.info("🔧 Starting LangChain tools execution")

            query = state["query"]
            aggregated_context = state.get("aggregated_context", {})

            try:
                # دریافت LLM و bind کردن با ابزارها
                llm = model_factory.create_model("fast")
                llm_with_tools = llm.bind_tools(LANGCHAIN_TOOLS)

                # فراخوانی LLM با ابزارها
                messages = [HumanMessage(content=f"Answer this query using available tools if needed: {query}")]
                response = await llm_with_tools.ainvoke(messages)

                tool_results = []

                # بررسی آیا ابزار فراخوانی شده است
                if hasattr(response, 'tool_calls') and response.tool_calls:
                    logger.info(f"🛠️ LLM requested {len(response.tool_calls)} tool calls")

                    # اجرای ابزارهای درخواست شده
                    for tool_call in response.tool_calls:
                        try:
                            tool_name = tool_call["name"]
                            tool_args = tool_call["args"]

                            logger.info(f"🔧 Executing tool: {tool_name} with args: {tool_args}")

                            # یافتن ابزار مناسب
                            tool_func = None
                            for tool in LANGCHAIN_TOOLS:
                                if tool.name == tool_name:
                                    tool_func = tool
                                    break

                            if tool_func:
                                # اجرای ابزار
                                result = await tool_func.ainvoke(tool_args)
                                tool_results.append({
                                    "tool": tool_name,
                                    "query": query,
                                    "args": tool_args,
                                    "result": result,
                                    "timestamp": datetime.now().isoformat()
                                })
                                logger.info(f"✅ Tool '{tool_name}' executed successfully")
                            else:
                                logger.warning(f"⚠️ Tool '{tool_name}' not found")

                        except Exception as e:
                            logger.warning(f"⚠️ Tool execution failed: {e}")
                else:
                    logger.info("ℹ️ LLM did not request any tools")

                # اضافه کردن نتایج ابزارها به context
                if tool_results:
                    state["external_tool_results"] = tool_results
                    state["tools_used"] = [r["tool"] for r in tool_results]

                    # اضافه کردن به aggregated_context
                    if "external_sources" not in aggregated_context:
                        aggregated_context["external_sources"] = []

                    for result in tool_results:
                        aggregated_context["external_sources"].append(result)

                    state["aggregated_context"] = aggregated_context
                    logger.info(f"📊 Added {len(tool_results)} LangChain tool results to context")
                else:
                    logger.info("ℹ️ No tool results to add to context")

                return state

            except Exception as e:
                logger.warning(f"⚠️ LangChain tools execution failed: {e}")
                return state

    def _simple_tool_selection(self, query: str) -> List[str]:
        """انتخاب ساده ابزار بر اساس کلمات کلیدی"""
        query_lower = query.lower()
        tools = []

        if any(word in query_lower for word in ["اخبار", "به‌روز", "جدیدترین", "news", "current"]):
            tools.append("web_search")

        if any(word in query_lower for word in ["محاسبه", "حساب", "calculate", "math"]):
            tools.append("calculate")

        if any(word in query_lower for word in ["زمان", "تاریخ", "time", "date", "today"]):
            tools.append("get_current_datetime")

        return tools[:2]  # حداکثر 2 ابزار

    async def _execute_tool(self, tool_name: str, query: str) -> Optional[Dict[str, Any]]:
        """اجرای یک ابزار خاص"""
        try:
            if tool_name == "web_search":
                return await self._execute_web_search(query)
            elif tool_name == "calculate":
                return await self._execute_calculator(query)
            elif tool_name == "get_current_datetime":
                return await self._execute_datetime_tool(query)
            else:
                logger.warning(f"⚠️ Unknown tool: {tool_name}")
                return None
        except Exception as e:
            logger.warning(f"⚠️ Tool execution failed for '{tool_name}': {e}")
            return None

    async def _execute_web_search(self, query: str) -> Dict[str, Any]:
        """اجرای جستجوی وب"""
        try:
            # استفاده از DuckDuckGo Instant Answer API یا مشابه
            # در صورت عدم دسترسی، از mock data استفاده می‌کنیم
            import requests

            # جستجوی ساده DuckDuckGo
            search_url = f"https://api.duckduckgo.com/?q={query}&format=json&no_html=1"

            response = requests.get(search_url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                answer = data.get("Answer", "")
                if not answer:
                    answer = data.get("AbstractText", "No direct answer found")

                return {
                    "tool": "web_search",
                    "query": query,
                    "result": answer[:500],  # محدود به 500 کاراکتر
                    "source": "DuckDuckGo Instant Answer"
                }
            else:
                # Fallback
                return {
                    "tool": "web_search",
                    "query": query,
                    "result": f"Web search simulation: Results for '{query}' would be shown here.",
                    "source": "Fallback"
                }

        except Exception as e:
            logger.warning(f"Web search failed: {e}")
            return {
                "tool": "web_search",
                "query": query,
                "result": f"Web search unavailable: {str(e)}",
                "source": "Error"
            }

    async def _execute_calculator(self, query: str) -> Dict[str, Any]:
        """اجرای ماشین حساب"""
        try:
            # استخراج عبارت ریاضی از query
            import re

            # جستجوی الگوهای ریاضی ساده
            math_patterns = [
                r'(\d+(?:\.\d+)?)\s*[\+\-\*\/]\s*(\d+(?:\.\d+)?)',  # عملیات پایه
                r'sqrt\((\d+(?:\.\d+)?)\)',  # جذر
                r'(\d+(?:\.\d+)?)\s*\^\s*(\d+(?:\.\d+)?)',  # توان
            ]

            for pattern in math_patterns:
                match = re.search(pattern, query)
                if match:
                    expression = match.group(0)
                    result = self._calculate_expression(expression)
                    return {
                        "tool": "calculate",
                        "query": query,
                        "result": f"Result of '{expression}' = {result}",
                        "expression": expression,
                        "calculated_result": result
                    }

            return {
                "tool": "calculate",
                "query": query,
                "result": "Could not identify mathematical expression in query",
                "expression": None,
                "calculated_result": None
            }

        except Exception as e:
            logger.warning(f"Calculator failed: {e}")
            return {
                "tool": "calculate",
                "query": query,
                "result": f"Calculation failed: {str(e)}",
                "expression": None,
                "calculated_result": None
            }

    def _calculate_expression(self, expression: str) -> str:
        """محاسبه عبارت ریاضی ساده"""
        try:
            # جایگزینی عملیات فارسی
            expression = expression.replace("×", "*").replace("÷", "/")

            # محاسبات امن
            if "sqrt(" in expression:
                import math
                num = float(re.search(r'sqrt\((\d+(?:\.\d+)?)\)', expression).group(1))
                return str(math.sqrt(num))
            elif "^" in expression:
                base, exp = expression.split("^")
                return str(float(base.strip()) ** float(exp.strip()))
            else:
                # استفاده از eval با محدودیت‌های امنیتی
                allowed_chars = "0123456789.+-*/()"
                if all(c in allowed_chars for c in expression):
                    result = eval(expression)
                    return str(result)
                else:
                    return "Unsupported operation"

        except Exception as e:
            return f"Error: {str(e)}"

    async def _execute_datetime_tool(self, query: str) -> Dict[str, Any]:
        """اجرای ابزار تاریخ/زمان"""
        try:
            from datetime import datetime
            import pytz

            # منطقه زمانی تهران
            tehran_tz = pytz.timezone('Asia/Tehran')
            now = datetime.now(tehran_tz)

            result = f"Current date and time in Tehran: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}"

            return {
                "tool": "get_current_datetime",
                "query": query,
                "result": result,
                "datetime": now.isoformat(),
                "timezone": "Asia/Tehran"
            }

        except Exception as e:
            logger.warning(f"Datetime tool failed: {e}")
            return {
                "tool": "get_current_datetime",
                "query": query,
                "result": f"Could not get current datetime: {str(e)}",
                "datetime": None,
                "timezone": None
            }

    async def run(self, 
                  query: str, 
                  user_id: Optional[str] = None,
                  conversation_history: Optional[List] = None) -> Dict[str, Any]:
        """
        اجرای کامل Agentic RAG workflow
        
        Args:
            query: سوال کاربر
            user_id: شناسه کاربر (اختیاری)
            conversation_history: تاریخچه مکالمه (اختیاری)
            
        Returns:
            نتیجه نهایی شامل پاسخ، منابع، و metadata
        """
        
        with PerformanceLogger(logger, "advanced_agentic_rag", query=query[:100]):
            
            # 🔥 comprehensive logging and monitoring
            logger.info("="*80)
            logger.info("🚀 Advanced Agentic RAG System - Starting Workflow")
            logger.info(f"📊 System Status:")
            logger.info(f"   - LangGraph Available: {LANGGRAPH_AVAILABLE}")
            logger.info(f"   - Graph Compiled: {self.graph is not None}")
            logger.info(f"   - Hybrid Model Strategy: {settings.use_hybrid_model_strategy}")
            logger.info(f"   - Configuration Validated: {self._validate_configuration() if hasattr(self, '_validate_configuration') else 'N/A'}")
            logger.info("="*80)
            
            if not LANGGRAPH_AVAILABLE or not self.graph:
                logger.warning("⚠️ LangGraph not available, using fallback")
                return await self._fallback_simple_rag(query)
            
            # State اولیه
            initial_state: AgenticRAGState = {
                "query": query,
                "user_id": user_id,
                "session_id": str(uuid.uuid4()),
                "conversation_history": conversation_history or [],
                "query_complexity": None,
                "decomposed_queries": [],
                "current_subquery_index": 0,
                "search_results": [],
                "tree_context": {},
                "analyzed_results": [],
                "partial_answers": [],
                "final_response": None,
                "confidence_score": 0.0,
                "sources": [],
                "current_action": None,
                "action_history": [],
                "reflection_notes": [],
                "errors": [],
                "retry_count": 0,
                "max_retries": 1,
                "needs_fallback": False  # 🔥 مدیریت fallback
            }
            
            try:
                logger.info("="*80)
                logger.info("🚀 Starting Advanced Agentic RAG Workflow")
                logger.info(f"📝 Query: {query}")
                logger.info(f"🆔 Session: {initial_state['session_id']}")
                logger.info(f"👤 User ID: {user_id or 'Anonymous'}")
                logger.info(f"💬 Conversation History: {len(conversation_history) if conversation_history else 0} messages")
                logger.info("="*80)
                
                # اجرای workflow
                final_state = await self.graph.ainvoke(initial_state)
                
                # آمارگیری
                total_actions = len(final_state["action_history"])
                unique_actions = len(set(final_state["action_history"]))
                
                logger.info("="*80)
                logger.info("✅ Workflow Completed Successfully")
                logger.info(f"🎯 Confidence: {final_state['confidence_score']:.2f}")
                logger.info(f"📊 Total Actions: {total_actions} ({unique_actions} unique)")
                logger.info(f"🔍 Search Results: {len(final_state['search_results'])}")
                logger.info(f"📚 Sources: {len(final_state['sources'])}")
                logger.info(f"⚠️  Errors: {len(final_state['errors'])}")
                logger.info(f"💭 Reflection Notes: {len(final_state['reflection_notes'])}")
                logger.info(f"🔄 Query Complexity: {final_state['query_complexity'].value if final_state['query_complexity'] else 'unknown'}")
                logger.info(f"🔄 Retry Count: {final_state['retry_count']}")
                logger.info("="*80)
                
                # لاگ action history
                logger.info("📋 Action History:")
                for i, action in enumerate(final_state["action_history"], 1):
                    logger.info(f"   {i}. {action.value}")

                # لاگ errors اگر وجود داشته باشد
                if final_state["errors"]:
                    logger.info("❌ Errors Encountered:")
                    for i, error in enumerate(final_state["errors"], 1):
                        logger.info(f"   {i}. {error}")

                # لاگ reflection notes اگر وجود داشته باشد
                if final_state["reflection_notes"]:
                    logger.info("💭 Reflection Notes:")
                    for i, note in enumerate(final_state["reflection_notes"], 1):
                        logger.info(f"   {i}. {note}")
                
                return {
                    "response": final_state["final_response"],
                    "confidence": final_state["confidence_score"],
                    "metadata": {
                        "sources": final_state["sources"],
                        "complexity": final_state["query_complexity"].value if final_state["query_complexity"] else "unknown",
                        "actions_taken": [a.value for a in final_state["action_history"]],
                        "reflection_notes": final_state["reflection_notes"],
                        "errors": final_state["errors"],
                        "session_id": final_state["session_id"],
                        "model": self._get_power_model(),  # اضافه کردن مدل استفاده شده
                        "rag_type": "agentic"
                    }
                }
                
            except Exception as e:
                logger.error(f"❌ Workflow failed: {e}", exc_info=True)
                return await self._fallback_simple_rag(query)
    
    async def _fallback_simple_rag(self, query: str) -> Dict[str, Any]:
        """
        Fallback به RAG ساده در صورت خطا
        """
        logger.info("🔄 Using fallback simple RAG")
        
        try:
            # استفاده از rag_service موجود
            result = await self.rag_service.generate_response(query)
            
            return {
                "response": result.get("response", "متأسفانه نمی‌توانم پاسخی ارائه دهم."),
                "confidence": result.get("confidence", 0.5),
                "metadata": {
                    "sources": result.get("sources", []),
                    "complexity": "unknown",
                    "actions_taken": ["fallback"],
                    "reflection_notes": [],
                    "errors": ["Using fallback mode"],
                    "session_id": str(uuid.uuid4()),
                    "model": settings.rag_model_loaded,
                    "rag_type": "fallback"
                }
            }
        except Exception as e:
            logger.error(f"❌ Fallback RAG also failed: {e}")
            return {
                "response": "متأسفانه خطایی رخ داده است.",
                "confidence": 0.0,
                "metadata": {
                    "sources": [],
                    "complexity": "unknown",
                    "actions_taken": [],
                    "reflection_notes": [],
                    "errors": [str(e)],
                    "session_id": str(uuid.uuid4()),
                    "model": "error",
                    "rag_type": "error"
                }
            }


# Global instance
advanced_agentic_rag = None


def get_advanced_agentic_rag(orchestrator, rag_service, weaviate_connector=None):
    """
    دریافت یا ایجاد instance
    """
    global advanced_agentic_rag
    
    if advanced_agentic_rag is None:
        advanced_agentic_rag = AdvancedAgenticRAG(
            orchestrator, 
            rag_service,
            weaviate_connector
        )
    
    return advanced_agentic_rag