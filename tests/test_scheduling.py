"""
Tests for job scheduling system.

Tests the job queue, worker pool, and monitoring components.
"""

import pytest
import time
import tempfile
from pathlib import Path

from astraeus.scheduling import (
    SimulationJob,
    JobQueue,
    JobStatus,
    JobPriority,
    WorkerPool,
    JobMonitor,
)


@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    yield db_path

    # Cleanup
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def job_queue(temp_db):
    """Create job queue for testing."""
    return JobQueue(db_path=temp_db)


def simple_executor(params):
    """Simple executor for testing."""
    time.sleep(params.get('duration', 0.1))
    return {'result': params.get('value', 0) * 2}


def failing_executor(params):
    """Executor that always fails."""
    raise ValueError("Simulated failure")


class TestSimulationJob:
    """Tests for SimulationJob class."""

    def test_job_creation(self):
        """Test job creation with default values."""
        job = SimulationJob(
            job_type='test',
            parameters={'key': 'value'}
        )

        assert job.job_type == 'test'
        assert job.parameters == {'key': 'value'}
        assert job.status == JobStatus.PENDING
        assert job.priority == JobPriority.NORMAL
        assert job.retry_count == 0

    def test_job_serialization(self):
        """Test job to/from dictionary conversion."""
        job = SimulationJob(
            job_type='test',
            parameters={'x': 1, 'y': 2},
            priority=JobPriority.HIGH,
            metadata={'desc': 'test job'}
        )

        # Convert to dict
        job_dict = job.to_dict()

        assert job_dict['job_type'] == 'test'
        assert job_dict['priority'] == 'HIGH'
        assert job_dict['parameters'] == {'x': 1, 'y': 2}

        # Convert back to job
        job2 = SimulationJob.from_dict(job_dict)

        assert job2.job_type == job.job_type
        assert job2.priority == job.priority
        assert job2.parameters == job.parameters


class TestJobQueue:
    """Tests for JobQueue class."""

    def test_submit_job(self, job_queue):
        """Test job submission."""
        job = SimulationJob(
            job_type='test',
            parameters={'value': 42}
        )

        job_id = job_queue.submit_job(job)

        assert job_id == job.job_id
        assert job.status == JobStatus.QUEUED
        assert job_queue.get_queue_size() == 1

    def test_get_next_job(self, job_queue):
        """Test getting next job from queue."""
        job1 = SimulationJob(job_type='test1', priority=JobPriority.NORMAL)
        job2 = SimulationJob(job_type='test2', priority=JobPriority.HIGH)

        job_queue.submit_job(job1)
        job_queue.submit_job(job2)

        # Should get high priority job first
        next_job = job_queue.get_next_job(timeout=1.0)

        assert next_job is not None
        assert next_job.job_id == job2.job_id
        assert next_job.status == JobStatus.RUNNING

    def test_mark_completed(self, job_queue):
        """Test marking job as completed."""
        job = SimulationJob(job_type='test', parameters={'value': 10})
        job_id = job_queue.submit_job(job)

        job_queue.get_next_job()  # Start job
        job_queue.mark_completed(job_id, result={'output': 20})

        completed_job = job_queue.get_job(job_id)
        assert completed_job.status == JobStatus.COMPLETED
        assert completed_job.result == {'output': 20}

    def test_mark_failed_with_retry(self, job_queue):
        """Test job failure with retry."""
        job = SimulationJob(
            job_type='test',
            parameters={'value': 10},
            max_retries=2
        )
        job_id = job_queue.submit_job(job)

        job_queue.get_next_job()  # Start job
        job_queue.mark_failed(job_id, "Test error", retry=True)

        failed_job = job_queue.get_job(job_id)
        assert failed_job.retry_count == 1
        assert failed_job.error == "Test error"

        # Job should be re-queued
        assert failed_job.status in [JobStatus.RETRYING, JobStatus.QUEUED]

    def test_job_dependencies(self, job_queue):
        """Test job dependency handling."""
        job1 = SimulationJob(job_type='test1')
        job2 = SimulationJob(
            job_type='test2',
            dependencies=[job1.job_id]
        )

        job_queue.submit_job(job1)
        job_queue.submit_job(job2)

        # Job2 should be pending (waiting for dependency)
        job2_state = job_queue.get_job(job2.job_id)
        assert job2_state.status == JobStatus.PENDING

        # Complete job1
        job_queue.get_next_job()  # Get job1
        job_queue.mark_completed(job1.job_id)

        # Job2 should now be queued
        job2_state = job_queue.get_job(job2.job_id)
        assert job2_state.status == JobStatus.QUEUED

    def test_cancel_job(self, job_queue):
        """Test job cancellation."""
        job = SimulationJob(job_type='test')
        job_id = job_queue.submit_job(job)

        job_queue.cancel_job(job_id)

        cancelled_job = job_queue.get_job(job_id)
        assert cancelled_job.status == JobStatus.CANCELLED

    def test_persistence(self, temp_db):
        """Test job persistence across queue restarts."""
        # Create queue and submit job
        queue1 = JobQueue(db_path=temp_db)
        job = SimulationJob(job_type='test', parameters={'value': 42})
        job_id = queue1.submit_job(job)

        # Create new queue with same database
        queue2 = JobQueue(db_path=temp_db)

        # Job should be restored
        restored_job = queue2.get_job(job_id)
        assert restored_job is not None
        assert restored_job.job_type == 'test'
        assert restored_job.parameters == {'value': 42}


class TestWorkerPool:
    """Tests for WorkerPool class."""

    def test_worker_pool_creation(self, job_queue):
        """Test worker pool creation."""
        pool = WorkerPool(job_queue, num_workers=2)

        assert pool.num_workers == 2
        assert len(pool.workers) == 0  # Not started yet

    def test_register_executor(self, job_queue):
        """Test executor registration."""
        pool = WorkerPool(job_queue, num_workers=2)
        pool.register_executor('test', simple_executor)

        assert 'test' in pool.executor_registry

    def test_execute_jobs(self, job_queue):
        """Test job execution by worker pool."""
        pool = WorkerPool(job_queue, num_workers=2)
        pool.register_executor('simple', simple_executor)

        # Submit jobs
        jobs = []
        for i in range(5):
            job = SimulationJob(
                job_type='simple',
                parameters={'value': i, 'duration': 0.1}
            )
            job_queue.submit_job(job)
            jobs.append(job)

        # Start pool
        pool.start()

        # Wait for completion
        pool.wait_for_completion()

        # Check all jobs completed
        for job in jobs:
            completed_job = job_queue.get_job(job.job_id)
            assert completed_job.status == JobStatus.COMPLETED
            assert completed_job.result['result'] == job.parameters['value'] * 2

        pool.stop()

    def test_worker_stats(self, job_queue):
        """Test worker statistics collection."""
        pool = WorkerPool(job_queue, num_workers=1)
        pool.register_executor('simple', simple_executor)

        # Submit and execute job
        job = SimulationJob(
            job_type='simple',
            parameters={'value': 5, 'duration': 0.1}
        )
        job_queue.submit_job(job)

        pool.start()
        pool.wait_for_completion()

        # Get stats
        stats = pool.get_stats()

        assert len(stats) == 1
        worker_stats = list(stats.values())[0]
        assert worker_stats.jobs_completed == 1
        assert worker_stats.jobs_failed == 0

        pool.stop()

    def test_pool_scaling(self, job_queue):
        """Test worker pool scaling."""
        pool = WorkerPool(job_queue, num_workers=2)
        pool.start()

        assert len(pool.workers) == 2

        # Scale up
        pool.scale(4)
        assert len(pool.workers) == 4

        # Scale down
        pool.scale(2)
        assert len(pool.workers) == 2

        pool.stop()


class TestJobMonitor:
    """Tests for JobMonitor class."""

    def test_monitor_creation(self, job_queue):
        """Test monitor creation."""
        monitor = JobMonitor(job_queue, update_interval=1.0)

        assert monitor.job_queue == job_queue
        assert monitor.update_interval == 1.0

    def test_statistics_update(self, job_queue):
        """Test statistics update."""
        monitor = JobMonitor(job_queue, update_interval=1.0, save_stats=False)

        # Submit some jobs
        for i in range(3):
            job = SimulationJob(job_type='test')
            job_queue.submit_job(job)

        # Update statistics
        monitor.update_statistics()

        stats = monitor.get_statistics()
        assert stats.total_jobs == 3
        assert stats.pending_jobs == 3

    def test_monitor_lifecycle(self, job_queue):
        """Test monitor start/stop."""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            stats_file = f.name

        monitor = JobMonitor(job_queue, update_interval=0.5, stats_file=stats_file)

        # Start monitor
        monitor.start()
        time.sleep(1.0)

        # Stop monitor
        monitor.stop()

        # Check stats file was created
        assert Path(stats_file).exists()

        # Cleanup
        Path(stats_file).unlink()


def test_end_to_end_workflow(temp_db):
    """Test complete workflow: queue, workers, monitor."""
    # Setup
    job_queue = JobQueue(db_path=temp_db)
    worker_pool = WorkerPool(job_queue, num_workers=2)
    worker_pool.register_executor('simple', simple_executor)

    with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
        stats_file = f.name

    monitor = JobMonitor(job_queue, update_interval=0.5, stats_file=stats_file)

    # Submit jobs
    num_jobs = 10
    for i in range(num_jobs):
        job = SimulationJob(
            job_type='simple',
            parameters={'value': i, 'duration': 0.1}
        )
        job_queue.submit_job(job)

    # Start execution
    worker_pool.start()
    monitor.start()

    # Wait for completion
    worker_pool.wait_for_completion()

    # Stop
    monitor.stop()
    worker_pool.stop()

    # Verify results
    stats = monitor.get_statistics()
    assert stats.total_jobs == num_jobs
    assert stats.completed_jobs == num_jobs
    assert stats.failed_jobs == 0

    # Cleanup
    Path(stats_file).unlink()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
