# Parallel Job Scheduling System

The Astraeus Apertura scheduling system provides a production-ready framework for executing antenna simulations in parallel, both on local machines and HPC clusters.

## Features

- **Priority-Based Job Queue**: Submit jobs with different priorities and dependencies
- **Worker Pool**: Multi-threaded parallel execution with configurable worker count
- **HPC Integration**: Submit jobs to SLURM and PBS clusters
- **Job Monitoring**: Real-time statistics and progress tracking
- **Failure Recovery**: Automatic retry with exponential backoff
- **Persistent State**: SQLite-based job persistence across restarts
- **Resource Management**: CPU and memory monitoring per worker

## Quick Start

### Local Parallel Execution

```python
from astraeus.scheduling import JobQueue, WorkerPool, JobMonitor, SimulationJob

# Initialize components
job_queue = JobQueue(db_path="my_jobs.db")
worker_pool = WorkerPool(job_queue, num_workers=4)
monitor = JobMonitor(job_queue)

# Register executor for your simulation type
def my_simulator(params):
    # Run simulation with params
    return {'gain': 8.5, 'vswr': 1.5}

worker_pool.register_executor('my_sim', my_simulator)

# Submit jobs
for i in range(100):
    job = SimulationJob(
        job_type='my_sim',
        parameters={'frequency_ghz': 2.0 + i * 0.1}
    )
    job_queue.submit_job(job)

# Execute
worker_pool.start()
monitor.start()
worker_pool.wait_for_completion()

# Get results
monitor.print_summary()
worker_pool.stop()
monitor.stop()
```

### HPC Cluster Execution

```python
from astraeus.scheduling import JobQueue, SimulationJob
from astraeus.scheduling.hpc_backend import SLURMBackend, HPCJobConfig

# Initialize
job_queue = JobQueue()
slurm = SLURMBackend()

# Configure HPC resources
config = HPCJobConfig(
    nodes=1,
    cpus_per_task=8,
    memory_mb=16384,
    time_limit="02:00:00",
    partition="compute"
)

# Submit job to cluster
job = SimulationJob(job_type='ansys_hfss', parameters={...})
job_queue.submit_job(job)

script = """
module load ansys/2024.1
python run_simulation.py
"""

hpc_job_id = slurm.submit_job(job, config, script)
print(f"Submitted to SLURM as job {hpc_job_id}")
```

## Components

### JobQueue

Thread-safe priority queue with persistence and dependency management.

**Key Features:**
- Priority scheduling (CRITICAL, HIGH, NORMAL, LOW)
- Job dependencies
- Automatic retry with backoff
- SQLite persistence
- Job cancellation

**Methods:**
- `submit_job(job)`: Add job to queue
- `get_next_job(timeout)`: Get next job (blocks)
- `mark_completed(job_id, result)`: Mark success
- `mark_failed(job_id, error, retry)`: Mark failure
- `cancel_job(job_id)`: Cancel job
- `get_job(job_id)`: Retrieve job
- `get_all_jobs(status)`: Get jobs by status

### WorkerPool

Manages worker threads that execute jobs in parallel.

**Key Features:**
- Configurable worker count
- Dynamic scaling
- Resource monitoring (CPU, memory)
- Worker statistics
- Graceful shutdown

**Methods:**
- `register_executor(job_type, executor)`: Register handler
- `start()`: Start all workers
- `stop(wait)`: Stop workers
- `scale(num_workers)`: Resize pool
- `get_stats()`: Get worker statistics
- `wait_for_completion()`: Block until queue empty

### JobMonitor

Real-time monitoring and statistics collection.

**Key Features:**
- Live statistics updates
- Performance metrics
- Failure analysis
- Timeline tracking
- Report export (JSON, Markdown, text)

**Methods:**
- `start()`: Start monitoring thread
- `stop()`: Stop monitoring
- `update_statistics()`: Manual update
- `get_statistics()`: Get current stats
- `print_summary()`: Print to console
- `export_report(filename)`: Save report

### HPC Backends

Submit jobs to cluster schedulers.

**SLURMBackend:**
- `submit_job(job, config, script)`: Submit to SLURM
- `get_job_status(hpc_job_id)`: Check status
- `cancel_job(hpc_job_id)`: Cancel job
- `is_available()`: Check if SLURM present

**PBSBackend:**
- Same interface as SLURM
- Compatible with PBS/Torque clusters

**Auto-detection:**
```python
from astraeus.scheduling.hpc_backend import get_available_backend

backend = get_available_backend()
if backend:
    print(f"Found {type(backend).__name__}")
```

## Job Configuration

### SimulationJob

```python
job = SimulationJob(
    job_id="optional-custom-id",
    job_type="ansys_hfss",
    parameters={'frequency_ghz': 10.0},
    priority=JobPriority.HIGH,
    dependencies=["job-id-1", "job-id-2"],
    max_retries=3,
    timeout=3600,  # seconds
    metadata={'description': 'Horn antenna at X-band'}
)
```

### HPCJobConfig

```python
config = HPCJobConfig(
    nodes=2,
    ntasks_per_node=8,
    cpus_per_task=4,
    memory_mb=32768,
    time_limit="04:00:00",
    partition="gpu",
    account="my_project",
    qos="high",
    gpu_count=1,
    gpu_type="v100",
    email="user@example.com",
    email_events="END,FAIL"
)
```

## Examples

### Parametric Sweep

See `examples/parametric_sweep_parallel.py` for a complete example of:
- Sweeping multiple parameters
- Parallel execution
- Result collection and visualization
- Performance monitoring

Run with:
```bash
python examples/parametric_sweep_parallel.py
```

### HPC Cluster Submission

See `examples/hpc_cluster_submission.py` for:
- Detecting available HPC backend
- Submitting to SLURM/PBS
- Monitoring cluster jobs
- Custom job scripts

## Performance Considerations

### Worker Count

```python
import multiprocessing as mp

# CPU-bound tasks: match CPU count
num_workers = mp.cpu_count()

# I/O-bound tasks: can exceed CPU count
num_workers = mp.cpu_count() * 2

# Memory-limited: reduce workers
num_workers = max(1, mp.cpu_count() // 2)
```

### Memory Management

```python
# Set per-worker memory limit
pool = WorkerPool(
    job_queue,
    num_workers=4,
    max_memory_per_worker_mb=8192  # 8 GB
)

# Monitor memory usage
stats = pool.get_stats()
for worker_id, stat in stats.items():
    print(f"{worker_id}: {stat.memory_usage_mb:.1f} MB")
```

### Database Optimization

```python
# Use in-memory database for temporary jobs
job_queue = JobQueue(db_path=":memory:")

# Use file database for persistence
job_queue = JobQueue(db_path="jobs.db")

# Clean up completed jobs periodically
job_queue.clear_completed()
```

## Best Practices

1. **Register executors before starting workers**
   ```python
   pool.register_executor('type1', executor1)
   pool.register_executor('type2', executor2)
   pool.start()  # Now start
   ```

2. **Use job dependencies for workflows**
   ```python
   job1 = SimulationJob(job_type='mesh')
   job2 = SimulationJob(
       job_type='solve',
       dependencies=[job1.job_id]  # Wait for mesh
   )
   ```

3. **Set appropriate timeouts**
   ```python
   job = SimulationJob(
       job_type='ansys_hfss',
       timeout=7200  # 2 hours
   )
   ```

4. **Handle failures gracefully**
   ```python
   job = SimulationJob(
       job_type='simulation',
       max_retries=3  # Retry up to 3 times
   )
   ```

5. **Monitor long-running jobs**
   ```python
   monitor.start()
   slow_jobs = monitor.get_slow_jobs(threshold_seconds=3600)
   for job in slow_jobs:
       print(f"Job {job.job_id} running for > 1 hour")
   ```

## Troubleshooting

### Jobs not executing

Check:
- Workers started: `pool.start()`
- Executor registered: `pool.register_executor(...)`
- Job type matches: `job.job_type == registered_type`

### High memory usage

Solutions:
- Reduce worker count
- Set memory limits
- Clear completed jobs
- Use file-based results storage

### HPC submission fails

Check:
- SLURM/PBS available: `backend.is_available()`
- Correct partition/account
- Valid time limit format
- Module load commands correct

## API Reference

See individual module docstrings:
- `astraeus.scheduling.job_queue`
- `astraeus.scheduling.worker_pool`
- `astraeus.scheduling.job_monitor`
- `astraeus.scheduling.hpc_backend`

## License

Part of the Astraeus Apertura project.
