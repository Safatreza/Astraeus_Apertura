"""Scheduling Agent for dependency analysis and timeline generation.

This agent handles the final stage of the systems engineering pipeline:
building dependency graphs, identifying critical paths, and generating
execution timelines.
"""

import logging
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Set

from agents.base_agent import (
    Action,
    BaseAgent,
    Observation,
    Task,
    Thought,
    Tool,
    ToolResult,
)
from artifacts.dependencies import Dependency, DependencyGraph, DependencyType
from artifacts.timeline import ExecutionTimeline, ScheduledTask
from artifacts.wbs import WorkBreakdownStructure, WorkPackage


logger = logging.getLogger("astraeus.agents.scheduling")


# Default duration estimates by work type (in days)
DEFAULT_DURATIONS = {
    "design": 20,
    "development": 40,
    "procurement": 30,
    "integration": 15,
    "test": 20,
    "verification": 10,
    "documentation": 5,
    "review": 3,
    "management": 10,
}


class SchedulingAgent(BaseAgent):
    """Agent for scheduling and timeline generation.

    Capabilities:
    - Build dependency graphs from WBS
    - Add technical and programmatic dependencies
    - Compute critical path
    - Generate execution timeline

    Tools:
    - initialize_dependency_graph: Create graph from WBS
    - add_dependency: Add a dependency relationship
    - compute_critical_path: Find critical path
    - generate_timeline: Create scheduled timeline
    """

    def __init__(
        self,
        name: str = "SchedulingAgent",
        max_iterations: int = 15,
        trace_enabled: bool = True,
    ):
        """Initialize the scheduling agent."""
        tools = self._create_tools()
        super().__init__(
            name=name,
            tools=tools,
            max_iterations=max_iterations,
            trace_enabled=trace_enabled,
        )

        self._dependency_graph: Optional[DependencyGraph] = None
        self._timeline: Optional[ExecutionTimeline] = None
        self._wbs: Optional[WorkBreakdownStructure] = None

    def _create_tools(self) -> List[Tool]:
        """Create the agent's tools."""
        return [
            Tool(
                name="initialize_dependency_graph",
                description="Initialize dependency graph from WBS",
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "wbs": {"type": "object"},
                        "default_durations": {"type": "object"},
                    },
                    "required": ["wbs"],
                },
                function=self._initialize_dependency_graph,
            ),
            Tool(
                name="add_dependency",
                description="Add a dependency between work packages",
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "source_id": {"type": "string"},
                        "target_id": {"type": "string"},
                        "dependency_type": {"type": "string"},
                        "description": {"type": "string"},
                    },
                    "required": ["source_id", "target_id"],
                },
                function=self._add_dependency,
            ),
            Tool(
                name="add_standard_dependencies",
                description="Add standard workflow dependencies",
                parameters_schema={
                    "type": "object",
                    "properties": {},
                },
                function=self._add_standard_dependencies,
            ),
            Tool(
                name="compute_critical_path",
                description="Compute the critical path",
                parameters_schema={
                    "type": "object",
                    "properties": {},
                },
                function=self._compute_critical_path,
            ),
            Tool(
                name="generate_timeline",
                description="Generate execution timeline",
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "start_date": {"type": "string"},
                        "work_days_per_week": {"type": "integer"},
                    },
                },
                function=self._generate_timeline,
            ),
            Tool(
                name="validate_schedule",
                description="Validate the schedule",
                parameters_schema={
                    "type": "object",
                    "properties": {},
                },
                function=self._validate_schedule,
            ),
            Tool(
                name="finalize_schedule",
                description="Finalize and return schedule artifacts",
                parameters_schema={
                    "type": "object",
                    "properties": {},
                },
                function=self._finalize_schedule,
            ),
        ]

    def _initialize_dependency_graph(
        self,
        wbs: Dict[str, Any],
        default_durations: Optional[Dict[str, int]] = None,
    ) -> ToolResult:
        """Initialize dependency graph from WBS."""
        try:
            self._wbs = WorkBreakdownStructure.from_dict(wbs)

            durations = default_durations or DEFAULT_DURATIONS

            # Build node durations from WBS
            node_durations: Dict[str, int] = {}
            for wp_id, wp in self._wbs.work_packages.items():
                if wp.duration_days:
                    node_durations[wp_id] = wp.duration_days
                else:
                    node_durations[wp_id] = durations.get(wp.work_type, 10)

            self._dependency_graph = DependencyGraph(
                mission_name=self._wbs.mission_name,
                node_durations=node_durations,
            )

            return ToolResult(
                success=True,
                data={
                    "total_nodes": len(node_durations),
                    "total_duration_days": sum(node_durations.values()),
                },
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def _add_dependency(
        self,
        source_id: str,
        target_id: str,
        dependency_type: str = "technical",
        description: str = "",
    ) -> ToolResult:
        """Add a dependency between work packages."""
        try:
            if self._dependency_graph is None:
                return ToolResult(
                    success=False,
                    error="Dependency graph not initialized.",
                )

            dep_type = DependencyType(dependency_type.lower())

            dependency = Dependency(
                source_id=source_id,
                target_id=target_id,
                dependency_type=dep_type,
                description=description,
            )

            self._dependency_graph.add_dependency(dependency)

            return ToolResult(
                success=True,
                data={
                    "source": source_id,
                    "target": target_id,
                    "type": dependency_type,
                },
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def _add_standard_dependencies(self) -> ToolResult:
        """Add standard workflow dependencies automatically."""
        try:
            if self._dependency_graph is None or self._wbs is None:
                return ToolResult(
                    success=False,
                    error="Dependency graph or WBS not initialized.",
                )

            added = []

            # Group work packages by PBS element
            pbs_groups: Dict[str, List[WorkPackage]] = {}
            for wp in self._wbs.work_packages.values():
                pbs_ref = wp.pbs_reference
                if pbs_ref not in pbs_groups:
                    pbs_groups[pbs_ref] = []
                pbs_groups[pbs_ref].append(wp)

            # Standard workflow: design -> development -> integration -> test
            workflow_order = ["design", "development", "procurement", "integration", "test", "verification"]

            for pbs_id, packages in pbs_groups.items():
                # Sort packages by workflow order
                sorted_packages = sorted(
                    packages,
                    key=lambda wp: (
                        workflow_order.index(wp.work_type)
                        if wp.work_type in workflow_order
                        else 99
                    ),
                )

                # Create sequential dependencies within same PBS element
                for i in range(len(sorted_packages) - 1):
                    source = sorted_packages[i]
                    target = sorted_packages[i + 1]

                    try:
                        dep = Dependency(
                            source_id=source.id,
                            target_id=target.id,
                            dependency_type=DependencyType.TECHNICAL,
                            description=f"Workflow dependency: {source.work_type} -> {target.work_type}",
                        )
                        self._dependency_graph.add_dependency(dep)
                        added.append(f"{source.id} -> {target.id}")
                    except ValueError:
                        # Skip if dependency already exists or would create cycle
                        pass

            # Add cross-PBS dependencies for integration
            # Component integrations depend on component development
            leaf_developments = [
                wp for wp in self._wbs.work_packages.values()
                if wp.work_type == "development" and "." in wp.pbs_reference.replace("PBS-", "").replace(".", "", 1)
            ]

            subsystem_integrations = [
                wp for wp in self._wbs.work_packages.values()
                if wp.work_type == "integration" and wp.pbs_reference.count(".") == 1
            ]

            for dev_wp in leaf_developments:
                # Find parent subsystem
                pbs_parts = dev_wp.pbs_reference.replace("PBS-", "").split(".")
                if len(pbs_parts) >= 2:
                    parent_pbs = f"PBS-{'.'.join(pbs_parts[:2])}"
                    for int_wp in subsystem_integrations:
                        if int_wp.pbs_reference == parent_pbs:
                            try:
                                dep = Dependency(
                                    source_id=dev_wp.id,
                                    target_id=int_wp.id,
                                    dependency_type=DependencyType.TECHNICAL,
                                    description=f"Component {dev_wp.pbs_reference} must be developed before {int_wp.pbs_reference} integration",
                                )
                                self._dependency_graph.add_dependency(dep)
                                added.append(f"{dev_wp.id} -> {int_wp.id}")
                            except ValueError:
                                pass

            return ToolResult(
                success=True,
                data={
                    "dependencies_added": len(added),
                    "added": added[:20],  # Limit output size
                },
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def _compute_critical_path(self) -> ToolResult:
        """Compute the critical path."""
        try:
            if self._dependency_graph is None:
                return ToolResult(
                    success=False,
                    error="Dependency graph not initialized.",
                )

            # Check for cycles first
            if self._dependency_graph.has_cycles():
                cycles = self._dependency_graph.find_cycles()
                return ToolResult(
                    success=False,
                    error=f"Graph contains cycles: {cycles[:3]}",  # Show first 3 cycles
                )

            critical_path = self._dependency_graph.find_critical_path()
            path_length = self._dependency_graph.get_critical_path_length()

            # Get work package names for the path
            path_names = []
            if self._wbs:
                for wp_id in critical_path:
                    wp = self._wbs.get_work_package(wp_id)
                    if wp:
                        path_names.append(f"{wp_id}: {wp.name}")
                    else:
                        path_names.append(wp_id)

            return ToolResult(
                success=True,
                data={
                    "critical_path": critical_path,
                    "critical_path_names": path_names,
                    "path_length_days": path_length,
                    "path_length_weeks": path_length / 5,  # Assuming 5-day work week
                },
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def _generate_timeline(
        self,
        start_date: Optional[str] = None,
        work_days_per_week: int = 5,
    ) -> ToolResult:
        """Generate execution timeline."""
        try:
            if self._dependency_graph is None or self._wbs is None:
                return ToolResult(
                    success=False,
                    error="Dependency graph or WBS not initialized.",
                )

            # Parse start date
            if start_date:
                try:
                    project_start = date.fromisoformat(start_date)
                except ValueError:
                    project_start = date.today()
            else:
                project_start = date.today()

            # Build work package names mapping
            wp_names = {
                wp_id: wp.name
                for wp_id, wp in self._wbs.work_packages.items()
            }

            # Generate timeline
            self._timeline = ExecutionTimeline.from_dependency_graph(
                dependency_graph=self._dependency_graph,
                work_package_names=wp_names,
                start_date=project_start,
                work_days_per_week=work_days_per_week,
            )

            return ToolResult(
                success=True,
                data={
                    "start_date": project_start.isoformat(),
                    "end_date": self._timeline.get_project_end_date().isoformat(),
                    "total_duration_days": self._timeline.total_duration_days,
                    "total_tasks": len(self._timeline.scheduled_tasks),
                    "critical_path_tasks": len(self._timeline.critical_path),
                },
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def _validate_schedule(self) -> ToolResult:
        """Validate the schedule."""
        try:
            if self._dependency_graph is None:
                return ToolResult(
                    success=False,
                    error="Dependency graph not initialized.",
                )

            validation = self._dependency_graph.validate_structure()

            if self._timeline:
                # Check for resource conflicts (if resources assigned)
                conflicts = self._timeline.detect_resource_conflicts()
                validation["resource_conflicts"] = conflicts

                # Add timeline-specific validation
                validation["timeline_valid"] = len(conflicts) == 0
                validation["milestones_count"] = len(self._timeline.get_milestones())

            return ToolResult(
                success=True,
                data=validation,
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def _finalize_schedule(self) -> ToolResult:
        """Finalize and return schedule artifacts."""
        if self._dependency_graph is None:
            return ToolResult(
                success=False,
                error="Dependency graph not initialized.",
            )

        result = {
            "dependency_graph": self._dependency_graph.export_to_dict(),
            "graph_summary": {
                "total_dependencies": len(self._dependency_graph.dependencies),
                "total_nodes": len(self._dependency_graph.node_durations),
                "has_cycles": self._dependency_graph.has_cycles(),
            },
        }

        if self._timeline:
            result["timeline"] = self._timeline.export_to_dict()
            result["timeline_summary"] = {
                "start_date": self._timeline.start_date.isoformat(),
                "end_date": self._timeline.get_project_end_date().isoformat(),
                "total_duration_days": self._timeline.total_duration_days,
                "critical_path_length": len(self._timeline.critical_path),
            }

        return ToolResult(success=True, data=result)

    def reason(self, context: Dict[str, Any]) -> Thought:
        """Generate reasoning about scheduling state."""
        task = context.get("task")
        observations = context.get("observations", [])
        iteration = context.get("iteration", 0)

        if iteration == 0:
            content = (
                f"Starting scheduling for task: {task.name}. "
                f"I need to build a dependency graph from the WBS, "
                f"add standard dependencies, compute the critical path, "
                f"and generate an execution timeline. "
                f"First action: initialize the dependency graph from WBS."
            )
            return Thought(
                content=content,
                next_action_rationale="Need to initialize dependency graph first",
            )

        last_obs = observations[-1] if observations else None
        if last_obs:
            if last_obs.action.tool_name == "initialize_dependency_graph":
                node_count = last_obs.result.data.get("total_nodes", 0)
                content = (
                    f"Dependency graph initialized with {node_count} nodes. "
                    f"Now I should add standard workflow dependencies."
                )
                return Thought(
                    content=content,
                    observation_summary=f"Initialized graph with {node_count} nodes",
                    next_action_rationale="Need to add standard dependencies",
                )

            elif last_obs.action.tool_name == "add_standard_dependencies":
                dep_count = last_obs.result.data.get("dependencies_added", 0)
                content = (
                    f"Added {dep_count} standard dependencies. "
                    f"Now I should compute the critical path."
                )
                return Thought(
                    content=content,
                    observation_summary=f"Added {dep_count} dependencies",
                    next_action_rationale="Need to compute critical path",
                )

            elif last_obs.action.tool_name == "compute_critical_path":
                if last_obs.result.success:
                    path_length = last_obs.result.data.get("path_length_days", 0)
                    content = (
                        f"Critical path computed: {path_length} days. "
                        f"Now I should generate the execution timeline."
                    )
                else:
                    content = (
                        f"Critical path computation failed: {last_obs.result.error}. "
                        f"Will proceed to timeline generation anyway."
                    )
                return Thought(
                    content=content,
                    observation_summary="Critical path analysis complete",
                    next_action_rationale="Need to generate timeline",
                )

            elif last_obs.action.tool_name == "generate_timeline":
                if last_obs.result.success:
                    end_date = last_obs.result.data.get("end_date", "unknown")
                    content = (
                        f"Timeline generated. Project ends {end_date}. "
                        f"Now I should validate the schedule."
                    )
                else:
                    content = (
                        f"Timeline generation failed: {last_obs.result.error}. "
                        f"Proceeding to validation."
                    )
                return Thought(
                    content=content,
                    observation_summary="Timeline generated",
                    next_action_rationale="Need to validate schedule",
                )

            elif last_obs.action.tool_name == "validate_schedule":
                is_valid = last_obs.result.data.get("is_valid", False)
                content = (
                    f"Schedule validation {'passed' if is_valid else 'found issues'}. "
                    f"Ready to finalize the schedule."
                )
                return Thought(
                    content=content,
                    observation_summary="Validation complete",
                    next_action_rationale="Ready to finalize schedule",
                )

            elif last_obs.action.tool_name == "finalize_schedule":
                content = "Scheduling complete. All artifacts are ready."
                return Thought(
                    content=content,
                    observation_summary="Finalized schedule artifacts",
                    next_action_rationale="Task complete",
                )

        return Thought(
            content="Continuing scheduling process...",
            next_action_rationale="Continue with next logical step",
        )

    def select_action(self, thought: Thought, context: Dict[str, Any]) -> Optional[Action]:
        """Select the next action based on current reasoning."""
        task = context.get("task")
        observations = context.get("observations", [])
        iteration = context.get("iteration", 0)

        if iteration == 0:
            wbs = task.inputs.get("wbs", {})
            return Action(
                tool_name="initialize_dependency_graph",
                parameters={"wbs": wbs},
                rationale="Initialize dependency graph from WBS",
            )

        executed_tools = [obs.action.tool_name for obs in observations]

        if "initialize_dependency_graph" in executed_tools and "add_standard_dependencies" not in executed_tools:
            return Action(
                tool_name="add_standard_dependencies",
                parameters={},
                rationale="Add standard workflow dependencies",
            )

        if "add_standard_dependencies" in executed_tools and "compute_critical_path" not in executed_tools:
            return Action(
                tool_name="compute_critical_path",
                parameters={},
                rationale="Compute the critical path",
            )

        if "compute_critical_path" in executed_tools and "generate_timeline" not in executed_tools:
            start_date = task.inputs.get("start_date")
            return Action(
                tool_name="generate_timeline",
                parameters={
                    "start_date": start_date,
                    "work_days_per_week": 5,
                },
                rationale="Generate execution timeline",
            )

        if "generate_timeline" in executed_tools and "validate_schedule" not in executed_tools:
            return Action(
                tool_name="validate_schedule",
                parameters={},
                rationale="Validate the schedule",
            )

        if "validate_schedule" in executed_tools and "finalize_schedule" not in executed_tools:
            return Action(
                tool_name="finalize_schedule",
                parameters={},
                rationale="Finalize and return schedule artifacts",
            )

        context["task_complete"] = True
        return None

    def get_dependency_graph(self) -> Optional[DependencyGraph]:
        """Get the current dependency graph."""
        return self._dependency_graph

    def get_timeline(self) -> Optional[ExecutionTimeline]:
        """Get the current timeline."""
        return self._timeline
