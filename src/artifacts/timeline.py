"""Execution timeline artifact models.

This module defines the data structures for representing scheduled
tasks and generating execution timelines from dependency graphs.
"""

import json
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field, field_validator, model_validator

from artifacts.dependencies import DependencyGraph


class ScheduledTask(BaseModel):
    """A scheduled task in the execution timeline.

    Represents a work package that has been scheduled with specific
    start and end dates.

    Attributes:
        work_package_id: ID of the associated work package.
        name: Task name for display.
        start_date: Scheduled start date.
        end_date: Scheduled end date.
        duration_days: Duration in working days.
        predecessors: IDs of predecessor tasks.
        successors: IDs of successor tasks.
        slack_days: Available slack/float in days.
        is_critical: Whether on the critical path.
        milestone: Whether this is a milestone (zero duration).
        assigned_resources: List of assigned resource names.
    """

    work_package_id: str = Field(..., pattern=r"^WBS-[0-9.]+$")
    name: str = Field(default="")
    start_date: date
    end_date: date
    duration_days: int = Field(ge=0)
    predecessors: List[str] = Field(default_factory=list)
    successors: List[str] = Field(default_factory=list)
    slack_days: int = Field(default=0, ge=0)
    is_critical: bool = Field(default=False)
    milestone: bool = Field(default=False)
    assigned_resources: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_dates(self) -> "ScheduledTask":
        """Ensure end_date is not before start_date."""
        if self.end_date < self.start_date:
            raise ValueError(
                f"End date {self.end_date} cannot be before start date {self.start_date}"
            )
        return self

    def get_duration(self) -> int:
        """Calculate duration from dates."""
        return (self.end_date - self.start_date).days

    def overlaps_with(self, other: "ScheduledTask") -> bool:
        """Check if this task overlaps with another."""
        return not (self.end_date < other.start_date or self.start_date > other.end_date)

    def to_gantt_dict(self) -> Dict[str, Any]:
        """Convert to Gantt chart data format."""
        return {
            "id": self.work_package_id,
            "name": self.name,
            "start": self.start_date.isoformat(),
            "end": self.end_date.isoformat(),
            "duration": self.duration_days,
            "dependencies": self.predecessors,
            "critical": self.is_critical,
            "milestone": self.milestone,
        }


class ExecutionTimeline(BaseModel):
    """Complete execution timeline for the project.

    Generates scheduled tasks from a dependency graph using
    topological sort and forward pass scheduling.

    Attributes:
        mission_name: Name of the mission.
        version: Timeline version identifier.
        start_date: Project start date.
        scheduled_tasks: Dictionary of scheduled tasks by WBS ID.
        critical_path: List of WBS IDs on the critical path.
        total_duration_days: Total project duration.
        work_hours_per_day: Working hours per day for calculations.
        work_days_per_week: Working days per week (for weekend skip).
    """

    mission_name: str
    version: str = Field(default="1.0")
    start_date: date = Field(default_factory=date.today)
    scheduled_tasks: Dict[str, ScheduledTask] = Field(default_factory=dict)
    critical_path: List[str] = Field(default_factory=list)
    total_duration_days: int = Field(default=0, ge=0)
    work_hours_per_day: int = Field(default=8, ge=1, le=24)
    work_days_per_week: int = Field(default=5, ge=1, le=7)

    def add_working_days(self, start: date, days: int) -> date:
        """Add working days to a date, skipping weekends if configured.

        Args:
            start: Starting date.
            days: Number of working days to add.

        Returns:
            Resulting date after adding working days.
        """
        if self.work_days_per_week == 7:
            # No weekend skip
            return start + timedelta(days=days)

        current = start
        remaining = days

        while remaining > 0:
            current += timedelta(days=1)
            # Skip weekends (Saturday=5, Sunday=6)
            if current.weekday() < self.work_days_per_week:
                remaining -= 1

        return current

    @classmethod
    def from_dependency_graph(
        cls,
        dependency_graph: DependencyGraph,
        work_package_names: Dict[str, str],
        start_date: Optional[date] = None,
        work_hours_per_day: int = 8,
        work_days_per_week: int = 5,
    ) -> "ExecutionTimeline":
        """Generate a timeline from a dependency graph.

        Args:
            dependency_graph: The dependency graph to schedule from.
            work_package_names: Mapping of WBS IDs to display names.
            start_date: Project start date (defaults to today).
            work_hours_per_day: Working hours per day.
            work_days_per_week: Working days per week.

        Returns:
            Generated ExecutionTimeline.
        """
        if start_date is None:
            start_date = date.today()

        timeline = cls(
            mission_name=dependency_graph.mission_name,
            start_date=start_date,
            work_hours_per_day=work_hours_per_day,
            work_days_per_week=work_days_per_week,
        )

        # Check for cycles
        if dependency_graph.has_cycles():
            raise ValueError("Cannot generate timeline: dependency graph has cycles")

        # Compute earliest times
        early_times = dependency_graph.compute_earliest_times()
        slack = dependency_graph.compute_slack()
        critical_path = dependency_graph.find_critical_path()

        # Get topological order
        topo_order = dependency_graph.get_topological_order()

        # Schedule each task
        for wp_id in topo_order:
            duration = dependency_graph.node_durations.get(wp_id, 0)
            early_start = early_times.get(wp_id, {}).get("early_start", 0)
            task_slack = slack.get(wp_id, 0)

            task_start = timeline.add_working_days(start_date, early_start)
            task_end = timeline.add_working_days(task_start, duration)

            predecessors = dependency_graph.get_predecessors(wp_id)
            successors = dependency_graph.get_successors(wp_id)

            scheduled_task = ScheduledTask(
                work_package_id=wp_id,
                name=work_package_names.get(wp_id, wp_id),
                start_date=task_start,
                end_date=task_end,
                duration_days=duration,
                predecessors=predecessors,
                successors=successors,
                slack_days=task_slack,
                is_critical=wp_id in critical_path,
                milestone=duration == 0,
            )

            timeline.scheduled_tasks[wp_id] = scheduled_task

        # Set critical path and total duration
        timeline.critical_path = critical_path
        timeline.total_duration_days = dependency_graph.get_critical_path_length()

        return timeline

    def get_task(self, wp_id: str) -> Optional[ScheduledTask]:
        """Get a scheduled task by work package ID."""
        return self.scheduled_tasks.get(wp_id)

    def get_tasks_on_date(self, target_date: date) -> List[ScheduledTask]:
        """Get all tasks active on a specific date."""
        return [
            task for task in self.scheduled_tasks.values()
            if task.start_date <= target_date <= task.end_date
        ]

    def get_tasks_in_range(
        self,
        range_start: date,
        range_end: date
    ) -> List[ScheduledTask]:
        """Get all tasks within a date range."""
        return [
            task for task in self.scheduled_tasks.values()
            if not (task.end_date < range_start or task.start_date > range_end)
        ]

    def get_milestones(self) -> List[ScheduledTask]:
        """Get all milestone tasks."""
        return [task for task in self.scheduled_tasks.values() if task.milestone]

    def get_critical_tasks(self) -> List[ScheduledTask]:
        """Get all tasks on the critical path."""
        return [task for task in self.scheduled_tasks.values() if task.is_critical]

    def get_project_end_date(self) -> date:
        """Get the project end date (latest task end date)."""
        if not self.scheduled_tasks:
            return self.start_date

        return max(task.end_date for task in self.scheduled_tasks.values())

    def get_resource_utilization(self, resource: str) -> List[Tuple[date, date]]:
        """Get date ranges when a resource is utilized."""
        ranges: List[Tuple[date, date]] = []

        for task in self.scheduled_tasks.values():
            if resource in task.assigned_resources:
                ranges.append((task.start_date, task.end_date))

        # Sort by start date
        ranges.sort(key=lambda x: x[0])
        return ranges

    def detect_resource_conflicts(self) -> Dict[str, List[Tuple[str, str]]]:
        """Detect overlapping tasks for the same resource.

        Returns:
            Dictionary mapping resource names to lists of conflicting task pairs.
        """
        conflicts: Dict[str, List[Tuple[str, str]]] = {}

        # Group tasks by resource
        resource_tasks: Dict[str, List[ScheduledTask]] = {}
        for task in self.scheduled_tasks.values():
            for resource in task.assigned_resources:
                if resource not in resource_tasks:
                    resource_tasks[resource] = []
                resource_tasks[resource].append(task)

        # Check for overlaps
        for resource, tasks in resource_tasks.items():
            for i, task1 in enumerate(tasks):
                for task2 in tasks[i + 1:]:
                    if task1.overlaps_with(task2):
                        if resource not in conflicts:
                            conflicts[resource] = []
                        conflicts[resource].append(
                            (task1.work_package_id, task2.work_package_id)
                        )

        return conflicts

    def calculate_progress(self, as_of_date: date) -> Dict[str, Any]:
        """Calculate project progress as of a date.

        Args:
            as_of_date: Date to calculate progress for.

        Returns:
            Dictionary with progress metrics.
        """
        total_tasks = len(self.scheduled_tasks)
        if total_tasks == 0:
            return {
                "total_tasks": 0,
                "completed": 0,
                "in_progress": 0,
                "not_started": 0,
                "completion_percentage": 0.0,
            }

        completed = sum(
            1 for task in self.scheduled_tasks.values()
            if task.end_date < as_of_date
        )
        in_progress = sum(
            1 for task in self.scheduled_tasks.values()
            if task.start_date <= as_of_date <= task.end_date
        )
        not_started = sum(
            1 for task in self.scheduled_tasks.values()
            if task.start_date > as_of_date
        )

        return {
            "as_of_date": as_of_date.isoformat(),
            "total_tasks": total_tasks,
            "completed": completed,
            "in_progress": in_progress,
            "not_started": not_started,
            "completion_percentage": (completed / total_tasks) * 100,
        }

    def to_gantt_data(self) -> List[Dict[str, Any]]:
        """Export timeline as Gantt chart data."""
        return [task.to_gantt_dict() for task in self.scheduled_tasks.values()]

    def to_icalendar(self) -> str:
        """Export timeline as iCalendar format."""
        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            f"PRODID:-//Astraeus Apertura//{self.mission_name}//EN",
        ]

        for task in self.scheduled_tasks.values():
            lines.extend([
                "BEGIN:VEVENT",
                f"UID:{task.work_package_id}@astraeus",
                f"DTSTART;VALUE=DATE:{task.start_date.strftime('%Y%m%d')}",
                f"DTEND;VALUE=DATE:{task.end_date.strftime('%Y%m%d')}",
                f"SUMMARY:{task.name}",
                f"DESCRIPTION:Duration: {task.duration_days} days",
                "END:VEVENT",
            ])

        lines.append("END:VCALENDAR")
        return "\n".join(lines)

    def export_to_dict(self) -> Dict[str, Any]:
        """Export timeline to dictionary format."""
        return {
            "mission_name": self.mission_name,
            "version": self.version,
            "start_date": self.start_date.isoformat(),
            "scheduled_tasks": {
                wp_id: {
                    **task.model_dump(),
                    "start_date": task.start_date.isoformat(),
                    "end_date": task.end_date.isoformat(),
                }
                for wp_id, task in self.scheduled_tasks.items()
            },
            "critical_path": self.critical_path,
            "total_duration_days": self.total_duration_days,
            "project_end_date": self.get_project_end_date().isoformat(),
        }

    def export_to_json(self, indent: int = 2) -> str:
        """Export timeline to JSON string."""
        return json.dumps(self.export_to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExecutionTimeline":
        """Create ExecutionTimeline from dictionary."""
        scheduled_tasks = {}
        for wp_id, task_data in data.get("scheduled_tasks", {}).items():
            task_data["start_date"] = date.fromisoformat(task_data["start_date"])
            task_data["end_date"] = date.fromisoformat(task_data["end_date"])
            scheduled_tasks[wp_id] = ScheduledTask(**task_data)

        return cls(
            mission_name=data["mission_name"],
            version=data.get("version", "1.0"),
            start_date=date.fromisoformat(data["start_date"]),
            scheduled_tasks=scheduled_tasks,
            critical_path=data.get("critical_path", []),
            total_duration_days=data.get("total_duration_days", 0),
        )

    def __len__(self) -> int:
        """Return the number of scheduled tasks."""
        return len(self.scheduled_tasks)
