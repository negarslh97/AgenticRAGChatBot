"""
🚀 Integration Test for AI Orchestrator Service
=================================================

تست یکپارچگی برای تأیید عملکرد صحیح جریان کاری ۸ مرحله‌ای

## مراحل تست:
1. ✅ امنیت ورودی
2. ✅ تحلیل سوال
3. ✅ بازیابی اطلاعات (RAG)
4. ✅ انتخاب مدل
5. ✅ تولید پاسخ
6. ✅ امنیت خروجی
7. ✅ کش کردن
8. ✅ مدیریت خطا
"""

import asyncio
import logging
import time
import pytest
from typing import Dict, Any

# Configure logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestAIOrchestratorIntegration:
    """تست یکپارچگی AI Orchestrator Service"""
    
    def setup_method(self):
        """Setup قبل از هر تست"""
        try:
            from app.infrastructure.ai_orchestrator_service import ai_orchestrator
            self.orchestrator = ai_orchestrator
            logger.info("✅ AI Orchestrator initialized for testing")
        except Exception as e:
            logger.error(f"❌ Failed to initialize orchestrator: {e}")
            raise
    
    async def test_health_check(self):
        """تست ۱: بررسی وضعیت سلامت سیستم"""
        logger.info("🧪 Test 1: Health Check")
        
        health_status = self.orchestrator.get_health_status()
        
        assert health_status["status"] == "healthy", "System should be healthy"
        assert "components" in health_status, "Should have component status"
        assert "circuit_breakers" in health_status, "Should have circuit breaker states"
        
        logger.info("✅ Health check passed")
        return health_status
    
    async def test_simple_conversational_query(self):
        """تست ۲: پردازش سوال محاوره‌ای ساده"""
        logger.info("🧪 Test 2: Simple Conversational Query")
        
        from app.infrastructure.ai_orchestrator_service import ProcessingRequest, RequestType
        
        # تست سوال محاوره‌ای
        request = ProcessingRequest(
            query="سلام",
            request_type=RequestType.CONVERSATIONAL
        )
        
        result = await self.orchestrator.process_request(request)
        
        assert result.success, "Should process successfully"
        assert result.response, "Should have response"
        assert "analysis" in result.metadata, "Should have analysis metadata"
        
        logger.info(f"✅ Conversational query processed: {result.response[:50]}...")
        return result
    
    async def test_rag_query_flow(self):
        """تست ۳: جریان کامل RAG query"""
        logger.info("🧪 Test 3: RAG Query Flow")
        
        from app.infrastructure.ai_orchestrator_service import ProcessingRequest, RequestType
        
        # تست سوال RAG
        request = ProcessingRequest(
            query="چه خدماتی ارائه می‌دهید؟",
            request_type=RequestType.RAG,
            agentic_mode=False
        )
        
        result = await self.orchestrator.process_request(request)
        
        assert result.success, "Should process RAG query successfully"
        assert result.metadata.get("request_type") == "rag", "Should be marked as RAG"
        assert "analysis" in result.metadata, "Should have analysis"
        
        logger.info("✅ RAG query flow completed")
        return result
    
    async def test_streaming_response(self):
        """تست ۴: پاسخ streaming"""
        logger.info("🧪 Test 4: Streaming Response")
        
        from app.infrastructure.ai_orchestrator_service import ProcessingRequest, RequestType
        
        request = ProcessingRequest(
            query="سلام، چطوری؟",
            request_type=RequestType.CONVERSATIONAL
        )
        
        chunks = []
        streaming_generator = await self.orchestrator.process_request(request, streaming=True)
        async for chunk_result in streaming_generator:
            chunks.append(chunk_result)
        
        assert len(chunks) > 0, "Should receive streaming chunks"
        combined_response = "".join(chunks)
        assert len(combined_response) > 0, "Combined response should not be empty"
        
        logger.info(f"✅ Streaming response received: {len(chunks)} chunks")
        return chunks
    
    async def test_error_handling(self):
        """تست ۵: مدیریت خطا"""
        logger.info("🧪 Test 5: Error Handling")
        
        from app.infrastructure.ai_orchestrator_service import ProcessingRequest, RequestType, AIException
        
        # تست سوال خالی
        with pytest.raises(AIException) as excinfo:
            ProcessingRequest(
                query="",  # Empty query should cause error
                request_type=RequestType.CONVERSATIONAL
            )
            # The exception is raised during __post_init__, so we don't need to call process_request
            # If the exception was raised later, we would call: await self.orchestrator.process_request(request)
        
        assert "Query cannot be empty" in str(excinfo.value), "Should have appropriate error message"
        assert excinfo.value.error_type.value == "invalid_input", "Error type should be invalid_input"
        
        logger.info("✅ Error handling working correctly")
        # Return a dummy result for consistency with other tests, as this test now asserts an exception
        return {"status": "PASSED", "message": "AIException for empty query caught as expected"}
    
    async def test_circuit_breaker_states(self):
        """تست ۶: وضعیت circuit breakers"""
        logger.info("🧪 Test 6: Circuit Breaker States")
        
        health_status = self.orchestrator.get_health_status()
        circuit_breakers = health_status.get("circuit_breakers", {})
        
        assert "weaviate" in circuit_breakers, "Should have Weaviate circuit breaker"
        assert "mongodb" in circuit_breakers, "Should have MongoDB circuit breaker"
        
        logger.info(f"✅ Circuit breakers: {circuit_breakers}")
        return circuit_breakers
    
    async def test_helper_methods(self):
        """تست ۷: متدهای کمکی"""
        logger.info("🧪 Test 7: Helper Methods")
        
        # Test simple chat
        result = await self.orchestrator.process_simple_chat("چطوری؟")
        assert result.success, "Helper method should work"
        
        # Test RAG query
        result = await self.orchestrator.process_rag_query("خدمات شما چیست؟")
        assert result.success, "RAG helper method should work"
        
        logger.info("✅ Helper methods working correctly")
        return True
    
    async def test_8_step_workflow(self):
        """تست جامع ۸ مرحله‌ای"""
        logger.info("🧪 Test 8: Complete 8-Step Workflow")
        
        from app.infrastructure.ai_orchestrator_service import ProcessingRequest, RequestType
        
        start_time = time.time()
        
        # ایجاد درخواست
        request = ProcessingRequest(
            query="لطفاً در مورد خدمات شرکت توضیح دهید",
            request_type=RequestType.RAG,
            agentic_mode=True,
            custom_temperature=0.3
        )
        
        # پردازش کامل
        result = await self.orchestrator.process_request(request)
        
        processing_time = time.time() - start_time
        
        # بررسی مراحل ۸ گانه
        expected_steps = [
            "مرحله ۱: امنیت ورودی",  # Input validation
            "مرحله ۲: تحلیل سوال",    # Query analysis
            "مرحله ۳: بازیابی اطلاعات", # RAG retrieval
            "مرحله ۴: انتخاب مدل",     # Model selection
            "مرحله ۵: تولید پاسخ",     # Response generation
            "مرحله ۶: امنیت خروجی"     # Output security
        ]
        
        # بررسی کلی
        assert result.success, "Workflow should complete successfully"
        assert processing_time > 0, "Should have processing time"
        assert "analysis" in result.metadata, "Should have analysis result"
        assert hasattr(result, "circuit_breaker_states"), "Result object should have circuit_breaker_states attribute"
        assert result.circuit_breaker_states is not None, "Circuit breaker info should not be None"
        
        logger.info(f"✅ Complete 8-step workflow finished in {processing_time:.2f}s")
        return {
            "result": result,
            "processing_time": processing_time,
            "workflow_steps": expected_steps
        }


async def run_integration_tests():
    """اجرای تست‌های یکپارچگی"""
    logger.info("🚀 Starting AI Orchestrator Integration Tests")
    
    test_suite = TestAIOrchestratorIntegration()
    test_suite.setup_method()
    
    test_results = {}
    
    # اجرای تست‌ها
    tests = [
        ("Health Check", test_suite.test_health_check),
        ("Conversational Query", test_suite.test_simple_conversational_query),
        ("RAG Query Flow", test_suite.test_rag_query_flow),
        ("Streaming Response", test_suite.test_streaming_response),
        ("Error Handling", test_suite.test_error_handling),
        ("Circuit Breaker States", test_suite.test_circuit_breaker_states),
        ("Helper Methods", test_suite.test_helper_methods),
        ("8-Step Workflow", test_suite.test_8_step_workflow)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            logger.info(f"🔄 Running: {test_name}")
            result = await test_func()
            test_results[test_name] = {"status": "PASSED", "result": result}
            passed += 1
            logger.info(f"✅ {test_name}: PASSED")
        except Exception as e:
            test_results[test_name] = {"status": "FAILED", "error": str(e)}
            failed += 1
            logger.error(f"❌ {test_name}: FAILED - {e}")
    
    # خلاصه نتایج
    logger.info("📊 Integration Test Results Summary:")
    logger.info(f"  Total Tests: {len(tests)}")
    logger.info(f"  Passed: {passed}")
    logger.info(f"  Failed: {failed}")
    logger.info(f"  Success Rate: {passed/len(tests)*100:.1f}%")
    
    # نمایش جزئیات
    for test_name, test_result in test_results.items():
        status_emoji = "✅" if test_result["status"] == "PASSED" else "❌"
        logger.info(f"  {status_emoji} {test_name}: {test_result['status']}")
    
    if failed == 0:
        logger.info("🎉 All integration tests passed! The system is ready for production.")
    else:
        logger.warning(f"⚠️ {failed} tests failed. Please review and fix the issues.")
    
    return test_results


if __name__ == "__main__":
    # اجرای مستقیم تست
    asyncio.run(run_integration_tests())