"""
Worker pool for parallel job execution.

This module provides a thread-safe worker pool that executes simulation jobs
in parallel with resource management and load balancing.
"""

import os
import time
import threading
import multiprocessing as mp
from enum import Enum
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime
import psutil
from loguru import logger

from .job_queue import JobQueue, SimulationJob, JobStatus


class WorkerStatus(Enum):
    """Status of a worker."""
    IDLE = "idle"
    BUSY = "busy"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class WorkerStats:
    """Statistics for a worker."""
    worker_id: str
    jobs_completed: int = 0
    jobs_failed: int = 0
    total_runtime: float = 0.0
    cpu_usage: float = 0.0
    memory_usage_mb: float = 0.0
    last_job_id: Optional[str] = None
    last_job_time: Optional[datetime] = None


class Worker:
    """
    Individual worker that executes jobs from the queue.

    Workers run in separate threads and pull jobs from the shared job queue.
    """

    def __init__(
        self,
        worker_id: str,
        job_queue: JobQueue,
        executor_registry: Dict[str, Callable],
        max_memory_mb: Optional[float] = None
    ):
        """
        Initialize worker.

        Args:
            worker_id: Unique worker identifier
            job_queue: Shared job queue
            executor_registry: Dictionary mapping job types to executor functions
            max_memory_mb: Maximum memory usage in MB (for monitoring)
        """
        self.worker_id = worker_id
        self.job_queue = job_queue
        self.executor_registry = executor_registry
        self.max_memory_mb = max_memory_mb or 4096

        self.status = WorkerStatus.IDLE
        self.current_job: Optional[SimulationJob] = None
        self.stats = WorkerStats(worker_id=worker_id)

        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._process = psutil.Process(os.getpid())

        logger.info(f"Worker {worker_id} initialized")

    def start(self):
        """Start the worker thread."""
        if self._thread is not None and self._thread.is_alive():
            logger.warning(f"Worker {self.worker_id} already running")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info(f"Worker {self.worker_id} started")

    def stop(self, wait: bool = True):
        """
        Stop the worker thread.

        Args:
            wait: Whether to wait for current job to complete
        """
        logger.info(f"Stopping worker {self.worker_id}")
        self.status = WorkerStatus.STOPPING
        self._stop_event.set()

        if wait and self._thread:
            self._thread.join(timeout=30)

        self.status = WorkerStatus.STOPPED
        logger.info(f"Worker {self.worker_id} stopped")

    def _run(self):
        """Main worker loop."""
        while not self._stop_event.is_set():
            try:
                # Get next job from queue
                job = self.job_queue.get_next_job(timeout=1.0)

                if job is None:
                    # No job available, stay idle
                    self.status = WorkerStatus.IDLE
                    continue

                # Execute job
                self._execute_job(job)

            except Exception as e:
                logger.error(f"Worker {self.worker_id} error: {e}")
                self.status = WorkerStatus.ERROR
                time.sleep(1)

        self.status = WorkerStatus.STOPPED

    def _execute_job(self, job: SimulationJob):
        """
        Execute a simulation job.

        Args:
            job: SimulationJob to execute
        """
        self.status = WorkerStatus.BUSY
        self.current_job = job
        job.worker_id = self.worker_id

        logger.info(f"Worker {self.worker_id} executing job {job.job_id} (type: {job.job_type})")

        start_time = time.time()

        try:
            # Get executor for this job type
            executor = self.executor_registry.get(job.job_type)

            if executor is None:
                raise ValueError(f"No executor registered for job type: {job.job_type}")

            # Check memory before execution
            self._update_resource_usage()
            if self.stats.memory_usage_mb > self.max_memory_mb:
                logger.warning(f"Worker {self.worker_id} memory usage high: {self.stats.memory_usage_mb:.1f} MB")

            # Execute with timeout if specified
            if job.timeout:
                result = self._execute_with_timeout(executor, job, job.timeout)
            else:
                result = executor(job.parameters)

            # Mark job as completed
            runtime = time.time() - start_time
            self.job_queue.mark_completed(job.job_id, result)

            # Update statistics
            self.stats.jobs_completed += 1
            self.stats.total_runtime += runtime
            self.stats.last_job_id = job.job_id
            self.stats.last_job_time = datetime.now()

            logger.info(f"Worker {self.worker_id} completed job {job.job_id} in {runtime:.2f}s")

        except TimeoutError:
            error_msg = f"Job timed out after {job.timeout}s"
            logger.error(f"Worker {self.worker_id} job {job.job_id} {error_msg}")
            self.job_queue.mark_failed(job.job_id, error_msg, retry=True)
            self.stats.jobs_failed += 1

        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            logger.error(f"Worker {self.worker_id} job {job.job_id} failed: {error_msg}")
            self.job_queue.mark_failed(job.job_id, error_msg, retry=True)
            self.stats.jobs_failed += 1

        finally:
            self.current_job = None
            self.status = WorkerStatus.IDLE

    def _execute_with_timeout(self, executor: Callable, job: SimulationJob, timeout: float) -> Any:
        """
        Execute job with timeout using multiprocessing.

        Args:
            executor: Executor function
            job: SimulationJob
            timeout: Timeout in seconds

        Returns:
            Execution result

        Raises:
            TimeoutError: If execution exceeds timeout
        """
        # Use thread-based timeout for simplicity
        # In production, use multiprocessing for true isolation
        result = [None]
        exception = [None]

        def target():
            try:
                result[0] = executor(job.parameters)
            except Exception as e:
                exception[0] = e

        thread = threading.Thread(target=target)
        thread.start()
        thread.join(timeout=timeout)

        if thread.is_alive():
            logger.warning(f"Job {job.job_id} exceeded timeout, attempting to continue...")
            # Note: Cannot reliably kill thread in Python
            raise TimeoutError(f"Execution exceeded {timeout}s")

        if exception[0]:
            raise exception[0]

        return result[0]

    def _update_resource_usage(self):
        """Update CPU and memory usage statistics."""
        try:
            self.stats.cpu_usage = self._process.cpu_percent(interval=0.1)
            self.stats.memory_usage_mb = self._process.memory_info().rss / 1024 / 1024
        except Exception as e:
            logger.debug(f"Failed to update resource usage: {e}")

    def get_stats(self) -> WorkerStats:
        """Get worker statistics."""
        self._update_resource_usage()
        return self.stats


class WorkerPool:
    """
    Manages a pool of workers for parallel job execution.

    Features:
    - Dynamic worker scaling
    - Load balancing
    - Resource monitoring
    - Graceful shutdown
    """

    def __init__(
        self,
        job_queue: JobQueue,
        num_workers: Optional[int] = None,
        max_memory_per_worker_mb: float = 4096
    ):
        """
        Initialize worker pool.

        Args:
            job_queue: Job queue to pull jobs from
            num_workers: Number of workers (defaults to CPU count)
            max_memory_per_worker_mb: Maximum memory per worker
        """
        self.job_queue = job_queue
        self.num_workers = num_workers or max(1, mp.cpu_count() - 1)
        self.max_memory_per_worker_mb = max_memory_per_worker_mb

        self.workers: Dict[str, Worker] = {}
        self.executor_registry: Dict[str, Callable] = {}
        self._lock = threading.RLock()

        logger.info(f"WorkerPool initialized with {self.num_workers} workers")

    def register_executor(self, job_type: str, executor: Callable):
        """
        Register an executor function for a job type.

        Args:
            job_type: Job type identifier
            executor: Function that takes job parameters and returns result
        """
        self.executor_registry[job_type] = executor
        logger.info(f"Registered executor for job type: {job_type}")

    def start(self):
        """Start all workers."""
        with self._lock:
            for i in range(self.num_workers):
                worker_id = f"worker-{i}"
                worker = Worker(
                    worker_id=worker_id,
                    job_queue=self.job_queue,
                    executor_registry=self.executor_registry,
                    max_memory_mb=self.max_memory_per_worker_mb
                )
                worker.start()
                self.workers[worker_id] = worker

        logger.info(f"Started {self.num_workers} workers")

    def stop(self, wait: bool = True):
        """
        Stop all workers.

        Args:
            wait: Whether to wait for current jobs to complete
        """
        logger.info("Stopping worker pool")

        with self._lock:
            for worker in self.workers.values():
                worker.stop(wait=wait)

        logger.info("Worker pool stopped")

    def scale(self, num_workers: int):
        """
        Scale the worker pool to a different size.

        Args:
            num_workers: Target number of workers
        """
        with self._lock:
            current_count = len(self.workers)

            if num_workers > current_count:
                # Add workers
                for i in range(current_count, num_workers):
                    worker_id = f"worker-{i}"
                    worker = Worker(
                        worker_id=worker_id,
                        job_queue=self.job_queue,
                        executor_registry=self.executor_registry,
                        max_memory_mb=self.max_memory_per_worker_mb
                    )
                    worker.start()
                    self.workers[worker_id] = worker

                logger.info(f"Scaled up from {current_count} to {num_workers} workers")

            elif num_workers < current_count:
                # Remove workers
                workers_to_remove = list(self.workers.values())[num_workers:]

                for worker in workers_to_remove:
                    worker.stop(wait=True)
                    del self.workers[worker.worker_id]

                logger.info(f"Scaled down from {current_count} to {num_workers} workers")

    def get_stats(self) -> Dict[str, WorkerStats]:
        """
        Get statistics for all workers.

        Returns:
            Dictionary mapping worker IDs to WorkerStats
        """
        with self._lock:
            return {worker_id: worker.get_stats() for worker_id, worker in self.workers.items()}

    def get_pool_status(self) -> Dict[str, Any]:
        """
        Get overall pool status.

        Returns:
            Dictionary with pool statistics
        """
        stats = self.get_stats()

        total_completed = sum(s.jobs_completed for s in stats.values())
        total_failed = sum(s.jobs_failed for s in stats.values())
        total_runtime = sum(s.total_runtime for s in stats.values())
        avg_cpu = sum(s.cpu_usage for s in stats.values()) / len(stats) if stats else 0
        total_memory = sum(s.memory_usage_mb for s in stats.values())

        idle_count = sum(1 for worker in self.workers.values() if worker.status == WorkerStatus.IDLE)
        busy_count = sum(1 for worker in self.workers.values() if worker.status == WorkerStatus.BUSY)

        return {
            'num_workers': len(self.workers),
            'idle_workers': idle_count,
            'busy_workers': busy_count,
            'total_jobs_completed': total_completed,
            'total_jobs_failed': total_failed,
            'total_runtime_seconds': total_runtime,
            'average_cpu_percent': avg_cpu,
            'total_memory_mb': total_memory,
            'queue_size': self.job_queue.get_queue_size(),
        }

    def wait_for_completion(self, check_interval: float = 1.0):
        """
        Wait for all queued jobs to complete.

        Args:
            check_interval: How often to check queue status (seconds)
        """
        logger.info("Waiting for all jobs to complete...")

        while True:
            queue_size = self.job_queue.get_queue_size()
            busy_workers = sum(1 for w in self.workers.values() if w.status == WorkerStatus.BUSY)

            if queue_size == 0 and busy_workers == 0:
                break

            logger.debug(f"Queue size: {queue_size}, Busy workers: {busy_workers}")
            time.sleep(check_interval)

        logger.info("All jobs completed")
