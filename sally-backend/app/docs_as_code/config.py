"""
Configuration for Docs-as-Code system.
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from pathlib import Path
import os


class GitConfig(BaseModel):
    """Git repository configuration."""
    repo_url: str = Field(..., description="Git repository URL for knowledge base")
    local_path: Path = Field(..., description="Local path to clone the repository")
    branch: str = Field(default="main", description="Git branch to use")
    username: Optional[str] = Field(None, description="Git username for authentication")
    password: Optional[str] = Field(None, description="Git password/token for authentication")
    sync_interval: int = Field(default=300, description="Sync interval in seconds")


class MarkdownConfig(BaseModel):
    """Markdown processing configuration."""
    frontmatter_schema: Dict[str, Any] = Field(
        default_factory=lambda: {
            "id": {"type": "string", "required": True},
            "title": {"type": "string", "required": True},
            "slug": {"type": "string", "required": True},
            "author_id": {"type": "string", "required": True},
            "category": {"type": "string", "required": False},
            "tags": {"type": "list", "required": False},
            "status": {"type": "string", "required": True, "choices": ["draft", "published", "archived"]},
            "visibility": {"type": "string", "required": False, "choices": ["public", "customer", "internal"]},
            "created_at": {"type": "datetime", "required": True},
            "updated_at": {"type": "datetime", "required": True},
            "published_at": {"type": "datetime", "required": False},
            "version": {"type": "integer", "required": True},
            "sync_hash": {"type": "string", "required": False}
        }
    )
    
    category_schema: Dict[str, Any] = Field(
        default_factory=lambda: {
            "name": {"type": "string", "required": True},
            "slug": {"type": "string", "required": True},
            "description": {"type": "string", "required": False},
            "parent": {"type": "string", "required": False},
            "is_public": {"type": "boolean", "required": True},
            "order": {"type": "integer", "required": False}
        }
    )


class ConversionConfig(BaseModel):
    """File conversion configuration."""
    supported_formats: Dict[str, str] = Field(
        default_factory=lambda: {
            ".docx": "docx",
            ".pdf": "pdf",
            ".html": "html",
            ".htm": "html",
            ".txt": "txt"
        }
    )
    
    pandoc_options: Dict[str, Any] = Field(
        default_factory=lambda: {
            "wrap": "preserve",
            "atx-headers": True,
            "markdown-headings": "atx"
        }
    )


class SyncConfig(BaseModel):
    """Synchronization configuration."""
    max_retries: int = Field(default=3, description="Maximum retry attempts for sync operations")
    retry_delay: int = Field(default=5, description="Delay between retries in seconds")
    conflict_resolution: str = Field(default="git", description="Conflict resolution strategy")
    batch_size: int = Field(default=100, description="Batch size for bulk operations")


class DocsAsCodeConfig(BaseModel):
    """Main Docs-as-Code configuration."""
    git: GitConfig
    markdown: MarkdownConfig = Field(default_factory=MarkdownConfig)
    conversion: ConversionConfig = Field(default_factory=ConversionConfig)
    sync: SyncConfig = Field(default_factory=SyncConfig)
    
    # Derived paths
    @property
    def articles_path(self) -> Path:
        return self.git.local_path / "articles"
    
    @property
    def categories_path(self) -> Path:
        return self.git.local_path / "categories"
    
    @property
    def assets_path(self) -> Path:
        return self.git.local_path / "assets"


# Default configuration
def get_default_config() -> DocsAsCodeConfig:
    """Get default configuration from environment variables."""
    return DocsAsCodeConfig(
        git=GitConfig(
            repo_url=os.getenv("KB_GIT_REPO_URL", "https://github.com/nslhsdgn/kb.git"),
            local_path=Path(os.getenv("KB_GIT_LOCAL_PATH", "./kb")),
            branch=os.getenv("KB_GIT_BRANCH", "master"),
            username=os.getenv("KB_GIT_USERNAME"),
            password=os.getenv("KB_GIT_PASSWORD"),
            sync_interval=int(os.getenv("KB_SYNC_INTERVAL", "300"))
        )
    )