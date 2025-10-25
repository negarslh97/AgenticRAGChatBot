"""
Weaviate Utilities - ابزارهای کمکی برای کار با Weaviate
========================================================

این فایل توابع کمکی برای مدیریت Collection های Weaviate و عملیات مرتبط را فراهم می‌کند.
"""

from app.core.config import settings


def get_weaviate_collection_name() -> str:
    """
    نام صحیح Weaviate collection را بر اساس مدل embedding فعلی برمی‌گرداند.

    این تابع تضمین می‌کند که همه قسمت‌های سیستم از نام Collection یکسانی استفاده کنند
    و از اشتباهات فاجعه‌بار (مثل پاک کردن Collection اشتباه) جلوگیری شود.

    Returns:
        str: نام Collection - "MarkdownNode_Small" یا "MarkdownNode_Large"
    """
    embedder_model = settings.embedder_model_loaded
    if embedder_model and "large" in embedder_model.lower():
        return "MarkdownNode_Large"
    else:
        return "MarkdownNode_Small"


def get_weaviate_vectorizer_config():
    """
    تنظیمات vectorizer را بر اساس مدل embedding فعلی برمی‌گرداند.

    Returns:
        dict: تنظیمات vectorizer برای Weaviate
    """
    from weaviate.classes.config import Configure

    embedder_model = settings.embedder_model_loaded
    embedder_base_url = settings.embedder_openai_base_url_loaded

    return Configure.Vectorizer.text2vec_openai(
        model=embedder_model,
        base_url=embedder_base_url
    )


def get_weaviate_properties():
    """
    لیست properties استاندارد برای MarkdownNode collection را برمی‌گرداند.

    Returns:
        list: لیست Property objects برای Weaviate schema
    """
    from weaviate.classes.config import Property, DataType

    return [
        Property(name="node_id", data_type=DataType.TEXT),
        Property(name="article_id", data_type=DataType.TEXT),
        Property(name="title", data_type=DataType.TEXT),
        Property(name="content", data_type=DataType.TEXT),
        Property(name="full_content", data_type=DataType.TEXT),
        Property(name="level", data_type=DataType.INT),
        Property(name="path", data_type=DataType.TEXT),
        Property(name="order", data_type=DataType.INT),
        Property(name="parent_id", data_type=DataType.TEXT),
        Property(name="visibility", data_type=DataType.TEXT),
        Property(name="category", data_type=DataType.TEXT),
    ]