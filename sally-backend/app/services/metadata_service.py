"""
Metadata Service for generating article metadata using AI.
این سرویس مسئولیت تولید متادیتای مقالات را بر عهده دارد.
"""

from typing import Dict, Any, Optional
from app.infrastructure.model_service import model_service
from app.infrastructure.prompt_service import prompt_service
from app.core.logging_config import get_logger, PerformanceLogger

logger = get_logger(__name__)


class MetadataService:
    """
    Service for generating article metadata using AI.
    
    Responsibilities:
    - Generate article summaries
    - Extract relevant tags
    - Suggest categories
    - Determine visibility levels
    """

    def __init__(self):
        logger.debug("📝 MetadataService initialized")

    async def generate_metadata(self, title: str, content: str) -> Dict[str, Any]:
        """
        Generate metadata for an article using AI.

        Args:
            title: Article title
            content: Article content

        Returns:
            Dict containing summary, tags, category, and visibility
        """
        with PerformanceLogger(logger, "generate_metadata", title=title[:50], content_length=len(content)):
            try:
                selected_model = "gpt-4o-mini"  # Use a reliable model for metadata generation
                logger.debug(
                    f"🔍 Generating metadata",
                    extra={
                        'extra_data': {
                            'model': selected_model,
                            'title': title[:100],
                            'content_length': len(content)
                        }
                    }
                )

                # Get model from ModelService
                model = model_service.get_model(
                    selected_model, 
                    force_json=True, 
                    max_tokens=1000
                )
                logger.debug(f"✅ Model loaded successfully: {selected_model}")

                # Get prompt from PromptService
                prompt_template = prompt_service.get_prompt("metadata_generation")
                prompt = ChatPromptTemplate.from_template(prompt_template)

                # Create the chain with JSON parser
                parser = JsonOutputParser()
                chain = prompt | model | parser

                # Run the chain with retry
                result = await self._call_with_retry(chain, {
                    "title": title,
                    "content": content
                })

                # Validate result structure manually
                if not isinstance(result, dict):
                    raise ValueError("AI response is not a valid dictionary")

                required_keys = ['summary', 'tags', 'suggested_category', 'suggested_visibility']
                for key in required_keys:
                    if key not in result:
                        raise ValueError(f"Missing required key: {key}")

                # Ensure tags is a list
                if not isinstance(result['tags'], list):
                    result['tags'] = [str(result['tags'])]

                logger.debug(
                    f"✨ Metadata generated successfully",
                    extra={
                        'extra_data': {
                            'summary_length': len(result.get('summary', '')),
                            'tags_count': len(result.get('tags', [])),
                            'category': result.get('suggested_category'),
                            'visibility': result.get('suggested_visibility')
                        }
                    }
                )

                return result

            except Exception as e:
                # Return default metadata if AI fails
                logger.debug(
                    f"❌ Metadata generation failed",
                    exc_info=True,
                    extra={
                        'extra_data': {
                            'model': selected_model,
                            'error': str(e)
                        }
                    }
                )
                logger.debug("⚠️ Using default metadata")
                return {
                    "summary": f"محتوای استخراج شده از فایل: {title}",
                    "tags": [],
                    "suggested_category": "",
                    "suggested_visibility": ""
                }

    async def _call_with_retry(self, chain, inputs: Dict[str, Any], max_retries: int = 3) -> Any:
        """
        Call chain with retry logic.
        
        Args:
            chain: LangChain chain
            inputs: Input data
            max_retries: Maximum number of retry attempts
            
        Returns:
            Chain output
        """
        from tenacity import (
            retry,
            stop_after_attempt,
            wait_exponential,
            retry_if_exception_type
        )
        
        @retry(
            stop=stop_after_attempt(max_retries),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            retry=retry_if_exception_type((Exception,))
        )
        async def _retry_call():
            return await chain.ainvoke(inputs)
        
        try:
            return await _retry_call()
        except Exception as e:
            logger.debug(
                f"⚠️ Chain call failed after {max_retries} retries",
                extra={'extra_data': {'error': str(e)}}
            )
            raise


# Global instance
metadata_service = MetadataService()