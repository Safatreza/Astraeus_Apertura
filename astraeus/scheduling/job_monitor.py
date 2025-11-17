"""
Job monitoring and statistics tracking.

This module provides real-time monitoring of job execution, statistics collection,
and performance analytics for the simulation job scheduler.
"""

import time
import threading
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
import json
from pathlib import Path
from loguru import logger

from .job_queue import JobQueue, JobStatus, SimulationJob


@dataclass
class JobStatistics:
    """Statistics for job execution."""
    total_jobs: int = 0
    completed_jobs: int = 0
    failed_jobs: int = 0
    cancelled_jobs: int = 0
    pending_jobs: int = 0
    running_jobs: int = 0

    total_runtime_seconds: float = 0.0
    average_runtime_seconds: float = 0.0
    min_runtime_seconds: float = float('inf')
    max_runtime_seconds: float = 0.0

    success_rate: float = 0.0
    jobs_per_hour: float = 0.0

    # Job type breakdown
    job_type_stats: Dict[str, Dict[str, int]] = field(default_factory=dict)

    # Failure analysis
    failure_reasons: Dict[str, int] = field(default_factory=lambda: defaultdict(int))

    # Timeline
    start_time: Optional[datetime] = None
    last_update: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'total_jobs': self.total_jobs,
            'completed_jobs': self.completed_jobs,
            'failed_jobs': self.failed_jobs,
            'cancelled_jobs': self.cancelled_jobs,
            'pending_jobs': self.pending_jobs,
            'running_jobs': self.running_jobs,
            'total_runtime_seconds': self.total_runtime_seconds,
            'average_runtime_seconds': self.average_runtime_seconds,
            'min_runtime_seconds': self.min_runtime_seconds if self.min_runtime_seconds != float('inf') else 0,
            'max_runtime_seconds': self.max_runtime_seconds,
            'success_rate': self.success_rate,
            'jobs_per_hour': self.jobs_per_hour,
            'job_type_stats': dict(self.job_type_stats),
            'failure_reasons': dict(self.failure_reasons),
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'last_update': self.last_update.isoformat() if self.last_update else None,
        }


class JobMonitor:
    """
    Monitors job execution and collects statistics.

    Features:
    - Real-time job status tracking
    - Performance statistics
    - Failure analysis
    - Historical data collection
    - Automatic reporting
    """

    def __init__(
        self,
        job_queue: JobQueue,
        update_interval: float = 5.0,
        save_stats: bool = True,
        stats_file: Optional[str] = None
    ):
        """
        Initialize job monitor.

        Args:
            job_queue: JobQueue to monitor
            update_interval: How often to update statistics (seconds)
            save_stats: Whether to save statistics to file
            stats_file: Path to statistics file
        """
        self.job_queue = job_queue
        self.update_interval = update_interval
        self.save_stats = save_stats
        self.stats_file = Path(stats_file or "job_statistics.json")

        self.statistics = JobStatistics(start_time=datetime.now())
        self._lock = threading.RLock()
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # Historical tracking
        self._job_history: List[Dict[str, Any]] = []
        self._hourly_stats: Dict[str, int] = defaultdict(int)

        logger.info("JobMonitor initialized")

    def start(self):
        """Start monitoring thread."""
        if self._monitor_thread is not None and self._monitor_thread.is_alive():
            logger.warning("JobMonitor already running")
            return

        self._stop_event.clear()
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.info("JobMonitor started")

    def stop(self):
        """Stop monitoring thread."""
        logger.info("Stopping JobMonitor")
        self._stop_event.set()

        if self._monitor_thread:
            self._monitor_thread.join(timeout=10)

        # Final statistics update
        self.update_statistics()

        if self.save_stats:
            self._save_statistics()

        logger.info("JobMonitor stopped")

    def _monitor_loop(self):
        """Main monitoring loop."""
        while not self._stop_event.is_set():
            try:
                self.update_statistics()

                if self.save_stats:
                    self._save_statistics()

                time.sleep(self.update_interval)

            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                time.sleep(self.update_interval)

    def update_statistics(self):
        """Update job statistics from queue."""
        with self._lock:
            all_jobs = self.job_queue.get_all_jobs()

            # Count jobs by status
            status_counts = defaultdict(int)
            for job in all_jobs:
                status_counts[job.status] += 1

            self.statistics.total_jobs = len(all_jobs)
            self.statistics.completed_jobs = status_counts[JobStatus.COMPLETED]
            self.statistics.failed_jobs = status_counts[JobStatus.FAILED]
            self.statistics.cancelled_jobs = status_counts[JobStatus.CANCELLED]
            self.statistics.pending_jobs = status_counts[JobStatus.PENDING] + status_counts[JobStatus.QUEUED]
            self.statistics.running_jobs = status_counts[JobStatus.RUNNING]

            # Calculate runtime statistics
            completed_jobs = [j for j in all_jobs if j.status == JobStatus.COMPLETED and j.completed_at and j.started_at]

            if completed_jobs:
                runtimes = [(j.completed_at - j.started_at).total_seconds() for j in completed_jobs]

                self.statistics.total_runtime_seconds = sum(runtimes)
                self.statistics.average_runtime_seconds = sum(runtimes) / len(runtimes)
                self.statistics.min_runtime_seconds = min(runtimes)
                self.statistics.max_runtime_seconds = max(runtimes)

            # Calculate success rate
            terminal_jobs = self.statistics.completed_jobs + self.statistics.failed_jobs + self.statistics.cancelled_jobs
            if terminal_jobs > 0:
                self.statistics.success_rate = self.statistics.completed_jobs / terminal_jobs

            # Calculate jobs per hour
            if self.statistics.start_time:
                elapsed_hours = (datetime.now() - self.statistics.start_time).total_seconds() / 3600
                if elapsed_hours > 0:
                    self.statistics.jobs_per_hour = self.statistics.completed_jobs / elapsed_hours

            # Job type statistics
            job_type_stats = defaultdict(lambda: defaultdict(int))
            for job in all_jobs:
                job_type_stats[job.job_type]['total'] += 1
                job_type_stats[job.job_type][job.status.name] += 1

            self.statistics.job_type_stats = {k: dict(v) for k, v in job_type_stats.items()}

            # Failure analysis
            failure_reasons = defaultdict(int)
            for job in all_jobs:
                if job.status == JobStatus.FAILED and job.error:
                    # Extract error type
                    error_type = job.error.split(':')[0] if ':' in job.error else 'Unknown'
                    failure_reasons[error_type] += 1

            self.statistics.failure_reasons = dict(failure_reasons)

            self.statistics.last_update = datetime.now()

            # Log summary periodically
            if len(all_jobs) > 0:
                logger.debug(
                    f"Job statistics: {self.statistics.completed_jobs}/{self.statistics.total_jobs} completed, "
                    f"{self.statistics.running_jobs} running, "
                    f"{self.statistics.failed_jobs} failed, "
                    f"success rate: {self.statistics.success_rate:.1%}"
                )

    def _save_statistics(self):
        """Save statistics to file."""
        try:
            stats_dict = self.statistics.to_dict()

            with open(self.stats_file, 'w') as f:
                json.dump(stats_dict, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to save statistics: {e}")

    def get_statistics(self) -> JobStatistics:
        """
        Get current statistics.

        Returns:
            JobStatistics object
        """
        with self._lock:
            return self.statistics

    def get_job_timeline(self, hours: int = 24) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get job timeline for the last N hours.

        Args:
            hours: Number of hours to include

        Returns:
            Dictionary with hourly job counts
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        all_jobs = self.job_queue.get_all_jobs()

        # Group jobs by hour
        timeline = defaultdict(lambda: {'completed': 0, 'failed': 0, 'running': 0, 'pending': 0})

        for job in all_jobs:
            if job.created_at and job.created_at >= cutoff_time:
                hour_key = job.created_at.strftime('%Y-%m-%d %H:00')

                if job.status == JobStatus.COMPLETED:
                    timeline[hour_key]['completed'] += 1
                elif job.status == JobStatus.FAILED:
                    timeline[hour_key]['failed'] += 1
                elif job.status == JobStatus.RUNNING:
                    timeline[hour_key]['running'] += 1
                else:
                    timeline[hour_key]['pending'] += 1

        return dict(timeline)

    def get_slow_jobs(self, threshold_seconds: float = 3600) -> List[SimulationJob]:
        """
        Get jobs that are running longer than threshold.

        Args:
            threshold_seconds: Threshold in seconds

        Returns:
            List of slow jobs
        """
        all_jobs = self.job_queue.get_all_jobs(status=JobStatus.RUNNING)
        slow_jobs = []

        now = datetime.now()
        for job in all_jobs:
            if job.started_at:
                runtime = (now - job.started_at).total_seconds()
                if runtime > threshold_seconds:
                    slow_jobs.append(job)

        return slow_jobs

    def get_failed_jobs(self, limit: int = 10) -> List[SimulationJob]:
        """
        Get recent failed jobs.

        Args:
            limit: Maximum number of jobs to return

        Returns:
            List of failed jobs
        """
        failed_jobs = self.job_queue.get_all_jobs(status=JobStatus.FAILED)

        # Sort by completion time (most recent first)
        failed_jobs.sort(key=lambda j: j.completed_at or datetime.min, reverse=True)

        return failed_jobs[:limit]

    def print_summary(self):
        """Print formatted summary of job statistics."""
        stats = self.get_statistics()

        print("\n" + "="*60)
        print("JOB EXECUTION SUMMARY")
        print("="*60)
        print(f"Total Jobs:      {stats.total_jobs}")
        print(f"  Completed:     {stats.completed_jobs} ({stats.success_rate:.1%})")
        print(f"  Failed:        {stats.failed_jobs}")
        print(f"  Cancelled:     {stats.cancelled_jobs}")
        print(f"  Running:       {stats.running_jobs}")
        print(f"  Pending:       {stats.pending_jobs}")
        print()
        print(f"Runtime Statistics:")
        print(f"  Total:         {stats.total_runtime_seconds/3600:.2f} hours")
        if stats.completed_jobs > 0:
            print(f"  Average:       {stats.average_runtime_seconds:.1f} seconds")
            print(f"  Min:           {stats.min_runtime_seconds:.1f} seconds")
            print(f"  Max:           {stats.max_runtime_seconds:.1f} seconds")
        print()
        print(f"Throughput:      {stats.jobs_per_hour:.1f} jobs/hour")
        print()

        if stats.job_type_stats:
            print("Job Type Breakdown:")
            for job_type, counts in stats.job_type_stats.items():
                print(f"  {job_type}:")
                for status, count in counts.items():
                    print(f"    {status}: {count}")
            print()

        if stats.failure_reasons:
            print("Failure Analysis:")
            for reason, count in sorted(stats.failure_reasons.items(), key=lambda x: x[1], reverse=True):
                print(f"  {reason}: {count}")
            print()

        if stats.start_time:
            elapsed = datetime.now() - stats.start_time
            print(f"Monitoring Duration: {elapsed}")

        print("="*60)
        print()

    def export_report(self, filename: str):
        """
        Export detailed report to file.

        Args:
            filename: Output filename (supports .txt, .json, .md)
        """
        path = Path(filename)
        ext = path.suffix.lower()

        if ext == '.json':
            self._export_json_report(path)
        elif ext == '.md':
            self._export_markdown_report(path)
        else:
            self._export_text_report(path)

        logger.info(f"Exported report to {filename}")

    def _export_json_report(self, path: Path):
        """Export report as JSON."""
        stats = self.statistics.to_dict()

        # Add additional data
        stats['slow_jobs'] = [j.to_dict() for j in self.get_slow_jobs()]
        stats['failed_jobs'] = [j.to_dict() for j in self.get_failed_jobs()]
        stats['timeline'] = self.get_job_timeline()

        with open(path, 'w') as f:
            json.dump(stats, f, indent=2)

    def _export_text_report(self, path: Path):
        """Export report as plain text."""
        import sys
        from io import StringIO

        # Capture print output
        old_stdout = sys.stdout
        sys.stdout = output = StringIO()

        self.print_summary()

        sys.stdout = old_stdout

        with open(path, 'w') as f:
            f.write(output.getvalue())

    def _export_markdown_report(self, path: Path):
        """Export report as Markdown."""
        stats = self.get_statistics()

        lines = [
            "# Job Execution Report",
            "",
            f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Summary",
            "",
            f"- **Total Jobs**: {stats.total_jobs}",
            f"- **Completed**: {stats.completed_jobs} ({stats.success_rate:.1%})",
            f"- **Failed**: {stats.failed_jobs}",
            f"- **Running**: {stats.running_jobs}",
            f"- **Pending**: {stats.pending_jobs}",
            "",
            "## Runtime Statistics",
            "",
            f"- **Total Runtime**: {stats.total_runtime_seconds/3600:.2f} hours",
        ]

        if stats.completed_jobs > 0:
            lines.extend([
                f"- **Average Runtime**: {stats.average_runtime_seconds:.1f} seconds",
                f"- **Min Runtime**: {stats.min_runtime_seconds:.1f} seconds",
                f"- **Max Runtime**: {stats.max_runtime_seconds:.1f} seconds",
            ])

        lines.extend([
            "",
            f"## Throughput",
            "",
            f"**{stats.jobs_per_hour:.1f}** jobs/hour",
            "",
        ])

        if stats.job_type_stats:
            lines.extend([
                "## Job Type Breakdown",
                "",
                "| Job Type | Total | Completed | Failed | Running |",
                "|----------|-------|-----------|--------|---------|",
            ])

            for job_type, counts in stats.job_type_stats.items():
                lines.append(
                    f"| {job_type} | {counts.get('total', 0)} | "
                    f"{counts.get('COMPLETED', 0)} | {counts.get('FAILED', 0)} | "
                    f"{counts.get('RUNNING', 0)} |"
                )

            lines.append("")

        if stats.failure_reasons:
            lines.extend([
                "## Failure Analysis",
                "",
                "| Error Type | Count |",
                "|------------|-------|",
            ])

            for reason, count in sorted(stats.failure_reasons.items(), key=lambda x: x[1], reverse=True):
                lines.append(f"| {reason} | {count} |")

            lines.append("")

        with open(path, 'w') as f:
            f.write('\n'.join(lines))
