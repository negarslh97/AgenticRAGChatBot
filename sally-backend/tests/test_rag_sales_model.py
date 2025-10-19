#!/usr/bin/env python3
"""
Complete RAG Test with "مدل فروش" Query
"""

import warnings
import sys
import os
import asyncio
import time
from pathlib import Path

# Suppress warnings
warnings.filterwarnings("ignore")
os.environ['PYTHONWARNINGS'] = 'ignore'

# Add project root to path if running as script
if __name__ == "__main__":
    current_dir = Path(__file__).resolve().parent
    project_root = current_dir.parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from app.services.rag_service import get_rag_service
from app.core.config import settings

async def test_rag_with_sales_model():
    """Test RAG with 'مدل فروش' query"""
    print("=" * 80)
    print("🧪 COMPLETE RAG TEST: 'مدل فروش'")
    print("=" * 80)
    
    # Test query
    test_query = "در مورد مدل فروش چی میدونی؟"
    
    print(f"📝 Test Query: '{test_query}'")
    print(f"🔧 RAG Model: {settings.rag_model_loaded}")
    print(f"🔑 OpenAI API Key: {'✅ Set' if settings.openai_api_key_loaded else '❌ Not Set'}")
    print(f"🌐 Weaviate URL: {settings.weaviate_url_loaded or 'http://localhost:8080'}")
    print(f"🔑 Embedder API Key: {'✅ Set' if settings.embedder_api_key_loaded else '❌ Not Set'}")
    print("=" * 80)
    
    try:
        # Get Simple RAG Service (for guest users)
        print("🔧 Initializing SimpleRAGService...")
        rag_service = get_rag_service(user=None, rag_type="simple")
        
        # Test retrieval first
        print("\n🔍 STEP 1: Testing Document Retrieval...")
        start_time = time.time()
        
        relevant_docs = await rag_service.retrieve_relevant_documents(test_query, is_public_only=True)
        retrieval_time = time.time() - start_time
        
        print(f"✅ Retrieval completed in {retrieval_time:.3f}s")
        print(f"📚 Found {len(relevant_docs)} relevant documents")
        
        # Show top documents
        if relevant_docs:
            print("\n📋 Top Retrieved Documents:")
            for i, doc in enumerate(relevant_docs[:5], 1):
                title = doc.get('title', 'No title')[:60]
                score = doc.get('score', 0)
                source = doc.get('source', 'unknown')
                print(f"   {i}. {title}... (Score: {score:.3f}, Source: {source})")
        
        # Test full RAG response
        print("\n🤖 STEP 2: Testing Full RAG Response Generation...")
        start_time = time.time()
        
        context = {
            "conversation_history": [],
            "user_id": None
        }
        
        rag_response = await rag_service.generate_response(test_query, context)
        total_time = time.time() - start_time
        
        print(f"✅ RAG Response generated in {total_time:.3f}s")
        
        # Display results
        print("\n" + "=" * 80)
        print("📊 RAG TEST RESULTS")
        print("=" * 80)
        
        print(f"📝 Query: '{test_query}'")
        print(f"⏱️  Total Time: {total_time:.3f}s")
        print(f"📚 Documents Retrieved: {len(relevant_docs)}")
        print(f"🎯 Confidence: {rag_response.get('confidence', 0):.2f}")
        
        print(f"\n🤖 Response:")
        print("-" * 40)
        response_text = rag_response.get('response', 'No response')
        print(response_text)
        print("-" * 40)
        
        # Show sources
        sources = rag_response.get('sources', [])
        if sources:
            print(f"\n📚 Sources ({len(sources)}):")
            for i, source in enumerate(sources[:3], 1):
                title = source.get('title', 'No title')[:50]
                score = source.get('score', 0)
                print(f"   {i}. {title}... (Score: {score:.3f})")
        
        # Show confidence analysis if available
        confidence_analysis = rag_response.get('confidence_analysis', {})
        if confidence_analysis:
            print(f"\n🎯 Confidence Analysis:")
            print(f"   Level: {confidence_analysis.get('confidence_level', 'Unknown')}")
            print(f"   Query Type: {confidence_analysis.get('query_type', 'Unknown')}")
            print(f"   Total Documents: {confidence_analysis.get('total_documents', 0)}")
            print(f"   Unique Sources: {confidence_analysis.get('unique_sources', 0)}")
            print(f"   Top Doc Score: {confidence_analysis.get('top_doc_score', 0):.3f}")
        
        # Show quality metrics if available
        quality_metrics = rag_response.get('quality_metrics', {})
        if quality_metrics:
            print(f"\n🔍 Quality Metrics:")
            print(f"   Quality Score: {quality_metrics.get('quality_score', 0):.2f}")
            print(f"   Acceptable: {quality_metrics.get('is_acceptable', False)}")
            if quality_metrics.get('issues'):
                print(f"   Issues: {', '.join(quality_metrics['issues'])}")
            if quality_metrics.get('warnings'):
                print(f"   Warnings: {', '.join(quality_metrics['warnings'])}")
        
        print("\n" + "=" * 80)
        print("✅ RAG TEST COMPLETED SUCCESSFULLY")
        print("=" * 80)
        
        return rag_response
        
    except Exception as e:
        print(f"\n❌ RAG Test Failed: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    asyncio.run(test_rag_with_sales_model())
