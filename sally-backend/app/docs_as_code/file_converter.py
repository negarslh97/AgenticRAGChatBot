"""
File conversion pipeline for Docs-as-Code system.
"""
import pypandoc
from pathlib import Path
from typing import Optional, Dict, Any
import html2text
import pdfplumber
import pymupdf
import re
import logging
from .config import ConversionConfig


logger = logging.getLogger(__name__)


class FileConverter:
    """Convert various file formats to standardized Markdown."""
    
    def __init__(self, config: ConversionConfig):
        self.config = config
        self.html_converter = html2text.HTML2Text()
        self._setup_html_converter()
    
    def _setup_html_converter(self):
        """Configure HTML to Markdown converter."""
        self.html_converter.ignore_links = False
        self.html_converter.ignore_images = False
        self.html_converter.body_width = 0  # No line wrapping
        self.html_converter.single_line_break = True
    
    async def convert_file(self, file_path: Path, target_format: Optional[str] = None) -> str:
        """Convert a file to Markdown based on its extension."""
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Determine target format
        if target_format is None:
            target_format = self._get_target_format(file_path)
        
        try:
            if target_format == "html":
                return await self._convert_html(file_path)
            elif target_format == "pdf":
                return await self._convert_pdf(file_path)
            else:
                return await self._convert_with_pandoc(file_path, target_format)
                
        except Exception as e:
            logger.error(f"Failed to convert {file_path}: {str(e)}")
            raise ConversionError(f"Conversion failed for {file_path}: {str(e)}")
    
    def _get_target_format(self, file_path: Path) -> str:
        """Get the target format based on file extension."""
        ext = file_path.suffix.lower()
        return self.config.supported_formats.get(ext, "txt")
    
    async def _convert_with_pandoc(self, file_path: Path, source_format: str) -> str:
        """Convert file using pandoc."""
        try:
            # Build pandoc arguments
            extra_args = []
            for key, value in self.config.pandoc_options.items():
                if isinstance(value, bool) and value:
                    extra_args.append(f"--{key}")
                else:
                    extra_args.extend([f"--{key}", str(value)])
            
            # Perform conversion
            output = pypandoc.convert_file(
                str(file_path),
                'markdown',
                format=source_format,
                extra_args=extra_args
            )
            
            return self._clean_markdown(output)
            
        except Exception as e:
            logger.error(f"Pandoc conversion failed for {file_path}: {str(e)}")
            raise
    
    async def _convert_html(self, file_path: Path) -> str:
        """Convert HTML file to Markdown."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            markdown_content = self.html_converter.handle(html_content)
            return self._clean_markdown(markdown_content)
            
        except Exception as e:
            logger.error(f"HTML conversion failed for {file_path}: {str(e)}")
            raise
    
    async def _convert_pdf(self, file_path: Path) -> str:
        """Convert PDF file to Markdown using multiple methods."""
        try:
            # Try pdfplumber first for better text extraction
            text_content = await self._convert_pdf_with_pdfplumber(file_path)
            if text_content.strip():
                return self._clean_markdown(text_content)
            
            # Fallback to pymupdf
            text_content = await self._convert_pdf_with_pymupdf(file_path)
            return self._clean_markdown(text_content)
            
        except Exception as e:
            logger.error(f"PDF conversion failed for {file_path}: {str(e)}")
            raise
    
    async def _convert_pdf_with_pdfplumber(self, file_path: Path) -> str:
        """Convert PDF using pdfplumber for better text extraction."""
        text_content = []
        
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    # Extract text with layout preservation
                    text = page.extract_text(layout=True)
                    if text:
                        text_content.append(text)
            
            return "\n\n".join(text_content)
        except Exception as e:
            logger.warning(f"pdfplumber failed, falling back to pymupdf: {str(e)}")
            return ""
    
    async def _convert_pdf_with_pymupdf(self, file_path: Path) -> str:
        """Convert PDF using pymupdf as fallback."""
        try:
            doc = pymupdf.open(file_path)
            text_content = []
            
            for page in doc:
                text = page.get_text()
                if text:
                    text_content.append(text)
            
            doc.close()
            return "\n\n".join(text_content)
        except Exception as e:
            logger.error(f"pymupdf conversion failed: {str(e)}")
            raise
    
    def _clean_markdown(self, markdown_text: str) -> str:
        """Clean and normalize Markdown content after conversion."""
        # Remove excessive line breaks
        cleaned = re.sub(r'\n{3,}', '\n\n', markdown_text)
        
        # Fix heading formatting
        cleaned = re.sub(r'^#+\s*(.*?)\s*#*$', self._normalize_heading, cleaned, flags=re.MULTILINE)
        
        # Remove extra spaces
        cleaned = re.sub(r'[ ]+', ' ', cleaned)
        
        # Fix list formatting
        cleaned = re.sub(r'^\s*[-*]\s+', '- ', cleaned, flags=re.MULTILINE)
        
        # Remove conversion artifacts
        cleaned = re.sub(r'<!--.*?-->', '', cleaned, flags=re.DOTALL)
        cleaned = re.sub(r'\\[\\\*_\{\}\[\]\(\)#\+\-\.!]', lambda m: m.group(0)[1:], cleaned)
        
        return cleaned.strip()
    
    def _normalize_heading(self, match) -> str:
        """Normalize heading formatting."""
        heading_text = match.group(1).strip()
        current_level = len(match.group(0).split()[0])
        
        # Ensure proper heading levels (max H3 for converted content)
        max_level = min(current_level, 3)
        return f"{'#' * max_level} {heading_text}"
    
    def extract_images(self, file_path: Path, output_dir: Path) -> Dict[str, str]:
        """Extract images from document and return mapping of original to new paths."""
        image_mapping = {}
        
        try:
            if file_path.suffix.lower() == '.pdf':
                return self._extract_images_from_pdf(file_path, output_dir)
            elif file_path.suffix.lower() in ['.docx', '.doc']:
                return self._extract_images_from_docx(file_path, output_dir)
                
        except Exception as e:
            logger.warning(f"Image extraction failed for {file_path}: {str(e)}")
        
        return image_mapping
    
    def _extract_images_from_pdf(self, file_path: Path, output_dir: Path) -> Dict[str, str]:
        """Extract images from PDF file."""
        image_mapping = {}
        
        try:
            doc = pymupdf.open(file_path)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            for page_num in range(len(doc)):
                image_list = doc[page_num].get_images()
                
                for img_index, img in enumerate(image_list):
                    xref = img[0]
                    pix = pymupdf.Pixmap(doc, xref)
                    
                    if pix.n - pix.alpha < 4:  # GRAY or RGB
                        image_data = pix.tobytes("png")
                        image_filename = f"page_{page_num + 1}_img_{img_index + 1}.png"
                        image_path = output_dir / image_filename
                        
                        with open(image_path, "wb") as f:
                            f.write(image_data)
                        
                        image_mapping[f"image_{xref}"] = f"assets/images/{image_filename}"
                    
                    pix = None  # Free Pixmap resources
            
            doc.close()
            
        except Exception as e:
            logger.error(f"PDF image extraction failed: {str(e)}")
        
        return image_mapping
    
    def _extract_images_from_docx(self, file_path: Path, output_dir: Path) -> Dict[str, str]:
        """Extract images from DOCX file."""
        # This would require additional dependencies like python-docx
        # For now, return empty mapping - can be implemented later
        logger.info(f"Image extraction from DOCX not yet implemented for {file_path}")
        return {}


class ConversionError(Exception):
    """Custom exception for conversion errors."""
    pass


# Utility function for HTML content from WYSIWYG editor
def html_to_markdown(html_content: str) -> str:
    """Convert HTML content from WYSIWYG editor to Markdown."""
    converter = html2text.HTML2Text()
    converter.ignore_links = False
    converter.ignore_images = False
    converter.body_width = 0
    converter.single_line_break = True
    
    markdown = converter.handle(html_content)
    
    # Clean up the result
    markdown = re.sub(r'\n{3,}', '\n\n', markdown)
    markdown = re.sub(r'\\[\\\*_\{\}\[\]\(\)#\+\-\.!]', lambda m: m.group(0)[1:], markdown)
    
    return markdown.strip()