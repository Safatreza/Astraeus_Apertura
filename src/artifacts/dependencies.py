"""Dependency graph artifact models.

This module defines the data structures for representing and analyzing
dependencies between work packages, including critical path analysis.
"""

import json
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

import networkx as nx
from pydantic import BaseModel, Field, field_validator, model_validator


class DependencyType(str, Enum):
    """Types of dependencies between work packages."""

    TECHNICAL = "technical"  # Technical/engineering dependency
    PROGRAMMATIC = "programmatic"  # Schedule/resource dependency
    EXTERNAL = "external"  # External supplier/partner dependency
    INFORMATION = "information"  # Information/data dependency
    RESOURCE = "resource"  # Shared resource dependency


class Dependency(BaseModel):
    """A dependency relationship between two work packages.

    Represents a directed edge from source to target, meaning
    target depends on source (source must complete before target).

    Attributes:
        source_id: ID of the predecessor work package.
        target_id: ID of the successor work package.
        dependency_type: Classification of the dependency.
        description: Human-readable description of the dependency.
        lag_days: Optional lag time between completion and start.
        is_critical: Whether this is on the critical path.
    """

    source_id: str = Field(..., pattern=r"^WBS-[0-9.]+$")
    target_id: str = Field(..., pattern=r"^WBS-[0-9.]+$")
    dependency_type: DependencyType = DependencyType.TECHNICAL
    description: str = Field(default="")
    lag_days: int = Field(default=0, ge=0)
    is_critical: bool = Field(default=False)

    @model_validator(mode="after")
    def validate_not_self_loop(self) -> "Dependency":
        """Ensure a work package doesn't depend on itself."""
        if self.source_id == self.target_id:
            raise ValueError(
                f"Self-dependency not allowed: {self.source_id}"
            )
        return self

    def to_edge_tuple(self) -> Tuple[str, str, Dict[str, Any]]:
        """Convert to networkx edge tuple format."""
        return (
            self.source_id,
            self.target_id,
            {
                "dependency_type": self.dependency_type.value,
                "description": self.description,
                "lag_days": self.lag_days,
                "is_critical": self.is_critical,
            },
        )


class DependencyGraph(BaseModel):
    """Dependency graph with analysis capabilities.

    Uses networkx for graph operations including cycle detection
    and critical path analysis.

    Attributes:
        mission_name: Name of the mission.
        version: Graph version identifier.
        dependencies: List of dependency relationships.
        node_durations: Mapping of node IDs to duration in days.
    """

    mission_name: str
    version: str = Field(default="1.0")
    dependencies: List[Dependency] = Field(default_factory=list)
    node_durations: Dict[str, int] = Field(default_factory=dict)

    # Internal graph representation (not serialized)
    _graph: Optional[nx.DiGraph] = None

    class Config:
        """Pydantic configuration."""
        arbitrary_types_allowed = True

    def model_post_init(self, __context) -> None:
        """Build the networkx graph after initialization."""
        self._build_graph()

    def _build_graph(self) -> None:
        """Build the internal networkx DiGraph from dependencies."""
        self._graph = nx.DiGraph()

        # Add nodes with durations
        for node_id, duration in self.node_durations.items():
            self._graph.add_node(node_id, duration=duration)

        # Add edges from dependencies
        for dep in self.dependencies:
            if dep.source_id not in self._graph:
                self._graph.add_node(dep.source_id, duration=0)
            if dep.target_id not in self._graph:
                self._graph.add_node(dep.target_id, duration=0)

            self._graph.add_edge(
                dep.source_id,
                dep.target_id,
                **dep.to_edge_tuple()[2]
            )

    def get_graph(self) -> nx.DiGraph:
        """Get the underlying networkx graph."""
        if self._graph is None:
            self._build_graph()
        return self._graph

    def add_dependency(self, dependency: Dependency) -> None:
        """Add a dependency to the graph."""
        # Check for duplicates
        for existing in self.dependencies:
            if (existing.source_id == dependency.source_id and
                existing.target_id == dependency.target_id):
                raise ValueError(
                    f"Dependency from {dependency.source_id} to "
                    f"{dependency.target_id} already exists"
                )

        self.dependencies.append(dependency)
        self._build_graph()

        # Check for cycles after adding
        if self.has_cycles():
            # Remove the dependency that caused the cycle
            self.dependencies.pop()
            self._build_graph()
            raise ValueError(
                f"Adding dependency {dependency.source_id} -> "
                f"{dependency.target_id} would create a cycle"
            )

    def remove_dependency(self, source_id: str, target_id: str) -> bool:
        """Remove a dependency from the graph."""
        for i, dep in enumerate(self.dependencies):
            if dep.source_id == source_id and dep.target_id == target_id:
                self.dependencies.pop(i)
                self._build_graph()
                return True
        return False

    def set_node_duration(self, node_id: str, duration: int) -> None:
        """Set the duration for a node."""
        self.node_durations[node_id] = duration
        if self._graph is not None and node_id in self._graph:
            self._graph.nodes[node_id]["duration"] = duration

    def has_cycles(self) -> bool:
        """Check if the graph contains cycles."""
        graph = self.get_graph()
        try:
            nx.find_cycle(graph)
            return True
        except nx.NetworkXNoCycle:
            return False

    def find_cycles(self) -> List[List[str]]:
        """Find all cycles in the graph."""
        graph = self.get_graph()
        try:
            cycles = list(nx.simple_cycles(graph))
            return cycles
        except Exception:
            return []

    def get_topological_order(self) -> List[str]:
        """Get nodes in topological order (respecting dependencies).

        Returns:
            List of node IDs in execution order.

        Raises:
            ValueError: If graph contains cycles.
        """
        graph = self.get_graph()
        if self.has_cycles():
            raise ValueError("Cannot compute topological order: graph has cycles")
        return list(nx.topological_sort(graph))

    def get_predecessors(self, node_id: str) -> List[str]:
        """Get all immediate predecessors of a node."""
        graph = self.get_graph()
        if node_id not in graph:
            return []
        return list(graph.predecessors(node_id))

    def get_successors(self, node_id: str) -> List[str]:
        """Get all immediate successors of a node."""
        graph = self.get_graph()
        if node_id not in graph:
            return []
        return list(graph.successors(node_id))

    def get_all_predecessors(self, node_id: str) -> Set[str]:
        """Get all predecessors (transitive closure)."""
        graph = self.get_graph()
        if node_id not in graph:
            return set()
        return nx.ancestors(graph, node_id)

    def get_all_successors(self, node_id: str) -> Set[str]:
        """Get all successors (transitive closure)."""
        graph = self.get_graph()
        if node_id not in graph:
            return set()
        return nx.descendants(graph, node_id)

    def compute_earliest_times(self) -> Dict[str, Dict[str, int]]:
        """Compute earliest start and finish times for all nodes.

        Returns:
            Dictionary mapping node IDs to {early_start, early_finish}.
        """
        graph = self.get_graph()
        if self.has_cycles():
            raise ValueError("Cannot compute times: graph has cycles")

        times: Dict[str, Dict[str, int]] = {}
        topo_order = self.get_topological_order()

        for node_id in topo_order:
            duration = self.node_durations.get(node_id, 0)
            predecessors = self.get_predecessors(node_id)

            if not predecessors:
                early_start = 0
            else:
                early_start = max(
                    times[pred]["early_finish"]
                    for pred in predecessors
                )
                # Add lag from dependency
                for dep in self.dependencies:
                    if dep.target_id == node_id and dep.source_id in predecessors:
                        early_start = max(early_start, times[dep.source_id]["early_finish"] + dep.lag_days)

            times[node_id] = {
                "early_start": early_start,
                "early_finish": early_start + duration,
            }

        return times

    def compute_latest_times(self, project_end: Optional[int] = None) -> Dict[str, Dict[str, int]]:
        """Compute latest start and finish times for all nodes.

        Args:
            project_end: Project end time. If None, uses max early finish.

        Returns:
            Dictionary mapping node IDs to {late_start, late_finish}.
        """
        graph = self.get_graph()
        if self.has_cycles():
            raise ValueError("Cannot compute times: graph has cycles")

        early_times = self.compute_earliest_times()

        if project_end is None:
            project_end = max(
                t["early_finish"] for t in early_times.values()
            ) if early_times else 0

        times: Dict[str, Dict[str, int]] = {}
        topo_order = list(reversed(self.get_topological_order()))

        for node_id in topo_order:
            duration = self.node_durations.get(node_id, 0)
            successors = self.get_successors(node_id)

            if not successors:
                late_finish = project_end
            else:
                late_finish = min(
                    times[succ]["late_start"]
                    for succ in successors
                )

            times[node_id] = {
                "late_start": late_finish - duration,
                "late_finish": late_finish,
            }

        return times

    def compute_slack(self) -> Dict[str, int]:
        """Compute slack (float) for all nodes.

        Slack = Late Start - Early Start

        Returns:
            Dictionary mapping node IDs to slack in days.
        """
        early = self.compute_earliest_times()
        late = self.compute_latest_times()

        return {
            node_id: late[node_id]["late_start"] - early[node_id]["early_start"]
            for node_id in early
        }

    def find_critical_path(self) -> List[str]:
        """Find the critical path (nodes with zero slack).

        Returns:
            List of node IDs on the critical path in order.
        """
        if not self.node_durations:
            return []

        slack = self.compute_slack()
        topo_order = self.get_topological_order()

        critical_path = [
            node_id for node_id in topo_order
            if slack.get(node_id, 0) == 0
        ]

        # Update dependencies to mark critical ones
        for dep in self.dependencies:
            if dep.source_id in critical_path and dep.target_id in critical_path:
                dep.is_critical = True
            else:
                dep.is_critical = False

        return critical_path

    def get_critical_path_length(self) -> int:
        """Get the total duration of the critical path."""
        if not self.node_durations:
            return 0

        early_times = self.compute_earliest_times()
        if not early_times:
            return 0

        return max(t["early_finish"] for t in early_times.values())

    def get_parallel_groups(self) -> List[Set[str]]:
        """Identify groups of nodes that can execute in parallel.

        Returns:
            List of sets, where each set contains nodes that can
            run concurrently at that stage.
        """
        if self.has_cycles():
            return []

        graph = self.get_graph()
        groups: List[Set[str]] = []
        remaining = set(graph.nodes())

        while remaining:
            # Find nodes with no unprocessed predecessors
            ready = {
                node for node in remaining
                if all(pred not in remaining for pred in graph.predecessors(node))
            }

            if not ready:
                break  # Shouldn't happen if no cycles

            groups.append(ready)
            remaining -= ready

        return groups

    def validate_structure(self) -> Dict[str, Any]:
        """Validate the dependency graph structure.

        Returns:
            Dictionary with validation results.
        """
        graph = self.get_graph()
        cycles = self.find_cycles()

        # Find orphaned nodes (no predecessors or successors)
        orphaned = [
            node for node in graph.nodes()
            if graph.in_degree(node) == 0 and graph.out_degree(node) == 0
        ]

        # Find start nodes (no predecessors)
        start_nodes = [
            node for node in graph.nodes()
            if graph.in_degree(node) == 0
        ]

        # Find end nodes (no successors)
        end_nodes = [
            node for node in graph.nodes()
            if graph.out_degree(node) == 0
        ]

        return {
            "is_valid": len(cycles) == 0,
            "has_cycles": len(cycles) > 0,
            "cycles": cycles,
            "orphaned_nodes": orphaned,
            "start_nodes": start_nodes,
            "end_nodes": end_nodes,
            "total_nodes": graph.number_of_nodes(),
            "total_edges": graph.number_of_edges(),
        }

    def export_to_dict(self) -> Dict[str, Any]:
        """Export dependency graph to dictionary format."""
        return {
            "mission_name": self.mission_name,
            "version": self.version,
            "dependencies": [dep.model_dump() for dep in self.dependencies],
            "node_durations": self.node_durations,
        }

    def export_to_json(self, indent: int = 2) -> str:
        """Export dependency graph to JSON string."""
        data = self.export_to_dict()
        # Convert enum to string for JSON serialization
        for dep in data["dependencies"]:
            dep["dependency_type"] = dep["dependency_type"]
        return json.dumps(data, indent=indent)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DependencyGraph":
        """Create DependencyGraph from dictionary."""
        dependencies = [
            Dependency(**dep_data)
            for dep_data in data.get("dependencies", [])
        ]
        return cls(
            mission_name=data["mission_name"],
            version=data.get("version", "1.0"),
            dependencies=dependencies,
            node_durations=data.get("node_durations", {}),
        )

    def __len__(self) -> int:
        """Return the number of dependencies."""
        return len(self.dependencies)
