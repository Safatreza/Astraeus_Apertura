"""Unit tests for artifact data models."""

import pytest
from datetime import date

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from artifacts.requirements import (
    RequirementCategory,
    RequirementItem,
    RequirementsSet,
    VerificationMethod,
)
from artifacts.pbs import PBSNode, ProductBreakdownStructure
from artifacts.wbs import WorkPackage, WorkBreakdownStructure
from artifacts.dependencies import Dependency, DependencyGraph, DependencyType
from artifacts.timeline import ScheduledTask, ExecutionTimeline


class TestRequirements:
    """Tests for requirements artifacts."""

    def test_requirement_item_creation(self):
        """Test creating a requirement item."""
        req = RequirementItem(
            id="REQ-FN-001",
            category=RequirementCategory.FUNCTIONAL,
            statement="The system shall detect debris objects.",
            verification_method=VerificationMethod.TEST,
        )
        assert req.id == "REQ-FN-001"
        assert req.category == RequirementCategory.FUNCTIONAL
        assert "shall" in req.statement

    def test_requirement_shall_validation(self):
        """Test that requirements must contain 'shall'."""
        with pytest.raises(ValueError, match="shall"):
            RequirementItem(
                id="REQ-FN-001",
                category=RequirementCategory.FUNCTIONAL,
                statement="The system detects debris objects.",  # Missing 'shall'
            )

    def test_requirements_set_unique_ids(self):
        """Test that requirements set enforces unique IDs."""
        req1 = RequirementItem(
            id="REQ-FN-001",
            category=RequirementCategory.FUNCTIONAL,
            statement="The system shall do X.",
        )
        req2 = RequirementItem(
            id="REQ-FN-001",  # Duplicate
            category=RequirementCategory.FUNCTIONAL,
            statement="The system shall do Y.",
        )
        with pytest.raises(ValueError, match="Duplicate"):
            RequirementsSet(
                mission_name="Test",
                requirements=[req1, req2],
            )

    def test_requirements_set_operations(self):
        """Test requirements set operations."""
        req_set = RequirementsSet(mission_name="Test")

        req1 = RequirementItem(
            id="REQ-FN-001",
            category=RequirementCategory.FUNCTIONAL,
            statement="The system shall do X.",
        )
        req_set.add_requirement(req1)

        assert len(req_set) == 1
        assert req_set.get_requirement("REQ-FN-001") == req1

    def test_requirements_categorization(self):
        """Test getting requirements by category."""
        req_set = RequirementsSet(mission_name="Test")

        req_set.add_requirement(RequirementItem(
            id="REQ-FN-001",
            category=RequirementCategory.FUNCTIONAL,
            statement="The system shall do X.",
        ))
        req_set.add_requirement(RequirementItem(
            id="REQ-PF-001",
            category=RequirementCategory.PERFORMANCE,
            statement="The system shall achieve Y.",
        ))

        functional = req_set.get_by_category(RequirementCategory.FUNCTIONAL)
        assert len(functional) == 1
        assert functional[0].id == "REQ-FN-001"


class TestPBS:
    """Tests for PBS artifacts."""

    def test_pbs_node_creation(self):
        """Test creating a PBS node."""
        node = PBSNode(
            id="PBS-1.1",
            name="Test Component",
            description="A test component",
            level=2,
        )
        assert node.id == "PBS-1.1"
        assert node.level == 2
        assert node.is_leaf()

    def test_pbs_structure_building(self):
        """Test building a PBS tree."""
        pbs = ProductBreakdownStructure(mission_name="Test")

        root = PBSNode(id="PBS-0", name="Root", level=0)
        child1 = PBSNode(id="PBS-1", name="Child 1", parent_id="PBS-0", level=1)
        child2 = PBSNode(id="PBS-2", name="Child 2", parent_id="PBS-0", level=1)

        pbs.add_node(root)
        pbs.add_node(child1)
        pbs.add_node(child2)

        assert len(pbs) == 3
        assert pbs.root_id == "PBS-0"
        assert len(pbs.get_children("PBS-0")) == 2

    def test_pbs_traversal(self):
        """Test PBS tree traversal."""
        pbs = ProductBreakdownStructure(mission_name="Test")

        pbs.add_node(PBSNode(id="PBS-0", name="Root", level=0, children=["PBS-1"]))
        pbs.add_node(PBSNode(id="PBS-1", name="Child", parent_id="PBS-0", level=1))

        nodes = list(pbs.traverse_preorder())
        assert len(nodes) == 2
        assert nodes[0].id == "PBS-0"
        assert nodes[1].id == "PBS-1"

    def test_pbs_mission_critical(self):
        """Test identifying mission-critical nodes."""
        pbs = ProductBreakdownStructure(mission_name="Test")

        pbs.add_node(PBSNode(id="PBS-0", name="Root", is_mission_critical=True))
        pbs.add_node(PBSNode(id="PBS-1", name="Non-critical", parent_id="PBS-0"))

        critical = pbs.get_mission_critical()
        assert len(critical) == 1
        assert critical[0].id == "PBS-0"


class TestWBS:
    """Tests for WBS artifacts."""

    def test_work_package_creation(self):
        """Test creating a work package."""
        wp = WorkPackage(
            id="WBS-1.1.1",
            name="Design Activity",
            pbs_reference="PBS-1.1",
            work_type="design",
            duration_days=20,
        )
        assert wp.id == "WBS-1.1.1"
        assert wp.work_type == "design"
        assert not wp.is_complete()

    def test_wbs_pbs_mapping(self):
        """Test WBS to PBS mapping."""
        wbs = WorkBreakdownStructure(mission_name="Test")

        wp1 = WorkPackage(
            id="WBS-1.1.1",
            name="Design",
            pbs_reference="PBS-1.1",
            work_type="design",
        )
        wp2 = WorkPackage(
            id="WBS-1.1.2",
            name="Development",
            pbs_reference="PBS-1.1",
            work_type="development",
        )

        wbs.add_work_package(wp1)
        wbs.add_work_package(wp2)

        packages = wbs.get_by_pbs("PBS-1.1")
        assert len(packages) == 2

    def test_wbs_by_work_type(self):
        """Test filtering by work type."""
        wbs = WorkBreakdownStructure(mission_name="Test")

        wbs.add_work_package(WorkPackage(
            id="WBS-1.1", name="Design", pbs_reference="PBS-1", work_type="design"
        ))
        wbs.add_work_package(WorkPackage(
            id="WBS-1.2", name="Test", pbs_reference="PBS-1", work_type="test"
        ))

        design_packages = wbs.get_by_work_type("design")
        assert len(design_packages) == 1


class TestDependencies:
    """Tests for dependency graph."""

    def test_dependency_creation(self):
        """Test creating a dependency."""
        dep = Dependency(
            source_id="WBS-1.1",
            target_id="WBS-1.2",
            dependency_type=DependencyType.TECHNICAL,
        )
        assert dep.source_id == "WBS-1.1"
        assert dep.target_id == "WBS-1.2"

    def test_dependency_self_loop_rejected(self):
        """Test that self-dependencies are rejected."""
        with pytest.raises(ValueError, match="Self-dependency"):
            Dependency(
                source_id="WBS-1.1",
                target_id="WBS-1.1",
            )

    def test_dependency_graph_cycle_detection(self):
        """Test cycle detection in dependency graph."""
        graph = DependencyGraph(
            mission_name="Test",
            node_durations={"WBS-1": 10, "WBS-2": 10, "WBS-3": 10},
        )

        graph.add_dependency(Dependency(source_id="WBS-1", target_id="WBS-2"))
        graph.add_dependency(Dependency(source_id="WBS-2", target_id="WBS-3"))

        # This would create a cycle
        with pytest.raises(ValueError, match="cycle"):
            graph.add_dependency(Dependency(source_id="WBS-3", target_id="WBS-1"))

    def test_dependency_graph_topological_sort(self):
        """Test topological sorting."""
        graph = DependencyGraph(
            mission_name="Test",
            node_durations={"WBS-1": 10, "WBS-2": 20, "WBS-3": 15},
        )

        graph.add_dependency(Dependency(source_id="WBS-1", target_id="WBS-2"))
        graph.add_dependency(Dependency(source_id="WBS-2", target_id="WBS-3"))

        order = graph.get_topological_order()
        assert order.index("WBS-1") < order.index("WBS-2")
        assert order.index("WBS-2") < order.index("WBS-3")

    def test_critical_path_calculation(self):
        """Test critical path calculation."""
        graph = DependencyGraph(
            mission_name="Test",
            node_durations={"WBS-1": 10, "WBS-2": 20, "WBS-3": 5},
        )

        graph.add_dependency(Dependency(source_id="WBS-1", target_id="WBS-2"))
        graph.add_dependency(Dependency(source_id="WBS-1", target_id="WBS-3"))

        critical_path = graph.find_critical_path()
        # WBS-1 -> WBS-2 is the critical path (10 + 20 = 30)
        # WBS-1 -> WBS-3 is shorter (10 + 5 = 15)
        assert "WBS-1" in critical_path
        assert "WBS-2" in critical_path


class TestTimeline:
    """Tests for timeline artifacts."""

    def test_scheduled_task_creation(self):
        """Test creating a scheduled task."""
        task = ScheduledTask(
            work_package_id="WBS-1.1",
            name="Design Task",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 15),
            duration_days=10,
        )
        assert task.work_package_id == "WBS-1.1"
        assert task.duration_days == 10

    def test_scheduled_task_overlap_detection(self):
        """Test overlap detection between tasks."""
        task1 = ScheduledTask(
            work_package_id="WBS-1",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 10),
            duration_days=10,
        )
        task2 = ScheduledTask(
            work_package_id="WBS-2",
            start_date=date(2026, 1, 5),
            end_date=date(2026, 1, 15),
            duration_days=10,
        )
        task3 = ScheduledTask(
            work_package_id="WBS-3",
            start_date=date(2026, 1, 20),
            end_date=date(2026, 1, 30),
            duration_days=10,
        )

        assert task1.overlaps_with(task2)
        assert not task1.overlaps_with(task3)

    def test_timeline_from_dependency_graph(self):
        """Test generating timeline from dependency graph."""
        graph = DependencyGraph(
            mission_name="Test",
            node_durations={"WBS-1": 10, "WBS-2": 15},
        )
        graph.add_dependency(Dependency(source_id="WBS-1", target_id="WBS-2"))

        timeline = ExecutionTimeline.from_dependency_graph(
            dependency_graph=graph,
            work_package_names={"WBS-1": "Task 1", "WBS-2": "Task 2"},
            start_date=date(2026, 1, 1),
            work_days_per_week=7,  # No weekends for simplicity
        )

        assert len(timeline) == 2
        assert timeline.total_duration_days == 25  # 10 + 15


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
