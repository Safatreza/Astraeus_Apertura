"""
Job queue system for managing simulation jobs with priority scheduling.

This module provides a sophisticated job queue that supports:
- Priority-based scheduling
- Job dependencies
- Retry logic with exponential backoff
- Job cancellation and cleanup
- Persistent job state
"""

import uuid
import time
import pickle
import threading
from enum import Enum
from typing import Dict, Any, Optional, List, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from queue import PriorityQueue
import sqlite3
from loguru import logger


class JobStatus(Enum):
    """Status of a simulation job."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class JobPriority(Enum):
    """Priority levels for job scheduling."""
    LOW = 3
    NORMAL = 2
    HIGH = 1
    CRITICAL = 0

    def __lt__(self, other):
        return self.value < other.value


@dataclass
class SimulationJob:
    """
    Represents a single simulation job.

    Attributes:
        job_id: Unique identifier for the job
        job_type: Type of simulation (e.g., 'ansys_hfss', 'openems')
        parameters: Simulation parameters
        priority: Job priority for scheduling
        dependencies: List of job IDs that must complete before this job
        max_retries: Maximum number of retry attempts
        timeout: Maximum execution time in seconds
        callback: Optional callback function on completion
        metadata: Additional metadata for the job
    """
    job_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    job_type: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    priority: JobPriority = JobPriority.NORMAL
    dependencies: List[str] = field(default_factory=list)
    max_retries: int = 3
    timeout: Optional[float] = None
    callback: Optional[Callable] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Runtime state
    status: JobStatus = JobStatus.PENDING
    retry_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    worker_id: Optional[str] = None

    def __lt__(self, other):
        """Compare jobs by priority for queue ordering."""
        return self.priority < other.priority

    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary (for serialization)."""
        return {
            'job_id': self.job_id,
            'job_type': self.job_type,
            'parameters': self.parameters,
            'priority': self.priority.name,
            'dependencies': self.dependencies,
            'max_retries': self.max_retries,
            'timeout': self.timeout,
            'metadata': self.metadata,
            'status': self.status.name,
            'retry_count': self.retry_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'error': self.error,
            'worker_id': self.worker_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SimulationJob':
        """Create job from dictionary."""
        job = cls(
            job_id=data['job_id'],
            job_type=data['job_type'],
            parameters=data['parameters'],
            priority=JobPriority[data['priority']],
            dependencies=data.get('dependencies', []),
            max_retries=data.get('max_retries', 3),
            timeout=data.get('timeout'),
            metadata=data.get('metadata', {}),
        )
        job.status = JobStatus[data['status']]
        job.retry_count = data.get('retry_count', 0)

        if data.get('created_at'):
            job.created_at = datetime.fromisoformat(data['created_at'])
        if data.get('started_at'):
            job.started_at = datetime.fromisoformat(data['started_at'])
        if data.get('completed_at'):
            job.completed_at = datetime.fromisoformat(data['completed_at'])

        job.error = data.get('error')
        job.worker_id = data.get('worker_id')

        return job


class JobQueue:
    """
    Thread-safe job queue with priority scheduling and persistence.

    Features:
    - Priority-based job scheduling
    - Job dependency management
    - Automatic retry with exponential backoff
    - Persistent state to SQLite database
    - Thread-safe operations
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize job queue.

        Args:
            db_path: Path to SQLite database for persistent state
        """
        self.db_path = db_path or "job_queue.db"
        self._queue: PriorityQueue = PriorityQueue()
        self._jobs: Dict[str, SimulationJob] = {}
        self._lock = threading.RLock()
        self._completed_jobs: Set[str] = set()

        # Initialize database
        self._init_database()

        # Load persisted jobs
        self._load_jobs()

        logger.info(f"JobQueue initialized with database: {self.db_path}")

    def _init_database(self):
        """Initialize SQLite database for job persistence."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    job_type TEXT NOT NULL,
                    parameters TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    dependencies TEXT,
                    max_retries INTEGER,
                    timeout REAL,
                    metadata TEXT,
                    status TEXT NOT NULL,
                    retry_count INTEGER DEFAULT 0,
                    created_at TEXT,
                    started_at TEXT,
                    completed_at TEXT,
                    error TEXT,
                    worker_id TEXT,
                    result BLOB
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_status ON jobs(status)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_priority ON jobs(priority)
            """)
            conn.commit()

    def _load_jobs(self):
        """Load jobs from database on startup."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT job_id, job_type, parameters, priority, dependencies,
                       max_retries, timeout, metadata, status, retry_count,
                       created_at, started_at, completed_at, error, worker_id, result
                FROM jobs
                WHERE status NOT IN ('completed', 'cancelled', 'failed')
            """)

            for row in cursor.fetchall():
                job_data = {
                    'job_id': row[0],
                    'job_type': row[1],
                    'parameters': pickle.loads(row[2].encode('latin1')),
                    'priority': row[3],
                    'dependencies': pickle.loads(row[4].encode('latin1')) if row[4] else [],
                    'max_retries': row[5],
                    'timeout': row[6],
                    'metadata': pickle.loads(row[7].encode('latin1')) if row[7] else {},
                    'status': row[8],
                    'retry_count': row[9],
                    'created_at': row[10],
                    'started_at': row[11],
                    'completed_at': row[12],
                    'error': row[13],
                    'worker_id': row[14],
                }

                job = SimulationJob.from_dict(job_data)

                # Restore result if available
                if row[15]:
                    job.result = pickle.loads(row[15])

                self._jobs[job.job_id] = job

                # Re-queue pending and queued jobs
                if job.status in [JobStatus.PENDING, JobStatus.QUEUED]:
                    self._queue.put((job.priority, job.created_at, job))
                    job.status = JobStatus.QUEUED

        logger.info(f"Loaded {len(self._jobs)} jobs from database")

    def _persist_job(self, job: SimulationJob):
        """Persist job to database."""
        with sqlite3.connect(self.db_path) as conn:
            # Serialize complex objects
            params_blob = pickle.dumps(job.parameters).decode('latin1')
            deps_blob = pickle.dumps(job.dependencies).decode('latin1') if job.dependencies else None
            meta_blob = pickle.dumps(job.metadata).decode('latin1') if job.metadata else None
            result_blob = pickle.dumps(job.result) if job.result else None

            conn.execute("""
                INSERT OR REPLACE INTO jobs (
                    job_id, job_type, parameters, priority, dependencies,
                    max_retries, timeout, metadata, status, retry_count,
                    created_at, started_at, completed_at, error, worker_id, result
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job.job_id,
                job.job_type,
                params_blob,
                job.priority.name,
                deps_blob,
                job.max_retries,
                job.timeout,
                meta_blob,
                job.status.name,
                job.retry_count,
                job.created_at.isoformat() if job.created_at else None,
                job.started_at.isoformat() if job.started_at else None,
                job.completed_at.isoformat() if job.completed_at else None,
                job.error,
                job.worker_id,
                result_blob
            ))
            conn.commit()

    def submit_job(self, job: SimulationJob) -> str:
        """
        Submit a job to the queue.

        Args:
            job: SimulationJob to submit

        Returns:
            Job ID
        """
        with self._lock:
            # Check if dependencies are satisfied
            if job.dependencies:
                for dep_id in job.dependencies:
                    if dep_id not in self._completed_jobs:
                        logger.info(f"Job {job.job_id} waiting for dependency {dep_id}")
                        job.status = JobStatus.PENDING
                        self._jobs[job.job_id] = job
                        self._persist_job(job)
                        return job.job_id

            # Queue the job
            job.status = JobStatus.QUEUED
            self._queue.put((job.priority, job.created_at, job))
            self._jobs[job.job_id] = job
            self._persist_job(job)

            logger.info(f"Job {job.job_id} queued with priority {job.priority.name}")
            return job.job_id

    def get_next_job(self, timeout: Optional[float] = None) -> Optional[SimulationJob]:
        """
        Get the next job from the queue (blocks if empty).

        Args:
            timeout: Maximum time to wait for a job (None = wait forever)

        Returns:
            Next SimulationJob or None if timeout
        """
        try:
            priority, created_at, job = self._queue.get(timeout=timeout)

            with self._lock:
                # Double-check job is still valid
                if job.job_id in self._jobs and job.status == JobStatus.QUEUED:
                    job.status = JobStatus.RUNNING
                    job.started_at = datetime.now()
                    self._persist_job(job)
                    return job
                else:
                    # Job was cancelled or removed, try next
                    return self.get_next_job(timeout=timeout)

        except Exception:
            return None

    def mark_completed(self, job_id: str, result: Any = None):
        """
        Mark a job as completed.

        Args:
            job_id: Job identifier
            result: Job result
        """
        with self._lock:
            if job_id not in self._jobs:
                logger.warning(f"Job {job_id} not found")
                return

            job = self._jobs[job_id]
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.now()
            job.result = result

            self._completed_jobs.add(job_id)
            self._persist_job(job)

            # Execute callback if provided
            if job.callback:
                try:
                    job.callback(job)
                except Exception as e:
                    logger.error(f"Callback failed for job {job_id}: {e}")

            # Check if any pending jobs can now be queued
            self._check_pending_jobs()

            logger.info(f"Job {job_id} completed successfully")

    def mark_failed(self, job_id: str, error: str, retry: bool = True):
        """
        Mark a job as failed.

        Args:
            job_id: Job identifier
            error: Error message
            retry: Whether to retry the job
        """
        with self._lock:
            if job_id not in self._jobs:
                logger.warning(f"Job {job_id} not found")
                return

            job = self._jobs[job_id]
            job.error = error

            if retry and job.retry_count < job.max_retries:
                # Retry with exponential backoff
                job.retry_count += 1
                job.status = JobStatus.RETRYING

                # Calculate backoff delay
                backoff_delay = 2 ** job.retry_count
                logger.warning(f"Job {job_id} failed, retrying in {backoff_delay}s (attempt {job.retry_count}/{job.max_retries})")

                # Re-queue after delay (simplified - in production use timer)
                time.sleep(backoff_delay)
                job.status = JobStatus.QUEUED
                self._queue.put((job.priority, datetime.now(), job))
                self._persist_job(job)
            else:
                # Final failure
                job.status = JobStatus.FAILED
                job.completed_at = datetime.now()
                self._persist_job(job)
                logger.error(f"Job {job_id} failed permanently: {error}")

    def cancel_job(self, job_id: str):
        """
        Cancel a job.

        Args:
            job_id: Job identifier
        """
        with self._lock:
            if job_id not in self._jobs:
                logger.warning(f"Job {job_id} not found")
                return

            job = self._jobs[job_id]

            if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                logger.warning(f"Job {job_id} already in terminal state: {job.status}")
                return

            job.status = JobStatus.CANCELLED
            job.completed_at = datetime.now()
            self._persist_job(job)

            logger.info(f"Job {job_id} cancelled")

    def _check_pending_jobs(self):
        """Check if any pending jobs can now be queued."""
        for job_id, job in list(self._jobs.items()):
            if job.status == JobStatus.PENDING:
                # Check if all dependencies are satisfied
                deps_satisfied = all(dep_id in self._completed_jobs for dep_id in job.dependencies)

                if deps_satisfied:
                    job.status = JobStatus.QUEUED
                    self._queue.put((job.priority, job.created_at, job))
                    self._persist_job(job)
                    logger.info(f"Job {job_id} dependencies satisfied, queuing")

    def get_job(self, job_id: str) -> Optional[SimulationJob]:
        """Get job by ID."""
        return self._jobs.get(job_id)

    def get_all_jobs(self, status: Optional[JobStatus] = None) -> List[SimulationJob]:
        """
        Get all jobs, optionally filtered by status.

        Args:
            status: Filter by job status

        Returns:
            List of SimulationJobs
        """
        with self._lock:
            if status is None:
                return list(self._jobs.values())
            else:
                return [job for job in self._jobs.values() if job.status == status]

    def get_queue_size(self) -> int:
        """Get number of jobs in queue."""
        return self._queue.qsize()

    def clear_completed(self):
        """Remove completed jobs from memory (keeps in database)."""
        with self._lock:
            completed = [job_id for job_id, job in self._jobs.items()
                        if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]]

            for job_id in completed:
                del self._jobs[job_id]

            logger.info(f"Cleared {len(completed)} completed jobs from memory")
