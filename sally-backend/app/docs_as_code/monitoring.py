"""
Monitoring and error handling for Docs-as-Code system.
"""
import logging
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from enum import Enum
import json
import asyncio
from dataclasses import dataclass, asdict
from pathlib import Path

from .sync_service import SyncService, MongoToGitSync
from .background_jobs import JobQueue, JobStatus, JobType
from .conflict_resolver import ConflictManager, ConflictResolution
from app.core.config import settings


logger = logging.getLogger(__name__)


class SyncStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    CONFLICT = "conflict"


@dataclass
class SyncMetrics:
    """Metrics for synchronization operations."""
    operation: str
    start_time: datetime
    end_time: Optional[datetime] = None
    articles_processed: int = 0
    articles_created: int = 0
    articles_updated: int = 0
    articles_deleted: int = 0
    conflicts_detected: int = 0
    conflicts_resolved: int = 0
    errors: List[str] = None
    status: SyncStatus = SyncStatus.SUCCESS
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        data = asdict(self)
        data['start_time'] = self.start_time.isoformat()
        data['end_time'] = self.end_time.isoformat() if self.end_time else None
        data['duration_seconds'] = self.duration_seconds
        return data
    
    @property
    def duration_seconds(self) -> Optional[float]:
        """Get duration in seconds."""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
    
    def mark_completed(self, status: SyncStatus = SyncStatus.SUCCESS):
        """Mark the operation as completed."""
        self.end_time = datetime.utcnow()
        self.status = status


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class SystemHealth:
    """System health status."""
    status: HealthStatus
    components: Dict[str, HealthStatus]
    last_check: datetime
    details: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert health status to dictionary."""
        return {
            'status': self.status.value,
            'components': {k: v.value for k, v in self.components.items()},
            'last_check': self.last_check.isoformat(),
            'details': self.details
        }


class MonitoringService:
    """Monitoring service for Docs-as-Code system."""
    
    def __init__(self):
        self._metrics_history: List[SyncMetrics] = []
        self._error_log: List[Dict[str, Any]] = []
        self._max_history_size = 1000  # Keep last 1000 metrics entries
    
    async def record_sync_metrics(self, metrics: SyncMetrics):
        """Record synchronization metrics."""
        metrics.mark_completed()
        self._metrics_history.append(metrics)
        
        # Trim history if needed
        if len(self._metrics_history) > self._max_history_size:
            self._metrics_history = self._metrics_history[-self._max_history_size:]
        
        # Log the metrics
        logger.info(f"Sync operation completed: {metrics.operation}, "
                   f"status: {metrics.status}, duration: {metrics.duration_seconds:.2f}s")
        
        if metrics.errors:
            for error in metrics.errors:
                self.record_error(metrics.operation, error)
    
    def record_error(self, operation: str, error: str, details: Dict[str, Any] = None):
        """Record an error."""
        error_record = {
            'timestamp': datetime.utcnow().isoformat(),
            'operation': operation,
            'error': error,
            'details': details or {}
        }
        self._error_log.append(error_record)
        logger.error(f"Error in {operation}: {error}")
    
    def get_recent_metrics(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent metrics."""
        return [metrics.to_dict() for metrics in self._metrics_history[-limit:]]
    
    def get_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get error summary for the last N hours."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        recent_errors = [
            error for error in self._error_log
            if datetime.fromisoformat(error['timestamp']) > cutoff_time
        ]
        
        return {
            'total_errors': len(recent_errors),
            'errors_by_operation': self._group_errors_by_operation(recent_errors),
            'error_trend': self._calculate_error_trend(hours)
        }
    
    def _group_errors_by_operation(self, errors: List[Dict[str, Any]]) -> Dict[str, int]:
        """Group errors by operation."""
        grouped = {}
        for error in errors:
            operation = error['operation']
            grouped[operation] = grouped.get(operation, 0) + 1
        return grouped
    
    def _calculate_error_trend(self, hours: int) -> str:
        """Calculate error trend (increasing, decreasing, stable)."""
        if hours < 2:
            return "insufficient_data"
        
        # Split the time period into two halves
        midpoint = datetime.utcnow() - timedelta(hours=hours/2)
        first_half = [
            error for error in self._error_log
            if datetime.fromisoformat(error['timestamp']) > midpoint
        ]
        second_half = [
            error for error in self._error_log
            if datetime.fromisoformat(error['timestamp']) <= midpoint and
            datetime.fromisoformat(error['timestamp']) > datetime.utcnow() - timedelta(hours=hours)
        ]
        
        if len(first_half) == 0 and len(second_half) == 0:
            return "stable"
        elif len(first_half) == 0:
            return "decreasing"
        elif len(second_half) == 0:
            return "increasing"
        
        first_half_count = len(first_half)
        second_half_count = len(second_half)
        
        if first_half_count > second_half_count * 1.5:
            return "increasing"
        elif second_half_count > first_half_count * 1.5:
            return "decreasing"
        else:
            return "stable"
    
    async def check_system_health(self, job_queue: JobQueue, conflict_manager: ConflictManager) -> SystemHealth:
        """Check system health status."""
        components = {}
        details = {}
        
        # Check job queue health
        job_queue_health = await self._check_job_queue_health(job_queue)
        components['job_queue'] = job_queue_health['status']
        details['job_queue'] = job_queue_health
        
        # Check conflict manager health
        conflict_health = self._check_conflict_manager_health(conflict_manager)
        components['conflict_manager'] = conflict_health['status']
        details['conflict_manager'] = conflict_health
        
        # Check Git repository health
        git_health = await self._check_git_health()
        components['git_repository'] = git_health['status']
        details['git_repository'] = git_health
        
        # Check database connectivity
        db_health = await self._check_database_health()
        components['database'] = db_health['status']
        details['database'] = db_health
        
        # Determine overall status
        if any(status == HealthStatus.UNHEALTHY for status in components.values()):
            overall_status = HealthStatus.UNHEALTHY
        elif any(status == HealthStatus.DEGRADED for status in components.values()):
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.HEALTHY
        
        return SystemHealth(
            status=overall_status,
            components=components,
            last_check=datetime.utcnow(),
            details=details
        )
    
    async def _check_job_queue_health(self, job_queue: JobQueue) -> Dict[str, Any]:
        """Check job queue health."""
        try:
            # Get recent jobs
            recent_jobs = list(job_queue._jobs.values())[-10:]  # Last 10 jobs
            
            failed_jobs = [job for job in recent_jobs if job.status == JobStatus.FAILED]
            running_jobs = [job for job in recent_jobs if job.status == JobStatus.RUNNING]
            
            failure_rate = len(failed_jobs) / len(recent_jobs) if recent_jobs else 0
            
            if failure_rate > 0.5:  # More than 50% failure rate
                status = HealthStatus.UNHEALTHY
            elif failure_rate > 0.2:  # More than 20% failure rate
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.HEALTHY
            
            return {
                'status': status,
                'total_jobs': len(job_queue._jobs),
                'recent_failures': len(failed_jobs),
                'running_jobs': len(running_jobs),
                'failure_rate': failure_rate
            }
        except Exception as e:
            return {
                'status': HealthStatus.UNHEALTHY,
                'error': str(e)
            }
    
    def _check_conflict_manager_health(self, conflict_manager: ConflictManager) -> Dict[str, Any]:
        """Check conflict manager health."""
        try:
            pending_conflicts = conflict_manager.get_pending_conflicts()
            total_conflicts = len(conflict_manager._conflicts)
            
            if len(pending_conflicts) > 10:  # More than 10 pending conflicts
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.HEALTHY
            
            return {
                'status': status,
                'total_conflicts': total_conflicts,
                'pending_conflicts': len(pending_conflicts),
                'resolution_history_count': len(conflict_manager._resolution_history)
            }
        except Exception as e:
            return {
                'status': HealthStatus.UNHEALTHY,
                'error': str(e)
            }
    
    async def _check_git_health(self) -> Dict[str, Any]:
        """Check Git repository health."""
        try:
            sync_service = SyncService()
            git_manager = sync_service.git_manager
            
            # Check if repository exists and is accessible
            repo_exists = git_manager.repo_path.exists() and git_manager.repo_path.is_dir()
            
            if not repo_exists:
                return {
                    'status': HealthStatus.UNHEALTHY,
                    'error': 'Git repository not found'
                }
            
            # Try to get latest commit
            latest_commit = await git_manager.get_latest_commit()
            
            return {
                'status': HealthStatus.HEALTHY,
                'repo_exists': True,
                'latest_commit': latest_commit[:40] if latest_commit else None
            }
        except Exception as e:
            return {
                'status': HealthStatus.UNHEALTHY,
                'error': str(e)
            }
    
    async def _check_database_health(self) -> Dict[str, Any]:
        """Check database connectivity."""
        try:
            from app.infrastructure.database.mongodb import init_beanie
            from motor.motor_asyncio import AsyncIOMotorClient
            
            # Try to connect to database
            client = AsyncIOMotorClient(settings.mongodb_url)
            db = client.get_database()
            
            # Try a simple operation
            await db.command('ping')
            
            return {
                'status': HealthStatus.HEALTHY,
                'connected': True
            }
        except Exception as e:
            return {
                'status': HealthStatus.UNHEALTHY,
                'error': str(e)
            }


class RetryManager:
    """Manages retry logic for failed operations."""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
    
    async def execute_with_retry(self, operation, *args, **kwargs):
        """Execute an operation with retry logic."""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):  # +1 for the initial attempt
            try:
                if asyncio.iscoroutinefunction(operation):
                    result = await operation(*args, **kwargs)
                else:
                    result = operation(*args, **kwargs)
                return result
            except Exception as e:
                last_exception = e
                
                if attempt < self.max_retries:
                    delay = self.base_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"Operation failed (attempt {attempt + 1}/{self.max_retries + 1}), "
                                 f"retrying in {delay:.2f}s: {str(e)}")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Operation failed after {self.max_retries + 1} attempts: {str(e)}")
                    raise last_exception
        
        raise last_exception  # This should never be reached, but just in case


# Global monitoring service instance
monitoring_service = MonitoringService()

# Global retry manager instance
retry_manager = RetryManager()


async def get_system_stats() -> Dict[str, Any]:
    """Get comprehensive system statistics."""
    # Import global instances
    from .background_jobs import job_queue
    from .conflict_resolver import conflict_manager

    try:
        health = await monitoring_service.check_system_health(job_queue, conflict_manager)
        recent_metrics = monitoring_service.get_recent_metrics(50)
        error_summary = monitoring_service.get_error_summary(24)

        # Add last_sync and pending_operations for compatibility
        last_sync = None
        pending_operations = 0

        # Try to get last sync from recent metrics
        if recent_metrics:
            last_sync = recent_metrics[0].get('timestamp') if isinstance(recent_metrics[0], dict) else None

        # Try to get pending operations from job queue
        try:
            pending_operations = await job_queue.get_pending_count()
        except Exception as e:
            logger.warning(f"Failed to get pending operations count: {e}")

        return {
            'health': health.to_dict(),
            'recent_operations': recent_metrics,
            'error_summary': error_summary,
            'last_sync': last_sync,
            'pending_operations': pending_operations,
            'timestamp': datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get system stats: {e}")
        # Return a basic structure if there's an error
        return {
            'health': {'status': 'error', 'components': {}, 'last_check': datetime.utcnow().isoformat(), 'details': {}},
            'recent_operations': [],
            'error_summary': [],
            'last_sync': None,
            'pending_operations': 0,
            'timestamp': datetime.utcnow().isoformat()
        }


def setup_logging():
    """Setup structured logging for Docs-as-Code system."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('docs_as_code.log', encoding='utf-8')
        ]
    )
    
    # Reduce noise from third-party libraries
    logging.getLogger('git').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)


# Initialize logging when module is imported
setup_logging()