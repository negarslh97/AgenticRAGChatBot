"""
Bidirectional synchronization service for Docs-as-Code system.
"""
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
import hashlib
import logging
from bson import ObjectId

from .config import DocsAsCodeConfig
from .git_manager import GitManager
from .markdown_processor import MarkdownProcessor, CategoryProcessor
from .file_converter import FileConverter
from app.domain.entities import KnowledgeBaseArticle, Category, ArticleStatus, ArticleVisibility


logger = logging.getLogger(__name__)


class SyncService:
    """Bidirectional synchronization between Git and MongoDB."""
    
    def __init__(self, config: DocsAsCodeConfig):
        self.config = config
        self.git_manager = GitManager(config.git)
        self.markdown_processor = MarkdownProcessor(config.markdown)
        self.category_processor = CategoryProcessor(config.markdown)
        self.file_converter = FileConverter(config.conversion)
    
    async def sync_git_to_mongo(self, full_sync: bool = False) -> Dict[str, Any]:
        """
        Synchronize changes from Git repository to MongoDB.
        
        Args:
            full_sync: If True, perform full sync (slower but more thorough)
            
        Returns:
            Dictionary with sync statistics
        """
        stats = {
            'articles_created': 0,
            'articles_updated': 0,
            'articles_deleted': 0,
            'categories_created': 0,
            'categories_updated': 0,
            'categories_deleted': 0,
            'errors': []
        }
        
        try:
            # Sync with remote first
            await self.git_manager.sync_with_remote()
            
            if full_sync:
                await self._full_sync_git_to_mongo(stats)
            else:
                await self._incremental_sync_git_to_mongo(stats)
                
        except Exception as e:
            logger.error(f"Git to MongoDB sync failed: {str(e)}")
            stats['errors'].append(str(e))
        
        return stats
    
    async def _full_sync_git_to_mongo(self, stats: Dict[str, Any]):
        """Perform full synchronization."""
        logger.info("Starting full Git to MongoDB sync")
        
        # Sync categories first
        await self._sync_categories_from_git(stats)
        
        # Sync articles
        await self._sync_articles_from_git(stats)
        
        # Clean up deleted articles
        await self._cleanup_deleted_articles(stats)
        
        logger.info(f"Full sync completed: {stats}")
    
    async def _incremental_sync_git_to_mongo(self, stats: Dict[str, Any]):
        """Perform incremental synchronization."""
        logger.info("Starting incremental Git to MongoDB sync")
        
        # Get changed files since last sync
        changed_files = await self.git_manager.get_changed_files()
        
        if not changed_files:
            logger.info("No changes detected in Git repository")
            return
        
        # Process changed files
        for file_info in changed_files:
            await self._process_changed_file(file_info, stats)
        
        logger.info(f"Incremental sync completed: {stats}")
    
    async def _sync_categories_from_git(self, stats: Dict[str, Any]):
        """Sync categories from Git to MongoDB."""
        categories_path = self.config.categories_path
        
        if not categories_path.exists():
            logger.warning("Categories directory not found in Git repository")
            return
        
        # Find all category files
        category_files = list(categories_path.rglob("_category.yaml"))
        
        for category_file in category_files:
            try:
                # Parse category data
                category_data = self.category_processor.parse_category_file(category_file)
                category_slug = category_data['slug']
                
                # Find or create category in MongoDB
                existing_category = await Category.find_one(Category.slug == category_slug)
                
                if existing_category:
                    # Update existing category
                    await self._update_category_from_git(existing_category, category_data)
                    stats['categories_updated'] += 1
                else:
                    # Create new category
                    await self._create_category_from_git(category_data, category_file.parent.name)
                    stats['categories_created'] += 1
                    
            except Exception as e:
                logger.error(f"Failed to sync category {category_file}: {str(e)}")
                stats['errors'].append(f"Category {category_file}: {str(e)}")
    
    async def _sync_articles_from_git(self, stats: Dict[str, Any]):
        """Sync articles from Git to MongoDB."""
        articles_path = self.config.articles_path
        
        if not articles_path.exists():
            logger.warning("Articles directory not found in Git repository")
            return
        
        # Find all markdown files
        markdown_files = list(articles_path.rglob("*.md"))
        
        for md_file in markdown_files:
            try:
                # Parse markdown file
                parsed = self.markdown_processor.parse_markdown_file(md_file)
                metadata = parsed['metadata']
                content = parsed['content']
                
                # Find or create article in MongoDB
                article_id = metadata.get('id')
                existing_article = None
                
                if article_id:
                    existing_article = await KnowledgeBaseArticle.get(ObjectId(article_id))
                
                if existing_article:
                    # Update existing article
                    await self._update_article_from_git(existing_article, metadata, content)
                    stats['articles_updated'] += 1
                else:
                    # Create new article
                    await self._create_article_from_git(metadata, content)
                    stats['articles_created'] += 1
                    
            except Exception as e:
                logger.error(f"Failed to sync article {md_file}: {str(e)}")
                stats['errors'].append(f"Article {md_file}: {str(e)}")
    
    async def _process_changed_file(self, file_info: Dict[str, Any], stats: Dict[str, Any]):
        """Process a single changed file."""
        file_path = Path(file_info['path'])
        
        if file_info['change_type'] == 'D':
            # File deleted
            await self._handle_file_deletion(file_path, stats)
        else:
            # File added or modified
            await self._handle_file_change(file_path, stats)
    
    async def _handle_file_deletion(self, file_path: Path, stats: Dict[str, Any]):
        """Handle file deletion from Git."""
        if file_path.name == "_category.yaml":
            # Category deletion
            category_slug = file_path.parent.name
            category = await Category.find_one(Category.slug == category_slug)
            if category:
                await category.delete()
                stats['categories_deleted'] += 1
        elif file_path.suffix == ".md":
            # Article deletion
            # We need to parse the file to get the ID, but it's deleted
            # For now, we'll rely on full sync for deletions
            pass
    
    async def _handle_file_change(self, file_path: Path, stats: Dict[str, Any]):
        """Handle file addition or modification."""
        if file_path.name == "_category.yaml":
            await self._sync_single_category(file_path, stats)
        elif file_path.suffix == ".md":
            await self._sync_single_article(file_path, stats)
    
    async def _sync_single_category(self, category_file: Path, stats: Dict[str, Any]):
        """Sync a single category file."""
        try:
            category_data = self.category_processor.parse_category_file(category_file)
            category_slug = category_data['slug']
            
            existing_category = await Category.find_one(Category.slug == category_slug)
            
            if existing_category:
                await self._update_category_from_git(existing_category, category_data)
                stats['categories_updated'] += 1
            else:
                await self._create_category_from_git(category_data, category_file.parent.name)
                stats['categories_created'] += 1
                
        except Exception as e:
            logger.error(f"Failed to sync category {category_file}: {str(e)}")
            stats['errors'].append(str(e))
    
    async def _sync_single_article(self, article_file: Path, stats: Dict[str, Any]):
        """Sync a single article file."""
        try:
            parsed = self.markdown_processor.parse_markdown_file(article_file)
            metadata = parsed['metadata']
            content = parsed['content']
            
            article_id = metadata.get('id')
            existing_article = None
            
            if article_id:
                existing_article = await KnowledgeBaseArticle.get(ObjectId(article_id))
            
            if existing_article:
                await self._update_article_from_git(existing_article, metadata, content)
                stats['articles_updated'] += 1
            else:
                await self._create_article_from_git(metadata, content)
                stats['articles_created'] += 1
                
        except Exception as e:
            logger.error(f"Failed to sync article {article_file}: {str(e)}")
            stats['errors'].append(str(e))
    
    async def _create_category_from_git(self, category_data: Dict[str, Any], slug: str):
        """Create a new category from Git data."""
        category = Category(
            name=category_data['name'],
            slug=slug,
            description=category_data.get('description'),
            is_public=category_data.get('is_public', True)
        )
        
        # Handle parent category
        parent_slug = category_data.get('parent')
        if parent_slug:
            parent_category = await Category.find_one(Category.slug == parent_slug)
            if parent_category:
                category.parent = parent_category
        
        await category.insert()
        await category.update_ancestors()
        await category.save()
    
    async def _update_category_from_git(self, category: Category, category_data: Dict[str, Any]):
        """Update existing category from Git data."""
        category.name = category_data['name']
        category.description = category_data.get('description')
        category.is_public = category_data.get('is_public', True)
        
        # Handle parent category
        parent_slug = category_data.get('parent')
        if parent_slug:
            parent_category = await Category.find_one(Category.slug == parent_slug)
            category.parent = parent_category if parent_category else None
        else:
            category.parent = None
        
        await category.update_ancestors()
        await category.save()
    
    async def _create_article_from_git(self, metadata: Dict[str, Any], content: str):
        """Create a new article from Git data."""
        # Convert markdown to HTML for the database
        from markdown import markdown
        content_html = markdown(content)
        
        article = KnowledgeBaseArticle(
            title=metadata['title'],
            content_markdown=content,
            content_html=content_html,
            summary=metadata.get('summary'),
            status=ArticleStatus(metadata['status']),
            visibility=ArticleVisibility(metadata['visibility']) if metadata.get('visibility') else None,
            version=metadata.get('version', 1),
            created_at=datetime.fromisoformat(metadata['created_at']),
            updated_at=datetime.fromisoformat(metadata['updated_at']),
            published_at=datetime.fromisoformat(metadata['published_at']) if metadata.get('published_at') else None
        )
        
        # Handle category
        category_slug = metadata.get('category')
        if category_slug:
            category = await Category.find_one(Category.slug == category_slug)
            if category:
                article.category = {
                    'id': str(category.id),
                    'name': category.name,
                    'slug': category.slug
                }
        
        # Handle tags
        tags = metadata.get('tags', [])
        if tags:
            # For now, store as simple list of tag names
            # In a more advanced implementation, we'd link to Tag documents
            article.tags = [{'id': tag, 'name': tag} for tag in tags]
        
        await article.insert()
    
    async def _update_article_from_git(self, article: KnowledgeBaseArticle, metadata: Dict[str, Any], content: str):
        """Update existing article from Git data."""
        from markdown import markdown
        
        article.title = metadata['title']
        article.content_markdown = content
        article.content_html = markdown(content)
        article.summary = metadata.get('summary')
        article.status = ArticleStatus(metadata['status'])
        article.visibility = ArticleVisibility(metadata['visibility']) if metadata.get('visibility') else None
        article.version = metadata.get('version', article.version + 1)
        article.updated_at = datetime.fromisoformat(metadata['updated_at'])
        
        if metadata.get('published_at'):
            article.published_at = datetime.fromisoformat(metadata['published_at'])
        
        # Handle category
        category_slug = metadata.get('category')
        if category_slug:
            category = await Category.find_one(Category.slug == category_slug)
            if category:
                article.category = {
                    'id': str(category.id),
                    'name': category.name,
                    'slug': category.slug
                }
        else:
            article.category = None
        
        # Handle tags
        tags = metadata.get('tags', [])
        article.tags = [{'id': tag, 'name': tag} for tag in tags]
        
        await article.save()
    
    async def _cleanup_deleted_articles(self, stats: Dict[str, Any]):
        """Clean up articles that no longer exist in Git."""
        # This is a simplified implementation
        # In production, you'd want a more sophisticated approach
        git_article_ids = await self._get_git_article_ids()
        
        all_articles = await KnowledgeBaseArticle.find_all().to_list()
        
        for article in all_articles:
            if str(article.id) not in git_article_ids:
                await article.delete()
                stats['articles_deleted'] += 1
    
    async def _get_git_article_ids(self) -> Set[str]:
        """Get set of all article IDs from Git repository."""
        article_ids = set()
        articles_path = self.config.articles_path
        
        if articles_path.exists():
            for md_file in articles_path.rglob("*.md"):
                try:
                    parsed = self.markdown_processor.parse_markdown_file(md_file)
                    article_id = parsed['metadata'].get('id')
                    if article_id:
                        article_ids.add(article_id)
                except Exception:
                    continue
        
        return article_ids


class MongoToGitSync:
    """Synchronize changes from MongoDB to Git repository."""
    
    def __init__(self, config: DocsAsCodeConfig):
        self.config = config
        self.git_manager = GitManager(config.git)
        self.markdown_processor = MarkdownProcessor(config.markdown)
        self.category_processor = CategoryProcessor(config.markdown)
    
    async def sync_article_to_git(self, article_id: str, author: Dict[str, str]) -> bool:
        """Sync a single article from MongoDB to Git."""
        try:
            article = await KnowledgeBaseArticle.get(ObjectId(article_id))
            if not article:
                logger.error(f"Article {article_id} not found")
                return False
            
            # Generate markdown file path
            file_path = await self._get_article_file_path(article)
            
            # Generate metadata
            metadata = await self._generate_article_metadata(article)
            
            # Write markdown file
            self.markdown_processor.write_markdown_file(
                file_path, metadata, article.content_markdown
            )
            
            # Commit and push changes
            commit_message = f"Update article: {article.title}"
            await self.git_manager.commit_changes([file_path], commit_message, author)
            await self.git_manager.push_changes()
            
            logger.info(f"Successfully synced article {article_id} to Git")
            return True
            
        except Exception as e:
            logger.error(f"Failed to sync article {article_id} to Git: {str(e)}")
            return False
    
    async def _get_article_file_path(self, article: KnowledgeBaseArticle) -> Path:
        """Generate file path for an article based on its category."""
        base_path = self.config.articles_path
        
        if article.category:
            # Use category slug for directory
            category_slug = article.category['slug']
            directory = base_path / category_slug
        else:
            directory = base_path / "uncategorized"
        
        # Use article slug for filename
        slug = article.category['slug'] if article.category else "article"
        filename = f"{slug}.md"
        
        return directory / filename
    
    async def _generate_article_metadata(self, article: KnowledgeBaseArticle) -> Dict[str, Any]:
        """Generate YAML front matter for an article."""
        return {
            'id': str(article.id),
            'title': article.title,
            'slug': article.category['slug'] if article.category else "article",
            'author_id': str(article.author.id) if hasattr(article, 'author') else "system",
            'category': article.category['slug'] if article.category else None,
            'tags': [tag['name'] for tag in article.tags],
            'status': article.status.value,
            'visibility': article.visibility.value if article.visibility else None,
            'created_at': article.created_at.isoformat(),
            'updated_at': article.updated_at.isoformat(),
            'published_at': article.published_at.isoformat() if article.published_at else None,
            'version': article.version,
            'sync_hash': self._calculate_sync_hash(article)
        }
    
    def _calculate_sync_hash(self, article: KnowledgeBaseArticle) -> str:
        """Calculate hash for sync conflict detection."""
        content = f"{article.title}{article.content_markdown}{article.updated_at.isoformat()}"
        return hashlib.sha256(content.encode()).hexdigest()


# Factory function for easy service creation
async def create_sync_service() -> SyncService:
    """Create a configured sync service."""
    config = DocsAsCodeConfig(
        git=GitConfig(
            repo_url="https://github.com/nslhsdgn/kb.git",
            local_path=Path("./kb"),
            branch="main"
        )
    )
    return SyncService(config)