# # from pydantic import BaseSettings
# from pydantic_settings import BaseSettings
# from typing import Optional


# class Settings(BaseSettings):
#     # Database
#     database_url: str = "mongodb://localhost:27017/SallyChatBot"
    
#     # JWT
#     jwt_secret_key: str = "your-secret-key-change-in-production"
#     jwt_algorithm: str = "HS256"
#     jwt_access_token_expire_minutes: int = 30
    
#     # OpenAI / OpenRouter (for RAG)
#     openai_api_key: Optional[str] = None
#     openai_base_url: Optional[str] = None  # For OpenRouter: "https://openrouter.ai/api/v1"
#     openai_model: Optional[str] = None  # For OpenRouter: "openai/gpt-3.5-turbo" or "anthropic/claude-3-haiku"
    
#     @property
#     def openai_api_key_loaded(self) -> Optional[str]:
#         """Get OpenAI API key from environment with fallback to uppercase."""
#         # Check lowercase first
#         if self.openai_api_key:
#             return self.openai_api_key
#         # Try uppercase from .env file
#         import os
#         return os.getenv("OPENAI_API_KEY")
    
#     @property
#     def openai_base_url_loaded(self) -> Optional[str]:
#         """Get OpenAI base URL from environment with fallback to uppercase."""
#         # Check lowercase first
#         if self.openai_base_url:
#             return self.openai_base_url
#         # Try uppercase from .env file
#         import os
#         return os.getenv("OPENAI_BASE_URL")
    
#     @property
#     def openai_model_loaded(self) -> Optional[str]:
#         """Get OpenAI model from environment with fallback to uppercase."""
#         # Check lowercase first
#         if self.openai_model:
#             return self.openai_model
#         # Try uppercase from .env file
#         import os
#         return os.getenv("OPENAI_MODEL")
    
#     # App settings
#     app_name: str = "Sally Customer Support"
#     debug: bool = True
    
#     class Config:
#         env_file = ".env"


# settings = Settings()











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

    # OpenAI / OpenRouter (for RAG)
    openai_api_key: Optional[str] = None
    openai_base_url: Optional[str] = None
    openai_model: Optional[str] = None
    
    @property
    def openai_api_key_loaded(self) -> Optional[str]:
        import os
        return self.openai_api_key or os.getenv("OPENAI_API_KEY")
    
    @property
    def openai_base_url_loaded(self) -> Optional[str]:
        import os
        return self.openai_base_url or os.getenv("OPENAI_BASE_URL")
    
    @property
    def openai_model_loaded(self) -> Optional[str]:
        import os
        return self.openai_model or os.getenv("OPENAI_MODEL")
    
    # App settings
    app_name: str = "Sally Customer Support"
    debug: bool = True
    
    class Config:
        env_file = ".env"

settings = Settings()