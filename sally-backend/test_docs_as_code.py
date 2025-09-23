"""
Test and validation script for the Docs-as-Code system.
"""
import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime
import json

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.docs_as_code.git_manager import GitManager
from app.docs_as_code.markdown_processor import MarkdownProcessor
from app.docs_as_code.file_converter import FileConverter
from app.docs_as_code.sync_service import SyncService, MongoToGitSync
from app.docs_as_code.background_jobs import start_background_jobs, stop_background_jobs, schedule_sync_git_to_mongo
from app.docs_as_code.conflict_resolver import ConflictResolver, conflict_manager
from app.docs_as_code.monitoring import monitoring_service, get_system_stats
from app.domain.entities_refactored import KnowledgeBaseArticle, Category, ArticleStatus, ArticleVisibility, Admin
from app.infrastructure.database_refactored import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings


class DocsAsCodeTester:
    """Test and validate the Docs-as-Code system."""
    
    def __init__(self):
        self.test_results = []
        self.errors = []
    
    async def setup(self):
        """Setup the test environment."""
        print("Setting up test environment...")
        
        # Initialize database connection
        try:
            client = AsyncIOMotorClient(settings.mongodb_url)
            db_name = client.get_default_database().name
            await init_beanie(database=client[db_name], document_models=[KnowledgeBaseArticle, Category, Admin])
            self.test_results.append(("Database Connection", "SUCCESS", "Connected to MongoDB"))
        except Exception as e:
            self.errors.append(("Database Connection", str(e)))
            self.test_results.append(("Database Connection", "FAILED", str(e)))
            return False
        
        # Start background jobs
        try:
            await start_background_jobs()
            self.test_results.append(("Background Jobs", "SUCCESS", "Background jobs started"))
        except Exception as e:
            self.errors.append(("Background Jobs", str(e)))
            self.test_results.append(("Background Jobs", "FAILED", str(e)))
            return False
        
        return True
    
    async def test_git_manager(self):
        """Test Git repository management."""
        print("Testing Git manager...")
        
        try:
            git_manager = GitManager()
            
            # Check if repository exists
            repo_exists = git_manager.repo_path.exists()
            self.test_results.append(("Git Repository Exists", "SUCCESS" if repo_exists else "FAILED", 
                                    "Exists" if repo_exists else "Not found"))
            
            if repo_exists:
                # Test getting latest commit
                commit = await git_manager.get_latest_commit()
                self.test_results.append(("Git Latest Commit", "SUCCESS", commit[:40] if commit else "No commits"))
                
                # Test listing files
                files = await git_manager.list_markdown_files()
                self.test_results.append(("Git List Files", "SUCCESS", f"Found {len(files)} markdown files"))
            
            return True
        except Exception as e:
            self.errors.append(("Git Manager", str(e)))
            self.test_results.append(("Git Manager", "FAILED", str(e)))
            return False
    
    async def test_markdown_processor(self):
        """Test Markdown processing."""
        print("Testing Markdown processor...")
        
        try:
            processor = MarkdownProcessor()
            
            # Create a test markdown file
            test_content = """---
title: Test Article
category: test
status: draft
visibility: internal
summary: This is a test article
tags: [test, validation]
updated_at: 2023-01-01T00:00:00Z
sync_hash: abc123
---

# Test Article Content

This is the content of the test article.
"""
            
            test_file = Path("test_article.md")
            test_file.write_text(test_content, encoding='utf-8')
            
            # Test parsing
            parsed = processor.parse_markdown_file(test_file)
            self.test_results.append(("Markdown Parsing", "SUCCESS", 
                                    f"Parsed metadata: {list(parsed['metadata'].keys())}"))
            
            # Test validation
            is_valid = processor.validate_markdown_structure(parsed['metadata'])
            self.test_results.append(("Markdown Validation", "SUCCESS" if is_valid else "FAILED", 
                                    "Valid" if is_valid else "Invalid"))
            
            # Clean up
            test_file.unlink()
            
            return True
        except Exception as e:
            self.errors.append(("Markdown Processor", str(e)))
            self.test_results.append(("Markdown Processor", "FAILED", str(e)))
            return False
    
    async def test_file_converter(self):
        """Test file conversion."""
        print("Testing file converter...")
        
        try:
            converter = FileConverter()
            
            # Test markdown to article conversion
            test_metadata = {
                'title': 'Test Article',
                'category': 'test',
                'status': 'draft',
                'visibility': 'internal',
                'summary': 'Test summary',
                'tags': ['test'],
                'updated_at': '2023-01-01T00:00:00Z'
            }
            
            test_content = "# Test Content"
            
            article_data = converter.markdown_to_article_data(test_metadata, test_content)
            self.test_results.append(("Markdown to Article", "SUCCESS", 
                                    f"Converted: {article_data['title']}"))
            
            # Test article to markdown conversion
            class MockArticle:
                def __init__(self):
                    self.id = "test123"
                    self.title = "Test Article"
                    self.content_markdown = "# Test Content"
                    self.summary = "Test summary"
                    self.status = ArticleStatus.DRAFT
                    self.visibility = ArticleVisibility.INTERNAL
                    self.updated_at = datetime.utcnow()
                    self.category = {'slug': 'test', 'name': 'Test Category'}
                    self.tags = [{'name': 'test', 'color': '#000000'}]
            
            mock_article = MockArticle()
            markdown_content = converter.article_to_markdown(mock_article, "Test Author")
            self.test_results.append(("Article to Markdown", "SUCCESS", 
                                    "Converted successfully"))
            
            return True
        except Exception as e:
            self.errors.append(("File Converter", str(e)))
            self.test_results.append(("File Converter", "FAILED", str(e)))
            return False
    
    async def test_sync_service(self):
        """Test synchronization service."""
        print("Testing sync service...")
        
        try:
            sync_service = SyncService()
            mongo_to_git_sync = MongoToGitSync()
            
            # Test Git to MongoDB sync (dry run)
            stats = await sync_service.sync_git_to_mongo(dry_run=True)
            self.test_results.append(("Git to MongoDB Sync", "SUCCESS", 
                                    f"Dry run: {stats}"))
            
            # Test conflict resolver
            resolver = ConflictResolver(MarkdownProcessor())
            self.test_results.append(("Conflict Resolver", "SUCCESS", "Initialized"))
            
            return True
        except Exception as e:
            self.errors.append(("Sync Service", str(e)))
            self.test_results.append(("Sync Service", "FAILED", str(e)))
            return False
    
    async def test_monitoring(self):
        """Test monitoring system."""
        print("Testing monitoring system...")
        
        try:
            # Get system stats
            stats = await get_system_stats()
            self.test_results.append(("Monitoring System", "SUCCESS", 
                                    f"Health: {stats['health']['status']}"))
            
            # Test error recording
            monitoring_service.record_error("Test Operation", "Test error message")
            self.test_results.append(("Error Recording", "SUCCESS", "Error recorded"))
            
            return True
        except Exception as e:
            self.errors.append(("Monitoring", str(e)))
            self.test_results.append(("Monitoring", "FAILED", str(e)))
            return False
    
    async def test_integration(self):
        """Test integrated workflow."""
        print("Testing integrated workflow...")
        
        try:
            # Create a test category
            test_category = Category(
                name="Test Category",
                slug="test-category",
                description="Test category for integration testing",
                is_public=True
            )
            await test_category.insert()
            self.test_results.append(("Category Creation", "SUCCESS", "Test category created"))
            
            # Create a test article
            test_article = KnowledgeBaseArticle(
                title="Integration Test Article",
                content_markdown="# Integration Test\n\nThis is a test article for integration testing.",
                content_html="<h1>Integration Test</h1><p>This is a test article for integration testing.</p>",
                summary="Integration test article summary",
                category={
                    'id': str(test_category.id),
                    'name': test_category.name,
                    'slug': test_category.slug
                },
                tags=[{'id': '1', 'name': 'integration-test', 'color': '#ff0000'}],
                status=ArticleStatus.DRAFT,
                visibility=ArticleVisibility.INTERNAL,
                author=await Admin.find_one()  # Use first admin as author
            )
            await test_article.insert()
            self.test_results.append(("Article Creation", "SUCCESS", "Test article created"))
            
            # Test sync to Git
            mongo_to_git_sync = MongoToGitSync()
            success = await mongo_to_git_sync.sync_article_to_git(
                str(test_article.id), 
                {'name': 'Test Author', 'email': 'test@example.com'}
            )
            self.test_results.append(("Article Sync to Git", "SUCCESS" if success else "FAILED", 
                                    "Synced" if success else "Failed"))
            
            # Clean up
            await test_article.delete()
            await test_category.delete()
            
            return True
        except Exception as e:
            self.errors.append(("Integration Test", str(e)))
            self.test_results.append(("Integration Test", "FAILED", str(e)))
            return False
    
    async def run_all_tests(self):
        """Run all tests."""
        print("Starting Docs-as-Code system validation...")
        print("=" * 60)
        
        # Setup
        if not await self.setup():
            print("Setup failed. Cannot proceed with tests.")
            return
        
        # Run individual tests
        await self.test_git_manager()
        await self.test_markdown_processor()
        await self.test_file_converter()
        await self.test_sync_service()
        await self.test_monitoring()
        await self.test_integration()
        
        # Print results
        print("\n" + "=" * 60)
        print("TEST RESULTS")
        print("=" * 60)
        
        for test_name, status, details in self.test_results:
            status_icon = "✅" if status == "SUCCESS" else "❌"
            print(f"{status_icon} {test_name}: {status} - {details}")
        
        # Print errors
        if self.errors:
            print("\n" + "=" * 60)
            print("ERRORS")
            print("=" * 60)
            for component, error in self.errors:
                print(f"❌ {component}: {error}")
        
        # Print summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r[1] == "SUCCESS"])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests == 0:
            print("\n🎉 All tests passed! Docs-as-Code system is ready.")
        else:
            print(f"\n⚠️  {failed_tests} test(s) failed. Please check the errors above.")
        
        # Cleanup
        await stop_background_jobs()


async def main():
    """Main test function."""
    tester = DocsAsCodeTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())