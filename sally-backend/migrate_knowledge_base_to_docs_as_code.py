#!/usr/bin/env python3
"""
Database migration script to transfer existing knowledge base data to the new Docs-as-Code system.

This script:
1. Migrates existing KnowledgeBaseArticle documents to the new model structure
2. Creates categories and tags in the new embedded format
3. Converts existing content to markdown and HTML formats
4. Sets up the Git repository with initial markdown files
5. Updates references to use the new model structure
"""

import asyncio
import logging
import sys
import os
from datetime import datetime
from bson import ObjectId
from pathlib import Path
import markdown

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
from app.domain.entities_refactored import (
    KnowledgeBaseArticle, Category, ArticleStatus, ArticleVisibility, 
    ArticleCategory, ArticleTag, Admin
)
from app.docs_as_code.git_manager import GitManager
from app.docs_as_code.file_converter import FileConverter
from app.docs_as_code.markdown_processor import MarkdownProcessor
from app.infrastructure.database_refactored import init_beanie

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class KnowledgeBaseMigration:
    def __init__(self):
        self.client = AsyncIOMotorClient(settings.mongodb_url)
        self.db = self.client.get_default_database()
        self.git_manager = GitManager()
        self.file_converter = FileConverter()
        self.markdown_processor = MarkdownProcessor()
    
    async def setup(self):
        """Setup the migration environment."""
        logger.info("Setting up migration environment...")
        
        # Initialize Beanie
        db_name = self.client.get_default_database().name
        await init_beanie(database=self.client[db_name], 
                         document_models=[KnowledgeBaseArticle, Category, Admin])
        
        # Initialize Git repository if it doesn't exist
        if not self.git_manager.repo_path.exists():
            await self.git_manager.initialize_repository()
            logger.info("Initialized Git repository")
        
        return True
    
    async def migrate_categories(self):
        """Migrate existing categories to the new structure."""
        logger.info("Migrating categories...")
        
        # Get existing categories from old structure
        old_categories = await self.db.categories.find({}).to_list(None)
        logger.info(f"Found {len(old_categories)} categories to migrate")
        
        migrated_categories = 0
        
        for old_cat in old_categories:
            try:
                # Check if category already exists in new structure
                existing_category = await Category.find_one(Category.name == old_cat['name'])
                
                if not existing_category:
                    # Create new category with slug and hierarchy support
                    category = Category(
                        name=old_cat['name'],
                        slug=self._generate_slug(old_cat['name']),
                        description=old_cat.get('description'),
                        is_public=old_cat.get('is_public', True),
                        created_at=old_cat.get('created_at', datetime.utcnow()),
                        updated_at=datetime.utcnow()
                    )
                    
                    # Handle parent category if exists
                    if old_cat.get('parent_id'):
                        parent_cat = await self.db.categories.find_one({'_id': ObjectId(old_cat['parent_id'])})
                        if parent_cat:
                            # Find or create parent category
                            parent_category = await Category.find_one(Category.name == parent_cat['name'])
                            if not parent_category:
                                parent_category = Category(
                                    name=parent_cat['name'],
                                    slug=self._generate_slug(parent_cat['name']),
                                    description=parent_cat.get('description'),
                                    is_public=parent_cat.get('is_public', True),
                                    created_at=parent_cat.get('created_at', datetime.utcnow()),
                                    updated_at=datetime.utcnow()
                                )
                                await parent_category.insert()
                            
                            category.parent = parent_category
                    
                    await category.insert()
                    await category.update_ancestors()  # Update ancestors hierarchy
                    await category.save()
                    
                    migrated_categories += 1
                    logger.info(f"Migrated category: {old_cat['name']}")
                else:
                    logger.info(f"Category already exists: {old_cat['name']}")
                    
            except Exception as e:
                logger.error(f"Error migrating category {old_cat['name']}: {str(e)}")
                continue
        
        logger.info(f"Category migration complete: {migrated_categories} categories migrated")
        return migrated_categories
    
    async def migrate_articles(self):
        """Migrate existing articles to the new structure."""
        logger.info("Migrating articles...")
        
        # Get existing articles from old structure
        old_articles = await self.db.knowledge_base_articles.find({}).to_list(None)
        logger.info(f"Found {len(old_articles)} articles to migrate")
        
        migrated_articles = 0
        failed_articles = 0
        
        for old_article in old_articles:
            try:
                # Check if article already exists in new structure
                existing_article = await KnowledgeBaseArticle.find_one(KnowledgeBaseArticle.title == old_article['title'])
                
                if not existing_article:
                    # Convert content to markdown and HTML
                    content_markdown = old_article['content']
                    content_html = markdown.markdown(content_markdown)
                    
                    # Handle category
                    category_data = None
                    if old_article.get('category_id'):
                        old_category = await self.db.categories.find_one({'_id': ObjectId(old_article['category_id'])})
                        if old_category:
                            # Find corresponding new category
                            new_category = await Category.find_one(Category.name == old_category['name'])
                            if new_category:
                                category_data = ArticleCategory(
                                    id=str(new_category.id),
                                    name=new_category.name,
                                    slug=new_category.slug
                                )
                    
                    # Handle tags
                    tags_data = []
                    if old_article.get('tags'):
                        for tag_name in old_article['tags']:
                            # Create embedded tag data
                            tag_data = ArticleTag(
                                id=str(ObjectId()),  # Generate new ID for embedded tag
                                name=tag_name,
                                color=None  # No color in old system
                            )
                            tags_data.append(tag_data)
                    
                    # Handle author
                    author = None
                    if old_article.get('author_id'):
                        # Find admin by old user ID
                        old_user = await self.db.users.find_one({'_id': ObjectId(old_article['author_id'])})
                        if old_user:
                            # Find corresponding admin
                            author = await Admin.find_one(Admin.email == old_user['email'])
                    
                    # If no author found, use first available admin
                    if not author:
                        author = await Admin.find_one()
                    
                    # Handle publisher
                    publisher = None
                    if old_article.get('published_by'):
                        old_user = await self.db.users.find_one({'_id': ObjectId(old_article['published_by'])})
                        if old_user:
                            publisher = await Admin.find_one(Admin.email == old_user['email'])
                    
                    # Create new article
                    article = KnowledgeBaseArticle(
                        title=old_article['title'],
                        content_markdown=content_markdown,
                        content_html=content_html,
                        summary=old_article.get('summary'),
                        category=category_data,
                        tags=tags_data,
                        status=ArticleStatus(old_article['status']),
                        visibility=ArticleVisibility(old_article['visibility']) if old_article.get('visibility') else None,
                        author=author,
                        publisher=publisher,
                        version=old_article.get('version', 1),
                        created_at=old_article.get('created_at', datetime.utcnow()),
                        updated_at=old_article.get('updated_at', datetime.utcnow()),
                        published_at=old_article.get('published_at')
                    )
                    
                    await article.insert()
                    migrated_articles += 1
                    logger.info(f"Migrated article: {old_article['title']}")
                    
                    # Sync to Git repository
                    await self._sync_article_to_git(article, "Migration Bot")
                    
                else:
                    logger.info(f"Article already exists: {old_article['title']}")
                    
            except Exception as e:
                failed_articles += 1
                logger.error(f"Error migrating article {old_article['title']}: {str(e)}")
                continue
        
        logger.info(f"Article migration complete: {migrated_articles} migrated, {failed_articles} failed")
        return migrated_articles, failed_articles
    
    async def _sync_article_to_git(self, article: KnowledgeBaseArticle, author_name: str):
        """Sync an article to the Git repository."""
        try:
            # Convert article to markdown
            markdown_content = self.file_converter.article_to_markdown(article, author_name)
            
            # Determine file path based on category
            if article.category:
                category_dir = self.git_manager.repo_path / article.category['slug']
                category_dir.mkdir(exist_ok=True)
                file_path = category_dir / f"{self._generate_slug(article.title)}.md"
            else:
                file_path = self.git_manager.repo_path / f"{self._generate_slug(article.title)}.md"
            
            # Write markdown file
            file_path.write_text(markdown_content, encoding='utf-8')
            
            # Commit to Git
            commit_message = f"Add article: {article.title}"
            await self.git_manager.commit_file(file_path, commit_message, author_name, "migration@example.com")
            
            logger.info(f"Synced article to Git: {article.title}")
            return True
            
        except Exception as e:
            logger.error(f"Error syncing article {article.title} to Git: {str(e)}")
            return False
    
    def _generate_slug(self, text: str) -> str:
        """Generate a URL-friendly slug from text."""
        import re
        import unicodedata
        
        # Normalize and convert to lowercase
        text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
        text = text.lower().strip()
        
        # Replace non-alphanumeric characters with hyphens
        text = re.sub(r'[^\w\s-]', '', text)
        text = re.sub(r'[-\s]+', '-', text)
        
        return text
    
    async def backup_old_data(self):
        """Create a backup of the old data before migration."""
        logger.info("Creating backup of old data...")
        
        try:
            # Create backup collections
            backup_timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            backup_collections = ['knowledge_base_articles', 'categories']
            
            for collection_name in backup_collections:
                backup_name = f"{collection_name}_backup_{backup_timestamp}"
                
                # Copy collection to backup
                collection = self.db[collection_name]
                backup_collection = self.db[backup_name]
                
                documents = await collection.find({}).to_list(None)
                if documents:
                    await backup_collection.insert_many(documents)
                    logger.info(f"Backed up {len(documents)} documents to {backup_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error creating backup: {str(e)}")
            return False
    
    async def validate_migration(self):
        """Validate that the migration was successful."""
        logger.info("Validating migration...")
        
        validation_results = {
            'categories': {'expected': 0, 'actual': 0, 'status': 'PASS'},
            'articles': {'expected': 0, 'actual': 0, 'status': 'PASS'},
            'git_files': {'expected': 0, 'actual': 0, 'status': 'PASS'}
        }
        
        try:
            # Validate categories
            old_categories_count = await self.db.categories.count_documents({})
            new_categories_count = await Category.find({}).count()
            
            validation_results['categories']['expected'] = old_categories_count
            validation_results['categories']['actual'] = new_categories_count
            validation_results['categories']['status'] = 'PASS' if new_categories_count >= old_categories_count else 'FAIL'
            
            # Validate articles
            old_articles_count = await self.db.knowledge_base_articles.count_documents({})
            new_articles_count = await KnowledgeBaseArticle.find({}).count()
            
            validation_results['articles']['expected'] = old_articles_count
            validation_results['articles']['actual'] = new_articles_count
            validation_results['articles']['status'] = 'PASS' if new_articles_count >= old_articles_count else 'FAIL'
            
            # Validate Git files
            git_files = await self.git_manager.list_markdown_files()
            validation_results['git_files']['expected'] = old_articles_count
            validation_results['git_files']['actual'] = len(git_files)
            validation_results['git_files']['status'] = 'PASS' if len(git_files) >= old_articles_count else 'FAIL'
            
            # Print validation results
            logger.info("Migration Validation Results:")
            for component, result in validation_results.items():
                status_icon = "✅" if result['status'] == 'PASS' else "❌"
                logger.info(f"{status_icon} {component}: {result['actual']}/{result['expected']} - {result['status']}")
            
            return all(result['status'] == 'PASS' for result in validation_results.values())
            
        except Exception as e:
            logger.error(f"Error during validation: {str(e)}")
            return False
    
    async def migrate_all(self, create_backup: bool = True):
        """Run complete migration process."""
        logger.info("Starting knowledge base migration to Docs-as-Code system...")
        
        try:
            # Setup environment
            await self.setup()
            
            # Create backup if requested
            if create_backup:
                await self.backup_old_data()
            
            # Migrate categories
            categories_migrated = await self.migrate_categories()
            
            # Migrate articles
            articles_migrated, articles_failed = await self.migrate_articles()
            
            # Validate migration
            validation_passed = await self.validate_migration()
            
            logger.info("Knowledge base migration completed!")
            
            return {
                "status": "success",
                "categories_migrated": categories_migrated,
                "articles_migrated": articles_migrated,
                "articles_failed": articles_failed,
                "validation_passed": validation_passed
            }
            
        except Exception as e:
            logger.error(f"Migration failed: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    async def rollback(self):
        """Rollback migration (for testing purposes)."""
        logger.warning("Starting rollback...")
        
        try:
            # Delete all documents from new collections
            collections_to_clean = [KnowledgeBaseArticle, Category]
            
            for model in collections_to_clean:
                result = await model.find({}).delete()
                logger.info(f"Cleared {result} documents from {model.__name__}")
            
            # Reset Git repository (remove all markdown files)
            git_files = await self.git_manager.list_markdown_files()
            for file_path in git_files:
                file_path.unlink()
            
            # Commit the removal
            await self.git_manager.commit_all_changes("Rollback: Remove migrated articles", 
                                                     "rollback@example.com", "Rollback Bot")
            
            logger.info("Rollback completed")
            return True
            
        except Exception as e:
            logger.error(f"Error during rollback: {str(e)}")
            return False


async def main():
    """Main migration function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate knowledge base to Docs-as-Code system')
    parser.add_argument('--no-backup', action='store_true', help='Skip backup creation')
    parser.add_argument('--rollback', action='store_true', help='Rollback migration')
    
    args = parser.parse_args()
    
    migration = KnowledgeBaseMigration()
    
    if args.rollback:
        confirm = input("Are you sure you want to rollback the migration? This will delete all migrated data. (y/N): ")
        if confirm.lower() == 'y':
            await migration.rollback()
        else:
            logger.info("Rollback cancelled")
        return
    
    # Run migration
    result = await migration.migrate_all(create_backup=not args.no_backup)
    
    if result["status"] == "success":
        logger.info("Migration successful!")
        logger.info(f"Categories migrated: {result['categories_migrated']}")
        logger.info(f"Articles migrated: {result['articles_migrated']}")
        logger.info(f"Articles failed: {result['articles_failed']}")
        logger.info(f"Validation passed: {result['validation_passed']}")
        
        if not result['validation_passed']:
            logger.warning("Migration completed but validation failed. Please check the data manually.")
    else:
        logger.error(f"Migration failed: {result['error']}")


if __name__ == "__main__":
    asyncio.run(main())