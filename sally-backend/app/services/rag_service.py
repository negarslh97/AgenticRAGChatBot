from typing import List, Dict, Any, Optional, Union, AsyncGenerator
from abc import ABC, abstractmethod
import logging
import requests
from bson import ObjectId
import hashlib
import time
import asyncio
import re
import math

from app.core.config import settings
from app.domain.entities import KnowledgeBaseArticle, ArticleStatus, ArticleVisibility, Customer, Admin

logger = logging.getLogger(__name__)


class RAGService(ABC):
    """Abstract base class for RAG services."""

    def __init__(self):
        # 🆕 تنظیمات Reranker API (Colab)
        self.reranker_api_url = getattr(settings, 'RERANKER_API_URL', None)
        if self.reranker_api_url:
            logger.debug(f"🔗 Reranker API configured: {self.reranker_api_url}")
        else:
            logger.debug("⚠️ Reranker API URL not configured - will use fallback scoring")
    
        self.response_cache = {}
        self.cache_ttl = 300
    
    def _get_cache_key(self, query: str, context: Optional[str] = None) -> str:
        query_hash = hashlib.md5(query.encode()).hexdigest()
        context_hash = hashlib.md5(context.encode() if context else "").hexdigest() if context else ""
        return f"{query_hash}_{context_hash}"
    
    def _is_cache_valid(self, cache_entry: dict) -> bool:
        return time.time() - cache_entry['timestamp'] < self.cache_ttl
    
    @abstractmethod
    async def generate_response(self, query: str, context: Optional[Dict[str, Any]] = None, streaming: bool = False) -> Union[Dict[str, Any], AsyncGenerator[Dict[str, Any], None]]:
        """Generate response using RAG."""
        pass
    
    async def retrieve_relevant_documents(self, query: str, is_public_only: bool = True) -> List[Dict[str, Any]]:
        """Retrieve relevant documents using Weaviate vector search + MongoDB metadata."""
        try:
            weaviate_results = await self._retrieve_from_weaviate(query, is_public_only)
            if weaviate_results:
                return await self._enrich_with_mongodb_metadata(weaviate_results, is_public_only)
            return await self._retrieve_from_mongodb(query, is_public_only)
        except Exception as e:
            logger.debug(f"❌ Hybrid search failed: {e}")
            return await self._retrieve_from_mongodb(query, is_public_only)

    def _extract_article_title_from_content(self, full_content: str) -> Optional[str]:
        if not full_content:
            return None
        lines = full_content.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('#'):
                title = line.lstrip('#').strip()
                if title:
                    return title
        return None
    
    def _get_display_title(self, doc: Dict[str, Any]) -> str:
        article_title = doc.get("article_title")
        if not article_title:
            full_article_content = doc.get("full_article_content", "")
            article_title = self._extract_article_title_from_content(full_article_content)
        if not article_title:
            article_title = doc.get("title", "بدون عنوان")
        return article_title
    
    async def _enrich_with_mongodb_metadata(self, weaviate_results: List[Dict[str, Any]], is_public_only: bool = True) -> List[Dict[str, Any]]:
        from app.infrastructure.database.mongodb import init_db, get_mongo_client
        
        if get_mongo_client() is None:
            await init_db()

        enriched_docs = []
        article_ids = []
        for weaviate_doc in weaviate_results:
            article_id = weaviate_doc.get("id") or weaviate_doc.get("article_id")
            if article_id:
                article_ids.append(article_id)
        
        articles_map = {}
        if article_ids:
            try:
                object_ids = [ObjectId(aid) for aid in set(article_ids) if ObjectId.is_valid(aid)]
                if object_ids:
                    articles_cursor = KnowledgeBaseArticle.find({"_id": {"$in": object_ids}})
                    articles_map = {str(article.id): article async for article in articles_cursor}
            except Exception as e:
                logger.debug(f"❌ Batch fetch failed: {e}")

        for weaviate_doc in weaviate_results:
            try:
                article_id = weaviate_doc.get("id") or weaviate_doc.get("article_id")
                
                # Default values from Weaviate
                doc_data = {
                    "id": article_id or weaviate_doc.get("node_id", "unknown"),
                    "title": weaviate_doc.get("title", "Untitled"),
                    "content": weaviate_doc.get("content", ""),
                    "score": weaviate_doc.get("score", 0.5),
                    "source": "weaviate",
                    "path": weaviate_doc.get("path", ""),
                    "raw_content": weaviate_doc.get("raw_content", weaviate_doc.get("content", "")),
                    "full_article_content": weaviate_doc.get("full_article_content", "")
                }

                if article_id and article_id in articles_map:
                    article = articles_map[article_id]
                    if is_public_only and article.visibility != ArticleVisibility.PUBLIC:
                        continue
                    
                    doc_data.update({
                        "article_title": article.title,
                        "summary": article.summary,
                        "url": getattr(article, 'url', None),
                        "tags": [tag.name for tag in getattr(article, 'tags', [])] if hasattr(article, 'tags') else [],
                        "category": getattr(article, 'category', {}).name if hasattr(article, 'category') and article.category else None,
                        "source": "hybrid"
                    })
                else:
                     # Attempt to extract title from content if not in DB
                    full_content = weaviate_doc.get("full_article_content", "")
                    extracted_title = self._extract_article_title_from_content(full_content)
                    doc_data["article_title"] = extracted_title or doc_data["title"]

                enriched_docs.append(doc_data)

            except Exception as e:
                logger.debug(f"❌ Error processing doc: {e}")
                continue

        return enriched_docs

    def _format_sources_markdown(self, documents: List[Dict[str, Any]], max_sources: int = None) -> List[Dict[str, Any]]:
        if max_sources is None:
            max_sources = settings.max_sources_to_format
        
        # Group by article_id to find best chunk per article
        article_best_scores = {}
        for doc in documents:
            article_id = str(doc.get("id", ""))
            score = doc.get("score", 0)
            if article_id not in article_best_scores or score > article_best_scores[article_id]["score"]:
                article_best_scores[article_id] = {"doc": doc, "score": score}

        sorted_articles = sorted(article_best_scores.items(), key=lambda x: x[1]["score"], reverse=True)
        formatted_sources = []

        for article_id, data in sorted_articles[:max_sources]:
            doc = data["doc"]
            content = doc.get("content", "")
            snippet = content[:200] + "..." if len(content) > 200 else content
            
            formatted_sources.append({
                "id": article_id,
                "title": self._get_display_title(doc),
                "score": data["score"],
                "category": doc.get("category"),
                "tags": doc.get("tags", []),
                "url": doc.get("url"),
                "snippet": snippet,
                "summary": doc.get("summary", "")
            })
        
        return formatted_sources

    async def _retrieve_from_weaviate(self, query: str, is_public_only: bool = True, limit: int = None) -> List[Dict[str, Any]]:
        if limit is None:
            limit = min(settings.weaviate_retrieval_limit, 8)
            
        try:
            import os
            from app.infrastructure.connection_manager import weaviate_client
            
            # API Key Setup
            api_key = settings.embedder_api_key_loaded or settings.openai_api_key_loaded
            if api_key:
                os.environ['Embedder_API_KEY'] = api_key

            with weaviate_client() as client:
                search_query = await self._expand_query_with_hyde(query)
                
                from app.core.weaviate_utils import get_weaviate_collection_name
                collection = client.collections.get(get_weaviate_collection_name())

                try:
                    response = collection.query.near_text(
                        query=search_query,
                        limit=limit,
                        return_metadata=['distance', 'certainty']
                    )
                    objects = response.objects if response.objects else []
                except Exception as e:
                    logger.debug(f"❌ Weaviate query error: {str(e)}")
                    objects = []
                
                relevant_docs = []
                seen_node_ids = set()
                
                for obj in objects:
                    node_id = obj.properties.get("node_id", "")
                    if node_id in seen_node_ids: continue
                    seen_node_ids.add(node_id)

                    score = obj.metadata.certainty if hasattr(obj.metadata, 'certainty') else 0.5
                    
                    relevant_docs.append({
                        "id": obj.properties.get("article_id", ""),
                        "node_id": node_id,
                        "title": obj.properties.get("title", ""),
                        "content": obj.properties.get("content", ""),
                        "raw_content": obj.properties.get("raw_content", obj.properties.get("content", "")),
                        "full_article_content": obj.properties.get("full_content", ""),
                        "path": obj.properties.get("path", ""),
                        "score": score
                    })

                reranked = await self._rerank_documents(query, relevant_docs, top_k=min(5, limit))
                return reranked

        except Exception as e:
            logger.debug(f"Weaviate search error: {e}")
            raise e

    async def _expand_query_with_hyde(self, query: str) -> str:
        try:
            from app.infrastructure.model_factory import model_factory
            llm = model_factory.create_model("fast")
            
            prompt = f"Generate a brief, factual answer to this question (2 sentences). Question: {query} Answer:"
            response = await llm.agenerate([prompt])
            hypothetical = response.generations[0][0].text.strip() if response.generations else ""
            
            return f"{query}\n\n{hypothetical}" if hypothetical else query
        except Exception:
            return query

    async def _rerank_documents(self, query: str, documents: List[Dict[str, Any]], top_k: int = 15) -> List[Dict[str, Any]]:
        # 1. External API
        if self.reranker_api_url:
            try:
                doc_contents = [d.get("raw_content", d.get("content", "")) for d in documents]
                resp = requests.post(self.reranker_api_url, json={"query": query, "documents": doc_contents}, timeout=2)
                resp.raise_for_status()
                scores = resp.json().get("scores", [])
                
                if len(scores) == len(documents):
                    for doc, score in zip(documents, scores):
                        doc["score"] = float(score)
                    documents.sort(key=lambda x: x["score"], reverse=True)
                    return documents[:top_k]
            except Exception as e:
                logger.debug(f"Reranker API failed: {e}")

        # 2. Local Fallback
        query_terms = set(query.lower().split())
        for doc in documents:
            base_score = doc.get("score", 0.5)
            text = (doc.get("title", "") + " " + doc.get("content", "")).lower()
            overlap = sum(1 for t in query_terms if t in text)
            doc["score"] = (base_score * 0.7) + (min(overlap * 0.1, 0.3))
        
        documents.sort(key=lambda x: x["score"], reverse=True)
        return documents[:top_k]

    async def _calculate_groundedness_score(self, query: str, answer: str, sources: List[Dict[str, Any]], top_score: float = None) -> float:
        if top_score is not None and top_score < 0.1: return 0.1
        if "اطلاعاتی ندارم" in answer or "موجود نیست" in answer: return 0.1
        if not settings.openai_api_key_loaded: return 0.5

        try:
            sources_text = "\n".join([f"- {s.get('title')}: {s.get('snippet', '')}" for s in sources[:3]])
            from app.infrastructure.langchain_orchestrator import orchestrator
            
            prompt = f"""Rate if the Answer is grounded in Sources for the Query.
            Query: {query}
            Answer: {answer}
            Sources: {sources_text}
            Return only a number between 0.0 and 1.0."""
            
            result = await orchestrator.process_request(query=prompt, context=None, conversation_history=None)
            match = re.search(r'(\d+\.?\d*)', result.content)
            return float(match.group(1)) if match else 0.5
        except Exception:
            return 0.5

    def _calculate_advanced_confidence(self, query: str, retrieved_docs: List[Dict[str, Any]], answer: str = None, verification_result: Dict = None, query_type: str = "general", groundedness_score: float = None) -> Dict[str, Any]:
        if not retrieved_docs:
            return {"confidence_score": 0.0, "confidence_level": "Low"}
        
        top_score = retrieved_docs[0].get("score", 0) if retrieved_docs else 0
        groundedness = groundedness_score if groundedness_score is not None else 0.5
        
        # Simplified weighted score
        score = (top_score * 0.4) + (groundedness * 0.4) + (0.2 if len(retrieved_docs) > 3 else 0)
        score = min(score, 1.0)
        
        level = "High" if score > 0.8 else "Medium" if score > 0.5 else "Low"
        return {"confidence_score": round(score, 2), "confidence_level": level}

    def _verify_answer_quality(self, query: str, answer: str, context: str, sources: List[Dict[str, Any]]) -> Dict[str, Any]:
        score = 1.0
        issues = []
        if len(answer) < 50: 
            score *= 0.8
            issues.append("Short answer")
        if not sources:
            score *= 0.5
            issues.append("No sources")
            
        return {"quality_score": score, "issues": issues, "warnings": []}

    async def _retrieve_from_mongodb(self, query: str, is_public_only: bool = True) -> List[Dict[str, Any]]:
        from app.infrastructure.database.mongodb import init_db, get_mongo_client
        if get_mongo_client() is None: await init_db()

        filter_query = {"status": ArticleStatus.PUBLISHED.value}
        if is_public_only:
            filter_query["visibility"] = ArticleVisibility.PUBLIC.value

        articles = await KnowledgeBaseArticle.find(filter_query).to_list()
        query_lower = query.lower().split()
        results = []

        for art in articles:
            score = 0
            text = (art.title + " " + art.summary).lower()
            if any(q in text for q in query_lower): score += 1
            
            if score > 0:
                results.append({
                    "id": str(art.id),
                    "title": art.title,
                    "content": art.content_markdown[:1000],
                    "summary": art.summary,
                    "score": min(score * 0.2, 0.9), # Normalized roughly
                    "source": "mongodb"
                })
        
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:5]


class SimpleRAGService(RAGService):
    """Simple RAG for guest users."""

    def _is_math_query(self, query: str) -> bool:
        indicators = ["محاسبه", "حساب", "جمع", "ضرب", "تقسیم", "math", "calculate", "+", "*"]
        return any(x in query.lower() for x in indicators)

    def _calculate_math_expression(self, query: str) -> Optional[str]:
        # Basic safe eval or regex logic (Simplified for brevity)
        try:
            allowed = set("0123456789+-*/. ")
            if not set(query).issubset(allowed): return None
            return str(eval(query))
        except: return None

    async def generate_response(self, query: str, context: Optional[Dict[str, Any]] = None, streaming: bool = False) -> Union[Dict[str, Any], AsyncGenerator[Dict[str, Any], None]]:
        # 1. Check Math
        if self._is_math_query(query):
            # ... implementation ...
            pass 

        # 2. Retrieve Docs
        relevant_docs = await self.retrieve_relevant_documents(query, is_public_only=True)
        formatted_sources = self._format_sources_markdown(relevant_docs)

        # 3. No Docs found
        if not relevant_docs:
            msg = "متأسفانه اطلاعاتی پیدا نشد."
            if streaming:
                async def stream_empty():
                    yield {"type": "complete", "full_response": msg, "confidence": 0.0}
                return stream_empty()
            return {"response": msg, "sources": [], "confidence": 0.0}

        # 4. Prepare Context
        context_text = "\n".join([f"Source: {d['title']}\n{d['content']}\n" for d in relevant_docs[:5]])
        
        # 5. Generate
        if streaming:
            async def stream_response():
                yield {"type": "sources", "sources": formatted_sources, "confidence": 0.8}
                
                from app.infrastructure.langchain_orchestrator import orchestrator
                full_resp = ""
                try:
                    # Pass context dict properly
                    custom_model = context.get("model") if context else None
                    history = context.get("conversation_history", []) if context else []
                    
                    async for chunk in orchestrator.process_streaming_request(
                        query=query, context=context_text, conversation_history=history, custom_model=custom_model
                    ):
                        full_resp += chunk
                        yield {"type": "chunk", "content": chunk}
                    
                    yield {"type": "complete", "full_response": full_resp, "confidence": 0.8, "rag_type": "simple"}
                except Exception as e:
                    yield {"type": "error", "message": str(e)}
            return stream_response()
        
        # Non-streaming fallback
        from app.infrastructure.langchain_orchestrator import orchestrator
        result = await orchestrator.process_request(query=query, context=context_text, conversation_history=[])
        return {"response": result.content, "sources": formatted_sources, "confidence": 0.8}


class AgenticRAGService(RAGService):
    """Agentic RAG for authenticated users."""
    
    def __init__(self):
        super().__init__()
        # 🔥 Safe local import (handled via Dependency Injection usually, but here inside init is safer than top-level)
        try:
            from app.infrastructure.langchain_orchestrator import orchestrator
            from app.infrastructure.agentic_rag_advanced import get_advanced_agentic_rag
            self.advanced_workflow = get_advanced_agentic_rag(orchestrator, self)
        except ImportError:
            logger.error("Could not import Agentic RAG workflow")
            self.advanced_workflow = None
    
    async def generate_response(self, query: str, context: Optional[Dict[str, Any]] = None, streaming: bool = False) -> Union[Dict[str, Any], AsyncGenerator[Dict[str, Any], None]]:
        cache_key = self._get_cache_key(query, str(context))
        if cache_key in self.response_cache and self._is_cache_valid(self.response_cache[cache_key]):
            cached = self.response_cache[cache_key]
            if streaming:
                async def stream_cached():
                    yield {"type": "sources", "sources": cached['metadata'].get('sources', []), "confidence": 1.0}
                    yield {"type": "chunk", "content": cached['response']}
                    yield {"type": "complete", "full_response": cached['response'], "confidence": 1.0}
                return stream_cached()
            return {"response": cached['response'], "metadata": cached['metadata']}

        if not self.advanced_workflow:
            # Fallback to Simple RAG logic
            fallback_service = SimpleRAGService()
            return await fallback_service.generate_response(query, context, streaming)

        # Execute Workflow
        try:
            # Note: This awaits the full execution (Simulated Streaming)
            workflow_result = await self.advanced_workflow.run(
                query=query,
                conversation_history=context.get("conversation_history", []) if context else []
            )
            
            # Cache
            self.response_cache[cache_key] = {
                'response': workflow_result['response'],
                'metadata': workflow_result['metadata'],
                'timestamp': time.time()
            }

            if streaming:
                async def stream_agentic():
                    if 'metadata' in workflow_result and 'sources' in workflow_result['metadata']:
                        yield {"type": "sources", "sources": workflow_result['metadata']['sources'], "confidence": workflow_result.get('confidence', 0.8)}
                    
                    # Simulated streaming
                    response = workflow_result.get('response', '')
                    words = response.split(' ')
                    for i, word in enumerate(words):
                        separator = " " if i < len(words) - 1 else ""
                        yield {"type": "chunk", "content": word + separator}
                        await asyncio.sleep(0.01) # Fast simulation
                    
                    yield {
                        "type": "complete", 
                        "full_response": response, 
                        "confidence": workflow_result.get('confidence', 0.8),
                        "rag_type": "agentic"
                    }
                return stream_agentic()

            return workflow_result

        except Exception as e:
            logger.error(f"Agentic workflow failed: {e}")
            if streaming:
                async def stream_error(): yield {"type": "error", "message": "Workflow Error"}
                return stream_error()
            return {"response": "Error in agentic workflow", "confidence": 0.0}


def get_rag_service(user: Optional[Union['Customer', 'Admin']] = None, rag_type: str = "simple") -> RAGService:
    if not user:
        return SimpleRAGService()
    if rag_type in ["agentic", "detailed"]:
        return AgenticRAGService()
    return SimpleRAGService()