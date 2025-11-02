# weaviate_utils.py

import logging
from app.core.config import settings
import weaviate.classes as wvc
from app.infrastructure.connection_manager import weaviate_client

logger = logging.getLogger(__name__)

def get_weaviate_collection_name() -> str:
    return "MarkdownNode"

def create_unified_collection() -> bool:
    collection_name = get_weaviate_collection_name()
    try:
        with weaviate_client() as client:
            if client.collections.exists(collection_name):
                logger.info(f"Collection '{collection_name}' از قبل موجود است.")
                return True

            logger.info(f"در حال ایجاد Collection '{collection_name}'...")

            vectorizer_config = wvc.config.Configure.Vectorizer.text2vec_openai(
                model=settings.embedder_model_loaded or "text-embedding-3-small"
            )

            properties = [
                wvc.config.Property(name="node_id", data_type=wvc.config.DataType.TEXT),
                wvc.config.Property(name="article_id", data_type=wvc.config.DataType.TEXT),
                wvc.config.Property(name="title", data_type=wvc.config.DataType.TEXT),
                wvc.config.Property(name="level", data_type=wvc.config.DataType.INT),
                wvc.config.Property(name="content", data_type=wvc.config.DataType.TEXT),
                wvc.config.Property(name="parent_id", data_type=wvc.config.DataType.TEXT),
                wvc.config.Property(name="path", data_type=wvc.config.DataType.TEXT),
                wvc.config.Property(name="order", data_type=wvc.config.DataType.INT),
                # ✅✅✅ اضافه کردن فیلدهای visibility و category به schema
                wvc.config.Property(
                    name="visibility",
                    data_type=wvc.config.DataType.TEXT,
                    skip_vectorization=True # این فیلدها برای فیلتر کردن هستند نه جستجوی معنایی
                ),
                wvc.config.Property(
                    name="category",
                    data_type=wvc.config.DataType.TEXT,
                    skip_vectorization=True
                ),
                wvc.config.Property(
                    name="full_content",
                    data_type=wvc.config.DataType.TEXT,
                    skip_vectorization=True
                ),
                wvc.config.Property(
                    name="embedder_model",
                    data_type=wvc.config.DataType.TEXT,
                    skip_vectorization=True
                ),
            ]

            client.collections.create(
                name=collection_name,
                description="Unified collection for knowledge base articles",
                vectorizer_config=vectorizer_config,
                properties=properties
            )

            logger.info(f"Collection '{collection_name}' با موفقیت ایجاد شد.")
            return True

    except Exception as e:
        logger.error(f"خطا در ایجاد Collection '{collection_name}': {e}", exc_info=True)
        return False

# ... (توابع منسوخ شده می‌توانند باقی بمانند یا حذف شوند) ...