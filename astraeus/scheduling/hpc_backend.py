"""
HPC cluster integration for distributed simulation execution.

This module provides backends for submitting jobs to HPC schedulers like SLURM and PBS,
enabling distributed execution across compute clusters.
"""

import os
import re
import subprocess
import tempfile
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from pathlib import Path
from loguru import logger

from .job_queue import SimulationJob, JobStatus


@dataclass
class HPCJobConfig:
    """Configuration for HPC job submission."""
    nodes: int = 1
    ntasks_per_node: int = 1
    cpus_per_task: int = 1
    memory_mb: int = 4096
    time_limit: str = "01:00:00"  # HH:MM:SS
    partition: Optional[str] = None
    account: Optional[str] = None
    qos: Optional[str] = None
    gpu_count: int = 0
    gpu_type: Optional[str] = None
    email: Optional[str] = None
    email_events: str = "FAIL"  # NONE, BEGIN, END, FAIL, ALL
    additional_args: List[str] = None


class HPCBackend(ABC):
    """
    Abstract base class for HPC scheduler backends.

    Subclasses implement specific schedulers (SLURM, PBS, etc.)
    """

    def __init__(self, work_dir: Optional[str] = None):
        """
        Initialize HPC backend.

        Args:
            work_dir: Working directory for job scripts and outputs
        """
        self.work_dir = Path(work_dir or tempfile.gettempdir()) / "astraeus_hpc"
        self.work_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"HPC backend initialized with work_dir: {self.work_dir}")

    @abstractmethod
    def submit_job(
        self,
        job: SimulationJob,
        config: HPCJobConfig,
        script_content: str
    ) -> str:
        """
        Submit a job to the HPC scheduler.

        Args:
            job: SimulationJob to submit
            config: HPC job configuration
            script_content: Shell script content to execute

        Returns:
            HPC job ID (scheduler-specific)
        """
        pass

    @abstractmethod
    def get_job_status(self, hpc_job_id: str) -> str:
        """
        Get status of an HPC job.

        Args:
            hpc_job_id: HPC scheduler job ID

        Returns:
            Job status string
        """
        pass

    @abstractmethod
    def cancel_job(self, hpc_job_id: str):
        """
        Cancel an HPC job.

        Args:
            hpc_job_id: HPC scheduler job ID
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if HPC scheduler is available.

        Returns:
            True if scheduler commands are available
        """
        pass

    def _run_command(self, cmd: List[str], check: bool = True) -> subprocess.CompletedProcess:
        """
        Run a shell command.

        Args:
            cmd: Command and arguments
            check: Whether to raise exception on error

        Returns:
            CompletedProcess result
        """
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=check
            )
            return result
        except subprocess.CalledProcessError as e:
            logger.error(f"Command failed: {' '.join(cmd)}")
            logger.error(f"stdout: {e.stdout}")
            logger.error(f"stderr: {e.stderr}")
            raise

    def _write_job_script(self, job_id: str, content: str) -> Path:
        """
        Write job script to file.

        Args:
            job_id: Job identifier
            content: Script content

        Returns:
            Path to script file
        """
        script_path = self.work_dir / f"{job_id}.sh"
        script_path.write_text(content)
        script_path.chmod(0o755)
        return script_path


class SLURMBackend(HPCBackend):
    """
    SLURM (Simple Linux Utility for Resource Management) backend.

    SLURM is widely used on HPC clusters for job scheduling.
    """

    def submit_job(
        self,
        job: SimulationJob,
        config: HPCJobConfig,
        script_content: str
    ) -> str:
        """
        Submit job to SLURM.

        Args:
            job: SimulationJob
            config: SLURM job configuration
            script_content: Bash script to execute

        Returns:
            SLURM job ID
        """
        # Build SLURM script
        slurm_script = self._build_slurm_script(job, config, script_content)

        # Write script to file
        script_path = self._write_job_script(job.job_id, slurm_script)

        # Submit using sbatch
        result = self._run_command(['sbatch', str(script_path)])

        # Parse job ID from output (e.g., "Submitted batch job 12345")
        match = re.search(r'Submitted batch job (\d+)', result.stdout)
        if not match:
            raise RuntimeError(f"Failed to parse SLURM job ID from: {result.stdout}")

        slurm_job_id = match.group(1)
        logger.info(f"Submitted job {job.job_id} to SLURM as {slurm_job_id}")

        return slurm_job_id

    def _build_slurm_script(
        self,
        job: SimulationJob,
        config: HPCJobConfig,
        script_content: str
    ) -> str:
        """Build SLURM batch script."""
        lines = ["#!/bin/bash"]

        # Job name
        lines.append(f"#SBATCH --job-name={job.job_id[:50]}")

        # Output files
        output_dir = self.work_dir / "outputs"
        output_dir.mkdir(exist_ok=True)
        lines.append(f"#SBATCH --output={output_dir}/{job.job_id}.out")
        lines.append(f"#SBATCH --error={output_dir}/{job.job_id}.err")

        # Resource allocation
        lines.append(f"#SBATCH --nodes={config.nodes}")
        lines.append(f"#SBATCH --ntasks-per-node={config.ntasks_per_node}")
        lines.append(f"#SBATCH --cpus-per-task={config.cpus_per_task}")
        lines.append(f"#SBATCH --mem={config.memory_mb}M")
        lines.append(f"#SBATCH --time={config.time_limit}")

        # Optional parameters
        if config.partition:
            lines.append(f"#SBATCH --partition={config.partition}")
        if config.account:
            lines.append(f"#SBATCH --account={config.account}")
        if config.qos:
            lines.append(f"#SBATCH --qos={config.qos}")

        # GPU resources
        if config.gpu_count > 0:
            if config.gpu_type:
                lines.append(f"#SBATCH --gres=gpu:{config.gpu_type}:{config.gpu_count}")
            else:
                lines.append(f"#SBATCH --gres=gpu:{config.gpu_count}")

        # Email notifications
        if config.email:
            lines.append(f"#SBATCH --mail-user={config.email}")
            lines.append(f"#SBATCH --mail-type={config.email_events}")

        # Additional arguments
        if config.additional_args:
            for arg in config.additional_args:
                lines.append(f"#SBATCH {arg}")

        # Script body
        lines.append("")
        lines.append("# Job information")
        lines.append("echo \"Job started at: $(date)\"")
        lines.append("echo \"Running on node: $(hostname)\"")
        lines.append("echo \"Job ID: $SLURM_JOB_ID\"")
        lines.append("")

        # User script
        lines.append("# User script")
        lines.append(script_content)

        lines.append("")
        lines.append("echo \"Job completed at: $(date)\"")

        return "\n".join(lines)

    def get_job_status(self, hpc_job_id: str) -> str:
        """
        Get SLURM job status.

        Args:
            hpc_job_id: SLURM job ID

        Returns:
            Status string (PENDING, RUNNING, COMPLETED, FAILED, CANCELLED)
        """
        try:
            result = self._run_command(
                ['sacct', '-j', hpc_job_id, '--format=State', '--noheader', '--parsable2'],
                check=False
            )

            if result.returncode != 0:
                # Job might not be in sacct yet, check squeue
                result = self._run_command(
                    ['squeue', '-j', hpc_job_id, '--format=%T', '--noheader'],
                    check=False
                )

            status = result.stdout.strip().split('\n')[0] if result.stdout else "UNKNOWN"

            # Map SLURM states to our states
            status_map = {
                'PENDING': 'PENDING',
                'RUNNING': 'RUNNING',
                'COMPLETED': 'COMPLETED',
                'FAILED': 'FAILED',
                'CANCELLED': 'CANCELLED',
                'TIMEOUT': 'FAILED',
                'OUT_OF_MEMORY': 'FAILED',
                'NODE_FAIL': 'FAILED',
            }

            return status_map.get(status, status)

        except Exception as e:
            logger.error(f"Failed to get SLURM job status: {e}")
            return "UNKNOWN"

    def cancel_job(self, hpc_job_id: str):
        """
        Cancel SLURM job.

        Args:
            hpc_job_id: SLURM job ID
        """
        try:
            self._run_command(['scancel', hpc_job_id])
            logger.info(f"Cancelled SLURM job {hpc_job_id}")
        except Exception as e:
            logger.error(f"Failed to cancel SLURM job {hpc_job_id}: {e}")

    def is_available(self) -> bool:
        """Check if SLURM is available."""
        try:
            self._run_command(['sbatch', '--version'], check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False


class PBSBackend(HPCBackend):
    """
    PBS (Portable Batch System) backend.

    PBS is another popular HPC scheduler, used on many clusters.
    """

    def submit_job(
        self,
        job: SimulationJob,
        config: HPCJobConfig,
        script_content: str
    ) -> str:
        """
        Submit job to PBS.

        Args:
            job: SimulationJob
            config: PBS job configuration
            script_content: Bash script to execute

        Returns:
            PBS job ID
        """
        # Build PBS script
        pbs_script = self._build_pbs_script(job, config, script_content)

        # Write script to file
        script_path = self._write_job_script(job.job_id, pbs_script)

        # Submit using qsub
        result = self._run_command(['qsub', str(script_path)])

        # PBS returns job ID directly (e.g., "12345.hostname")
        pbs_job_id = result.stdout.strip()
        logger.info(f"Submitted job {job.job_id} to PBS as {pbs_job_id}")

        return pbs_job_id

    def _build_pbs_script(
        self,
        job: SimulationJob,
        config: HPCJobConfig,
        script_content: str
    ) -> str:
        """Build PBS batch script."""
        lines = ["#!/bin/bash"]

        # Job name
        lines.append(f"#PBS -N {job.job_id[:15]}")  # PBS has shorter limit

        # Output files
        output_dir = self.work_dir / "outputs"
        output_dir.mkdir(exist_ok=True)
        lines.append(f"#PBS -o {output_dir}/{job.job_id}.out")
        lines.append(f"#PBS -e {output_dir}/{job.job_id}.err")

        # Resource allocation
        total_cpus = config.nodes * config.ntasks_per_node * config.cpus_per_task
        lines.append(f"#PBS -l nodes={config.nodes}:ppn={config.ntasks_per_node * config.cpus_per_task}")
        lines.append(f"#PBS -l mem={config.memory_mb}mb")
        lines.append(f"#PBS -l walltime={config.time_limit}")

        # Optional parameters
        if config.partition:
            lines.append(f"#PBS -q {config.partition}")
        if config.account:
            lines.append(f"#PBS -A {config.account}")

        # GPU resources
        if config.gpu_count > 0:
            if config.gpu_type:
                lines.append(f"#PBS -l nodes={config.nodes}:ppn={config.ntasks_per_node}:gpus={config.gpu_count}:{config.gpu_type}")
            else:
                lines.append(f"#PBS -l gpus={config.gpu_count}")

        # Email notifications
        if config.email:
            lines.append(f"#PBS -M {config.email}")
            # Convert SLURM-style to PBS-style
            event_map = {
                'NONE': 'n',
                'BEGIN': 'b',
                'END': 'e',
                'FAIL': 'a',
                'ALL': 'abe'
            }
            pbs_events = event_map.get(config.email_events, 'a')
            lines.append(f"#PBS -m {pbs_events}")

        # Additional arguments
        if config.additional_args:
            for arg in config.additional_args:
                lines.append(f"#PBS {arg}")

        # Change to working directory
        lines.append("")
        lines.append("cd $PBS_O_WORKDIR")
        lines.append("")

        # Job information
        lines.append("# Job information")
        lines.append("echo \"Job started at: $(date)\"")
        lines.append("echo \"Running on node: $(hostname)\"")
        lines.append("echo \"Job ID: $PBS_JOBID\"")
        lines.append("")

        # User script
        lines.append("# User script")
        lines.append(script_content)

        lines.append("")
        lines.append("echo \"Job completed at: $(date)\"")

        return "\n".join(lines)

    def get_job_status(self, hpc_job_id: str) -> str:
        """
        Get PBS job status.

        Args:
            hpc_job_id: PBS job ID

        Returns:
            Status string
        """
        try:
            result = self._run_command(
                ['qstat', '-f', hpc_job_id],
                check=False
            )

            if result.returncode != 0:
                return "UNKNOWN"

            # Parse job state from qstat output
            match = re.search(r'job_state = ([A-Z])', result.stdout)
            if not match:
                return "UNKNOWN"

            state = match.group(1)

            # Map PBS states to our states
            status_map = {
                'Q': 'PENDING',  # Queued
                'R': 'RUNNING',  # Running
                'E': 'RUNNING',  # Exiting (still running)
                'C': 'COMPLETED',  # Completed
                'H': 'PENDING',  # Held
                'S': 'PENDING',  # Suspended
            }

            return status_map.get(state, state)

        except Exception as e:
            logger.error(f"Failed to get PBS job status: {e}")
            return "UNKNOWN"

    def cancel_job(self, hpc_job_id: str):
        """
        Cancel PBS job.

        Args:
            hpc_job_id: PBS job ID
        """
        try:
            self._run_command(['qdel', hpc_job_id])
            logger.info(f"Cancelled PBS job {hpc_job_id}")
        except Exception as e:
            logger.error(f"Failed to cancel PBS job {hpc_job_id}: {e}")

    def is_available(self) -> bool:
        """Check if PBS is available."""
        try:
            self._run_command(['qsub', '--version'], check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False


def get_available_backend() -> Optional[HPCBackend]:
    """
    Detect and return available HPC backend.

    Returns:
        HPCBackend instance or None if no HPC scheduler available
    """
    slurm = SLURMBackend()
    if slurm.is_available():
        logger.info("Detected SLURM scheduler")
        return slurm

    pbs = PBSBackend()
    if pbs.is_available():
        logger.info("Detected PBS scheduler")
        return pbs

    logger.info("No HPC scheduler detected, will use local execution")
    return None
