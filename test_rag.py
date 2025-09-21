from app.infrastructure.rag_service import get_rag_service
from app.domain.entities_refactored import Customer
import asyncio

async def test_rag():
    # Create a test customer
    customer = Customer(
        email='test@example.com',
        hashed_password='dummy',
        full_name='Test User'
    )

    # Get RAG service
    rag_service = get_rag_service(customer)
    print(f'RAG Service Type: {type(rag_service).__name__}')

    # Test document retrieval
    try:
        docs = await rag_service.retrieve_relevant_documents('چطور می‌توانم محصول CRM این شرکت رو بخرم؟', is_public_only=False)
        print(f'Found {len(docs)} relevant documents')
        for doc in docs:
            print(f'Title: {doc["title"]}, Score: {doc["score"]}')
    except Exception as e:
        print(f'Error retrieving documents: {e}')

asyncio.run(test_rag())
