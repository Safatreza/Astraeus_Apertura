"""Supervisor Agent - Orchestrates the multi-agent antenna design workflow."""

from typing import Any, Dict, List, Optional
from enum import Enum
from uuid import uuid4

from loguru import logger

from astraeus.core.agent_base import BaseAgent
from astraeus.core.message import Message, MessagePriority, MessageType
from astraeus.data.parameters import MissionRequirements


class DesignPhase(Enum):
    """Design workflow phases."""

    REQUIREMENTS_ANALYSIS = "requirements_analysis"
    ARCHITECTURE_SELECTION = "architecture_selection"
    MATERIAL_SELECTION = "material_selection"
    GEOMETRY_GENERATION = "geometry_generation"
    SIMULATION = "simulation"
    OPTIMIZATION = "optimization"
    VALIDATION = "validation"
    COMPLETED = "completed"


class SupervisorAgent(BaseAgent):
    """
    Supervisor agent that orchestrates the multi-agent design workflow.

    Primary Responsibilities:
    - Coordinate workflow between specialized agents
    - Manage design state and transitions
    - Monitor progress and handle deadlocks
    - Aggregate results from multiple agents
    - Make high-level design decisions
    - Request human review at key checkpoints
    - Maintain design traceability
    """

    def _initialize(self) -> None:
        """Initialize the Supervisor Agent."""
        self.agent_type = "SupervisorAgent"
        self.knowledge_domains = [
            "workflow_management",
            "project_coordination",
            "systems_engineering",
            "decision_aggregation",
            "risk_management",
        ]
        self.capabilities = [
            "workflow_orchestration",
            "agent_coordination",
            "progress_monitoring",
            "decision_synthesis",
            "checkpoint_management",
            "human_in_the_loop",
        ]

        # Workflow state
        self.current_phase = DesignPhase.REQUIREMENTS_ANALYSIS
        self.workflow_history = []
        self.active_tasks = {}
        self.completed_tasks = {}

        # Agent registry (will be populated by communication hub)
        self.agent_registry = {}

        # Design state
        self.current_design = {
            "id": str(uuid4()),
            "phase": self.current_phase.value,
            "requirements": None,
            "architecture": None,
            "materials": None,
            "geometry": None,
            "simulation_results": None,
            "optimization_results": None,
            "validation_results": None,
        }

        # Human review checkpoints
        self.review_checkpoints = [
            DesignPhase.ARCHITECTURE_SELECTION,
            DesignPhase.OPTIMIZATION,
            DesignPhase.VALIDATION,
        ]

        # Workflow configuration
        self.workflow_config = {
            "max_optimization_iterations": 3,
            "require_validation_pass": True,
            "enable_human_review": True,
        }

        logger.info("Supervisor Agent initialized")

    def process_message(self, message: Message) -> Optional[List[Message]]:
        """
        Process incoming messages.

        Args:
            message: Message to process

        Returns:
            List of response messages
        """
        if message.message_type == MessageType.DATA_TRANSFER:
            return self._handle_data_transfer(message)
        elif message.message_type == MessageType.STATUS_UPDATE:
            return self._handle_status_update(message)
        elif message.message_type == MessageType.QUERY:
            return self._handle_query(message)
        elif message.message_type == MessageType.REQUEST_TASK:
            return self._handle_task_request(message)
        else:
            logger.debug(f"Unhandled message type: {message.message_type}")
            return None

    def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute supervisor task.

        Args:
            task: Task specification

        Returns:
            Task results
        """
        task_type = task.get("type")

        if task_type == "start_design":
            return self._start_design_workflow(task["requirements"])
        elif task_type == "advance_phase":
            return self._advance_workflow_phase()
        elif task_type == "get_status":
            return self._get_workflow_status()
        elif task_type == "request_review":
            return self._request_human_review(task.get("topic"))
        else:
            raise ValueError(f"Unknown task type: {task_type}")

    def _start_design_workflow(
        self, requirements: MissionRequirements
    ) -> Dict[str, Any]:
        """
        Start the antenna design workflow.

        Args:
            requirements: Mission requirements

        Returns:
            Workflow initialization results
        """
        logger.info("Starting antenna design workflow")

        # Reset workflow state
        self.current_phase = DesignPhase.REQUIREMENTS_ANALYSIS
        self.workflow_history = []
        self.active_tasks = {}
        self.completed_tasks = {}

        # Initialize design
        self.current_design = {
            "id": str(uuid4()),
            "phase": self.current_phase.value,
            "requirements": requirements,
            "architecture": None,
            "materials": None,
            "geometry": None,
            "simulation_results": None,
            "optimization_results": None,
            "validation_results": None,
        }

        # Start requirements analysis phase
        result = self._execute_requirements_phase(requirements)

        # Log workflow start
        self.log_decision(
            decision="Started antenna design workflow",
            rationale=f"Processing requirements for {requirements.mission_name}",
            metadata={
                "design_id": self.current_design["id"],
                "mission_name": requirements.mission_name,
            },
        )

        return {
            "workflow_started": True,
            "design_id": self.current_design["id"],
            "current_phase": self.current_phase.value,
            "initial_results": result,
        }

    def _execute_requirements_phase(
        self, requirements: MissionRequirements
    ) -> Dict[str, Any]:
        """Execute requirements analysis phase."""
        logger.info("Executing requirements analysis phase")

        # In a real implementation, would send message to RequirementsAnalystAgent
        # For now, simplified assumption that requirements are validated
        self.current_design["requirements"] = requirements

        # Record phase completion
        self._record_phase_completion(
            DesignPhase.REQUIREMENTS_ANALYSIS,
            {"status": "completed", "requirements_validated": True},
        )

        # Advance to next phase
        return self._advance_to_architecture_phase()

    def _advance_to_architecture_phase(self) -> Dict[str, Any]:
        """Advance to architecture selection phase."""
        logger.info("Advancing to architecture selection phase")

        self.current_phase = DesignPhase.ARCHITECTURE_SELECTION

        # In real implementation, would send task to ArchitectureAgent
        # Simplified mock result
        architecture_result = {
            "selected_architecture": "patch_array",
            "configuration": {
                "operating_frequency_ghz": self.current_design["requirements"].frequency.center_frequency_ghz,
                "target_gain_dbi": self.current_design["requirements"].radiation_pattern.gain_dbi,
                "estimated_elements": 64,
            },
            "rationale": "Patch array optimal for frequency and gain requirements",
        }

        self.current_design["architecture"] = architecture_result

        # Record phase completion
        self._record_phase_completion(
            DesignPhase.ARCHITECTURE_SELECTION, architecture_result
        )

        # Check if human review is needed
        if self._should_request_review():
            return self._request_architecture_review(architecture_result)

        # Continue to material selection
        return self._advance_to_material_phase()

    def _advance_to_material_phase(self) -> Dict[str, Any]:
        """Advance to material selection phase."""
        logger.info("Advancing to material selection phase")

        self.current_phase = DesignPhase.MATERIAL_SELECTION

        # Mock material selection result
        materials_result = {
            "materials": {
                "substrate": {"name": "Rogers RO4003C", "properties": {}},
                "conductor": {"name": "Copper", "properties": {}},
                "structure": {"name": "Aluminum 6061-T6", "properties": {}},
            },
            "rationale": "Materials optimized for space environment and performance",
        }

        self.current_design["materials"] = materials_result

        self._record_phase_completion(
            DesignPhase.MATERIAL_SELECTION, materials_result
        )

        # Continue to geometry generation
        return self._advance_to_geometry_phase()

    def _advance_to_geometry_phase(self) -> Dict[str, Any]:
        """Advance to geometry generation phase."""
        logger.info("Advancing to geometry generation phase")

        self.current_phase = DesignPhase.GEOMETRY_GENERATION

        # Mock geometry generation result
        geometry_result = {
            "geometry": {
                "type": "patch_array",
                "num_components": 64,
                "total_dimensions": {
                    "length": 0.5,
                    "width": 0.5,
                    "height": 0.01,
                },
            },
            "mesh": {"num_elements": 50000, "quality": "medium"},
        }

        self.current_design["geometry"] = geometry_result

        self._record_phase_completion(
            DesignPhase.GEOMETRY_GENERATION, geometry_result
        )

        # Continue to simulation
        return self._advance_to_simulation_phase()

    def _advance_to_simulation_phase(self) -> Dict[str, Any]:
        """Advance to simulation phase."""
        logger.info("Advancing to simulation phase")

        self.current_phase = DesignPhase.SIMULATION

        # Mock simulation results
        simulation_result = {
            "electromagnetic": {
                "metrics": {
                    "peak_gain_dbi": 30.5,
                    "s11_worst_db": -15.2,
                    "vswr_max": 1.4,
                    "beamwidth_deg": 12.0,
                },
            },
            "thermal": {
                "metrics": {
                    "max_temperature_c": 85.0,
                    "min_temperature_c": -20.0,
                },
            },
            "structural": {
                "metrics": {
                    "safety_factor": 2.1,
                    "max_stress_mpa": 120.0,
                },
            },
        }

        self.current_design["simulation_results"] = simulation_result

        self._record_phase_completion(DesignPhase.SIMULATION, simulation_result)

        # Continue to optimization
        return self._advance_to_optimization_phase()

    def _advance_to_optimization_phase(self) -> Dict[str, Any]:
        """Advance to optimization phase."""
        logger.info("Advancing to optimization phase")

        self.current_phase = DesignPhase.OPTIMIZATION

        # Mock optimization results
        optimization_result = {
            "optimal_design": {
                "patch_length": 0.015,
                "patch_width": 0.015,
                "element_spacing": 0.03,
            },
            "optimal_objectives": {
                "gain_dbi": 31.2,
                "efficiency": 0.88,
                "s11_db": -18.5,
            },
            "improvement_percent": 8.5,
            "converged": True,
        }

        self.current_design["optimization_results"] = optimization_result

        self._record_phase_completion(DesignPhase.OPTIMIZATION, optimization_result)

        # Check if human review is needed
        if self._should_request_review():
            return self._request_optimization_review(optimization_result)

        # Continue to validation
        return self._advance_to_validation_phase()

    def _advance_to_validation_phase(self) -> Dict[str, Any]:
        """Advance to validation phase."""
        logger.info("Advancing to validation phase")

        self.current_phase = DesignPhase.VALIDATION

        # Mock validation results
        validation_result = {
            "overall_status": "PASSED",
            "compliance_score": 0.95,
            "passed": [
                "Gain requirement met",
                "VSWR within specification",
                "Mass within budget",
                "Thermal limits satisfied",
            ],
            "failed": [],
            "warnings": ["Slight beamwidth variation from target"],
        }

        self.current_design["validation_results"] = validation_result

        self._record_phase_completion(DesignPhase.VALIDATION, validation_result)

        # Check if validation passed
        if validation_result["overall_status"] == "PASSED":
            return self._complete_workflow()
        else:
            # May need to iterate or request human review
            if self._should_request_review():
                return self._request_validation_review(validation_result)
            else:
                # Re-optimize or modify design
                return {"status": "requires_iteration"}

    def _complete_workflow(self) -> Dict[str, Any]:
        """Complete the design workflow."""
        logger.info("Design workflow completed successfully")

        self.current_phase = DesignPhase.COMPLETED

        # Generate final design package
        design_package = {
            "design_id": self.current_design["id"],
            "status": "completed",
            "requirements": self.current_design["requirements"],
            "architecture": self.current_design["architecture"],
            "materials": self.current_design["materials"],
            "geometry": self.current_design["geometry"],
            "simulation_results": self.current_design["simulation_results"],
            "optimization_results": self.current_design["optimization_results"],
            "validation_results": self.current_design["validation_results"],
            "workflow_history": self.workflow_history,
        }

        self.log_decision(
            decision="Design workflow completed successfully",
            rationale=f"All phases completed and validated",
            metadata={
                "design_id": self.current_design["id"],
                "phases_completed": len(self.workflow_history),
                "validation_score": self.current_design["validation_results"]["compliance_score"],
            },
        )

        return design_package

    def _advance_workflow_phase(self) -> Dict[str, Any]:
        """Advance to the next workflow phase."""
        phase_transitions = {
            DesignPhase.REQUIREMENTS_ANALYSIS: self._advance_to_architecture_phase,
            DesignPhase.ARCHITECTURE_SELECTION: self._advance_to_material_phase,
            DesignPhase.MATERIAL_SELECTION: self._advance_to_geometry_phase,
            DesignPhase.GEOMETRY_GENERATION: self._advance_to_simulation_phase,
            DesignPhase.SIMULATION: self._advance_to_optimization_phase,
            DesignPhase.OPTIMIZATION: self._advance_to_validation_phase,
            DesignPhase.VALIDATION: self._complete_workflow,
        }

        transition_func = phase_transitions.get(self.current_phase)
        if transition_func:
            return transition_func()
        else:
            return {"status": "no_transition_available"}

    def _get_workflow_status(self) -> Dict[str, Any]:
        """Get current workflow status."""
        return {
            "design_id": self.current_design["id"],
            "current_phase": self.current_phase.value,
            "phases_completed": [
                entry["phase"] for entry in self.workflow_history
            ],
            "active_tasks": len(self.active_tasks),
            "completed_tasks": len(self.completed_tasks),
            "design_state": {
                "has_requirements": self.current_design["requirements"] is not None,
                "has_architecture": self.current_design["architecture"] is not None,
                "has_materials": self.current_design["materials"] is not None,
                "has_geometry": self.current_design["geometry"] is not None,
                "has_simulation": self.current_design["simulation_results"] is not None,
                "has_optimization": self.current_design["optimization_results"] is not None,
                "has_validation": self.current_design["validation_results"] is not None,
            },
        }

    def _should_request_review(self) -> bool:
        """Determine if human review should be requested."""
        if not self.workflow_config["enable_human_review"]:
            return False

        return self.current_phase in self.review_checkpoints

    def _request_architecture_review(
        self, architecture_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Request human review of architecture selection."""
        logger.info("Requesting human review of architecture selection")

        self.request_human_review(
            topic="Architecture Selection",
            options=[
                {
                    "name": architecture_result["selected_architecture"],
                    "rationale": architecture_result["rationale"],
                }
            ],
            rationale="Architecture selection is a critical decision point",
            priority=MessagePriority.HIGH,
        )

        return {
            "status": "awaiting_review",
            "phase": self.current_phase.value,
            "review_topic": "architecture_selection",
        }

    def _request_optimization_review(
        self, optimization_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Request human review of optimization results."""
        logger.info("Requesting human review of optimization results")

        self.request_human_review(
            topic="Optimization Results",
            options=[
                {
                    "improvement": optimization_result["improvement_percent"],
                    "converged": optimization_result["converged"],
                }
            ],
            rationale="Review optimization improvements before proceeding",
            priority=MessagePriority.MEDIUM,
        )

        return {
            "status": "awaiting_review",
            "phase": self.current_phase.value,
            "review_topic": "optimization",
        }

    def _request_validation_review(
        self, validation_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Request human review of validation results."""
        logger.info("Requesting human review of validation results")

        self.request_human_review(
            topic="Design Validation",
            options=[
                {
                    "status": validation_result["overall_status"],
                    "compliance_score": validation_result["compliance_score"],
                    "failed": validation_result["failed"],
                }
            ],
            rationale="Final design validation review",
            priority=MessagePriority.HIGH,
        )

        return {
            "status": "awaiting_review",
            "phase": self.current_phase.value,
            "review_topic": "validation",
        }

    def _request_human_review(self, topic: Optional[str] = None) -> Dict[str, Any]:
        """Request human review for current phase."""
        if topic is None:
            topic = f"Review {self.current_phase.value}"

        self.request_human_review(
            topic=topic,
            options=[{"current_state": self.current_design}],
            rationale=f"Review requested for {self.current_phase.value}",
        )

        return {
            "review_requested": True,
            "topic": topic,
            "phase": self.current_phase.value,
        }

    def _record_phase_completion(
        self, phase: DesignPhase, results: Dict[str, Any]
    ) -> None:
        """Record completion of a workflow phase."""
        self.workflow_history.append({
            "phase": phase.value,
            "timestamp": self._get_timestamp(),
            "results": results,
        })

        logger.info(f"Completed phase: {phase.value}")

    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime

        return datetime.now().isoformat()

    def _handle_data_transfer(self, message: Message) -> List[Message]:
        """Handle data transfer messages from other agents."""
        # Extract results from agent
        sender = message.sender
        payload = message.payload

        logger.debug(f"Received data from {sender}: {payload.keys()}")

        # Update design state based on sender
        # This would be more sophisticated in production

        return []

    def _handle_status_update(self, message: Message) -> List[Message]:
        """Handle status update messages."""
        sender = message.sender
        status = message.payload.get("status")

        logger.debug(f"Status update from {sender}: {status}")

        # Update task tracking
        if "task_id" in message.payload:
            task_id = message.payload["task_id"]
            if status == "completed":
                if task_id in self.active_tasks:
                    self.completed_tasks[task_id] = self.active_tasks.pop(task_id)

        return []

    def _handle_query(self, message: Message) -> List[Message]:
        """Handle query messages."""
        status = self._get_workflow_status()

        response = message.create_reply(
            sender=self.agent_id,
            message_type=MessageType.DATA_TRANSFER,
            payload={"status": status},
            rationale="Workflow status query",
        )

        return [response]

    def _handle_task_request(self, message: Message) -> List[Message]:
        """Handle task request messages."""
        task_data = message.payload.get("task")
        if task_data:
            result = self.execute_task(task_data)
            response = message.create_reply(
                sender=self.agent_id,
                message_type=MessageType.DATA_TRANSFER,
                payload={"result": result},
                rationale="Supervisor task completed",
            )
            return [response]
        return []
