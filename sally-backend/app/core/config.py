# مسیر: sally-backend/app/core/config.py

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional, List

class Settings(BaseSettings):

    # Database
    MONGODB_URL: str = Field(default="", env="MONGODB_URL")
    
    # JWT
    jwt_secret_key: str = "sally-chatbot-super-secure-secret-key-2025-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 43200  # 30 days
    
    # RBAC Settings for Default Super admin
    default_SuperAdmin_email: str = "xtra@sally.com"
    default_SuperAdmin_password: str = "admin123"
    
    # CORS
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:3001", "http://0.0.0.0:3000", "http://0.0.0.0:3001"]

    # Weaviate Vector Database Configuration
    weaviate_url: Optional[str] = None
    weaviate_api_key: Optional[str] = None

    # AI Models Configuration
    # 📌 توصیه: برای هر نوع provider، از تنظیمات مناسب استفاده کنید
    metadata_model: Optional[str] = None
    rag_model: Optional[str] = None
    chat_model: Optional[str] = None
    intent_model: Optional[str] = None
    
    # 🔑 OpenRouter / Custom Provider Configuration (پیش‌فرض)
    # برای مدل‌های OpenRouter, Anthropic, Google, etc.
    openai_api_key: Optional[str] = None
    openai_base_url: Optional[str] = None
    
    # 🔑 OpenAI Official Configuration
    # برای استفاده از OpenAI رسمی (gpt-4o, gpt-3.5-turbo)
    embedder_api_key: Optional[str] = None           # OpenAI Official API Key
    embedder_openai_base_url: Optional[str] = None   # پیش‌فرض: https://api.openai.com/v1
    embedder_model: Optional[str] = None
    # Ollama Configuration for local embeddings fallback
    ollama_url: Optional[str] = None
    ollama_embedding_model: Optional[str] = None
    
    # 🆕 Reranker API Configuration
    # توصیه می‌شود از یکی از موارد زیر استفاده کنید:
    # 1. Self-hosted Reranker: مدل BAAI/bge-reranker-v2-m3 روی FastAPI + GPU
    # 2. Managed Service: Cohere Rerank API یا Jina Rerank API
    # 3. External Service: Colab API (فقط برای تست - برای پروداکشن مناسب نیست)
    reranker_api_url: Optional[str] = None
    reranker_timeout: int = 60  # تایم‌اوت به ثانیه
    
    # 🆕 RAG Retrieval Configuration
    # 🔥 OPTIMIZED for Performance - Reduced from high values to prevent memory issues
    weaviate_retrieval_limit: int = 8       # تعداد اسناد برای بازیابی اولیه (کاهش یافته از 30)
    reranker_top_k: int = 5                 # تعداد اسناد برتر بعد از reranking (کاهش یافته از 30)
    context_documents_count: int = 5        # تعداد اسناد TOP برای ارسال full context (بهینه)
    max_sources_to_format: int = 5          # حداکثر تعداد منابع یکتا برای نمایش (کاهش یافته از 10)
    
    # 🆕 Hybrid Model Strategy (برای کاهش هزینه و بهبود سرعت)
    # برای وظایف ساده از مدل سریع و ارزان، برای وظایف پیچیده از مدل قدرتمند
    agentic_fast_model: Optional[str] = None    # برای analyze_query, plan_strategy
    agentic_power_model: Optional[str] = None   # برای synthesize_answer
    use_hybrid_model_strategy: bool = False      # فعال/غیرفعال کردن
    
    # 🆕 Agentic RAG Configuration
    # 🔥 OPTIMIZED for Performance - Reduced resource usage
    agentic_search_limit: int = 3                # تعداد نتایج جستجو (کاهش یافته از 5)
    agentic_max_subqueries: int = 2              # حداکثر تعداد زیرسوالات (کاهش یافته از 3)
    agentic_context_chunk_size: int = 400        # اندازه chunk برای context (کاهش یافته از 500)
    agentic_history_messages_count: int = 3      # تعداد پیام‌های تاریخچه (کاهش یافته از 5)
    agentic_min_confidence_threshold: float = 0.4 # حداقل confidence برای retry (افزایش یافته از 0.3)
    agentic_max_retries: int = 1                 # حداکثر تعداد retry (ثابت)
    
    # Weaviate Sync Configuration
    enable_weaviate_sync: bool = True          # فعال/غیرفعال کردن همگام‌سازی با Weaviate

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
    def intent_model_loaded(self) -> str:
        import os
        return self.intent_model or os.getenv("INTENT_MODEL")

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
        return self.embedder_model or os.getenv("EMBEDDER_MODEL")
        
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

    # Prompts directory configuration
    prompts_dir: str = "app/prompts"

    @property
    def prompts_dir_loaded(self) -> str:
        import os
        return self.prompts_dir or os.getenv("PROMPTS_DIR")

    # Versioning for A/B Testing
    prompt_version: str = "v1.0.0"
    analyzer_version: str = "v1.0.0"

    model_config = {
        "protected_namespaces": ("settings_",),
        "env_file": ".env",
        "extra": "ignore"  # Ignore extra fields from environment variables
    }

settings = Settings()