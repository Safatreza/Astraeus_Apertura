"""Requirements Agent for parsing and classifying mission requirements.

This agent handles the first stage of the systems engineering pipeline:
converting mission inputs into structured, validated requirements.
"""

import logging
import re
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from agents.base_agent import (
    Action,
    BaseAgent,
    Observation,
    Task,
    Thought,
    Tool,
    ToolResult,
)
from artifacts.requirements import (
    RequirementCategory,
    RequirementItem,
    RequirementsSet,
    VerificationMethod,
)


logger = logging.getLogger("astraeus.agents.requirements")


class MissionInput(BaseModel):
    """Structured mission input data."""

    mission_name: str
    launch_target: str
    primary_objective: str
    constraints: Dict[str, Any]
    payload_requirements: List[str]
    additional_inputs: Dict[str, Any] = {}


class RequirementsAgent(BaseAgent):
    """Agent for extracting and managing requirements.

    Capabilities:
    - Parse mission inputs to extract requirements
    - Classify requirements by category
    - Validate requirement completeness and consistency
    - Generate derived requirements from constraints

    Tools:
    - extract_requirements: Parse mission inputs
    - classify_requirement: Categorize a requirement
    - validate_requirement_set: Check completeness
    - generate_derived_requirements: Create derived reqs
    """

    def __init__(
        self,
        name: str = "RequirementsAgent",
        max_iterations: int = 10,
        trace_enabled: bool = True,
    ):
        """Initialize the requirements agent with its tools."""
        tools = self._create_tools()
        super().__init__(
            name=name,
            tools=tools,
            max_iterations=max_iterations,
            trace_enabled=trace_enabled,
        )

        self._requirements_set: Optional[RequirementsSet] = None
        self._requirement_counter = 0

    def _create_tools(self) -> List[Tool]:
        """Create the agent's tools."""
        return [
            Tool(
                name="extract_requirements",
                description="Extract requirements from mission input data",
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "mission_input": {"type": "object"},
                    },
                    "required": ["mission_input"],
                },
                function=self._extract_requirements,
            ),
            Tool(
                name="classify_requirement",
                description="Classify a requirement by category",
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "statement": {"type": "string"},
                    },
                    "required": ["statement"],
                },
                function=self._classify_requirement,
            ),
            Tool(
                name="validate_requirement_set",
                description="Validate the current requirements set",
                parameters_schema={
                    "type": "object",
                    "properties": {},
                },
                function=self._validate_requirement_set,
            ),
            Tool(
                name="add_requirement",
                description="Add a new requirement to the set",
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "category": {"type": "string"},
                        "statement": {"type": "string"},
                        "source": {"type": "string"},
                        "parent_id": {"type": "string"},
                    },
                    "required": ["category", "statement"],
                },
                function=self._add_requirement,
            ),
            Tool(
                name="generate_derived_requirements",
                description="Generate derived requirements from constraints",
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "constraints": {"type": "object"},
                    },
                    "required": ["constraints"],
                },
                function=self._generate_derived_requirements,
            ),
            Tool(
                name="finalize_requirements",
                description="Finalize and return the requirements set",
                parameters_schema={
                    "type": "object",
                    "properties": {},
                },
                function=self._finalize_requirements,
            ),
        ]

    def _generate_requirement_id(self, category: RequirementCategory) -> str:
        """Generate a unique requirement ID."""
        self._requirement_counter += 1
        prefix_map = {
            RequirementCategory.FUNCTIONAL: "FN",
            RequirementCategory.PERFORMANCE: "PF",
            RequirementCategory.INTERFACE: "IF",
            RequirementCategory.ENVIRONMENTAL: "EN",
            RequirementCategory.OPERATIONAL: "OP",
            RequirementCategory.CONSTRAINT: "CN",
        }
        prefix = prefix_map.get(category, "GN")
        return f"REQ-{prefix}-{self._requirement_counter:03d}"

    def _extract_requirements(self, mission_input: Dict[str, Any]) -> ToolResult:
        """Extract requirements from mission input data."""
        try:
            mission_name = mission_input.get("mission_name", "Unknown")

            # Initialize requirements set
            self._requirements_set = RequirementsSet(mission_name=mission_name)
            self._requirement_counter = 0

            extracted = []

            # Extract from primary objective
            objective = mission_input.get("primary_objective", "")
            if objective:
                req_id = self._generate_requirement_id(RequirementCategory.FUNCTIONAL)
                statement = f"The system shall {objective.lower()}"
                if "shall" not in statement.lower():
                    statement = f"The system shall accomplish the primary objective: {objective}"

                req = RequirementItem(
                    id=req_id,
                    category=RequirementCategory.FUNCTIONAL,
                    statement=statement,
                    source="Mission Objectives",
                    priority=1,
                )
                self._requirements_set.add_requirement(req)
                extracted.append(req_id)

            # Extract from payload requirements
            for payload_req in mission_input.get("payload_requirements", []):
                category = self._infer_category(payload_req)
                req_id = self._generate_requirement_id(category)

                # Ensure shall format
                if "shall" in payload_req.lower():
                    statement = payload_req
                else:
                    statement = f"The payload shall {payload_req.lower()}"

                req = RequirementItem(
                    id=req_id,
                    category=category,
                    statement=statement,
                    source="Payload Requirements",
                    priority=1,
                )
                self._requirements_set.add_requirement(req)
                extracted.append(req_id)

            return ToolResult(
                success=True,
                data={
                    "extracted_count": len(extracted),
                    "requirement_ids": extracted,
                },
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def _infer_category(self, statement: str) -> RequirementCategory:
        """Infer requirement category from statement text."""
        lower = statement.lower()

        # Performance indicators
        if any(kw in lower for kw in ["detect", "measure", "accuracy", "rate", "range", "resolution"]):
            return RequirementCategory.PERFORMANCE

        # Interface indicators
        if any(kw in lower for kw in ["interface", "connect", "communicate", "downlink", "uplink"]):
            return RequirementCategory.INTERFACE

        # Environmental indicators
        if any(kw in lower for kw in ["temperature", "radiation", "vacuum", "thermal"]):
            return RequirementCategory.ENVIRONMENTAL

        # Operational indicators
        if any(kw in lower for kw in ["operate", "mode", "command", "control"]):
            return RequirementCategory.OPERATIONAL

        # Constraint indicators
        if any(kw in lower for kw in ["mass", "power", "volume", "budget", "limit"]):
            return RequirementCategory.CONSTRAINT

        # Default to functional
        return RequirementCategory.FUNCTIONAL

    def _classify_requirement(self, statement: str) -> ToolResult:
        """Classify a requirement statement by category."""
        category = self._infer_category(statement)
        return ToolResult(
            success=True,
            data={
                "category": category.value,
                "confidence": 0.8,
            },
        )

    def _add_requirement(
        self,
        category: str,
        statement: str,
        source: str = "Derived",
        parent_id: Optional[str] = None,
    ) -> ToolResult:
        """Add a new requirement to the set."""
        try:
            if self._requirements_set is None:
                return ToolResult(
                    success=False,
                    error="Requirements set not initialized. Run extract_requirements first.",
                )

            cat = RequirementCategory(category.lower())
            req_id = self._generate_requirement_id(cat)

            # Ensure shall format
            if "shall" not in statement.lower():
                statement = f"The system shall {statement.lower()}"

            req = RequirementItem(
                id=req_id,
                category=cat,
                statement=statement,
                source=source,
                parent_id=parent_id,
            )
            self._requirements_set.add_requirement(req)

            return ToolResult(
                success=True,
                data={"requirement_id": req_id},
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def _generate_derived_requirements(
        self, constraints: Dict[str, Any]
    ) -> ToolResult:
        """Generate derived requirements from constraints."""
        try:
            if self._requirements_set is None:
                return ToolResult(
                    success=False,
                    error="Requirements set not initialized.",
                )

            derived = []

            # Mass constraint
            if "mass_budget_kg" in constraints:
                mass = constraints["mass_budget_kg"]
                req_id = self._generate_requirement_id(RequirementCategory.CONSTRAINT)
                req = RequirementItem(
                    id=req_id,
                    category=RequirementCategory.CONSTRAINT,
                    statement=f"The system shall have a total mass not exceeding {mass} kg",
                    source="System Constraints",
                    verification_method=VerificationMethod.TEST,
                )
                self._requirements_set.add_requirement(req)
                derived.append(req_id)

            # Power constraint
            if "power_budget_w" in constraints:
                power = constraints["power_budget_w"]
                req_id = self._generate_requirement_id(RequirementCategory.CONSTRAINT)
                req = RequirementItem(
                    id=req_id,
                    category=RequirementCategory.CONSTRAINT,
                    statement=f"The system shall operate within a power budget of {power} W",
                    source="System Constraints",
                    verification_method=VerificationMethod.TEST,
                )
                self._requirements_set.add_requirement(req)
                derived.append(req_id)

            # Data rate constraint
            if "data_rate_mbps" in constraints:
                rate = constraints["data_rate_mbps"]
                req_id = self._generate_requirement_id(RequirementCategory.PERFORMANCE)
                req = RequirementItem(
                    id=req_id,
                    category=RequirementCategory.PERFORMANCE,
                    statement=f"The system shall support a data rate of at least {rate} Mbps",
                    source="System Constraints",
                    verification_method=VerificationMethod.TEST,
                )
                self._requirements_set.add_requirement(req)
                derived.append(req_id)

            # Form factor constraint
            if "form_factor" in constraints:
                form = constraints["form_factor"]
                req_id = self._generate_requirement_id(RequirementCategory.CONSTRAINT)
                req = RequirementItem(
                    id=req_id,
                    category=RequirementCategory.CONSTRAINT,
                    statement=f"The system shall conform to {form} form factor specifications",
                    source="System Constraints",
                    verification_method=VerificationMethod.INSPECTION,
                )
                self._requirements_set.add_requirement(req)
                derived.append(req_id)

            return ToolResult(
                success=True,
                data={
                    "derived_count": len(derived),
                    "requirement_ids": derived,
                },
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def _validate_requirement_set(self) -> ToolResult:
        """Validate the current requirements set."""
        try:
            if self._requirements_set is None:
                return ToolResult(
                    success=False,
                    error="Requirements set not initialized.",
                )

            issues = self._requirements_set.validate_completeness()
            counts = self._requirements_set.count_by_category()

            return ToolResult(
                success=True,
                data={
                    "is_valid": len(issues) == 0,
                    "total_requirements": len(self._requirements_set),
                    "issues": issues,
                    "counts_by_category": {k.value: v for k, v in counts.items()},
                },
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def _finalize_requirements(self) -> ToolResult:
        """Finalize and return the requirements set."""
        if self._requirements_set is None:
            return ToolResult(
                success=False,
                error="Requirements set not initialized.",
            )

        return ToolResult(
            success=True,
            data={
                "requirements_set": self._requirements_set.model_dump(),
                "total_requirements": len(self._requirements_set),
            },
        )

    def reason(self, context: Dict[str, Any]) -> Thought:
        """Generate reasoning about current requirements processing state."""
        task = context.get("task")
        observations = context.get("observations", [])
        iteration = context.get("iteration", 0)

        # Determine current state
        if iteration == 0:
            content = (
                f"Starting requirements extraction for task: {task.name}. "
                f"I need to parse the mission inputs and extract structured requirements. "
                f"First action: extract requirements from the mission input data."
            )
            return Thought(
                content=content,
                next_action_rationale="Need to extract requirements from mission inputs first",
            )

        # Analyze last observation
        last_obs = observations[-1] if observations else None
        if last_obs:
            if last_obs.action.tool_name == "extract_requirements":
                content = (
                    f"Extracted {last_obs.result.data.get('extracted_count', 0)} requirements. "
                    f"Now I should generate derived requirements from constraints and validate."
                )
                return Thought(
                    content=content,
                    observation_summary=f"Extracted initial requirements",
                    next_action_rationale="Need to add constraint-derived requirements",
                )

            elif last_obs.action.tool_name == "generate_derived_requirements":
                content = (
                    f"Generated {last_obs.result.data.get('derived_count', 0)} derived requirements. "
                    f"Now I should validate the complete requirements set."
                )
                return Thought(
                    content=content,
                    observation_summary="Generated derived requirements from constraints",
                    next_action_rationale="Need to validate requirements completeness",
                )

            elif last_obs.action.tool_name == "validate_requirement_set":
                validation = last_obs.result.data
                if validation.get("is_valid", False):
                    content = (
                        f"Requirements validation passed with {validation.get('total_requirements', 0)} requirements. "
                        f"Ready to finalize the requirements set."
                    )
                else:
                    content = (
                        f"Validation found issues: {validation.get('issues', {})}. "
                        f"Proceeding to finalize despite minor issues."
                    )
                return Thought(
                    content=content,
                    observation_summary="Completed validation",
                    next_action_rationale="Ready to finalize requirements",
                )

            elif last_obs.action.tool_name == "finalize_requirements":
                content = "Requirements extraction complete. Task finished."
                return Thought(
                    content=content,
                    observation_summary="Finalized requirements set",
                    next_action_rationale="Task complete",
                )

        return Thought(
            content="Continuing requirements processing...",
            next_action_rationale="Continue with next logical step",
        )

    def select_action(self, thought: Thought, context: Dict[str, Any]) -> Optional[Action]:
        """Select the next action based on current reasoning."""
        task = context.get("task")
        observations = context.get("observations", [])
        iteration = context.get("iteration", 0)

        # First action: extract requirements
        if iteration == 0:
            mission_input = task.inputs.get("mission_input", {})
            return Action(
                tool_name="extract_requirements",
                parameters={"mission_input": mission_input},
                rationale="Extract initial requirements from mission inputs",
            )

        # Determine next action based on what we've done
        executed_tools = [obs.action.tool_name for obs in observations]

        if "extract_requirements" in executed_tools and "generate_derived_requirements" not in executed_tools:
            constraints = task.inputs.get("mission_input", {}).get("constraints", {})
            return Action(
                tool_name="generate_derived_requirements",
                parameters={"constraints": constraints},
                rationale="Generate requirements from system constraints",
            )

        if "generate_derived_requirements" in executed_tools and "validate_requirement_set" not in executed_tools:
            return Action(
                tool_name="validate_requirement_set",
                parameters={},
                rationale="Validate the complete requirements set",
            )

        if "validate_requirement_set" in executed_tools and "finalize_requirements" not in executed_tools:
            return Action(
                tool_name="finalize_requirements",
                parameters={},
                rationale="Finalize and return the requirements set",
            )

        # Task complete
        context["task_complete"] = True
        return None

    def get_requirements_set(self) -> Optional[RequirementsSet]:
        """Get the current requirements set."""
        return self._requirements_set
