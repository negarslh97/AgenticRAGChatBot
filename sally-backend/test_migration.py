import asyncio
from app.infrastructure.database_refactored import init_db
from app.domain.entities_refactored import KnowledgeBaseArticle

async def test_articles():
    await init_db()

    try:
        # Test loading articles
        articles = await KnowledgeBaseArticle.find({}).to_list()
        print(f'Successfully loaded {len(articles)} articles')

        if articles:
            article = articles[0]
            print(f'First article title: {article.title}')
            print(f'Has content_markdown: {hasattr(article, "content_markdown")}')
            print(f'Has content_html: {hasattr(article, "content_html")}')
            print(f'Tags type: {type(article.tags)}')
            if article.tags:
                print(f'First tag: {article.tags[0]}')

    except Exception as e:
        print(f'Error: {e}')

if __name__ == "__main__":
    asyncio.run(test_articles())
