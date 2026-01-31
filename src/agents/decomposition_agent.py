"""Decomposition Agent for generating PBS and WBS.

This agent handles the decomposition stage of the systems engineering
pipeline: converting requirements into Product and Work Breakdown Structures.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from agents.base_agent import (
    Action,
    BaseAgent,
    Observation,
    Task,
    Thought,
    Tool,
    ToolResult,
)
from artifacts.pbs import PBSNode, ProductBreakdownStructure
from artifacts.requirements import RequirementsSet
from artifacts.wbs import WorkBreakdownStructure, WorkPackage


logger = logging.getLogger("astraeus.agents.decomposition")


# Default PBS template for radar payload missions
RADAR_PAYLOAD_PBS_TEMPLATE = {
    "PBS-0": {
        "name": "Space Segment",
        "description": "Complete space segment including payload and bus",
        "level": 0,
        "children": ["PBS-1", "PBS-2"],
    },
    "PBS-1": {
        "name": "Radar Payload",
        "description": "Active radar payload for debris detection",
        "level": 1,
        "children": ["PBS-1.1", "PBS-1.2", "PBS-1.3"],
        "is_mission_critical": True,
    },
    "PBS-1.1": {
        "name": "Payload Sensor",
        "description": "Radar sensor assembly",
        "level": 2,
        "children": ["PBS-1.1.1", "PBS-1.1.2"],
        "is_mission_critical": True,
    },
    "PBS-1.1.1": {
        "name": "Antenna",
        "description": "Radar antenna array",
        "level": 3,
        "is_mission_critical": True,
    },
    "PBS-1.1.2": {
        "name": "RF Front-End",
        "description": "Radio frequency front-end electronics",
        "level": 3,
        "is_mission_critical": True,
    },
    "PBS-1.2": {
        "name": "Payload Processing & Control",
        "description": "Signal processing and control electronics",
        "level": 2,
        "children": ["PBS-1.2.1", "PBS-1.2.2", "PBS-1.2.3"],
        "is_mission_critical": True,
    },
    "PBS-1.2.1": {
        "name": "Payload OBC",
        "description": "Payload onboard computer",
        "level": 3,
        "is_mission_critical": True,
    },
    "PBS-1.2.2": {
        "name": "SDR/ADC",
        "description": "Software-defined radio and analog-to-digital converter",
        "level": 3,
        "is_mission_critical": True,
    },
    "PBS-1.2.3": {
        "name": "Data Handling & Storage",
        "description": "Data handling and mass storage",
        "level": 3,
    },
    "PBS-1.3": {
        "name": "Payload Support Interfaces",
        "description": "Interfaces between payload and spacecraft bus",
        "level": 2,
        "children": ["PBS-1.3.1", "PBS-1.3.2", "PBS-1.3.3", "PBS-1.3.4"],
    },
    "PBS-1.3.1": {
        "name": "Mechanical Interface",
        "description": "Mechanical mounting and structural interface",
        "level": 3,
    },
    "PBS-1.3.2": {
        "name": "Electrical Interface",
        "description": "Power and electrical interfaces",
        "level": 3,
    },
    "PBS-1.3.3": {
        "name": "Data Interface",
        "description": "Data communication interfaces",
        "level": 3,
    },
    "PBS-1.3.4": {
        "name": "Thermal Interface",
        "description": "Thermal management interface",
        "level": 3,
    },
    "PBS-2": {
        "name": "Spacecraft Bus",
        "description": "Spacecraft bus/platform",
        "level": 1,
        "children": ["PBS-2.1", "PBS-2.2", "PBS-2.3", "PBS-2.4", "PBS-2.5", "PBS-2.6"],
    },
    "PBS-2.1": {
        "name": "Structure",
        "description": "Primary and secondary structure",
        "level": 2,
    },
    "PBS-2.2": {
        "name": "Power Subsystem",
        "description": "Electrical power system",
        "level": 2,
        "is_mission_critical": True,
    },
    "PBS-2.3": {
        "name": "ADCS",
        "description": "Attitude determination and control system",
        "level": 2,
        "is_mission_critical": True,
    },
    "PBS-2.4": {
        "name": "TT&C",
        "description": "Telemetry, tracking, and command",
        "level": 2,
        "is_mission_critical": True,
    },
    "PBS-2.5": {
        "name": "OBC",
        "description": "Onboard computer/command and data handling",
        "level": 2,
        "is_mission_critical": True,
    },
    "PBS-2.6": {
        "name": "Thermal Control",
        "description": "Thermal control system",
        "level": 2,
    },
}


class DecompositionAgent(BaseAgent):
    """Agent for generating PBS and WBS from requirements.

    Capabilities:
    - Generate PBS from mission requirements
    - Derive WBS from PBS elements
    - Validate decomposition completeness
    - Apply mission-critical inclusion rules

    Tools:
    - create_pbs_node: Create a new PBS element
    - derive_wbs_from_pbs: Generate WBS from PBS
    - validate_decomposition: Check completeness
    - allocate_requirements: Allocate requirements to PBS
    """

    def __init__(
        self,
        name: str = "DecompositionAgent",
        max_iterations: int = 15,
        trace_enabled: bool = True,
    ):
        """Initialize the decomposition agent."""
        tools = self._create_tools()
        super().__init__(
            name=name,
            tools=tools,
            max_iterations=max_iterations,
            trace_enabled=trace_enabled,
        )

        self._pbs: Optional[ProductBreakdownStructure] = None
        self._wbs: Optional[WorkBreakdownStructure] = None

    def _create_tools(self) -> List[Tool]:
        """Create the agent's tools."""
        return [
            Tool(
                name="initialize_pbs",
                description="Initialize PBS structure from template",
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "mission_name": {"type": "string"},
                        "use_template": {"type": "boolean"},
                    },
                    "required": ["mission_name"],
                },
                function=self._initialize_pbs,
            ),
            Tool(
                name="create_pbs_node",
                description="Create a new PBS node",
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                        "parent_id": {"type": "string"},
                        "is_mission_critical": {"type": "boolean"},
                    },
                    "required": ["id", "name"],
                },
                function=self._create_pbs_node,
            ),
            Tool(
                name="allocate_requirements",
                description="Allocate requirements to PBS elements",
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "requirements_set": {"type": "object"},
                    },
                    "required": ["requirements_set"],
                },
                function=self._allocate_requirements,
            ),
            Tool(
                name="derive_wbs_from_pbs",
                description="Derive WBS work packages from PBS",
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "work_types": {"type": "array"},
                    },
                },
                function=self._derive_wbs_from_pbs,
            ),
            Tool(
                name="validate_decomposition",
                description="Validate PBS and WBS completeness",
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "requirements_ids": {"type": "array"},
                    },
                },
                function=self._validate_decomposition,
            ),
            Tool(
                name="finalize_decomposition",
                description="Finalize and return PBS and WBS",
                parameters_schema={
                    "type": "object",
                    "properties": {},
                },
                function=self._finalize_decomposition,
            ),
        ]

    def _initialize_pbs(
        self,
        mission_name: str,
        use_template: bool = True
    ) -> ToolResult:
        """Initialize PBS structure."""
        try:
            self._pbs = ProductBreakdownStructure(mission_name=mission_name)

            if use_template:
                # Build PBS from template
                for pbs_id, template in RADAR_PAYLOAD_PBS_TEMPLATE.items():
                    # Determine parent_id from structure
                    parent_id = None
                    if "." in pbs_id.replace("PBS-", ""):
                        parts = pbs_id.replace("PBS-", "").rsplit(".", 1)
                        parent_id = f"PBS-{parts[0]}"

                    node = PBSNode(
                        id=pbs_id,
                        name=template["name"],
                        description=template.get("description", ""),
                        parent_id=parent_id,
                        level=template.get("level", 0),
                        children=template.get("children", []),
                        is_mission_critical=template.get("is_mission_critical", False),
                    )
                    self._pbs.nodes[pbs_id] = node

                self._pbs.root_id = "PBS-0"

            return ToolResult(
                success=True,
                data={
                    "mission_name": mission_name,
                    "total_nodes": len(self._pbs.nodes),
                    "template_used": use_template,
                },
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def _create_pbs_node(
        self,
        id: str,
        name: str,
        description: str = "",
        parent_id: Optional[str] = None,
        is_mission_critical: bool = False,
    ) -> ToolResult:
        """Create a new PBS node."""
        try:
            if self._pbs is None:
                return ToolResult(
                    success=False,
                    error="PBS not initialized. Run initialize_pbs first.",
                )

            # Determine level from parent
            level = 0
            if parent_id and parent_id in self._pbs.nodes:
                level = self._pbs.nodes[parent_id].level + 1

            node = PBSNode(
                id=id,
                name=name,
                description=description,
                parent_id=parent_id,
                level=level,
                is_mission_critical=is_mission_critical,
            )

            self._pbs.add_node(node)

            return ToolResult(
                success=True,
                data={"node_id": id, "level": level},
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def _allocate_requirements(
        self,
        requirements_set: Dict[str, Any]
    ) -> ToolResult:
        """Allocate requirements to PBS elements."""
        try:
            if self._pbs is None:
                return ToolResult(
                    success=False,
                    error="PBS not initialized.",
                )

            # Parse requirements set
            reqs = RequirementsSet(**requirements_set)
            allocations = []

            # Simple allocation strategy based on keywords
            for req in reqs.requirements:
                statement = req.statement.lower()
                allocated_to = []

                # Radar/detection -> Payload Sensor
                if any(kw in statement for kw in ["radar", "detect", "debris", "sensor"]):
                    allocated_to.extend(["PBS-1.1", "PBS-1.1.1", "PBS-1.1.2"])

                # Processing/signal -> Payload Processing
                if any(kw in statement for kw in ["process", "signal", "data", "storage"]):
                    allocated_to.extend(["PBS-1.2", "PBS-1.2.1", "PBS-1.2.2", "PBS-1.2.3"])

                # Downlink/communication -> TT&C
                if any(kw in statement for kw in ["downlink", "uplink", "communication", "telemetry"]):
                    allocated_to.append("PBS-2.4")

                # Power -> Power Subsystem
                if any(kw in statement for kw in ["power", "watt", "energy"]):
                    allocated_to.append("PBS-2.2")

                # Mass/structure -> Structure
                if any(kw in statement for kw in ["mass", "kg", "structure", "mount"]):
                    allocated_to.append("PBS-2.1")

                # Thermal -> Thermal Control
                if any(kw in statement for kw in ["thermal", "temperature", "heat"]):
                    allocated_to.extend(["PBS-2.6", "PBS-1.3.4"])

                # Interface -> Support Interfaces
                if any(kw in statement for kw in ["interface"]):
                    allocated_to.append("PBS-1.3")

                # Default allocation to top-level if no specific match
                if not allocated_to:
                    allocated_to.append("PBS-0")

                # Update PBS nodes
                for pbs_id in allocated_to:
                    if pbs_id in self._pbs.nodes:
                        if req.id not in self._pbs.nodes[pbs_id].allocated_requirements:
                            self._pbs.nodes[pbs_id].allocated_requirements.append(req.id)

                allocations.append({
                    "requirement_id": req.id,
                    "allocated_to": allocated_to,
                })

            return ToolResult(
                success=True,
                data={
                    "total_allocated": len(allocations),
                    "allocations": allocations,
                },
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def _derive_wbs_from_pbs(
        self,
        work_types: Optional[List[str]] = None
    ) -> ToolResult:
        """Derive WBS from PBS."""
        try:
            if self._pbs is None:
                return ToolResult(
                    success=False,
                    error="PBS not initialized.",
                )

            if work_types is None:
                work_types = ["design", "development", "integration", "test"]

            self._wbs = WorkBreakdownStructure(
                mission_name=self._pbs.mission_name
            )

            created_packages = []

            # Create work packages for leaf nodes
            for node in self._pbs.get_leaves():
                packages = self._wbs.derive_from_pbs_node(
                    pbs_id=node.id,
                    pbs_name=node.name,
                    work_types=work_types,
                )
                created_packages.extend([wp.id for wp in packages])

            # Also create integration work packages for parent nodes
            for node in self._pbs.nodes.values():
                if not node.is_leaf() and node.level > 0:
                    integration_types = ["integration", "test"]
                    wbs_base = node.id.replace("PBS-", "WBS-")

                    for idx, work_type in enumerate(integration_types, start=10):
                        wp = WorkPackage(
                            id=f"{wbs_base}.{idx}",
                            name=f"{node.name} - {work_type.title()}",
                            description=f"Subsystem {work_type} for {node.name}",
                            pbs_reference=node.id,
                            work_type=work_type,
                            deliverables=[f"{node.name} {work_type} report"],
                        )
                        self._wbs.add_work_package(wp)
                        created_packages.append(wp.id)

            return ToolResult(
                success=True,
                data={
                    "total_work_packages": len(self._wbs.work_packages),
                    "created_packages": created_packages,
                },
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def _validate_decomposition(
        self,
        requirements_ids: Optional[List[str]] = None
    ) -> ToolResult:
        """Validate PBS and WBS completeness."""
        try:
            if self._pbs is None:
                return ToolResult(
                    success=False,
                    error="PBS not initialized.",
                )

            results = {"pbs_validation": {}, "wbs_validation": {}}

            # Validate PBS
            if requirements_ids:
                results["pbs_validation"] = self._pbs.validate_completeness(
                    requirements_ids
                )
            else:
                results["pbs_validation"] = {
                    "total_nodes": len(self._pbs.nodes),
                    "total_leaves": len(self._pbs.get_leaves()),
                    "mission_critical_count": len(self._pbs.get_mission_critical()),
                }

            # Validate WBS
            if self._wbs:
                pbs_leaf_ids = [node.id for node in self._pbs.get_leaves()]
                results["wbs_validation"] = self._wbs.validate_against_pbs(pbs_leaf_ids)
            else:
                results["wbs_validation"] = {"error": "WBS not yet derived"}

            # Overall validation status
            pbs_ok = results["pbs_validation"].get("is_complete", True)
            wbs_ok = results["wbs_validation"].get("is_complete", True)
            results["is_valid"] = pbs_ok and wbs_ok

            return ToolResult(
                success=True,
                data=results,
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def _finalize_decomposition(self) -> ToolResult:
        """Finalize and return PBS and WBS."""
        if self._pbs is None:
            return ToolResult(
                success=False,
                error="PBS not initialized.",
            )

        result = {
            "pbs": self._pbs.export_to_dict(),
            "pbs_summary": {
                "total_nodes": len(self._pbs.nodes),
                "total_leaves": len(self._pbs.get_leaves()),
                "mission_critical_count": len(self._pbs.get_mission_critical()),
            },
        }

        if self._wbs:
            result["wbs"] = self._wbs.export_to_dict()
            result["wbs_summary"] = {
                "total_work_packages": len(self._wbs.work_packages),
                "total_effort_hours": self._wbs.calculate_total_effort(),
            }

        return ToolResult(success=True, data=result)

    def reason(self, context: Dict[str, Any]) -> Thought:
        """Generate reasoning about decomposition state."""
        task = context.get("task")
        observations = context.get("observations", [])
        iteration = context.get("iteration", 0)

        if iteration == 0:
            content = (
                f"Starting decomposition for task: {task.name}. "
                f"I need to create a PBS structure, allocate requirements, "
                f"derive WBS work packages, and validate completeness. "
                f"First action: initialize the PBS structure using the radar payload template."
            )
            return Thought(
                content=content,
                next_action_rationale="Need to initialize PBS structure first",
            )

        last_obs = observations[-1] if observations else None
        if last_obs:
            if last_obs.action.tool_name == "initialize_pbs":
                node_count = last_obs.result.data.get("total_nodes", 0)
                content = (
                    f"PBS initialized with {node_count} nodes from template. "
                    f"Now I should allocate requirements to PBS elements."
                )
                return Thought(
                    content=content,
                    observation_summary=f"PBS initialized with {node_count} nodes",
                    next_action_rationale="Need to allocate requirements to PBS",
                )

            elif last_obs.action.tool_name == "allocate_requirements":
                count = last_obs.result.data.get("total_allocated", 0)
                content = (
                    f"Allocated {count} requirements to PBS elements. "
                    f"Now I should derive WBS work packages from PBS."
                )
                return Thought(
                    content=content,
                    observation_summary=f"Allocated {count} requirements",
                    next_action_rationale="Need to derive WBS from PBS",
                )

            elif last_obs.action.tool_name == "derive_wbs_from_pbs":
                wp_count = last_obs.result.data.get("total_work_packages", 0)
                content = (
                    f"Derived {wp_count} work packages from PBS. "
                    f"Now I should validate the decomposition."
                )
                return Thought(
                    content=content,
                    observation_summary=f"Derived {wp_count} work packages",
                    next_action_rationale="Need to validate decomposition",
                )

            elif last_obs.action.tool_name == "validate_decomposition":
                is_valid = last_obs.result.data.get("is_valid", False)
                content = (
                    f"Decomposition validation {'passed' if is_valid else 'found issues'}. "
                    f"Ready to finalize the decomposition."
                )
                return Thought(
                    content=content,
                    observation_summary=f"Validation {'passed' if is_valid else 'found issues'}",
                    next_action_rationale="Ready to finalize decomposition",
                )

            elif last_obs.action.tool_name == "finalize_decomposition":
                content = "Decomposition complete. PBS and WBS are ready."
                return Thought(
                    content=content,
                    observation_summary="Finalized PBS and WBS",
                    next_action_rationale="Task complete",
                )

        return Thought(
            content="Continuing decomposition process...",
            next_action_rationale="Continue with next logical step",
        )

    def select_action(self, thought: Thought, context: Dict[str, Any]) -> Optional[Action]:
        """Select the next action based on current reasoning."""
        task = context.get("task")
        observations = context.get("observations", [])
        iteration = context.get("iteration", 0)

        mission_name = task.inputs.get("mission_name", "ATLAS-III")

        if iteration == 0:
            return Action(
                tool_name="initialize_pbs",
                parameters={"mission_name": mission_name, "use_template": True},
                rationale="Initialize PBS from radar payload template",
            )

        executed_tools = [obs.action.tool_name for obs in observations]

        if "initialize_pbs" in executed_tools and "allocate_requirements" not in executed_tools:
            requirements_set = task.inputs.get("requirements_set", {})
            return Action(
                tool_name="allocate_requirements",
                parameters={"requirements_set": requirements_set},
                rationale="Allocate requirements to PBS elements",
            )

        if "allocate_requirements" in executed_tools and "derive_wbs_from_pbs" not in executed_tools:
            return Action(
                tool_name="derive_wbs_from_pbs",
                parameters={"work_types": ["design", "development", "integration", "test"]},
                rationale="Derive WBS work packages from PBS",
            )

        if "derive_wbs_from_pbs" in executed_tools and "validate_decomposition" not in executed_tools:
            requirements_set = task.inputs.get("requirements_set", {})
            req_ids = [
                req.get("id") for req in requirements_set.get("requirements", [])
            ]
            return Action(
                tool_name="validate_decomposition",
                parameters={"requirements_ids": req_ids},
                rationale="Validate PBS and WBS completeness",
            )

        if "validate_decomposition" in executed_tools and "finalize_decomposition" not in executed_tools:
            return Action(
                tool_name="finalize_decomposition",
                parameters={},
                rationale="Finalize and return PBS and WBS",
            )

        context["task_complete"] = True
        return None

    def get_pbs(self) -> Optional[ProductBreakdownStructure]:
        """Get the current PBS."""
        return self._pbs

    def get_wbs(self) -> Optional[WorkBreakdownStructure]:
        """Get the current WBS."""
        return self._wbs
