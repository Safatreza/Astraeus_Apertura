"""Cross-artifact consistency checking tools.

This module provides tools for verifying consistency across
multiple SE artifacts and building traceability matrices.
"""

import logging
from typing import Any, Dict, List, Optional, Set, Tuple

from pydantic import BaseModel, Field

from artifacts.requirements import RequirementsSet
from artifacts.pbs import ProductBreakdownStructure
from artifacts.wbs import WorkBreakdownStructure
from artifacts.dependencies import DependencyGraph


logger = logging.getLogger("astraeus.tools.consistency")


class TraceabilityEntry(BaseModel):
    """An entry in the traceability matrix."""

    requirement_id: str
    pbs_nodes: List[str] = Field(default_factory=list)
    work_packages: List[str] = Field(default_factory=list)
    is_complete: bool = False


class TraceabilityMatrix(BaseModel):
    """Requirements traceability matrix.

    Maps requirements through PBS to WBS, showing complete
    traceability chain for each requirement.

    Attributes:
        mission_name: Name of the mission.
        entries: List of traceability entries.
        summary: Summary statistics.
    """

    mission_name: str
    entries: List[TraceabilityEntry] = Field(default_factory=list)
    summary: Dict[str, Any] = Field(default_factory=dict)

    def get_entry(self, requirement_id: str) -> Optional[TraceabilityEntry]:
        """Get entry for a specific requirement."""
        for entry in self.entries:
            if entry.requirement_id == requirement_id:
                return entry
        return None

    def get_complete_entries(self) -> List[TraceabilityEntry]:
        """Get entries with complete traceability."""
        return [e for e in self.entries if e.is_complete]

    def get_incomplete_entries(self) -> List[TraceabilityEntry]:
        """Get entries with incomplete traceability."""
        return [e for e in self.entries if not e.is_complete]


class ConsistencyIssue(BaseModel):
    """A consistency issue found during checking."""

    issue_type: str
    severity: str  # "error", "warning", "info"
    message: str
    affected_artifacts: List[str] = Field(default_factory=list)


class ConsistencyReport(BaseModel):
    """Report from consistency checking.

    Attributes:
        is_consistent: Whether all artifacts are consistent.
        issues: List of identified issues.
        statistics: Consistency statistics.
    """

    is_consistent: bool
    issues: List[ConsistencyIssue] = Field(default_factory=list)
    statistics: Dict[str, Any] = Field(default_factory=dict)

    def get_errors(self) -> List[ConsistencyIssue]:
        """Get error-level issues."""
        return [i for i in self.issues if i.severity == "error"]

    def get_warnings(self) -> List[ConsistencyIssue]:
        """Get warning-level issues."""
        return [i for i in self.issues if i.severity == "warning"]


def verify_traceability(
    requirements: RequirementsSet,
    pbs: ProductBreakdownStructure,
    wbs: WorkBreakdownStructure,
) -> TraceabilityMatrix:
    """Build and verify the requirements traceability matrix.

    Traces each requirement through:
    1. Requirement -> PBS node allocation
    2. PBS node -> WBS work package derivation

    Args:
        requirements: The requirements set.
        pbs: The Product Breakdown Structure.
        wbs: The Work Breakdown Structure.

    Returns:
        TraceabilityMatrix with complete traceability information.
    """
    entries: List[TraceabilityEntry] = []
    complete_count = 0

    for req in requirements:
        # Get PBS allocations
        pbs_nodes = req.allocation_target.copy()

        # Get WBS work packages for those PBS nodes
        work_packages: List[str] = []
        for pbs_id in pbs_nodes:
            wbs_packages = wbs.pbs_to_wbs_mapping.get(pbs_id, [])
            work_packages.extend(wbs_packages)

        # Determine completeness
        is_complete = bool(pbs_nodes and work_packages)
        if is_complete:
            complete_count += 1

        entry = TraceabilityEntry(
            requirement_id=req.id,
            pbs_nodes=pbs_nodes,
            work_packages=work_packages,
            is_complete=is_complete,
        )
        entries.append(entry)

    # Build summary
    total = len(entries)
    summary = {
        "total_requirements": total,
        "complete_traceability": complete_count,
        "incomplete_traceability": total - complete_count,
        "completeness_percentage": (complete_count / total * 100) if total else 100,
    }

    return TraceabilityMatrix(
        mission_name=requirements.mission_name,
        entries=entries,
        summary=summary,
    )


def detect_orphaned_elements(
    pbs: ProductBreakdownStructure,
    wbs: WorkBreakdownStructure,
) -> Dict[str, List[str]]:
    """Detect orphaned elements in PBS and WBS.

    Orphaned elements are:
    - PBS nodes with no requirements and no children
    - WBS packages referencing non-existent PBS nodes
    - WBS packages with no dependencies and not depended upon

    Args:
        pbs: The Product Breakdown Structure.
        wbs: The Work Breakdown Structure.

    Returns:
        Dictionary mapping category to list of orphaned element IDs.
    """
    orphaned: Dict[str, List[str]] = {
        "pbs_no_requirements": [],
        "pbs_no_children_no_requirements": [],
        "wbs_invalid_pbs_reference": [],
        "wbs_isolated": [],
    }

    # Check PBS nodes
    for node_id, node in pbs.nodes.items():
        if not node.allocated_requirements:
            orphaned["pbs_no_requirements"].append(node_id)

            if node.is_leaf():
                orphaned["pbs_no_children_no_requirements"].append(node_id)

    # Check WBS packages
    pbs_ids = set(pbs.nodes.keys())
    all_dependencies: Set[str] = set()
    all_dependents: Set[str] = set()

    for wp_id, wp in wbs.work_packages.items():
        # Check PBS reference
        if wp.pbs_reference not in pbs_ids:
            orphaned["wbs_invalid_pbs_reference"].append(wp_id)

        # Track dependencies
        all_dependencies.update(wp.dependencies)
        if wp.dependencies:
            all_dependents.add(wp_id)

    # Find isolated WBS packages (no deps and not a dependency)
    for wp_id in wbs.work_packages:
        if wp_id not in all_dependencies and wp_id not in all_dependents:
            orphaned["wbs_isolated"].append(wp_id)

    return orphaned


def check_cross_artifact_consistency(
    artifacts: Dict[str, Any],
) -> ConsistencyReport:
    """Check consistency across all artifacts.

    Performs comprehensive consistency checks including:
    - ID reference validation
    - Hierarchy validation
    - Cross-reference validation
    - Completeness checks

    Args:
        artifacts: Dictionary containing artifacts:
            - requirements: RequirementsSet
            - pbs: ProductBreakdownStructure
            - wbs: WorkBreakdownStructure
            - dependency_graph: DependencyGraph (optional)

    Returns:
        ConsistencyReport with all identified issues.
    """
    issues: List[ConsistencyIssue] = []

    # Extract artifacts
    requirements = artifacts.get("requirements")
    pbs = artifacts.get("pbs")
    wbs = artifacts.get("wbs")
    dep_graph = artifacts.get("dependency_graph")

    # Basic existence checks
    if not requirements:
        issues.append(ConsistencyIssue(
            issue_type="missing_artifact",
            severity="error",
            message="Requirements set is missing",
            affected_artifacts=["requirements"],
        ))

    if not pbs:
        issues.append(ConsistencyIssue(
            issue_type="missing_artifact",
            severity="error",
            message="PBS is missing",
            affected_artifacts=["pbs"],
        ))

    if not wbs:
        issues.append(ConsistencyIssue(
            issue_type="missing_artifact",
            severity="error",
            message="WBS is missing",
            affected_artifacts=["wbs"],
        ))

    # If we have all core artifacts, do detailed checks
    if requirements and pbs and wbs:
        # Check requirement allocations
        pbs_ids = set(pbs.nodes.keys())
        for req in requirements:
            for target in req.allocation_target:
                if target not in pbs_ids:
                    issues.append(ConsistencyIssue(
                        issue_type="invalid_reference",
                        severity="error",
                        message=f"Requirement {req.id} allocated to non-existent PBS {target}",
                        affected_artifacts=["requirements", "pbs"],
                    ))

        # Check WBS-PBS consistency
        for wp_id, wp in wbs.work_packages.items():
            if wp.pbs_reference not in pbs_ids:
                issues.append(ConsistencyIssue(
                    issue_type="invalid_reference",
                    severity="error",
                    message=f"WBS {wp_id} references non-existent PBS {wp.pbs_reference}",
                    affected_artifacts=["wbs", "pbs"],
                ))

        # Check WBS dependency consistency
        wbs_ids = set(wbs.work_packages.keys())
        for wp_id, wp in wbs.work_packages.items():
            for dep_id in wp.dependencies:
                if dep_id not in wbs_ids:
                    issues.append(ConsistencyIssue(
                        issue_type="invalid_reference",
                        severity="error",
                        message=f"WBS {wp_id} depends on non-existent WBS {dep_id}",
                        affected_artifacts=["wbs"],
                    ))

        # Check mission name consistency
        mission_names = {
            requirements.mission_name,
            pbs.mission_name,
            wbs.mission_name,
        }
        if len(mission_names) > 1:
            issues.append(ConsistencyIssue(
                issue_type="inconsistent_metadata",
                severity="warning",
                message=f"Inconsistent mission names: {mission_names}",
                affected_artifacts=["requirements", "pbs", "wbs"],
            ))

        # Check traceability completeness
        trace_matrix = verify_traceability(requirements, pbs, wbs)
        incomplete = trace_matrix.get_incomplete_entries()
        if incomplete:
            for entry in incomplete:
                issues.append(ConsistencyIssue(
                    issue_type="incomplete_traceability",
                    severity="warning",
                    message=f"Requirement {entry.requirement_id} has incomplete traceability",
                    affected_artifacts=["requirements"],
                ))

        # Check orphaned elements
        orphaned = detect_orphaned_elements(pbs, wbs)
        for category, elements in orphaned.items():
            if elements and category == "wbs_invalid_pbs_reference":
                for elem in elements:
                    issues.append(ConsistencyIssue(
                        issue_type="orphaned_element",
                        severity="error",
                        message=f"Orphaned {category}: {elem}",
                        affected_artifacts=["pbs", "wbs"],
                    ))

    # Check dependency graph if present
    if dep_graph and wbs:
        wbs_ids = set(wbs.work_packages.keys())
        dep_node_ids = set(dep_graph.node_durations.keys())

        # Check all WBS packages are in dependency graph
        missing_in_graph = wbs_ids - dep_node_ids
        if missing_in_graph:
            issues.append(ConsistencyIssue(
                issue_type="missing_in_graph",
                severity="warning",
                message=f"WBS packages not in dependency graph: {list(missing_in_graph)[:5]}...",
                affected_artifacts=["wbs", "dependency_graph"],
            ))

        # Check for cycles
        if dep_graph.has_cycles():
            cycles = dep_graph.find_cycles()
            issues.append(ConsistencyIssue(
                issue_type="circular_dependency",
                severity="error",
                message=f"Dependency graph has cycles: {cycles[:3]}",
                affected_artifacts=["dependency_graph"],
            ))

    # Build statistics
    statistics = {
        "total_issues": len(issues),
        "errors": len([i for i in issues if i.severity == "error"]),
        "warnings": len([i for i in issues if i.severity == "warning"]),
    }

    return ConsistencyReport(
        is_consistent=statistics["errors"] == 0,
        issues=issues,
        statistics=statistics,
    )


def generate_consistency_summary(
    report: ConsistencyReport
) -> str:
    """Generate a human-readable summary of consistency check.

    Args:
        report: The consistency report to summarize.

    Returns:
        Formatted string summary.
    """
    lines = [
        "=" * 60,
        "CONSISTENCY CHECK SUMMARY",
        "=" * 60,
        f"Overall Status: {'CONSISTENT' if report.is_consistent else 'INCONSISTENT'}",
        f"Total Issues: {report.statistics.get('total_issues', 0)}",
        f"  Errors: {report.statistics.get('errors', 0)}",
        f"  Warnings: {report.statistics.get('warnings', 0)}",
        "",
    ]

    if report.issues:
        lines.append("ISSUES:")
        lines.append("-" * 40)

        for issue in report.issues:
            prefix = "ERROR" if issue.severity == "error" else "WARN"
            lines.append(f"[{prefix}] {issue.issue_type}")
            lines.append(f"       {issue.message}")
            if issue.affected_artifacts:
                lines.append(f"       Affects: {', '.join(issue.affected_artifacts)}")
            lines.append("")

    lines.append("=" * 60)

    return "\n".join(lines)
