"""
Markdown processing utilities for Docs-as-Code system.
"""
import frontmatter
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import yaml
import hashlib
import re
from .config import MarkdownConfig


class MarkdownProcessor:
    """Process Markdown files with YAML front matter."""
    
    def __init__(self, config: MarkdownConfig):
        self.config = config
    
    def parse_markdown_file(self, file_path: Path) -> Dict[str, Any]:
        """Parse a Markdown file with YAML front matter."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                post = frontmatter.load(f)
            
            return {
                'metadata': post.metadata,
                'content': post.content,
                'file_path': file_path,
                'file_hash': self._calculate_file_hash(file_path)
            }
        except Exception as e:
            raise MarkdownParseError(f"Failed to parse Markdown file {file_path}: {str(e)}")
    
    def generate_markdown(self, metadata: Dict[str, Any], content: str) -> str:
        """Generate Markdown content with YAML front matter."""
        try:
            # Validate metadata against schema
            self._validate_metadata(metadata)
            
            # Create frontmatter post
            post = frontmatter.Post(content, **metadata)
            return frontmatter.dumps(post)
        except Exception as e:
            raise MarkdownGenerationError(f"Failed to generate Markdown: {str(e)}")
    
    def write_markdown_file(self, file_path: Path, metadata: Dict[str, Any], content: str):
        """Write Markdown content to file with proper formatting."""
        try:
            # Ensure directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Generate Markdown
            markdown_content = self.generate_markdown(metadata, content)
            
            # Write to file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
                
        except Exception as e:
            raise MarkdownWriteError(f"Failed to write Markdown file {file_path}: {str(e)}")
    
    def _validate_metadata(self, metadata: Dict[str, Any]):
        """Validate metadata against the configured schema."""
        schema = self.config.frontmatter_schema
        
        for field, field_config in schema.items():
            if field_config.get('required', False) and field not in metadata:
                raise ValidationError(f"Required field '{field}' is missing")
            
            if field in metadata:
                value = metadata[field]
                field_type = field_config.get('type')
                
                # Type validation
                if field_type == 'string' and not isinstance(value, str):
                    raise ValidationError(f"Field '{field}' must be a string")
                elif field_type == 'integer' and not isinstance(value, int):
                    raise ValidationError(f"Field '{field}' must be an integer")
                elif field_type == 'boolean' and not isinstance(value, bool):
                    raise ValidationError(f"Field '{field}' must be a boolean")
                elif field_type == 'list' and not isinstance(value, list):
                    raise ValidationError(f"Field '{field}' must be a list")
                elif field_type == 'datetime' and not isinstance(value, (str, datetime)):
                    raise ValidationError(f"Field '{field}' must be a datetime or ISO string")
                
                # Choice validation
                if 'choices' in field_config and value not in field_config['choices']:
                    raise ValidationError(f"Field '{field}' must be one of {field_config['choices']}")
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file content."""
        with open(file_path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    
    def clean_markdown_content(self, content: str) -> str:
        """Clean and normalize Markdown content."""
        # Remove excessive line breaks
        cleaned = re.sub(r'\n{3,}', '\n\n', content)
        
        # Normalize headings
        cleaned = re.sub(r'^#+\s*(.*?)\s*#*$', r'# \1', cleaned, flags=re.MULTILINE)
        
        # Fix image references
        cleaned = re.sub(r'!\[(.*?)\]\((.+?)\)', self._process_image_ref, cleaned)
        
        return cleaned.strip()
    
    def _process_image_ref(self, match) -> str:
        """Process image references to ensure proper formatting."""
        alt_text = match.group(1)
        image_path = match.group(2)
        
        # Ensure image path is relative to assets directory
        if not image_path.startswith('assets/'):
            image_path = f"assets/images/{image_path}"
            
        return f"![{alt_text}]({image_path})"


class CategoryProcessor:
    """Process category metadata files."""
    
    def __init__(self, config: MarkdownConfig):
        self.config = config
    
    def parse_category_file(self, file_path: Path) -> Dict[str, Any]:
        """Parse a category YAML file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                category_data = yaml.safe_load(f)
            
            self._validate_category_data(category_data)
            return category_data
            
        except Exception as e:
            raise CategoryParseError(f"Failed to parse category file {file_path}: {str(e)}")
    
    def write_category_file(self, file_path: Path, category_data: Dict[str, Any]):
        """Write category data to YAML file."""
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            self._validate_category_data(category_data)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(category_data, f, default_flow_style=False, allow_unicode=True)
                
        except Exception as e:
            raise CategoryWriteError(f"Failed to write category file {file_path}: {str(e)}")
    
    def _validate_category_data(self, category_data: Dict[str, Any]):
        """Validate category data against schema."""
        schema = self.config.category_schema
        
        for field, field_config in schema.items():
            if field_config.get('required', False) and field not in category_data:
                raise ValidationError(f"Required category field '{field}' is missing")
            
            if field in category_data:
                value = category_data[field]
                field_type = field_config.get('type')
                
                # Type validation
                if field_type == 'string' and not isinstance(value, str):
                    raise ValidationError(f"Category field '{field}' must be a string")
                elif field_type == 'integer' and not isinstance(value, int):
                    raise ValidationError(f"Category field '{field}' must be an integer")
                elif field_type == 'boolean' and not isinstance(value, bool):
                    raise ValidationError(f"Category field '{field}' must be a boolean")


# Custom exceptions
class MarkdownParseError(Exception):
    pass

class MarkdownGenerationError(Exception):
    pass

class MarkdownWriteError(Exception):
    pass

class CategoryParseError(Exception):
    pass

class CategoryWriteError(Exception):
    pass

class ValidationError(Exception):
    pass