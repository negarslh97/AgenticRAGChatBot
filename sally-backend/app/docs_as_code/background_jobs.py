
"""
Background job processing for Docs-as-Code synchronization operations.
"""
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging
from bson import ObjectId
from enum import Enum
import json

from .sync_service import SyncService, MongoToGitSync
from app.domain.entities_refactored import KnowledgeBaseArticle, Category
from app.core.config import settings


logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(str, Enum):
    SYNC_GIT_TO_MONGO = "sync_git_to_mongo"
    SYNC_ARTICLE_TO_GIT = "sync_article_to_git"
    FULL_SYNC = "full_sync"
    CLEANUP = "cleanup"
    BACKUP = "backup"


class SyncJob:
    """Represents a synchronization job."""
    
    def __init__(self, job_id: str, job_type: JobType, data: Dict[str, Any]):
        self.job_id = job_id
        self.job_type = job_type
        self.data = data
        self.status = JobStatus.PENDING
        self.created_at = datetime.utcnow()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.progress = 0
        self.result: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary for storage."""
        return {
            'job_id': self.job_id,
            'job_type': self.job_type.value,
            'data': self.data,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'progress': self.progress,
            'result': self.result,
            'error': self.error
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SyncJob':
        """Create job from dictionary."""
        job = cls(
            job_id=data['job_id'],
            job_type=JobType(data['job_type']),
            data=data['data']
        )
        job.status = JobStatus(data['status'])
        job.created_at = datetime.fromisoformat(data['created_at'])
        
        if data['started_at']:
            job.started_at = datetime.fromisoformat(data['started_at'])
        if data['completed_at']:
            job.completed_at = datetime.fromisoformat(data['completed_at'])
        
        job.progress = data['progress']
        job.result = data['result']
        job.error = data['error']
        
        return job


class JobQueue:
    """In-memory job queue for sync operations."""
    
    def __init__(self):
        self._queue: asyncio.Queue = asyncio.Queue()
        self._jobs: Dict[str, SyncJob] = {}
        self._running = False
        self._processor_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the job processor."""
        if self._running:
            return
        
        self._running = True
        self._processor_task = asyncio.create_task(self._process_jobs())
        logger.info("Job queue processor started")
    
    async def stop(self):
        """Stop the job processor."""
        self._running = False
        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass
        logger.info("Job queue processor stopped")
    
    async def add_job(self, job_type: JobType, data: Dict[str, Any]) -> str:
        """Add a new job to the queue."""
        job_id = f"job_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{len(self._jobs)}"
        job = SyncJob(job_id, job_type, data)
        
        self._jobs[job_id] = job
        await self._queue.put(job)
        
        logger.info(f"Added job {job_id} of type {job_type}")
        return job_id
    
    async def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a job."""
        job = self._jobs.get(job_id)
        return job.to_dict() if job else None
    
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a pending job."""
        job = self._jobs.get(job_id)
        if not job or job.status != JobStatus.PENDING:
            return False
        
        job.status = JobStatus.CANCELLED
        job.completed_at = datetime.utcnow()
        return True
    
    async def _process_jobs(self):
        """Process jobs from the queue."""
        while self._running:
            try:
                job = await self._queue.get()
                
                # Skip if job was cancelled
                if job.status == JobStatus.CANCELLED:
                    self._queue.task_done()
                    continue
                
                # Process the job
                await self._process_job(job)
                self._queue.task_done()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing job: {str(e)}")
    
    async def _process_job(self, job: SyncJob):
        """Process a single job."""
        job.status = JobStatus.RUNNING
        job.started_at = datetime.utcnow()
        
        try:
            if job.job_type == JobType.SYNC_GIT_TO_MONGO:
                await self._process_sync_git_to_mongo(job)
            elif job.job_type == JobType.SYNC_ARTICLE_TO_GIT:
                await self._process_sync_article_to_git(job)
            elif job.job_type == JobType.FULL_SYNC:
                await self._process_full_sync(job)
            elif job.job_type == JobType.CLEANUP:
                await self._process_cleanup(job)
            elif job.job_type == JobType.BACKUP:
                await self._process_backup(job)
            
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.utcnow()
            job.progress = 100
            
        except Exception as e:
            job.status = JobStatus.FAILED
            job.completed_at = datetime.utcnow()
            job.error = str(e)
            logger.error(f"Job {job.job_id} failed: {str(e)}")
    
    async def _process_sync_git_to_mongo(self, job: SyncJob):
        """Process Git to MongoDB sync job."""
        full_sync = job.data.get('full_sync', False)
        sync_service = SyncService()
        
        job.progress = 10
        stats = await sync_service.sync_git_to_mongo(full_sync=full_sync)
        
        job.result = {
            'stats': stats,
            'timestamp': datetime.utcnow().isoformat()
        }
        job.progress = 100
    
    async def _process_sync_article_to_git(self, job: SyncJob):
        """Process article sync to Git job."""
        article_id = job.data.get('article_id')
        author_info = job.data.get('author_info', {})
        
        if not article_id:
            raise ValueError("Article ID is required")
        
        sync_service = MongoToGitSync()
        job.progress = 25
        
        success = await sync_service.sync_article_to_git(article_id, author_info)
        
        job.result = {
            'success': success,
            'article_id': article_id,
            'timestamp': datetime.utcnow().isoformat()
        }
        job.progress = 100
    
    async def _process_full_sync(self, job: SyncJob):
        """Process full synchronization job."""
        sync_service = SyncService()
        
        # Sync Git to MongoDB
        job.progress = 20
        git_to_mongo_stats = await sync_service.sync_git_to_mongo(full_sync=True)
        
        # Additional sync operations can be added here
        job.progress = 80
        
        job.result = {
            'git_to_mongo': git_to_mongo_stats,
            'timestamp': datetime.utcnow().isoformat()
        }
        job.progress = 100
    
    async def _process_cleanup(self, job: SyncJob):
        """Process cleanup job."""
        # Clean up old jobs
        cutoff_time = datetime.utcnow() - timedelta(days=7)
        jobs_to_remove = []
        
        for job_id, job_obj in self._jobs.items():
            if (job_obj.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED] and
                job_obj.completed_at and job_obj.completed_at < cutoff_time):
                jobs_to_remove.append(job_id)
        
        for job_id in jobs_to_remove:
            del self._jobs[job_id]
        
        job.result = {
            'cleaned_jobs': len(jobs_to_remove),
            'timestamp': datetime.utcnow().isoformat()
        }
        job.progress = 100
    
    async def _process_backup(self, job: SyncJob):
        """Process backup job."""
        # Create backup of current job state
        backup_data = {
            'jobs': {job_id: job_obj.to_dict() for job_id, job_obj in self._jobs.items()},
            'timestamp': datetime.utcnow().isoformat(),
            'total_jobs': len(self._jobs)
        }
        
        # Save backup to file (in production, this would go to cloud storage)
        backup_file = f"job_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False)
        
        job.result = {
            'backup_file': backup_file,
            'total_jobs': len(self._jobs),
            'timestamp': datetime.utcnow().isoformat()
        }
        job.progress = 100


# Global job queue instance
job_queue = JobQueue()


async def start_background_jobs():
    """Start the background job processor."""
    await job_queue.start()


async def stop_background_jobs():
    """Stop the background job processor."""
    await job_queue.stop()


async def schedule_sync_git_to_mongo(full_sync: bool = False) -> str:
    """Schedule a Git to MongoDB sync job."""
    return await job_queue.add_job(
        JobType.SYNC_GIT_TO_MONGO,
        {'full_sync': full_sync}
    )


async def schedule_sync_article_to_git(article_id: str, author_info: Dict[str, str]) -> str:
    """Schedule an article sync to Git job."""
    return await job_queue.add_job(
        JobType.SYNC_ARTICLE_TO_GIT,
        {'article_id': article_id, 'author_info': author_info}
    )


async def schedule_full_sync() -> str:
    """Schedule a full synchronization job."""
    return await job_queue.add_job(JobType.FULL_SYNC, {})


async def schedule_cleanup() -> str:
    """Schedule a cleanup job."""
    return await job_queue.add_job(JobType.CLEANUP, {})


async def schedule_backup() -> str:
    """Schedule a backup job."""
    return await job_queue.add_job(JobType.BACKUP, {})


async def get_job_status(job_id: str) -> Optional[Dict[str, Any]]:
    """Get the status of a job."""
    return await job_queue.get_job_status(job_id)


async def cancel_job(job_id: str) -> bool:
    """Cancel a job."""
    return await job_queue.cancel_job(job_id)