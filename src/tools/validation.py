"""Validation tools for SE artifacts.

This module provides validation functions for checking
artifact completeness and correctness.
"""

import logging
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, Field

from artifacts.requirements import RequirementCategory, RequirementsSet
from artifacts.pbs import ProductBreakdownStructure
from artifacts.wbs import WorkBreakdownStructure


logger = logging.getLogger("astraeus.tools.validation")


class ValidationResult(BaseModel):
    """Result of a validation check.

    Attributes:
        is_valid: Whether validation passed.
        errors: List of error messages.
        warnings: List of warning messages.
        statistics: Validation statistics.
    """

    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    statistics: Dict[str, Any] = Field(default_factory=dict)


def validate_requirements_completeness(
    requirements: RequirementsSet,
    required_categories: Optional[List[RequirementCategory]] = None,
    min_requirements: int = 1,
) -> ValidationResult:
    """Validate requirements set completeness.

    Checks:
    - Minimum number of requirements met
    - Required categories are present
    - All requirements have proper shall statements
    - All requirements have verification methods
    - No orphaned references

    Args:
        requirements: The requirements set to validate.
        required_categories: Categories that must be present.
        min_requirements: Minimum number of requirements.

    Returns:
        ValidationResult with errors and warnings.
    """
    errors: List[str] = []
    warnings: List[str] = []
    statistics: Dict[str, Any] = {}

    # Check minimum requirements
    total_reqs = len(requirements)
    statistics["total_requirements"] = total_reqs

    if total_reqs < min_requirements:
        errors.append(
            f"Insufficient requirements: {total_reqs} < {min_requirements}"
        )

    # Check required categories
    if required_categories:
        present_categories = set(req.category for req in requirements)
        missing = set(required_categories) - present_categories
        if missing:
            errors.append(
                f"Missing required categories: {[c.value for c in missing]}"
            )

    # Validate individual requirements
    for req in requirements:
        # Check shall statement
        if "shall" not in req.statement.lower():
            warnings.append(
                f"{req.id}: Statement does not follow 'shall' format"
            )

        # Check rationale
        if not req.rationale:
            warnings.append(f"{req.id}: Missing rationale")

        # Check allocation
        if not req.allocation_target:
            warnings.append(f"{req.id}: Not allocated to any PBS element")

    # Check parent references
    req_ids = {req.id for req in requirements}
    for req in requirements:
        if req.parent_id and req.parent_id not in req_ids:
            errors.append(
                f"{req.id}: References non-existent parent {req.parent_id}"
            )

    # Calculate statistics
    statistics["by_category"] = requirements.count_by_category()
    statistics["unallocated_count"] = len(requirements.get_unallocated())
    statistics["root_count"] = len(requirements.get_root_requirements())

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        statistics={k: (v if not hasattr(v, 'items') else {str(kk): vv for kk, vv in v.items()}) for k, v in statistics.items()},
    )


def validate_pbs_coverage(
    pbs: ProductBreakdownStructure,
    requirements: RequirementsSet,
) -> ValidationResult:
    """Validate PBS coverage of requirements.

    Checks:
    - All requirements are allocated to existing PBS nodes
    - All leaf PBS nodes have at least one requirement
    - No orphaned PBS nodes (no requirements, no children)
    - PBS hierarchy is valid

    Args:
        pbs: The PBS to validate.
        requirements: The requirements set to check against.

    Returns:
        ValidationResult with coverage analysis.
    """
    errors: List[str] = []
    warnings: List[str] = []
    statistics: Dict[str, Any] = {}

    pbs_node_ids = set(pbs.nodes.keys())
    statistics["total_pbs_nodes"] = len(pbs_node_ids)
    statistics["total_leaves"] = len(pbs.get_leaves())

    # Check requirements allocation targets exist in PBS
    for req in requirements:
        for target in req.allocation_target:
            if target not in pbs_node_ids:
                errors.append(
                    f"Requirement {req.id} allocated to non-existent PBS node {target}"
                )

    # Check PBS nodes have allocated requirements
    allocated_to_pbs: Dict[str, List[str]] = {node_id: [] for node_id in pbs_node_ids}
    for req in requirements:
        for target in req.allocation_target:
            if target in allocated_to_pbs:
                allocated_to_pbs[target].append(req.id)

    # Check leaf nodes have requirements
    orphaned_leaves = []
    for leaf in pbs.get_leaves():
        if not leaf.allocated_requirements and not allocated_to_pbs.get(leaf.id):
            orphaned_leaves.append(leaf.id)
            warnings.append(
                f"PBS leaf node {leaf.id} ({leaf.name}) has no allocated requirements"
            )

    statistics["orphaned_leaves"] = orphaned_leaves
    statistics["coverage_percentage"] = (
        (len(pbs.get_leaves()) - len(orphaned_leaves)) / len(pbs.get_leaves()) * 100
        if pbs.get_leaves() else 100
    )

    # Validate hierarchy
    for node_id, node in pbs.nodes.items():
        if node.parent_id and node.parent_id not in pbs_node_ids:
            errors.append(
                f"PBS node {node_id} references non-existent parent {node.parent_id}"
            )

        for child_id in node.children:
            if child_id not in pbs_node_ids:
                errors.append(
                    f"PBS node {node_id} references non-existent child {child_id}"
                )

    # Check mission critical elements
    mission_critical = pbs.get_mission_critical()
    statistics["mission_critical_count"] = len(mission_critical)

    # Ensure mission critical elements have requirements
    for mc_node in mission_critical:
        if not mc_node.allocated_requirements and not allocated_to_pbs.get(mc_node.id):
            warnings.append(
                f"Mission-critical PBS node {mc_node.id} has no requirements"
            )

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        statistics=statistics,
    )


def validate_wbs_derivation(
    wbs: WorkBreakdownStructure,
    pbs: ProductBreakdownStructure,
) -> ValidationResult:
    """Validate WBS derivation from PBS.

    Checks:
    - All WBS work packages reference existing PBS nodes
    - All PBS leaf nodes have associated work packages
    - Work package dependencies reference existing packages
    - Standard work types are covered for each PBS element

    Args:
        wbs: The WBS to validate.
        pbs: The PBS to check against.

    Returns:
        ValidationResult with derivation analysis.
    """
    errors: List[str] = []
    warnings: List[str] = []
    statistics: Dict[str, Any] = {}

    pbs_node_ids = set(pbs.nodes.keys())
    wbs_wp_ids = set(wbs.work_packages.keys())

    statistics["total_work_packages"] = len(wbs_wp_ids)
    statistics["total_pbs_leaves"] = len(pbs.get_leaves())

    # Check PBS references exist
    referenced_pbs: Set[str] = set()
    for wp_id, wp in wbs.work_packages.items():
        if wp.pbs_reference not in pbs_node_ids:
            errors.append(
                f"Work package {wp_id} references non-existent PBS node {wp.pbs_reference}"
            )
        else:
            referenced_pbs.add(wp.pbs_reference)

    # Check PBS coverage
    pbs_leaves = {node.id for node in pbs.get_leaves()}
    uncovered_pbs = pbs_leaves - referenced_pbs

    if uncovered_pbs:
        for pbs_id in uncovered_pbs:
            warnings.append(
                f"PBS leaf node {pbs_id} has no associated work packages"
            )

    statistics["pbs_coverage_percentage"] = (
        len(pbs_leaves - uncovered_pbs) / len(pbs_leaves) * 100
        if pbs_leaves else 100
    )

    # Check dependencies
    for wp_id, wp in wbs.work_packages.items():
        for dep_id in wp.dependencies:
            if dep_id not in wbs_wp_ids:
                errors.append(
                    f"Work package {wp_id} depends on non-existent package {dep_id}"
                )

    # Check work type coverage
    standard_types = {"design", "development", "integration", "test"}
    for pbs_id in referenced_pbs:
        wp_types = {
            wp.work_type
            for wp in wbs.work_packages.values()
            if wp.pbs_reference == pbs_id
        }
        missing_types = standard_types - wp_types
        if missing_types and pbs_id in pbs_leaves:
            warnings.append(
                f"PBS node {pbs_id} missing work types: {missing_types}"
            )

    # Calculate statistics
    statistics["work_types"] = {}
    for wp in wbs.work_packages.values():
        statistics["work_types"][wp.work_type] = (
            statistics["work_types"].get(wp.work_type, 0) + 1
        )

    statistics["total_effort_hours"] = wbs.calculate_total_effort()
    statistics["total_duration_days"] = wbs.calculate_total_duration()

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        statistics=statistics,
    )


def validate_all_artifacts(
    requirements: RequirementsSet,
    pbs: ProductBreakdownStructure,
    wbs: WorkBreakdownStructure,
) -> Dict[str, ValidationResult]:
    """Run all validation checks on a complete artifact set.

    Args:
        requirements: The requirements set.
        pbs: The Product Breakdown Structure.
        wbs: The Work Breakdown Structure.

    Returns:
        Dictionary mapping validation name to result.
    """
    return {
        "requirements_completeness": validate_requirements_completeness(requirements),
        "pbs_coverage": validate_pbs_coverage(pbs, requirements),
        "wbs_derivation": validate_wbs_derivation(wbs, pbs),
    }
