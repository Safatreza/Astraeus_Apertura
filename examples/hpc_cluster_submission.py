"""
HPC Cluster Submission Example.

This example demonstrates how to submit antenna simulation jobs to
an HPC cluster using SLURM or PBS schedulers.

This enables distributed execution across compute nodes for large-scale
design space exploration.
"""

import sys
import time
from pathlib import Path
from typing import Dict, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from astraeus.scheduling import (
    SimulationJob,
    JobQueue,
    JobPriority,
)
from astraeus.scheduling.hpc_backend import (
    HPCJobConfig,
    SLURMBackend,
    PBSBackend,
    get_available_backend
)
from loguru import logger


def create_simulation_script(job: SimulationJob) -> str:
    """
    Create a bash script for HPC execution.

    Args:
        job: SimulationJob to execute

    Returns:
        Bash script content
    """
    # In production, this would serialize the job parameters,
    # call the Python script on the compute node, and collect results

    script = f"""#!/bin/bash

# Load required modules (customize for your HPC environment)
module load python/3.9
module load ansys/2024.1

# Activate virtual environment (if using one)
# source /path/to/venv/bin/activate

# Set up environment
export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK

# Create working directory
WORK_DIR=$TMPDIR/astraeus_job_{job.job_id}
mkdir -p $WORK_DIR
cd $WORK_DIR

# Run the simulation
echo "Starting simulation at $(date)"
echo "Job ID: {job.job_id}"
echo "Job Type: {job.job_type}"
echo "Parameters: {job.parameters}"

# Call Python simulation script
# In production, you would:
# 1. Copy simulation script to compute node
# 2. Serialize job parameters to JSON
# 3. Call your simulation executable
# 4. Collect results back to shared storage

python << EOF
import json
import time
import sys

# Simulate work
print("Running simulation...")
time.sleep(5)

# Mock results
results = {{
    'job_id': '{job.job_id}',
    'status': 'completed',
    'gain_dbi': 8.5,
    'vswr': 1.5,
    'efficiency': 0.85
}}

# Save results to shared storage
with open('/shared/results/{job.job_id}_results.json', 'w') as f:
    json.dump(results, f, indent=2)

print("Simulation complete")
EOF

# Cleanup
cd $HOME
rm -rf $WORK_DIR

echo "Job completed at $(date)"
"""

    return script


def submit_to_slurm():
    """Example: Submit jobs to SLURM cluster."""
    print("="*70)
    print("SLURM CLUSTER SUBMISSION EXAMPLE")
    print("="*70)
    print()

    # Check if SLURM is available
    slurm = SLURMBackend()

    if not slurm.is_available():
        print("ERROR: SLURM is not available on this system")
        print("This example requires a SLURM cluster environment")
        return

    print("SLURM detected ✓")
    print()

    # Initialize job queue
    job_queue = JobQueue(db_path="hpc_jobs.db")

    # Create HPC job configuration
    hpc_config = HPCJobConfig(
        nodes=1,
        ntasks_per_node=1,
        cpus_per_task=8,
        memory_mb=16384,  # 16 GB
        time_limit="02:00:00",  # 2 hours
        partition="compute",  # Adjust for your cluster
        account="antenna_design",  # Adjust for your cluster
        email="user@example.com",
        email_events="END,FAIL"
    )

    print("HPC Configuration:")
    print(f"  Nodes:          {hpc_config.nodes}")
    print(f"  CPUs per task:  {hpc_config.cpus_per_task}")
    print(f"  Memory:         {hpc_config.memory_mb} MB")
    print(f"  Time limit:     {hpc_config.time_limit}")
    print(f"  Partition:      {hpc_config.partition}")
    print()

    # Create and submit jobs
    print("Creating simulation jobs...")

    jobs_to_submit = [
        {
            'job_type': 'horn_antenna',
            'parameters': {
                'aperture_width': 50.0,
                'aperture_height': 50.0,
                'frequency_ghz': 10.0
            },
            'priority': JobPriority.HIGH
        },
        {
            'job_type': 'patch_array',
            'parameters': {
                'elements': 16,
                'spacing_lambda': 0.5,
                'frequency_ghz': 5.8
            },
            'priority': JobPriority.NORMAL
        },
        {
            'job_type': 'reflector',
            'parameters': {
                'diameter_m': 2.0,
                'f_over_d': 0.4,
                'frequency_ghz': 12.0
            },
            'priority': JobPriority.NORMAL
        },
    ]

    hpc_job_ids = []

    for job_spec in jobs_to_submit:
        # Create simulation job
        job = SimulationJob(
            job_type=job_spec['job_type'],
            parameters=job_spec['parameters'],
            priority=job_spec['priority'],
            metadata={'hpc_backend': 'slurm'}
        )

        # Add to queue
        job_queue.submit_job(job)

        # Create execution script
        script = create_simulation_script(job)

        # Submit to SLURM
        try:
            hpc_job_id = slurm.submit_job(job, hpc_config, script)
            hpc_job_ids.append((job.job_id, hpc_job_id))

            print(f"✓ Submitted {job.job_type} as SLURM job {hpc_job_id}")

        except Exception as e:
            print(f"✗ Failed to submit {job.job_type}: {e}")

    print()
    print(f"Submitted {len(hpc_job_ids)} jobs to SLURM")
    print()

    # Monitor job status
    print("Monitoring job status...")
    print("(Press Ctrl+C to stop monitoring)")
    print()

    try:
        while True:
            print("\nJob Status:")
            print("-" * 60)

            all_complete = True

            for job_id, hpc_job_id in hpc_job_ids:
                status = slurm.get_job_status(hpc_job_id)
                print(f"  Job {job_id[:8]}... (SLURM {hpc_job_id}): {status}")

                if status not in ['COMPLETED', 'FAILED', 'CANCELLED']:
                    all_complete = False

            if all_complete:
                print("\nAll jobs completed!")
                break

            time.sleep(10)  # Check every 10 seconds

    except KeyboardInterrupt:
        print("\n\nMonitoring stopped by user")

    print()
    print("HPC submission complete")
    print()


def submit_to_pbs():
    """Example: Submit jobs to PBS cluster."""
    print("="*70)
    print("PBS CLUSTER SUBMISSION EXAMPLE")
    print("="*70)
    print()

    # Check if PBS is available
    pbs = PBSBackend()

    if not pbs.is_available():
        print("ERROR: PBS is not available on this system")
        print("This example requires a PBS cluster environment")
        return

    print("PBS detected ✓")
    print()

    # Similar to SLURM example, but using PBS backend
    # (Implementation would be similar to submit_to_slurm)

    print("PBS submission workflow would be similar to SLURM")
    print("Refer to submit_to_slurm() function for implementation details")
    print()


def auto_detect_and_submit():
    """Auto-detect available HPC backend and submit jobs."""
    print("="*70)
    print("AUTO-DETECT HPC BACKEND")
    print("="*70)
    print()

    backend = get_available_backend()

    if backend is None:
        print("No HPC scheduler detected (SLURM/PBS)")
        print("Falling back to local execution")
        print()
        print("To run on HPC cluster:")
        print("  1. Run this script on a cluster login node")
        print("  2. Ensure SLURM or PBS is installed and configured")
        print("  3. Adjust partition/account settings in the script")
        return

    backend_name = type(backend).__name__.replace('Backend', '')
    print(f"Detected HPC backend: {backend_name}")
    print()

    if isinstance(backend, SLURMBackend):
        submit_to_slurm()
    elif isinstance(backend, PBSBackend):
        submit_to_pbs()


if __name__ == '__main__':
    print()
    print("HPC Cluster Submission Example")
    print("="*70)
    print()
    print("This example demonstrates submitting antenna simulations to HPC clusters")
    print()
    print("Options:")
    print("  1. Auto-detect backend and submit")
    print("  2. SLURM submission (requires SLURM)")
    print("  3. PBS submission (requires PBS)")
    print()

    try:
        choice = input("Select option (1-3, or Enter for auto-detect): ").strip()

        if choice == '2':
            submit_to_slurm()
        elif choice == '3':
            submit_to_pbs()
        else:
            auto_detect_and_submit()

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()

    print()
    print("="*70)
    print()
    print("NOTE: This is a demonstration example.")
    print("In production, you would:")
    print("  1. Customize module loading for your HPC environment")
    print("  2. Set correct partition/account/QoS settings")
    print("  3. Configure shared storage paths")
    print("  4. Implement result collection from compute nodes")
    print("  5. Add proper error handling and retry logic")
    print()
