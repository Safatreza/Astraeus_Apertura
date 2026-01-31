"""Requirements artifact models.

This module defines the data structures for capturing and managing
system requirements in the ATLAS-III mission planning framework.
"""

from enum import Enum
from typing import Dict, List, Optional, Set

from pydantic import BaseModel, Field, field_validator, model_validator


class RequirementCategory(str, Enum):
    """Categories of system requirements."""

    FUNCTIONAL = "functional"
    PERFORMANCE = "performance"
    INTERFACE = "interface"
    ENVIRONMENTAL = "environmental"
    OPERATIONAL = "operational"
    CONSTRAINT = "constraint"


class VerificationMethod(str, Enum):
    """Methods for verifying requirements."""

    ANALYSIS = "analysis"
    INSPECTION = "inspection"
    DEMONSTRATION = "demonstration"
    TEST = "test"


class RequirementItem(BaseModel):
    """A single system requirement.

    Attributes:
        id: Unique identifier (e.g., "REQ-001", "REQ-PL-001").
        category: Classification of the requirement type.
        statement: The requirement text in "shall" format.
        rationale: Justification for the requirement.
        verification_method: How the requirement will be verified.
        allocation_target: PBS element(s) this requirement allocates to.
        parent_id: Parent requirement ID for derived requirements.
        priority: Requirement priority (1=highest, 3=lowest).
        status: Current status of the requirement.
        source: Origin of the requirement (e.g., "Mission Objectives").
    """

    id: str = Field(..., pattern=r"^REQ-[A-Z0-9-]+$")
    category: RequirementCategory
    statement: str = Field(..., min_length=10)
    rationale: Optional[str] = None
    verification_method: VerificationMethod = VerificationMethod.TEST
    allocation_target: List[str] = Field(default_factory=list)
    parent_id: Optional[str] = Field(default=None, pattern=r"^REQ-[A-Z0-9-]+$")
    priority: int = Field(default=2, ge=1, le=3)
    status: str = Field(default="draft")
    source: Optional[str] = None

    @field_validator("statement")
    @classmethod
    def validate_shall_statement(cls, v: str) -> str:
        """Ensure requirement uses 'shall' format."""
        if "shall" not in v.lower():
            raise ValueError("Requirement statement must use 'shall' format")
        return v

    def is_allocated(self) -> bool:
        """Check if requirement is allocated to at least one PBS element."""
        return len(self.allocation_target) > 0

    def derives_from(self, parent: "RequirementItem") -> bool:
        """Check if this requirement derives from another."""
        return self.parent_id == parent.id


class RequirementsSet(BaseModel):
    """Collection of requirements with validation.

    Attributes:
        mission_name: Name of the mission these requirements apply to.
        version: Version of the requirements set.
        requirements: List of individual requirements.
    """

    mission_name: str
    version: str = Field(default="1.0")
    requirements: List[RequirementItem] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_unique_ids(self) -> "RequirementsSet":
        """Ensure all requirement IDs are unique."""
        ids = [req.id for req in self.requirements]
        if len(ids) != len(set(ids)):
            duplicates = [id for id in ids if ids.count(id) > 1]
            raise ValueError(f"Duplicate requirement IDs found: {set(duplicates)}")
        return self

    @model_validator(mode="after")
    def validate_parent_references(self) -> "RequirementsSet":
        """Ensure all parent_id references exist."""
        ids = {req.id for req in self.requirements}
        for req in self.requirements:
            if req.parent_id and req.parent_id not in ids:
                raise ValueError(
                    f"Requirement {req.id} references non-existent parent {req.parent_id}"
                )
        return self

    def add_requirement(self, requirement: RequirementItem) -> None:
        """Add a requirement to the set."""
        existing_ids = {req.id for req in self.requirements}
        if requirement.id in existing_ids:
            raise ValueError(f"Requirement {requirement.id} already exists")
        self.requirements.append(requirement)

    def get_requirement(self, req_id: str) -> Optional[RequirementItem]:
        """Get a requirement by ID."""
        for req in self.requirements:
            if req.id == req_id:
                return req
        return None

    def get_by_category(self, category: RequirementCategory) -> List[RequirementItem]:
        """Get all requirements of a specific category."""
        return [req for req in self.requirements if req.category == category]

    def get_unallocated(self) -> List[RequirementItem]:
        """Get requirements not yet allocated to PBS elements."""
        return [req for req in self.requirements if not req.is_allocated()]

    def get_children(self, parent_id: str) -> List[RequirementItem]:
        """Get all requirements derived from a parent."""
        return [req for req in self.requirements if req.parent_id == parent_id]

    def get_root_requirements(self) -> List[RequirementItem]:
        """Get top-level requirements (no parent)."""
        return [req for req in self.requirements if req.parent_id is None]

    def get_allocation_targets(self) -> Set[str]:
        """Get all unique PBS element IDs referenced in allocations."""
        targets: Set[str] = set()
        for req in self.requirements:
            targets.update(req.allocation_target)
        return targets

    def validate_completeness(self) -> Dict[str, List[str]]:
        """Check for completeness issues.

        Returns:
            Dictionary of issue types to lists of affected requirement IDs.
        """
        issues: Dict[str, List[str]] = {
            "missing_rationale": [],
            "unallocated": [],
            "missing_source": [],
        }

        for req in self.requirements:
            if not req.rationale:
                issues["missing_rationale"].append(req.id)
            if not req.is_allocated():
                issues["unallocated"].append(req.id)
            if not req.source:
                issues["missing_source"].append(req.id)

        return {k: v for k, v in issues.items() if v}

    def to_traceability_dict(self) -> Dict[str, List[str]]:
        """Create requirement-to-PBS traceability mapping."""
        return {req.id: req.allocation_target for req in self.requirements}

    def count_by_category(self) -> Dict[RequirementCategory, int]:
        """Count requirements by category."""
        counts: Dict[RequirementCategory, int] = {}
        for category in RequirementCategory:
            counts[category] = len(self.get_by_category(category))
        return counts

    def __len__(self) -> int:
        """Return the number of requirements."""
        return len(self.requirements)

    def __iter__(self):
        """Iterate over requirements."""
        return iter(self.requirements)
