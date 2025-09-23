# مسیر: sally-backend/app/core/config.py

from pydantic_settings import BaseSettings
from typing import Optional, List

class Settings(BaseSettings):

    # Database
    database_url: str = "mongodb://localhost:27017/SallyChatBot"
    
    # JWT
    jwt_secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 43200  # 30 days
    
    # RBAC Settings for Default Super admin
    default_SuperAdmin_email: str = "admin@sally.com"
    default_SuperAdmin_password: str = "admin123"
    
    # CORS
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:3001"]

    # AI Models Configuration
    metadata_model: Optional[str] = None
    rag_model: Optional[str] = None
    chat_model: Optional[str] = None
    openai_api_key: Optional[str] = None
    openai_base_url: Optional[str] = None

    # Legacy fields for backward compatibility
    api_key: Optional[str] = None
    model: Optional[str] = None
    model_api_key: Optional[str] = None
    model_base_url: Optional[str] = None

    @property
    def metadata_model_loaded(self) -> str:
        import os
        return self.metadata_model or os.getenv("METADATA_MODEL") or "gpt-3.5-turbo"

    @property
    def rag_model_loaded(self) -> str:
        import os
        return self.rag_model or os.getenv("RAG_MODEL") or "gpt-3.5-turbo"

    @property
    def chat_model_loaded(self) -> str:
        import os
        return self.chat_model or os.getenv("CHAT_MODEL") or "gpt-3.5-turbo"

    @property
    def openai_api_key_loaded(self) -> Optional[str]:
        import os
        return self.openai_api_key or os.getenv("OPENAI_API_KEY")

    @property
    def openai_base_url_loaded(self) -> Optional[str]:
        import os
        return self.openai_base_url or os.getenv("OPENAI_BASE_URL")
    
    # App settings
    app_name: str = "Sally Customer Support"
    debug: bool = True
    
    class Config:
        env_file = ".env"

settings = Settings()