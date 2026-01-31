"""Work Breakdown Structure (WBS) artifact models.

This module defines the data structures for representing work packages
derived from the PBS, with support for effort estimation and dependencies.
"""

import json
from typing import Any, Dict, Iterator, List, Optional, Set

from pydantic import BaseModel, Field, field_validator, model_validator


class WorkPackage(BaseModel):
    """A work package in the Work Breakdown Structure.

    Represents a unit of work required to develop, integrate, test,
    or deliver a PBS element.

    Attributes:
        id: Unique identifier (e.g., "WBS-1.1.1.1").
        name: Short descriptive name.
        description: Detailed description of the work.
        pbs_reference: ID of the PBS element this derives from.
        work_type: Type of work (design, development, integration, test, etc.).
        deliverables: List of deliverable items.
        duration_days: Estimated duration in working days.
        effort_hours: Estimated effort in person-hours.
        dependencies: IDs of work packages this depends on.
        responsible_team: Team or role responsible.
        status: Current status of the work package.
        completion_percent: Percentage complete (0-100).
        cost_estimate: Estimated cost in mission currency.
    """

    id: str = Field(..., pattern=r"^WBS-[0-9.]+$")
    name: str = Field(..., min_length=1, max_length=150)
    description: str = Field(default="")
    pbs_reference: str = Field(..., pattern=r"^PBS-[0-9.]+$")
    work_type: str = Field(default="development")
    deliverables: List[str] = Field(default_factory=list)
    duration_days: Optional[int] = Field(default=None, ge=1)
    effort_hours: Optional[float] = Field(default=None, ge=0)
    dependencies: List[str] = Field(default_factory=list)
    responsible_team: Optional[str] = None
    status: str = Field(default="not_started")
    completion_percent: int = Field(default=0, ge=0, le=100)
    cost_estimate: Optional[float] = Field(default=None, ge=0)

    @field_validator("work_type")
    @classmethod
    def validate_work_type(cls, v: str) -> str:
        """Validate work type is a known category."""
        valid_types = {
            "design",
            "development",
            "procurement",
            "integration",
            "test",
            "verification",
            "documentation",
            "review",
            "management",
        }
        if v.lower() not in valid_types:
            # Allow custom types but normalize
            return v.lower()
        return v.lower()

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate status is a known value."""
        valid_statuses = {
            "not_started",
            "in_progress",
            "completed",
            "blocked",
            "on_hold",
            "cancelled",
        }
        if v.lower() not in valid_statuses:
            raise ValueError(f"Invalid status: {v}. Must be one of {valid_statuses}")
        return v.lower()

    def get_level(self) -> int:
        """Get the level from the WBS ID structure."""
        parts = self.id.replace("WBS-", "").split(".")
        return len(parts) - 1

    def is_complete(self) -> bool:
        """Check if work package is completed."""
        return self.status == "completed" or self.completion_percent == 100

    def is_blocked(self) -> bool:
        """Check if work package is blocked."""
        return self.status == "blocked"

    def has_dependencies(self) -> bool:
        """Check if work package has dependencies."""
        return len(self.dependencies) > 0


class WorkBreakdownStructure(BaseModel):
    """Complete Work Breakdown Structure.

    Represents the full set of work packages derived from the PBS,
    organized hierarchically with support for dependency tracking.

    Attributes:
        mission_name: Name of the mission.
        version: WBS version identifier.
        work_packages: Dictionary mapping WBS IDs to WorkPackage objects.
        pbs_to_wbs_mapping: Mapping from PBS IDs to associated WBS IDs.
    """

    mission_name: str
    version: str = Field(default="1.0")
    work_packages: Dict[str, WorkPackage] = Field(default_factory=dict)
    pbs_to_wbs_mapping: Dict[str, List[str]] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_dependencies(self) -> "WorkBreakdownStructure":
        """Validate all dependency references exist."""
        wp_ids = set(self.work_packages.keys())
        for wp_id, wp in self.work_packages.items():
            for dep_id in wp.dependencies:
                if dep_id not in wp_ids:
                    raise ValueError(
                        f"Work package {wp_id} depends on non-existent {dep_id}"
                    )
        return self

    @model_validator(mode="after")
    def build_pbs_mapping(self) -> "WorkBreakdownStructure":
        """Build the PBS to WBS mapping from work packages."""
        mapping: Dict[str, List[str]] = {}
        for wp_id, wp in self.work_packages.items():
            pbs_ref = wp.pbs_reference
            if pbs_ref not in mapping:
                mapping[pbs_ref] = []
            mapping[pbs_ref].append(wp_id)
        self.pbs_to_wbs_mapping = mapping
        return self

    def add_work_package(self, work_package: WorkPackage) -> None:
        """Add a work package to the structure."""
        if work_package.id in self.work_packages:
            raise ValueError(f"Work package {work_package.id} already exists")

        self.work_packages[work_package.id] = work_package

        # Update PBS mapping
        pbs_ref = work_package.pbs_reference
        if pbs_ref not in self.pbs_to_wbs_mapping:
            self.pbs_to_wbs_mapping[pbs_ref] = []
        self.pbs_to_wbs_mapping[pbs_ref].append(work_package.id)

    def get_work_package(self, wp_id: str) -> Optional[WorkPackage]:
        """Get a work package by ID."""
        return self.work_packages.get(wp_id)

    def get_by_pbs(self, pbs_id: str) -> List[WorkPackage]:
        """Get all work packages derived from a PBS element."""
        wp_ids = self.pbs_to_wbs_mapping.get(pbs_id, [])
        return [self.work_packages[wp_id] for wp_id in wp_ids if wp_id in self.work_packages]

    def get_by_work_type(self, work_type: str) -> List[WorkPackage]:
        """Get all work packages of a specific type."""
        return [
            wp for wp in self.work_packages.values()
            if wp.work_type == work_type.lower()
        ]

    def get_by_status(self, status: str) -> List[WorkPackage]:
        """Get all work packages with a specific status."""
        return [
            wp for wp in self.work_packages.values()
            if wp.status == status.lower()
        ]

    def get_blocked(self) -> List[WorkPackage]:
        """Get all blocked work packages."""
        return self.get_by_status("blocked")

    def get_in_progress(self) -> List[WorkPackage]:
        """Get all in-progress work packages."""
        return self.get_by_status("in_progress")

    def get_completed(self) -> List[WorkPackage]:
        """Get all completed work packages."""
        return self.get_by_status("completed")

    def get_ready_to_start(self) -> List[WorkPackage]:
        """Get work packages with all dependencies satisfied."""
        ready: List[WorkPackage] = []
        for wp in self.work_packages.values():
            if wp.status != "not_started":
                continue

            all_deps_complete = all(
                self.work_packages.get(dep_id, WorkPackage(
                    id="WBS-0", name="", pbs_reference="PBS-0"
                )).is_complete()
                for dep_id in wp.dependencies
            )

            if all_deps_complete:
                ready.append(wp)

        return ready

    def get_dependents(self, wp_id: str) -> List[WorkPackage]:
        """Get work packages that depend on the given one."""
        return [
            wp for wp in self.work_packages.values()
            if wp_id in wp.dependencies
        ]

    def get_dependency_chain(self, wp_id: str, visited: Optional[Set[str]] = None) -> List[str]:
        """Get the full chain of dependencies (recursive)."""
        if visited is None:
            visited = set()

        if wp_id in visited:
            return []  # Cycle detected

        visited.add(wp_id)
        wp = self.work_packages.get(wp_id)
        if not wp:
            return []

        chain = list(wp.dependencies)
        for dep_id in wp.dependencies:
            chain.extend(self.get_dependency_chain(dep_id, visited))

        return chain

    def calculate_total_effort(self) -> float:
        """Calculate total estimated effort hours."""
        return sum(
            wp.effort_hours or 0
            for wp in self.work_packages.values()
        )

    def calculate_total_duration(self) -> int:
        """Calculate total estimated duration (not accounting for parallelism)."""
        return sum(
            wp.duration_days or 0
            for wp in self.work_packages.values()
        )

    def calculate_total_cost(self) -> float:
        """Calculate total estimated cost."""
        return sum(
            wp.cost_estimate or 0
            for wp in self.work_packages.values()
        )

    def calculate_completion_percentage(self) -> float:
        """Calculate overall completion percentage."""
        if not self.work_packages:
            return 0.0
        total_completion = sum(wp.completion_percent for wp in self.work_packages.values())
        return total_completion / len(self.work_packages)

    def validate_against_pbs(self, pbs_node_ids: List[str]) -> Dict[str, Any]:
        """Validate WBS coverage against PBS.

        Args:
            pbs_node_ids: List of PBS node IDs to check coverage for.

        Returns:
            Dictionary with validation results.
        """
        covered_pbs = set(self.pbs_to_wbs_mapping.keys())
        required_pbs = set(pbs_node_ids)

        uncovered = required_pbs - covered_pbs
        orphaned = covered_pbs - required_pbs

        return {
            "is_complete": len(uncovered) == 0,
            "uncovered_pbs_elements": list(uncovered),
            "orphaned_wbs_references": list(orphaned),
            "total_work_packages": len(self.work_packages),
            "coverage_percentage": (
                len(covered_pbs & required_pbs) / len(required_pbs) * 100
                if required_pbs else 100
            ),
        }

    def derive_from_pbs_node(
        self,
        pbs_id: str,
        pbs_name: str,
        work_types: Optional[List[str]] = None
    ) -> List[WorkPackage]:
        """Derive work packages from a PBS node.

        Default work types for each PBS element:
        - Design
        - Development/Procurement
        - Integration
        - Test

        Args:
            pbs_id: PBS node ID to derive from.
            pbs_name: PBS node name for work package naming.
            work_types: Optional list of work types to generate.

        Returns:
            List of generated work packages.
        """
        if work_types is None:
            work_types = ["design", "development", "integration", "test"]

        wbs_base = pbs_id.replace("PBS-", "WBS-")
        work_packages: List[WorkPackage] = []

        for idx, work_type in enumerate(work_types, start=1):
            wp = WorkPackage(
                id=f"{wbs_base}.{idx}",
                name=f"{pbs_name} - {work_type.title()}",
                description=f"{work_type.title()} activities for {pbs_name}",
                pbs_reference=pbs_id,
                work_type=work_type,
                deliverables=[f"{pbs_name} {work_type} deliverable"],
            )
            work_packages.append(wp)
            self.add_work_package(wp)

        return work_packages

    def export_to_dict(self) -> Dict[str, Any]:
        """Export WBS to dictionary format."""
        return {
            "mission_name": self.mission_name,
            "version": self.version,
            "work_packages": {
                wp_id: wp.model_dump()
                for wp_id, wp in self.work_packages.items()
            },
            "pbs_to_wbs_mapping": self.pbs_to_wbs_mapping,
        }

    def export_to_json(self, indent: int = 2) -> str:
        """Export WBS to JSON string."""
        return json.dumps(self.export_to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkBreakdownStructure":
        """Create WBS from dictionary."""
        work_packages = {
            wp_id: WorkPackage(**wp_data)
            for wp_id, wp_data in data.get("work_packages", {}).items()
        }
        return cls(
            mission_name=data["mission_name"],
            version=data.get("version", "1.0"),
            work_packages=work_packages,
        )

    def __len__(self) -> int:
        """Return the number of work packages."""
        return len(self.work_packages)

    def __iter__(self) -> Iterator[WorkPackage]:
        """Iterate over work packages."""
        return iter(self.work_packages.values())

    def __contains__(self, wp_id: str) -> bool:
        """Check if a work package ID exists."""
        return wp_id in self.work_packages
