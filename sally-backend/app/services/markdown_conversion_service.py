"""
Markdown Conversion Service for converting plain text to structured Markdown.
این سرویس مسئولیت تبدیل متن ساده به فرمت Markdown را بر عهده دارد.
"""

from typing import Dict, Any, Optional
from app.infrastructure.model_service import model_service
from app.infrastructure.prompt_service import prompt_service
from app.core.logging_config import get_logger, PerformanceLogger

logger = get_logger(__name__)


class MarkdownConversionService:
    """
    Service for converting plain text to structured Markdown using AI.
    
    Responsibilities:
    - Convert plain text to Markdown format
    - Apply proper Markdown syntax (headers, lists, emphasis, etc.)
    - Maintain content structure and readability
    - Handle different content types (articles, documentation, etc.)
    """

    def __init__(self):
        logger.debug("📝 MarkdownConversionService initialized")

    async def convert_text_to_markdown(self, title: str, content: str) -> str:
        """
        Convert plain text to structured Markdown using AI.

        Args:
            title: Article title
            content: Plain text content

        Returns:
            Formatted Markdown content
        """
        with PerformanceLogger(logger, "convert_text_to_markdown", title=title[:50], content_length=len(content)):
            try:
                selected_model = "gpt-4o-mini"  # Use a reliable model for markdown conversion
                logger.debug(f"🔄 تبدیل متن به Markdown با مدل: {selected_model}")
                logger.debug(f"📝 عنوان: {title[:100]}...")
                logger.debug(f"📊 طول محتوا: {len(content)} کاراکتر")

                # Get model from ModelService
                model = model_service.get_model(
                    selected_model, 
                    force_json=False, 
                    max_tokens=4096
                )
                logger.debug(f"✅ مدل {selected_model} برای تبدیل Markdown بارگذاری شد (max_tokens: 4096)")

                # Get prompt from PromptService
                prompt_template = prompt_service.get_prompt("markdown_conversion")
                prompt = ChatPromptTemplate.from_template(prompt_template)

                # Create the chain
                chain = prompt | model

                # Run the chain
                result = await chain.ainvoke({
                    "title": title,
                    "content": content
                })

                markdown_content = result.content.strip()
                logger.debug(f"✅ متن با موفقیت به Markdown تبدیل شد - طول: {len(markdown_content)} کاراکتر")
                
                return markdown_content

            except Exception as e:
                logger.debug(f"❌ خطا در تبدیل متن به Markdown: {str(e)}")
                # Return original content with basic title formatting if AI conversion fails
                return f"# {title}\n\n{content}"

    async def convert_with_custom_instructions(
        self, 
        title: str, 
        content: str, 
        custom_instructions: str
    ) -> str:
        """
        Convert text to Markdown with custom instructions.

        Args:
            title: Article title
            content: Plain text content
            custom_instructions: Additional conversion instructions

        Returns:
            Formatted Markdown content
        """
        try:
            selected_model = "gpt-4o-mini"
            logger.debug(f"🔄 تبدیل متن به Markdown با دستورات سفارشی: {selected_model}")

            # Get model from ModelService
            model = model_service.get_model(
                selected_model, 
                force_json=False, 
                max_tokens=4096
            )

            # Get prompt from PromptService and add custom instructions
            prompt_template = prompt_service.get_prompt("markdown_conversion")
            enhanced_prompt = f"{prompt_template}\n\n**دستورات سفارشی:**\n{custom_instructions}"
            
            prompt = ChatPromptTemplate.from_template(enhanced_prompt)

            # Create the chain
            chain = prompt | model

            # Run the chain
            result = await chain.ainvoke({
                "title": title,
                "content": content
            })

            markdown_content = result.content.strip()
            logger.debug(f"✅ متن با دستورات سفارشی با موفقیت به Markdown تبدیل شد - طول: {len(markdown_content)} کاراکتر")
            
            return markdown_content

        except Exception as e:
            logger.debug(f"❌ خطا در تبدیل متن به Markdown با دستورات سفارشی: {str(e)}")
            # Fallback to basic conversion
            return await self.convert_text_to_markdown(title, content)

    async def validate_markdown(self, markdown_content: str) -> Dict[str, Any]:
        """
        Validate the generated Markdown content.

        Args:
            markdown_content: Markdown content to validate

        Returns:
            Validation results with issues and suggestions
        """
        validation_results = {
            "is_valid": True,
            "issues": [],
            "suggestions": [],
            "statistics": {
                "total_characters": len(markdown_content),
                "total_lines": markdown_content.count('\n') + 1,
                "headers_count": len([line for line in markdown_content.split('\n') if line.strip().startswith('#')]),
                "lists_count": len([line for line in markdown_content.split('\n') if line.strip().startswith(('-', '*', '+', '1.', '2.', '3.'))]),
                "code_blocks_count": markdown_content.count('```')
            }
        }

        # Basic validation checks
        if not markdown_content.strip():
            validation_results["is_valid"] = False
            validation_results["issues"].append("محتوای Markdown خالی است")
        
        # Check for balanced headers
        headers = [line for line in markdown_content.split('\n') if line.strip().startswith('#')]
        if len(headers) == 0:
            validation_results["suggestions"].append("بهتر است از عناوین (headers) برای ساختاردهی محتوا استفاده کنید")
        
        # Check for code blocks
        if '```' not in markdown_content and any(word in markdown_content.lower() for word in ['کد', 'code', 'برنامه', 'script']):
            validation_results["suggestions"].append("اگر محتوا شامل کد است، از بلوک‌های کد (```) استفاده کنید")
        
        return validation_results


# Global instance
markdown_conversion_service = MarkdownConversionService()