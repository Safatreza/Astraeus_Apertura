"""Unit tests for agent implementations."""

import pytest

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agents.base_agent import BaseAgent, Task, Thought, Action, Tool, ToolResult
from agents.requirements_agent import RequirementsAgent
from agents.decomposition_agent import DecompositionAgent
from agents.scheduling_agent import SchedulingAgent


class TestBaseAgent:
    """Tests for base agent functionality."""

    def test_tool_registration(self):
        """Test registering tools with an agent."""
        class TestAgent(BaseAgent):
            def reason(self, context):
                return Thought(content="Test thought")

            def select_action(self, thought, context):
                return None

        tool = Tool(
            name="test_tool",
            description="A test tool",
            parameters_schema={"type": "object"},
            function=lambda: ToolResult(success=True, data="test"),
        )

        agent = TestAgent(name="TestAgent", tools=[tool])
        assert "test_tool" in agent.list_tools()
        assert agent.get_tool("test_tool") is not None

    def test_tool_execution(self):
        """Test executing a tool."""
        def add_numbers(a: int, b: int) -> ToolResult:
            return ToolResult(success=True, data=a + b)

        tool = Tool(
            name="add",
            description="Add two numbers",
            parameters_schema={
                "type": "object",
                "properties": {
                    "a": {"type": "integer"},
                    "b": {"type": "integer"},
                },
            },
            function=add_numbers,
        )

        result = tool.execute(a=2, b=3)
        assert result.success
        assert result.data == 5


class TestRequirementsAgent:
    """Tests for requirements agent."""

    def test_agent_initialization(self):
        """Test requirements agent initialization."""
        agent = RequirementsAgent()
        assert agent.name == "RequirementsAgent"
        assert len(agent.list_tools()) > 0

    def test_extract_requirements_tool(self):
        """Test requirements extraction tool."""
        agent = RequirementsAgent()

        mission_input = {
            "mission_name": "Test Mission",
            "primary_objective": "Test detection capability",
            "constraints": {
                "mass_budget_kg": 10,
                "power_budget_w": 30,
            },
            "payload_requirements": [
                "The system shall detect objects at 100km range",
            ],
        }

        tool = agent.get_tool("extract_requirements")
        result = tool.execute(mission_input=mission_input)

        assert result.success
        assert result.data["extracted_count"] > 0

    def test_classify_requirement_tool(self):
        """Test requirement classification."""
        agent = RequirementsAgent()

        tool = agent.get_tool("classify_requirement")

        # Test performance requirement
        result = tool.execute(statement="Detect objects at 500km range")
        assert result.success
        assert result.data["category"] == "performance"

        # Test interface requirement
        result = tool.execute(statement="Interface with S-band communication")
        assert result.success
        assert result.data["category"] == "interface"

    def test_full_requirements_workflow(self):
        """Test running the full requirements agent workflow."""
        agent = RequirementsAgent(max_iterations=5)

        task = Task(
            id="test-req-task",
            name="Extract Requirements",
            description="Extract requirements from mission inputs",
            inputs={
                "mission_input": {
                    "mission_name": "Test",
                    "primary_objective": "Debris detection",
                    "constraints": {"mass_budget_kg": 12},
                    "payload_requirements": ["Shall detect debris at 500km"],
                },
            },
        )

        result = agent.run(task)
        assert result.task_id == "test-req-task"
        # Check that agent produced some output
        assert len(result.thoughts) > 0


class TestDecompositionAgent:
    """Tests for decomposition agent."""

    def test_agent_initialization(self):
        """Test decomposition agent initialization."""
        agent = DecompositionAgent()
        assert agent.name == "DecompositionAgent"
        assert len(agent.list_tools()) > 0

    def test_initialize_pbs_tool(self):
        """Test PBS initialization tool."""
        agent = DecompositionAgent()

        tool = agent.get_tool("initialize_pbs")
        result = tool.execute(mission_name="Test Mission", use_template=True)

        assert result.success
        assert result.data["total_nodes"] > 0

    def test_derive_wbs_tool(self):
        """Test WBS derivation tool."""
        agent = DecompositionAgent()

        # First initialize PBS
        init_tool = agent.get_tool("initialize_pbs")
        init_tool.execute(mission_name="Test", use_template=True)

        # Then derive WBS
        derive_tool = agent.get_tool("derive_wbs_from_pbs")
        result = derive_tool.execute(work_types=["design", "test"])

        assert result.success
        assert result.data["total_work_packages"] > 0


class TestSchedulingAgent:
    """Tests for scheduling agent."""

    def test_agent_initialization(self):
        """Test scheduling agent initialization."""
        agent = SchedulingAgent()
        assert agent.name == "SchedulingAgent"
        assert len(agent.list_tools()) > 0

    def test_initialize_dependency_graph_tool(self):
        """Test dependency graph initialization."""
        agent = SchedulingAgent()

        wbs = {
            "mission_name": "Test",
            "version": "1.0",
            "work_packages": {
                "WBS-1.1": {
                    "id": "WBS-1.1",
                    "name": "Test WP 1",
                    "pbs_reference": "PBS-1",
                    "work_type": "design",
                    "duration_days": 10,
                    "dependencies": [],
                },
                "WBS-1.2": {
                    "id": "WBS-1.2",
                    "name": "Test WP 2",
                    "pbs_reference": "PBS-1",
                    "work_type": "test",
                    "duration_days": 5,
                    "dependencies": ["WBS-1.1"],
                },
            },
        }

        tool = agent.get_tool("initialize_dependency_graph")
        result = tool.execute(wbs=wbs)

        assert result.success
        assert result.data["total_nodes"] == 2

    def test_add_dependency_tool(self):
        """Test adding dependencies."""
        agent = SchedulingAgent()

        # Initialize with WBS
        wbs = {
            "mission_name": "Test",
            "work_packages": {
                "WBS-1.1": {
                    "id": "WBS-1.1",
                    "name": "WP 1",
                    "pbs_reference": "PBS-1",
                    "work_type": "design",
                },
                "WBS-1.2": {
                    "id": "WBS-1.2",
                    "name": "WP 2",
                    "pbs_reference": "PBS-1",
                    "work_type": "test",
                },
            },
        }

        init_tool = agent.get_tool("initialize_dependency_graph")
        init_tool.execute(wbs=wbs)

        # Add dependency
        dep_tool = agent.get_tool("add_dependency")
        result = dep_tool.execute(
            source_id="WBS-1.1",
            target_id="WBS-1.2",
            dependency_type="technical",
        )

        assert result.success


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
