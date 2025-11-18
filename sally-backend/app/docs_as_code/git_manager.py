"""
Git repository management service for Docs-as-Code system.
"""
import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any
from git import Repo, GitCommandError
from git.remote import Remote
import logging
import shutil
from .config import GitConfig


logger = logging.getLogger(__name__)


class GitManager:
    """Manage Git repository operations for Docs-as-Code system."""
    
    def __init__(self, config: Optional[GitConfig] = None):
        self.config = config or GitConfig()
        self.repo: Optional[Repo] = None
        self.repo_path = self.config.local_path
        self._setup_repository()
    
    def _setup_repository(self):
        """Setup or clone the Git repository."""
        try:
            if self.config.local_path.exists():
                logger.info(f"Opening existing repository at {self.config.local_path}")
                self.repo = Repo(self.config.local_path)
                
                # Check if repository is valid
                if not self.repo.bare:
                    # Update to latest
                    self._pull_latest()
                else:
                    raise GitError("Repository is bare, cannot use")
            else:
                logger.info(f"Cloning repository from {self.config.repo_url} to {self.config.local_path}")
                self.repo = Repo.clone_from(
                    self.config.repo_url,
                    self.config.local_path,
                    branch=self.config.branch
                )
                
        except GitCommandError as e:
            logger.error(f"Git setup failed: {str(e)}")
            raise GitError(f"Failed to setup repository: {str(e)}")
    
    def _pull_latest(self):
        """Pull latest changes from remote."""
        try:
            origin = self.repo.remotes.origin
            origin.pull()
            logger.info("Successfully pulled latest changes")
        except GitCommandError as e:
            logger.error(f"Failed to pull latest changes: {str(e)}")
            raise GitError(f"Pull failed: {str(e)}")
    
    async def sync_with_remote(self) -> bool:
        """Sync local repository with remote."""
        try:
            if not self.repo:
                raise GitError("Repository not initialized")
            
            # Check if we're behind remote
            origin = self.repo.remotes.origin
            origin.fetch()
            
            # Get current branch
            current_branch = self.repo.active_branch
            remote_branch = origin.refs[current_branch.name]
            
            # Check if we need to pull
            commits_behind = list(self.repo.iter_commits(f"{current_branch}..{remote_branch}"))
            
            if commits_behind:
                logger.info(f"Pulling {len(commits_behind)} new commits")
                origin.pull()
                return True
            
            return False
            
        except GitCommandError as e:
            logger.error(f"Sync failed: {str(e)}")
            raise GitError(f"Sync failed: {str(e)}")
    
    async def commit_changes(self, file_paths: List[Path], commit_message: str, author: Optional[Dict[str, str]] = None) -> bool:
        """Commit changes to the repository."""
        try:
            if not self.repo:
                raise GitError("Repository not initialized")
            
            # Add files to index
            for file_path in file_paths:
                if file_path.exists():
                    self.repo.index.add(str(file_path))
                else:
                    self.repo.index.remove([str(file_path)])
            
            # Create commit
            if author:
                commit = self.repo.index.commit(
                    commit_message,
                    author=f"{author.get('name', 'SallyBot')} <{author.get('email', 'bot@sally.com')}>",
                    committer=f"{author.get('name', 'SallyBot')} <{author.get('email', 'bot@sally.com')}>"
                )
            else:
                commit = self.repo.index.commit(commit_message)
            
            logger.info(f"Committed changes: {commit.hexsha[:8]} - {commit_message}")
            return True
            
        except GitCommandError as e:
            logger.error(f"Commit failed: {str(e)}")
            raise GitError(f"Commit failed: {str(e)}")
    
    async def push_changes(self) -> bool:
        """Push changes to remote repository."""
        try:
            if not self.repo:
                raise GitError("Repository not initialized")
            
            origin = self.repo.remotes.origin
            
            # Check if we have changes to push
            if not self.repo.head.is_valid():
                logger.info("No changes to push")
                return False
            
            # Push changes
            push_info = origin.push()
            
            for info in push_info:
                if info.flags & info.ERROR:
                    logger.error(f"Push error: {info.summary}")
                    raise GitError(f"Push failed: {info.summary}")
                elif info.flags & info.REJECTED:
                    logger.warning(f"Push rejected: {info.summary}")
                    # Handle rejection (might need pull and merge)
                    await self._handle_push_rejection()
                    return False
            
            logger.info("Successfully pushed changes to remote")
            return True
            
        except GitCommandError as e:
            logger.error(f"Push failed: {str(e)}")
            raise GitError(f"Push failed: {str(e)}")
    
    async def _handle_push_rejection(self):
        """Handle push rejection by pulling and merging."""
        try:
            logger.info("Handling push rejection - pulling and merging")
            origin = self.repo.remotes.origin
            origin.pull()
            
            # Try push again
            await self.push_changes()
            
        except GitCommandError as e:
            logger.error(f"Push rejection handling failed: {str(e)}")
            raise GitError(f"Could not resolve push rejection: {str(e)}")
    
    async def get_file_history(self, file_path: Path, limit: int = 10) -> List[Dict[str, Any]]:
        """Get commit history for a specific file."""
        try:
            if not self.repo:
                raise GitError("Repository not initialized")
            
            # Check if file exists in repository
            if not file_path.exists():
                return []
            
            commits = list(self.repo.iter_commits(
                paths=str(file_path.relative_to(self.repo_path)),
                max_count=limit
            ))
            
            history = []
            for commit in commits:
                history.append({
                    'hash': commit.hexsha,
                    'message': commit.message.strip(),
                    'author_name': commit.author.name,
                    'author_email': commit.author.email,
                    'timestamp': commit.authored_datetime
                })
            
            return history
            
        except GitCommandError as e:
            logger.error(f"Failed to get file history: {str(e)}")
            raise GitError(f"History retrieval failed: {str(e)}")
    
    async def get_changed_files(self, since_commit: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get list of files changed since a specific commit."""
        try:
            if not self.repo:
                raise GitError("Repository not initialized")
            
            if since_commit:
                # Get changes since specific commit
                diff_index = self.repo.index.diff(since_commit)
            else:
                # Get unstaged changes
                diff_index = self.repo.index.diff(None)
            
            changed_files = []
            for diff in diff_index:
                changed_files.append({
                    'path': diff.a_path,
                    'change_type': diff.change_type,
                    'new_file': diff.new_file,
                    'deleted_file': diff.deleted_file
                })
            
            return changed_files
            
        except GitCommandError as e:
            logger.error(f"Failed to get changed files: {str(e)}")
            raise GitError(f"Changed files retrieval failed: {str(e)}")
    
    async def create_branch(self, branch_name: str) -> bool:
        """Create a new branch for feature development."""
        try:
            if not self.repo:
                raise GitError("Repository not initialized")
            
            # Check if branch exists
            if branch_name in [ref.name for ref in self.repo.branches]:
                logger.warning(f"Branch {branch_name} already exists")
                return False
            
            # Create new branch
            self.repo.create_head(branch_name)
            logger.info(f"Created new branch: {branch_name}")
            return True
            
        except GitCommandError as e:
            logger.error(f"Branch creation failed: {str(e)}")
            raise GitError(f"Branch creation failed: {str(e)}")
    
    async def switch_branch(self, branch_name: str) -> bool:
        """Switch to a different branch."""
        try:
            if not self.repo:
                raise GitError("Repository not initialized")
            
            # Check if branch exists
            if branch_name not in [ref.name for ref in self.repo.branches]:
                logger.error(f"Branch {branch_name} does not exist")
                return False
            
            # Switch branch
            self.repo.git.checkout(branch_name)
            logger.info(f"Switched to branch: {branch_name}")
            return True
            
        except GitCommandError as e:
            logger.error(f"Branch switch failed: {str(e)}")
            raise GitError(f"Branch switch failed: {str(e)}")
    
    async def get_status(self) -> Dict[str, Any]:
        """Get current repository status."""
        try:
            if not self.repo:
                raise GitError("Repository not initialized")
            
            status = {
                'branch': self.repo.active_branch.name if self.repo.active_branch else None,
                'dirty': self.repo.is_dirty(),
                'untracked_files': self.repo.untracked_files,
                'ahead': len(list(self.repo.iter_commits(f"{self.repo.active_branch.name}@{{u}}..{self.repo.active_branch.name}"))),
                'behind': len(list(self.repo.iter_commits(f"{self.repo.active_branch.name}..{self.repo.active_branch.name}@{{u}}"))),
                'last_commit': {
                    'hash': self.repo.head.commit.hexsha,
                    'message': self.repo.head.commit.message.strip(),
                    'date': self.repo.head.commit.committed_datetime.isoformat()
                } if self.repo.head.is_valid() else None
            }
            
            return status
            
        except GitCommandError as e:
            logger.error(f"Status retrieval failed: {str(e)}")
            raise GitError(f"Status retrieval failed: {str(e)}")
    
    def cleanup(self):
        """Clean up repository resources."""
        if self.repo:
            self.repo.close()

    async def initialize_repository(self) -> bool:
        """Initialize a new Git repository if it doesn't exist."""
        try:
            if self.repo_path.exists():
                return True
                
            self.repo_path.mkdir(parents=True, exist_ok=True)
            self.repo = Repo.init(self.repo_path)
            
            # Create initial commit
            readme_path = self.repo_path / "README.md"
            readme_path.write_text("# Knowledge Base Repository\n\nThis repository contains knowledge base articles managed by SallyBot.")
            
            self.repo.index.add([str(readme_path)])
            self.repo.index.commit("Initial commit: Knowledge base repository setup")
            
            logger.info(f"Initialized new Git repository at {self.repo_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize repository: {str(e)}")
            return False

    async def list_markdown_files(self) -> List[Path]:
        """List all markdown files in the repository."""
        try:
            if not self.repo_path.exists():
                return []
                
            markdown_files = []
            for file_path in self.repo_path.rglob("*.md"):
                if file_path.is_file():
                    markdown_files.append(file_path)
                    
            return markdown_files
            
        except Exception as e:
            logger.error(f"Failed to list markdown files: {str(e)}")
            return []

    async def commit_file(self, file_path: Path, message: str, author_name: str, author_email: str) -> bool:
        """Commit a single file to the repository."""
        try:
            if not self.repo:
                raise GitError("Repository not initialized")
                
            # Add the file to index
            self.repo.index.add([str(file_path.relative_to(self.repo_path))])
            
            # Create commit
            commit = self.repo.index.commit(
                message,
                author=f"{author_name} <{author_email}>",
                committer=f"{author_name} <{author_email}>"
            )
            
            logger.info(f"Committed file: {file_path} - {commit.hexsha[:8]}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to commit file {file_path}: {str(e)}")
            return False

    async def commit_all_changes(self, message: str, author_email: str, author_name: str) -> bool:
        """Commit all changes in the repository."""
        try:
            if not self.repo:
                raise GitError("Repository not initialized")
                
            # Add all changes
            self.repo.git.add(A=True)
            
            # Check if there are changes to commit
            if not self.repo.index.diff("HEAD"):
                logger.info("No changes to commit")
                return True
                
            # Create commit
            commit = self.repo.index.commit(
                message,
                author=f"{author_name} <{author_email}>",
                committer=f"{author_name} <{author_email}>"
            )
            
            logger.info(f"Committed all changes: {commit.hexsha[:8]}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to commit all changes: {str(e)}")
            return False


class GitError(Exception):
    """Custom exception for Git operations."""
    pass


# Async wrapper for Git operations that might block
async def run_git_operation(func, *args, **kwargs):
    """Run Git operation in thread pool to avoid blocking."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, func, *args, **kwargs)