"""
Conflict resolution mechanisms for Docs-as-Code synchronization.
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum
import hashlib
from pathlib import Path

from .markdown_processor import MarkdownProcessor
from app.domain.entities import KnowledgeBaseArticle, Category
from bson import ObjectId


logger = logging.getLogger(__name__)


class ConflictType(str, Enum):
    """Types of synchronization conflicts."""
    CONTENT_MODIFIED_BOTH_SIDES = "content_modified_both_sides"
    FILE_DELETED_IN_GIT = "file_deleted_in_git"
    ARTICLE_DELETED_IN_DB = "article_deleted_in_db"
    CATEGORY_MISMATCH = "category_mismatch"
    METADATA_CONFLICT = "metadata_conflict"


class ConflictResolution(str, Enum):
    """Available conflict resolution strategies."""
    KEEP_GIT_VERSION = "keep_git_version"
    KEEP_DB_VERSION = "keep_db_version"
    MERGE_CONTENT = "merge_content"
    MANUAL_RESOLUTION = "manual_resolution"
    SKIP = "skip"


class Conflict:
    """Represents a synchronization conflict."""
    
    def __init__(self, conflict_type: ConflictType, article_id: str, 
                 git_data: Optional[Dict[str, Any]] = None,
                 db_data: Optional[Dict[str, Any]] = None,
                 details: Optional[str] = None):
        self.conflict_type = conflict_type
        self.article_id = article_id
        self.git_data = git_data or {}
        self.db_data = db_data or {}
        self.details = details
        self.created_at = datetime.utcnow()
        self.resolved_at: Optional[datetime] = None
        self.resolution: Optional[ConflictResolution] = None
        self.resolution_notes: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert conflict to dictionary."""
        return {
            'conflict_type': self.conflict_type.value,
            'article_id': self.article_id,
            'git_data': self.git_data,
            'db_data': self.db_data,
            'details': self.details,
            'created_at': self.created_at.isoformat(),
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'resolution': self.resolution.value if self.resolution else None,
            'resolution_notes': self.resolution_notes
        }
    
    def mark_resolved(self, resolution: ConflictResolution, notes: str = None):
        """Mark conflict as resolved."""
        self.resolution = resolution
        self.resolution_notes = notes
        self.resolved_at = datetime.utcnow()


class ConflictResolver:
    """Handles detection and resolution of synchronization conflicts."""
    
    def __init__(self, markdown_processor: MarkdownProcessor):
        self.markdown_processor = markdown_processor
        self._conflicts: List[Conflict] = []
    
    async def detect_conflicts(self, git_file_path: Path, article: KnowledgeBaseArticle) -> List[Conflict]:
        """Detect conflicts between Git file and database article."""
        conflicts = []
        
        try:
            # Parse Git file
            parsed = self.markdown_processor.parse_markdown_file(git_file_path)
            git_metadata = parsed['metadata']
            git_content = parsed['content']
            
            # Calculate hashes for comparison
            git_hash = self._calculate_content_hash(git_content, git_metadata)
            db_hash = self._calculate_db_hash(article)
            
            # Check if both sides have been modified
            if git_metadata.get('sync_hash') and git_metadata['sync_hash'] != db_hash:
                conflicts.append(Conflict(
                    conflict_type=ConflictType.CONTENT_MODIFIED_BOTH_SIDES,
                    article_id=str(article.id),
                    git_data={'sync_hash': git_metadata.get('sync_hash'), 'title': git_metadata.get('title')},
                    db_data={'sync_hash': db_hash, 'title': article.title},
                    details=f"Both Git and database versions have been modified since last sync"
                ))
            
            # Check category mismatch
            git_category = git_metadata.get('category')
            db_category = article.category['slug'] if article.category else None
            
            if git_category != db_category:
                conflicts.append(Conflict(
                    conflict_type=ConflictType.CATEGORY_MISMATCH,
                    article_id=str(article.id),
                    git_data={'category': git_category},
                    db_data={'category': db_category},
                    details=f"Category mismatch: Git={git_category}, DB={db_category}"
                ))
            
            # Check metadata conflicts
            metadata_conflicts = self._check_metadata_conflicts(git_metadata, article)
            if metadata_conflicts:
                conflicts.append(Conflict(
                    conflict_type=ConflictType.METADATA_CONFLICT,
                    article_id=str(article.id),
                    git_data=git_metadata,
                    db_data=self._article_to_dict(article),
                    details=f"Metadata conflicts: {', '.join(metadata_conflicts)}"
                ))
                
        except Exception as e:
            logger.error(f"Error detecting conflicts for article {article.id}: {str(e)}")
        
        return conflicts
    
    async def resolve_conflict(self, conflict: Conflict, resolution: ConflictResolution, 
                             notes: str = None) -> bool:
        """Resolve a conflict using the specified strategy."""
        try:
            if resolution == ConflictResolution.KEEP_GIT_VERSION:
                await self._apply_git_version(conflict)
            elif resolution == ConflictResolution.KEEP_DB_VERSION:
                await self._apply_db_version(conflict)
            elif resolution == ConflictResolution.MERGE_CONTENT:
                await self._merge_content(conflict)
            elif resolution == ConflictResolution.MANUAL_RESOLUTION:
                # Manual resolution requires external intervention
                # Just mark as resolved and log
                logger.info(f"Manual resolution required for conflict {conflict.article_id}")
            elif resolution == ConflictResolution.SKIP:
                # Skip this conflict
                logger.info(f"Skipping conflict {conflict.article_id}")
            
            conflict.mark_resolved(resolution, notes)
            return True
            
        except Exception as e:
            logger.error(f"Error resolving conflict {conflict.article_id}: {str(e)}")
            return False
    
    async def auto_resolve_conflicts(self, conflicts: List[Conflict]) -> Dict[str, Any]:
        """Automatically resolve conflicts using predefined rules."""
        stats = {
            'total_conflicts': len(conflicts),
            'resolved': 0,
            'failed': 0,
            'requires_manual': 0
        }
        
        for conflict in conflicts:
            # Auto-resolution rules
            resolution = self._get_auto_resolution_strategy(conflict)
            
            if resolution != ConflictResolution.MANUAL_RESOLUTION:
                success = await self.resolve_conflict(conflict, resolution, "Auto-resolved")
                if success:
                    stats['resolved'] += 1
                else:
                    stats['failed'] += 1
            else:
                stats['requires_manual'] += 1
        
        return stats
    
    def _get_auto_resolution_strategy(self, conflict: Conflict) -> ConflictResolution:
        """Determine automatic resolution strategy based on conflict type and context."""
        if conflict.conflict_type == ConflictType.CONTENT_MODIFIED_BOTH_SIDES:
            # For content conflicts, prefer the more recent version
            git_timestamp = self._parse_timestamp(conflict.git_data.get('updated_at'))
            db_timestamp = conflict.db_data.get('updated_at')
            
            if isinstance(db_timestamp, str):
                db_timestamp = datetime.fromisoformat(db_timestamp.replace('Z', '+00:00'))
            
            if git_timestamp and db_timestamp:
                if git_timestamp > db_timestamp:
                    return ConflictResolution.KEEP_GIT_VERSION
                else:
                    return ConflictResolution.KEEP_DB_VERSION
            
            # Default to Git version if timestamps are unclear
            return ConflictResolution.KEEP_GIT_VERSION
        
        elif conflict.conflict_type == ConflictType.CATEGORY_MISMATCH:
            # Prefer database version for category assignments
            return ConflictResolution.KEEP_DB_VERSION
        
        elif conflict.conflict_type == ConflictType.METADATA_CONFLICT:
            # Merge metadata, preferring Git for content, DB for system fields
            return ConflictResolution.MERGE_CONTENT
        
        # Default to manual resolution for complex conflicts
        return ConflictResolution.MANUAL_RESOLUTION
    
    async def _apply_git_version(self, conflict: Conflict):
        """Apply Git version to database."""
        article = await KnowledgeBaseArticle.get(ObjectId(conflict.article_id))
        if not article:
            raise ValueError(f"Article {conflict.article_id} not found")
        
        # Update article with Git data
        git_metadata = conflict.git_data
        
        # Convert markdown to HTML
        from markdown import markdown
        git_content = conflict.git_data.get('content', '')
        content_html = markdown(git_content)
        
        article.title = git_metadata.get('title', article.title)
        article.content_markdown = git_content
        article.content_html = content_html
        article.summary = git_metadata.get('summary', article.summary)
        article.updated_at = datetime.utcnow()
        article.version += 1
        
        # Handle category
        category_slug = git_metadata.get('category')
        if category_slug:
            category = await Category.find_one(Category.slug == category_slug)
            if category:
                article.category = {
                    'id': str(category.id),
                    'name': category.name,
                    'slug': category.slug
                }
        
        await article.save()
    
    async def _apply_db_version(self, conflict: Conflict):
        """Apply database version to Git (this would update the Git file)."""
        # This would typically be handled by the sync service
        # For now, we'll just mark that DB version should be preferred
        logger.info(f"DB version preferred for article {conflict.article_id}")
    
    async def _merge_content(self, conflict: Conflict):
        """Merge content from both versions."""
        article = await KnowledgeBaseArticle.get(ObjectId(conflict.article_id))
        if not article:
            raise ValueError(f"Article {conflict.article_id} not found")
        
        git_content = conflict.git_data.get('content', '')
        db_content = article.content_markdown
        
        # Simple merge strategy: prefer Git content, keep DB metadata
        from markdown import markdown
        content_html = markdown(git_content)
        
        article.content_markdown = git_content
        article.content_html = content_html
        article.updated_at = datetime.utcnow()
        article.version += 1
        
        await article.save()
    
    def _calculate_content_hash(self, content: str, metadata: Dict[str, Any]) -> str:
        """Calculate hash for content and metadata."""
        hash_data = f"{content}{metadata.get('title', '')}{metadata.get('updated_at', '')}"
        return hashlib.sha256(hash_data.encode()).hexdigest()
    
    def _calculate_db_hash(self, article: KnowledgeBaseArticle) -> str:
        """Calculate hash for database article."""
        hash_data = f"{article.content_markdown}{article.title}{article.updated_at.isoformat()}"
        return hashlib.sha256(hash_data.encode()).hexdigest()
    
    def _check_metadata_conflicts(self, git_metadata: Dict[str, Any], article: KnowledgeBaseArticle) -> List[str]:
        """Check for metadata conflicts between Git and database."""
        conflicts = []
        
        # Check title
        if git_metadata.get('title') != article.title:
            conflicts.append('title')
        
        # Check status
        git_status = git_metadata.get('status')
        if git_status and git_status != article.status.value:
            conflicts.append('status')
        
        # Check visibility
        git_visibility = git_metadata.get('visibility')
        if git_visibility and git_visibility != (article.visibility.value if article.visibility else None):
            conflicts.append('visibility')
        
        return conflicts
    
    def _article_to_dict(self, article: KnowledgeBaseArticle) -> Dict[str, Any]:
        """Convert article to dictionary for comparison."""
        return {
            'title': article.title,
            'status': article.status.value,
            'visibility': article.visibility.value if article.visibility else None,
            'category': article.category['slug'] if article.category else None,
            'updated_at': article.updated_at.isoformat(),
            'version': article.version
        }
    
    def _parse_timestamp(self, timestamp_str: str) -> Optional[datetime]:
        """Parse timestamp string to datetime object."""
        if not timestamp_str:
            return None
        
        try:
            # Handle various timestamp formats
            if 'T' in timestamp_str:
                return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            else:
                return datetime.fromisoformat(timestamp_str)
        except ValueError:
            return None


class ConflictManager:
    """Manages conflict tracking and resolution history."""
    
    def __init__(self):
        self._conflicts: Dict[str, Conflict] = {}
        self._resolution_history: List[Dict[str, Any]] = []
    
    def add_conflict(self, conflict: Conflict):
        """Add a conflict to be managed."""
        self._conflicts[conflict.article_id] = conflict
    
    def get_conflict(self, article_id: str) -> Optional[Conflict]:
        """Get conflict for article."""
        return self._conflicts.get(article_id)
    
    def get_pending_conflicts(self) -> List[Conflict]:
        """Get all unresolved conflicts."""
        return [conflict for conflict in self._conflicts.values() 
                if conflict.resolution is None]
    
    def record_resolution(self, conflict: Conflict, resolution: ConflictResolution, notes: str = None):
        """Record a conflict resolution."""
        resolution_record = {
            'article_id': conflict.article_id,
            'conflict_type': conflict.conflict_type.value,
            'resolution': resolution.value,
            'notes': notes,
            'resolved_at': datetime.utcnow().isoformat()
        }
        self._resolution_history.append(resolution_record)
    
    def get_resolution_history(self, article_id: str = None) -> List[Dict[str, Any]]:
        """Get resolution history, optionally filtered by article."""
        if article_id:
            return [record for record in self._resolution_history 
                    if record['article_id'] == article_id]
        return self._resolution_history


# Global conflict manager instance
conflict_manager = ConflictManager()