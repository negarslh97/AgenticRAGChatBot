"""
LangGraph Workflows برای RAG پیشرفته

این ماژول شامل workflow‌های پیچیده برای:
- Multi-step RAG با routing هوشمند
- Self-reflection و query refinement  
- Parallel document retrieval
- Adaptive RAG با fallback strategies
- Conversational RAG با memory
"""

from typing import Dict, Any, List, Optional, Tuple, Annotated
from typing_extensions import TypedDict
from enum import Enum
import operator

from app.core.logging_config import get_logger, PerformanceLogger
from app.core.config import settings

logger = get_logger(__name__)

try:
    from langgraph.graph import StateGraph, END
    from langgraph.prebuilt import ToolExecutor, ToolInvocation
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    logger.warning("⚠️ LangGraph not installed. Advanced workflows will not be available.")

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser


class RAGStrategy(str, Enum):
    """استراتژی‌های مختلف RAG"""
    SIMPLE = "simple"              # جستجوی ساده vector
    HYBRID = "hybrid"              # ترکیب vector + keyword
    RERANK = "rerank"              # با re-ranking
    ITERATIVE = "iterative"        # چند مرحله‌ای با refinement
    ADAPTIVE = "adaptive"          # انتخاب خودکار بهترین استراتژی


class QueryType(str, Enum):
    """انواع query"""
    FACTUAL = "factual"            # سوال واقعی که نیاز به دانش دارد
    CONVERSATIONAL = "conversational"  # گفتگوی معمولی
    PROCEDURAL = "procedural"      # نیاز به مراحل گام به گام
    COMPARISON = "comparison"      # مقایسه بین چیزها
    CLARIFICATION = "clarification"  # نیاز به توضیح بیشتر


class WorkflowState(TypedDict):
    """
    State برای workflow
    """
    # ورودی کاربر
    query: str
    query_type: Optional[QueryType]
    user_id: Optional[str]
    conversation_history: List[Dict[str, str]]
    
    # مراحل پردازش
    refined_query: Optional[str]
    search_strategy: Optional[RAGStrategy]
    
    # نتایج retrieval
    retrieved_documents: List[Dict[str, Any]]
    reranked_documents: List[Dict[str, Any]]
    
    # تولید پاسخ
    generated_response: Optional[str]
    confidence_score: float
    sources: List[Dict[str, Any]]
    
    # Metadata
    workflow_steps: Annotated[List[str], operator.add]
    errors: Annotated[List[str], operator.add]


class AdaptiveRAGWorkflow:
    """
    Workflow هوشمند برای RAG که به صورت خودکار استراتژی را انتخاب می‌کند
    """
    
    def __init__(self, langchain_service, rag_service):
        self.langchain_service = langchain_service
        self.rag_service = rag_service
        self.graph = None
        
        if LANGGRAPH_AVAILABLE:
            self._build_graph()
            logger.info("🎯 AdaptiveRAGWorkflow initialized with LangGraph")
        else:
            logger.warning("⚠️ LangGraph not available, using fallback mode")
    
    def _build_graph(self):
        """ساخت workflow graph"""
        
        # ایجاد graph
        workflow = StateGraph(WorkflowState)
        
        # اضافه کردن node‌ها
        workflow.add_node("classify_query", self.classify_query)
        workflow.add_node("refine_query", self.refine_query)
        workflow.add_node("select_strategy", self.select_strategy)
        workflow.add_node("retrieve_documents", self.retrieve_documents)
        workflow.add_node("rerank_documents", self.rerank_documents)
        workflow.add_node("generate_response", self.generate_response)
        workflow.add_node("validate_response", self.validate_response)
        
        # تعریف edges
        workflow.set_entry_point("classify_query")
        
        workflow.add_edge("classify_query", "refine_query")
        workflow.add_edge("refine_query", "select_strategy")
        workflow.add_edge("select_strategy", "retrieve_documents")
        workflow.add_edge("retrieve_documents", "rerank_documents")
        workflow.add_edge("rerank_documents", "generate_response")
        workflow.add_edge("generate_response", "validate_response")
        
        # Conditional edge برای validation
        workflow.add_conditional_edges(
            "validate_response",
            self.should_retry,
            {
                "retry": "refine_query",
                "end": END
            }
        )
        
        self.graph = workflow.compile()
        logger.info("✅ Workflow graph compiled successfully")
    
    async def classify_query(self, state: WorkflowState) -> WorkflowState:
        """طبقه‌بندی نوع query"""
        
        with PerformanceLogger(logger, "classify_query"):
            logger.info(f"🔍 Classifying query: {state['query'][:100]}")
            
            try:
                # استفاده از LLM برای تشخیص نوع query
                prompt = ChatPromptTemplate.from_template("""
                Classify the following user query into one of these categories:
                - factual: Questions requiring factual knowledge
                - conversational: Casual conversation, greetings
                - procedural: How-to questions requiring steps
                - comparison: Comparing multiple things
                - clarification: Asking for more explanation
                
                Query: {query}
                
                Respond with only the category name.
                """)
                
                model = self.langchain_service._get_model(
                    settings.chat_model_loaded,
                    max_tokens=50
                )
                
                chain = prompt | model | StrOutputParser()
                result = await chain.ainvoke({"query": state["query"]})
                
                query_type = result.strip().lower()
                
                # Validate and convert to enum
                try:
                    state["query_type"] = QueryType(query_type)
                except ValueError:
                    state["query_type"] = QueryType.FACTUAL  # default
                
                logger.info(f"✅ Query classified as: {state['query_type'].value}")
                state["workflow_steps"].append(f"classified:{state['query_type'].value}")
                
            except Exception as e:
                logger.error(f"❌ Query classification failed: {e}")
                state["query_type"] = QueryType.FACTUAL
                state["errors"].append(f"classification_error:{str(e)}")
            
            return state
    
    async def refine_query(self, state: WorkflowState) -> WorkflowState:
        """بهبود و بازنویسی query برای جستجوی بهتر"""
        
        with PerformanceLogger(logger, "refine_query"):
            logger.info(f"🔧 Refining query")
            
            try:
                # برای conversational queries نیازی به refinement نیست
                if state["query_type"] == QueryType.CONVERSATIONAL:
                    state["refined_query"] = state["query"]
                    logger.info("ℹ️  Skipping refinement for conversational query")
                    return state
                
                # استفاده از LLM برای بهبود query
                prompt = ChatPromptTemplate.from_template("""
                Rewrite the following query to make it more effective for semantic search.
                Make it more specific and add relevant keywords while preserving the intent.
                
                Original query: {query}
                Query type: {query_type}
                
                Refined query:""")
                
                model = self.langchain_service._get_model(
                    settings.chat_model_loaded,
                    max_tokens=100
                )
                
                chain = prompt | model | StrOutputParser()
                refined = await chain.ainvoke({
                    "query": state["query"],
                    "query_type": state["query_type"].value
                })
                
                state["refined_query"] = refined.strip()
                logger.info(f"✅ Query refined: {state['refined_query'][:100]}")
                state["workflow_steps"].append("refined")
                
            except Exception as e:
                logger.error(f"❌ Query refinement failed: {e}")
                state["refined_query"] = state["query"]
                state["errors"].append(f"refinement_error:{str(e)}")
            
            return state
    
    async def select_strategy(self, state: WorkflowState) -> WorkflowState:
        """انتخاب استراتژی مناسب برای RAG"""
        
        with PerformanceLogger(logger, "select_strategy"):
            logger.info(f"🎯 Selecting RAG strategy")
            
            # انتخاب استراتژی بر اساس نوع query
            strategy_map = {
                QueryType.FACTUAL: RAGStrategy.HYBRID,
                QueryType.CONVERSATIONAL: RAGStrategy.SIMPLE,
                QueryType.PROCEDURAL: RAGStrategy.RERANK,
                QueryType.COMPARISON: RAGStrategy.HYBRID,
                QueryType.CLARIFICATION: RAGStrategy.SIMPLE
            }
            
            state["search_strategy"] = strategy_map.get(
                state["query_type"],
                RAGStrategy.SIMPLE
            )
            
            logger.info(f"✅ Strategy selected: {state['search_strategy'].value}")
            state["workflow_steps"].append(f"strategy:{state['search_strategy'].value}")
            
            return state
    
    async def retrieve_documents(self, state: WorkflowState) -> WorkflowState:
        """جستجوی اسناد مرتبط"""
        
        with PerformanceLogger(logger, "retrieve_documents"):
            logger.info(f"📚 Retrieving documents")
            
            try:
                query = state["refined_query"] or state["query"]
                
                # استفاده از rag_service برای جستجو
                documents = await self.rag_service.retrieve_relevant_documents(
                    query,
                    is_public_only=True  # یا بر اساس user context
                )
                
                state["retrieved_documents"] = documents
                logger.info(f"✅ Retrieved {len(documents)} documents")
                state["workflow_steps"].append(f"retrieved:{len(documents)}")
                
            except Exception as e:
                logger.error(f"❌ Document retrieval failed: {e}")
                state["retrieved_documents"] = []
                state["errors"].append(f"retrieval_error:{str(e)}")
            
            return state
    
    async def rerank_documents(self, state: WorkflowState) -> WorkflowState:
        """مرتب‌سازی مجدد اسناد بر اساس relevance"""
        
        with PerformanceLogger(logger, "rerank_documents"):
            logger.info(f"🔄 Reranking documents")
            
            try:
                # برای استراتژی‌های SIMPLE و CONVERSATIONAL نیازی به rerank نیست
                if state["search_strategy"] in [RAGStrategy.SIMPLE, RAGStrategy.ADAPTIVE]:
                    state["reranked_documents"] = state["retrieved_documents"]
                    logger.info("ℹ️  Skipping reranking")
                    return state
                
                # TODO: پیاده‌سازی reranking واقعی با cross-encoder
                # فعلا فقط sort می‌کنیم
                sorted_docs = sorted(
                    state["retrieved_documents"],
                    key=lambda x: x.get("score", 0),
                    reverse=True
                )
                
                state["reranked_documents"] = sorted_docs[:5]  # top 5
                logger.info(f"✅ Documents reranked, kept top {len(state['reranked_documents'])}")
                state["workflow_steps"].append("reranked")
                
            except Exception as e:
                logger.error(f"❌ Document reranking failed: {e}")
                state["reranked_documents"] = state["retrieved_documents"]
                state["errors"].append(f"reranking_error:{str(e)}")
            
            return state
    
    async def generate_response(self, state: WorkflowState) -> WorkflowState:
        """تولید پاسخ نهایی"""
        
        with PerformanceLogger(logger, "generate_response"):
            logger.info(f"💬 Generating response")
            
            try:
                documents = state["reranked_documents"]
                
                if documents:
                    # تولید context از اسناد
                    context = "\n\n".join([
                        f"Document {i+1}: {doc['title']}\n{doc['content']}"
                        for i, doc in enumerate(documents[:3])
                    ])
                    
                    # استفاده از LangChain برای تولید پاسخ
                    response = await self.langchain_service.generate_rag_response(
                        state["query"],
                        context
                    )
                    
                    state["generated_response"] = response
                    state["sources"] = documents[:3]
                    state["confidence_score"] = 0.9
                    
                else:
                    # اگر سندی پیدا نشد، پاسخ مستقیم
                    response = await self.langchain_service.generate_chat_response([
                        {"role": "user", "content": state["query"]}
                    ])
                    
                    state["generated_response"] = response
                    state["sources"] = []
                    state["confidence_score"] = 0.5
                
                logger.info(f"✅ Response generated (confidence: {state['confidence_score']})")
                state["workflow_steps"].append("generated")
                
            except Exception as e:
                logger.error(f"❌ Response generation failed: {e}")
                state["generated_response"] = "متأسفانه نمی‌توانم به سوال شما پاسخ دهم."
                state["confidence_score"] = 0.0
                state["sources"] = []
                state["errors"].append(f"generation_error:{str(e)}")
            
            return state
    
    async def validate_response(self, state: WorkflowState) -> WorkflowState:
        """اعتبارسنجی پاسخ تولید شده"""
        
        with PerformanceLogger(logger, "validate_response"):
            logger.info(f"✔️  Validating response")
            
            # بررسی طول پاسخ
            if not state["generated_response"] or len(state["generated_response"]) < 10:
                logger.warning("⚠️ Response too short")
                state["confidence_score"] *= 0.5
            
            # بررسی وجود منابع برای query‌های factual
            if state["query_type"] == QueryType.FACTUAL and not state["sources"]:
                logger.warning("⚠️ No sources found for factual query")
                state["confidence_score"] *= 0.7
            
            logger.info(f"✅ Validation complete (final confidence: {state['confidence_score']})")
            state["workflow_steps"].append("validated")
            
            return state
    
    def should_retry(self, state: WorkflowState) -> str:
        """تصمیم‌گیری برای retry"""
        
        # اگر confidence خیلی پایین است و هنوز retry نکرده‌ایم
        retry_count = sum(1 for step in state["workflow_steps"] if step == "refined")
        
        if state["confidence_score"] < 0.3 and retry_count < 2:
            logger.info("🔄 Low confidence, retrying with refined query")
            return "retry"
        
        logger.info("✅ Workflow complete")
        return "end"
    
    async def run(self, query: str, user_id: Optional[str] = None, conversation_history: Optional[List] = None) -> Dict[str, Any]:
        """
        اجرای workflow
        
        Args:
            query: سوال کاربر
            user_id: شناسه کاربر (اختیاری)
            conversation_history: تاریخچه مکالمه (اختیاری)
            
        Returns:
            نتیجه نهایی workflow
        """
        
        with PerformanceLogger(logger, "adaptive_rag_workflow", query=query[:100]):
            
            if not LANGGRAPH_AVAILABLE or not self.graph:
                logger.warning("⚠️ LangGraph not available, using fallback")
                # استفاده از روش قدیمی
                return await self._fallback_rag(query, user_id)
            
            # State اولیه
            initial_state: WorkflowState = {
                "query": query,
                "query_type": None,
                "user_id": user_id,
                "conversation_history": conversation_history or [],
                "refined_query": None,
                "search_strategy": None,
                "retrieved_documents": [],
                "reranked_documents": [],
                "generated_response": None,
                "confidence_score": 0.0,
                "sources": [],
                "workflow_steps": [],
                "errors": []
            }
            
            try:
                # اجرای graph
                final_state = await self.graph.ainvoke(initial_state)
                
                logger.info(
                    f"✅ Workflow completed successfully",
                    extra={
                        'extra_data': {
                            'steps': final_state["workflow_steps"],
                            'confidence': final_state["confidence_score"],
                            'errors': final_state["errors"]
                        }
                    }
                )
                
                return {
                    "response": final_state["generated_response"],
                    "sources": final_state["sources"],
                    "confidence": final_state["confidence_score"],
                    "workflow_steps": final_state["workflow_steps"],
                    "errors": final_state["errors"]
                }
                
            except Exception as e:
                logger.error(f"❌ Workflow failed: {e}", exc_info=True)
                return await self._fallback_rag(query, user_id)
    
    async def _fallback_rag(self, query: str, user_id: Optional[str]) -> Dict[str, Any]:
        """
        Fallback RAG ساده زمانی که LangGraph در دسترس نیست
        """
        logger.info("🔄 Using fallback RAG")
        
        try:
            documents = await self.rag_service.retrieve_relevant_documents(query, is_public_only=True)
            
            if documents:
                context = "\n\n".join([
                    f"{doc['title']}: {doc['content']}"
                    for doc in documents[:3]
                ])
                
                response = await self.langchain_service.generate_rag_response(query, context)
                
                return {
                    "response": response,
                    "sources": documents[:3],
                    "confidence": 0.8,
                    "workflow_steps": ["fallback"],
                    "errors": []
                }
            else:
                response = await self.langchain_service.generate_chat_response([
                    {"role": "user", "content": query}
                ])
                
                return {
                    "response": response,
                    "sources": [],
                    "confidence": 0.5,
                    "workflow_steps": ["fallback_no_docs"],
                    "errors": []
                }
                
        except Exception as e:
            logger.error(f"❌ Fallback RAG failed: {e}")
            return {
                "response": "متأسفانه نمی‌توانم به سوال شما پاسخ دهم.",
                "sources": [],
                "confidence": 0.0,
                "workflow_steps": ["fallback_error"],
                "errors": [str(e)]
            }


# Global workflow instance (will be initialized when needed)
adaptive_rag_workflow = None


def get_adaptive_rag_workflow(langchain_service, rag_service):
    """
    دریافت یا ایجاد workflow instance
    """
    global adaptive_rag_workflow
    
    if adaptive_rag_workflow is None:
        adaptive_rag_workflow = AdaptiveRAGWorkflow(langchain_service, rag_service)
    
    return adaptive_rag_workflow

