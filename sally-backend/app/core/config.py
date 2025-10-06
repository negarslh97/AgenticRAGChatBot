# مسیر: sally-backend/app/core/config.py

from pydantic_settings import BaseSettings
from typing import Optional, List

class Settings(BaseSettings):

    # Database
    database_url: str = "mongodb://localhost:27017/SallyChatBot"
    
    # JWT
    jwt_secret_key: str = "sally-chatbot-super-secure-secret-key-2025-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 43200  # 30 days
    
    # RBAC Settings for Default Super admin
    default_SuperAdmin_email: str = "admin@sally.com"
    default_SuperAdmin_password: str = "admin123"
    
    # CORS
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:3001"]

    # Weaviate Vector Database Configuration
    weaviate_url: Optional[str] = None
    weaviate_api_key: Optional[str] = None

    # AI Models Configuration
    metadata_model: Optional[str] = None
    rag_model: Optional[str] = None
    chat_model: Optional[str] = None
    openai_api_key: Optional[str] = None
    openai_base_url: Optional[str] = None
    embedder_api_key: Optional[str] = None
    embedder_openai_base_url: Optional[str] = None
    embedder_model: Optional[str] = None
    # Ollama Configuration for local embeddings fallback
    ollama_url: Optional[str] = None
    ollama_embedding_model: Optional[str] = None
    
    # 🆕 Reranker API Configuration (External Colab)
    reranker_api_url: Optional[str] = None

    # Docs-as-Code Git Configuration
    kb_git_repo_url: Optional[str] = None
    kb_git_username: Optional[str] = None
    kb_git_password: Optional[str] = None
    kb_git_local_path: str = "./knowledge-base"
    kb_git_branch: str = "main"
    kb_sync_interval: int = 300

    # Legacy fields for backward compatibility
    api_key: Optional[str] = None
    model: Optional[str] = None
    model_api_key: Optional[str] = None
    model_base_url: Optional[str] = None

    @property
    def metadata_model_loaded(self) -> str:
        import os
        return self.metadata_model or os.getenv("METADATA_MODEL")

    @property
    def rag_model_loaded(self) -> str:
        import os
        return self.rag_model or os.getenv("RAG_MODEL")

    @property
    def chat_model_loaded(self) -> str:
        import os
        return self.chat_model or os.getenv("CHAT_MODEL")

    @property
    def openai_api_key_loaded(self) -> Optional[str]:
        import os
        return self.openai_api_key or os.getenv("OPENAI_API_KEY")

    @property
    def openai_base_url_loaded(self) -> Optional[str]:
        import os
        return self.openai_base_url or os.getenv("OPENAI_BASE_URL")

    @property
    def weaviate_url_loaded(self) -> Optional[str]:
        import os
        return self.weaviate_url or os.getenv("WEAVIATE_URL")

    @property
    def weaviate_api_key_loaded(self) -> Optional[str]:
        import os
        return self.weaviate_api_key or os.getenv("WEAVIATE_API_KEY")

    @property
    def embedder_api_key_loaded(self) -> Optional[str]:
        import os
        return self.embedder_api_key or os.getenv("Embedder_API_KEY")

    @property
    def embedder_openai_base_url_loaded(self) -> Optional[str]:
        import os
        return self.embedder_openai_base_url or os.getenv("Embedder_OPENAI_BASE_URL")

    @property
    def embedder_model_loaded(self) -> str:
        import os
        return self.embedder_model or os.getenv("EMBEDDER_MODEL") or "text-embedding-3-small"

    @property
    def ollama_url_loaded(self) -> Optional[str]:
        import os
        return self.ollama_url or os.getenv("OLLAMA_URL")

    @property
    def ollama_embedding_model_loaded(self) -> Optional[str]:
        import os
        return self.ollama_embedding_model or os.getenv("OLLAMA_EMBEDDING_MODEL")

    @property
    def RERANKER_API_URL(self) -> Optional[str]:
        """🆕 URL for external Reranker API (Colab)"""
        import os
        return self.reranker_api_url or os.getenv("RERANKER_API_URL")

    # App settings
    app_name: str = "Sally Customer Support"
    debug: bool = True

    model_config = {
        "protected_namespaces": ("settings_",),
        "env_file": ".env",
        "extra": "ignore"  # Ignore extra fields from environment variables
    }

settings = Settings()