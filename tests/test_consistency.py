"""Tests for consistency checking tools."""

import pytest

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from artifacts.requirements import (
    RequirementCategory,
    RequirementItem,
    RequirementsSet,
)
from artifacts.pbs import PBSNode, ProductBreakdownStructure
from artifacts.wbs import WorkPackage, WorkBreakdownStructure
from tools.validation import (
    validate_requirements_completeness,
    validate_pbs_coverage,
    validate_wbs_derivation,
)
from tools.consistency_checker import (
    check_cross_artifact_consistency,
    detect_orphaned_elements,
    verify_traceability,
)


@pytest.fixture
def sample_requirements():
    """Create sample requirements set."""
    req_set = RequirementsSet(mission_name="Test")

    req_set.add_requirement(RequirementItem(
        id="REQ-FN-001",
        category=RequirementCategory.FUNCTIONAL,
        statement="The system shall detect objects.",
        allocation_target=["PBS-1.1"],
        rationale="Core function",
        source="Mission",
    ))
    req_set.add_requirement(RequirementItem(
        id="REQ-PF-001",
        category=RequirementCategory.PERFORMANCE,
        statement="The system shall achieve 95% detection rate.",
        allocation_target=["PBS-1.1"],
        rationale="Performance target",
        source="Mission",
    ))

    return req_set


@pytest.fixture
def sample_pbs():
    """Create sample PBS."""
    pbs = ProductBreakdownStructure(mission_name="Test")

    pbs.add_node(PBSNode(
        id="PBS-0",
        name="System",
        level=0,
        children=["PBS-1"],
    ))
    pbs.add_node(PBSNode(
        id="PBS-1",
        name="Subsystem",
        parent_id="PBS-0",
        level=1,
        children=["PBS-1.1"],
    ))
    pbs.add_node(PBSNode(
        id="PBS-1.1",
        name="Component",
        parent_id="PBS-1",
        level=2,
        allocated_requirements=["REQ-FN-001", "REQ-PF-001"],
    ))

    return pbs


@pytest.fixture
def sample_wbs():
    """Create sample WBS."""
    wbs = WorkBreakdownStructure(mission_name="Test")

    wbs.add_work_package(WorkPackage(
        id="WBS-1.1.1",
        name="Design",
        pbs_reference="PBS-1.1",
        work_type="design",
    ))
    wbs.add_work_package(WorkPackage(
        id="WBS-1.1.2",
        name="Development",
        pbs_reference="PBS-1.1",
        work_type="development",
        dependencies=["WBS-1.1.1"],
    ))

    return wbs


class TestRequirementsValidation:
    """Tests for requirements validation."""

    def test_valid_requirements(self, sample_requirements):
        """Test validation of valid requirements."""
        result = validate_requirements_completeness(sample_requirements)
        assert result.is_valid
        assert len(result.errors) == 0

    def test_missing_category_warning(self):
        """Test that missing categories generate warnings."""
        req_set = RequirementsSet(mission_name="Test")
        req_set.add_requirement(RequirementItem(
            id="REQ-FN-001",
            category=RequirementCategory.FUNCTIONAL,
            statement="The system shall do X.",
        ))

        result = validate_requirements_completeness(
            req_set,
            required_categories=[RequirementCategory.FUNCTIONAL, RequirementCategory.PERFORMANCE],
        )
        assert not result.is_valid
        assert any("Missing required categories" in e for e in result.errors)


class TestPBSValidation:
    """Tests for PBS validation."""

    def test_valid_pbs_coverage(self, sample_pbs, sample_requirements):
        """Test validation of valid PBS coverage."""
        result = validate_pbs_coverage(sample_pbs, sample_requirements)
        assert result.is_valid
        assert len(result.errors) == 0

    def test_invalid_allocation_target(self):
        """Test detection of invalid allocation targets."""
        req_set = RequirementsSet(mission_name="Test")
        req_set.add_requirement(RequirementItem(
            id="REQ-FN-001",
            category=RequirementCategory.FUNCTIONAL,
            statement="The system shall do X.",
            allocation_target=["PBS-INVALID"],  # Non-existent
        ))

        pbs = ProductBreakdownStructure(mission_name="Test")
        pbs.add_node(PBSNode(id="PBS-1", name="Real Node"))

        result = validate_pbs_coverage(pbs, req_set)
        assert not result.is_valid
        assert any("non-existent PBS node" in e for e in result.errors)


class TestWBSValidation:
    """Tests for WBS validation."""

    def test_valid_wbs_derivation(self, sample_pbs, sample_wbs):
        """Test validation of valid WBS derivation."""
        result = validate_wbs_derivation(sample_wbs, sample_pbs)
        assert result.is_valid

    def test_invalid_pbs_reference(self, sample_pbs):
        """Test detection of invalid PBS references in WBS."""
        wbs = WorkBreakdownStructure(mission_name="Test")
        wbs.add_work_package(WorkPackage(
            id="WBS-1.1.1",
            name="Design",
            pbs_reference="PBS-INVALID",  # Non-existent
            work_type="design",
        ))

        result = validate_wbs_derivation(wbs, sample_pbs)
        assert not result.is_valid
        assert any("non-existent PBS node" in e for e in result.errors)


class TestConsistencyChecker:
    """Tests for cross-artifact consistency checking."""

    def test_consistent_artifacts(self, sample_requirements, sample_pbs, sample_wbs):
        """Test consistency check on valid artifacts."""
        artifacts = {
            "requirements": sample_requirements,
            "pbs": sample_pbs,
            "wbs": sample_wbs,
        }

        report = check_cross_artifact_consistency(artifacts)
        # May have warnings but no errors for valid data
        assert report.statistics["errors"] == 0

    def test_missing_artifact_detection(self):
        """Test detection of missing artifacts."""
        artifacts = {}  # Empty

        report = check_cross_artifact_consistency(artifacts)
        assert not report.is_consistent
        assert any(i.issue_type == "missing_artifact" for i in report.issues)


class TestTraceability:
    """Tests for traceability matrix."""

    def test_complete_traceability(self, sample_requirements, sample_pbs, sample_wbs):
        """Test traceability matrix with complete trace."""
        matrix = verify_traceability(sample_requirements, sample_pbs, sample_wbs)

        assert matrix.summary["total_requirements"] == 2
        # Both requirements should have complete traceability
        complete = matrix.get_complete_entries()
        assert len(complete) == 2

    def test_incomplete_traceability(self):
        """Test detection of incomplete traceability."""
        req_set = RequirementsSet(mission_name="Test")
        req_set.add_requirement(RequirementItem(
            id="REQ-FN-001",
            category=RequirementCategory.FUNCTIONAL,
            statement="The system shall do X.",
            allocation_target=[],  # Not allocated
        ))

        pbs = ProductBreakdownStructure(mission_name="Test")
        wbs = WorkBreakdownStructure(mission_name="Test")

        matrix = verify_traceability(req_set, pbs, wbs)

        incomplete = matrix.get_incomplete_entries()
        assert len(incomplete) == 1
        assert incomplete[0].requirement_id == "REQ-FN-001"


class TestOrphanedElements:
    """Tests for orphaned element detection."""

    def test_detect_orphaned_pbs(self, sample_pbs, sample_wbs):
        """Test detection of orphaned PBS nodes."""
        orphaned = detect_orphaned_elements(sample_pbs, sample_wbs)

        # PBS-0 and PBS-1 have no direct requirements
        assert len(orphaned["pbs_no_requirements"]) > 0

    def test_detect_orphaned_wbs(self, sample_pbs):
        """Test detection of WBS with invalid PBS reference."""
        wbs = WorkBreakdownStructure(mission_name="Test")
        wbs.add_work_package(WorkPackage(
            id="WBS-1.1.1",
            name="Orphan",
            pbs_reference="PBS-INVALID",
            work_type="design",
        ))

        orphaned = detect_orphaned_elements(sample_pbs, wbs)
        assert "WBS-1.1.1" in orphaned["wbs_invalid_pbs_reference"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
