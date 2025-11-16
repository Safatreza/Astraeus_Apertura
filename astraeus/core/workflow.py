"""Workflow orchestration for autonomous antenna design."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from loguru import logger

from astraeus.core.communication import CommunicationHub
from astraeus.core.message import Message, MessagePriority, MessageType


class WorkflowPhase(Enum):
    """Phases of the design workflow."""

    INITIALIZATION = "initialization"
    REQUIREMENTS_ANALYSIS = "requirements_analysis"
    ARCHITECTURE_DESIGN = "architecture_design"
    GEOMETRY_GENERATION = "geometry_generation"
    MATERIAL_SELECTION = "material_selection"
    SIMULATION = "simulation"
    OPTIMIZATION = "optimization"
    VALIDATION = "validation"
    REVIEW = "review"
    FINALIZATION = "finalization"
    COMPLETED = "completed"
    FAILED = "failed"


class TerminationCondition(Enum):
    """Conditions that can terminate the workflow."""

    CONVERGENCE = "convergence"  # Performance plateaued
    REQUIREMENTS_MET = "requirements_met"  # All requirements satisfied
    ITERATION_LIMIT = "iteration_limit"  # Max iterations reached
    VALIDATION_FAILURE = "validation_failure"  # Design cannot meet constraints
    RESOURCE_EXHAUSTION = "resource_exhaustion"  # Out of time/compute budget
    HUMAN_INTERVENTION = "human_intervention"  # Manual halt
    ERROR = "error"  # Unrecoverable error occurred


class DesignWorkflow:
    """
    Orchestrates the multi-agent design workflow.

    Manages the overall design process from requirements to validated design,
    coordinating agent activities and tracking progress.
    """

    def __init__(
        self,
        max_iterations: int = 50,
        convergence_threshold: float = 0.001,
        enable_human_review: bool = True,
    ):
        """
        Initialize design workflow.

        Args:
            max_iterations: Maximum number of optimization iterations
            convergence_threshold: Performance improvement threshold for convergence
            enable_human_review: Whether to enable human review checkpoints
        """
        self.workflow_id = uuid4()
        self.max_iterations = max_iterations
        self.convergence_threshold = convergence_threshold
        self.enable_human_review = enable_human_review

        # Communication infrastructure
        self.comm_hub = CommunicationHub()

        # Workflow state
        self.current_phase = WorkflowPhase.INITIALIZATION
        self.iteration_count = 0
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None

        # Design tracking
        self.requirements: Optional[Dict[str, Any]] = None
        self.current_design: Optional[Dict[str, Any]] = None
        self.design_history: List[Dict[str, Any]] = []
        self.performance_history: List[Dict[str, Any]] = []

        # Termination tracking
        self.termination_condition: Optional[TerminationCondition] = None
        self.termination_reason: str = ""

        # Checkpoints for human review
        self.review_checkpoints = [
            WorkflowPhase.ARCHITECTURE_DESIGN,
            WorkflowPhase.OPTIMIZATION,
            WorkflowPhase.VALIDATION,
        ]

        logger.info(f"Initialized design workflow: {self.workflow_id}")

    def register_agent(self, agent) -> None:
        """
        Register an agent with the workflow.

        Args:
            agent: Agent instance to register
        """
        self.comm_hub.register_agent(agent)

    def execute(
        self, requirements: Dict[str, Any], config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute the complete design workflow.

        Args:
            requirements: Design requirements specification
            config: Optional workflow configuration

        Returns:
            Final design package with all artifacts
        """
        self.requirements = requirements
        self.start_time = datetime.now()
        self.current_phase = WorkflowPhase.REQUIREMENTS_ANALYSIS

        logger.info(
            f"Starting design workflow {self.workflow_id} "
            f"with requirements: {requirements}"
        )

        try:
            # Execute workflow phases sequentially
            self._execute_requirements_analysis()
            self._execute_architecture_design()
            self._execute_geometry_generation()
            self._execute_material_selection()

            # Iterative optimization loop
            while not self._should_terminate():
                self._execute_simulation()
                self._execute_optimization()
                self._execute_validation()
                self.iteration_count += 1

                logger.info(
                    f"Completed iteration {self.iteration_count}/{self.max_iterations}"
                )

            # Finalization
            self._execute_finalization()

            self.current_phase = WorkflowPhase.COMPLETED
            self.end_time = datetime.now()

            logger.info(
                f"Workflow {self.workflow_id} completed successfully "
                f"in {(self.end_time - self.start_time).total_seconds():.1f}s"
            )

            return self._generate_final_package()

        except Exception as e:
            logger.error(f"Workflow {self.workflow_id} failed: {e}", exc_info=True)
            self.current_phase = WorkflowPhase.FAILED
            self.termination_condition = TerminationCondition.ERROR
            self.termination_reason = str(e)
            self.end_time = datetime.now()

            raise

    def _execute_requirements_analysis(self) -> None:
        """Execute requirements analysis phase."""
        self.current_phase = WorkflowPhase.REQUIREMENTS_ANALYSIS
        logger.info("Phase: Requirements Analysis")

        # Get Requirements Analyst agent
        analysts = self.comm_hub.get_agents_by_type("RequirementsAnalyst")
        if not analysts:
            raise RuntimeError("No Requirements Analyst agent registered")

        analyst = analysts[0]

        # Request requirements analysis
        task = {
            "type": "analyze_requirements",
            "requirements": self.requirements,
        }

        result = analyst.execute_task(task)

        # Store analyzed requirements
        self.requirements = result.get("validated_requirements", self.requirements)

        logger.info("Requirements analysis complete")

    def _execute_architecture_design(self) -> None:
        """Execute architecture design phase."""
        self.current_phase = WorkflowPhase.ARCHITECTURE_DESIGN
        logger.info("Phase: Architecture Design")

        # Human review checkpoint
        if (
            self.enable_human_review
            and self.current_phase in self.review_checkpoints
        ):
            self._request_human_review("Architecture Design")

        # Get Architecture agent
        architects = self.comm_hub.get_agents_by_type("ArchitectureAgent")
        if not architects:
            raise RuntimeError("No Architecture agent registered")

        architect = architects[0]

        # Request architecture design
        task = {
            "type": "design_architecture",
            "requirements": self.requirements,
        }

        result = architect.execute_task(task)

        # Store architecture
        if not self.current_design:
            self.current_design = {}
        self.current_design["architecture"] = result.get("architecture", {})

        logger.info("Architecture design complete")

    def _execute_geometry_generation(self) -> None:
        """Execute geometry generation phase."""
        self.current_phase = WorkflowPhase.GEOMETRY_GENERATION
        logger.info("Phase: Geometry Generation")

        # Get Geometry Generator agent
        generators = self.comm_hub.get_agents_by_type("GeometryGenerator")
        if not generators:
            raise RuntimeError("No Geometry Generator agent registered")

        generator = generators[0]

        # Request geometry generation
        task = {
            "type": "generate_geometry",
            "architecture": self.current_design.get("architecture", {}),
            "requirements": self.requirements,
        }

        result = generator.execute_task(task)

        # Store geometry
        self.current_design["geometry"] = result.get("geometry", {})

        logger.info("Geometry generation complete")

    def _execute_material_selection(self) -> None:
        """Execute material selection phase."""
        self.current_phase = WorkflowPhase.MATERIAL_SELECTION
        logger.info("Phase: Material Selection")

        # Get Material Selector agent
        selectors = self.comm_hub.get_agents_by_type("MaterialSelector")
        if not selectors:
            raise RuntimeError("No Material Selector agent registered")

        selector = selectors[0]

        # Request material selection
        task = {
            "type": "select_materials",
            "geometry": self.current_design.get("geometry", {}),
            "requirements": self.requirements,
        }

        result = selector.execute_task(task)

        # Store materials
        self.current_design["materials"] = result.get("materials", {})

        logger.info("Material selection complete")

    def _execute_simulation(self) -> None:
        """Execute simulation phase."""
        self.current_phase = WorkflowPhase.SIMULATION
        logger.info(f"Phase: Simulation (Iteration {self.iteration_count + 1})")

        # Get Simulation agent
        simulators = self.comm_hub.get_agents_by_type("SimulationAgent")
        if not simulators:
            raise RuntimeError("No Simulation agent registered")

        simulator = simulators[0]

        # Request simulation
        task = {
            "type": "run_simulation",
            "design": self.current_design,
            "requirements": self.requirements,
        }

        result = simulator.execute_task(task)

        # Store simulation results
        self.current_design["simulation_results"] = result.get("results", {})
        self.performance_history.append(
            {
                "iteration": self.iteration_count,
                "timestamp": datetime.now().isoformat(),
                "performance": result.get("performance_metrics", {}),
            }
        )

        logger.info("Simulation complete")

    def _execute_optimization(self) -> None:
        """Execute optimization phase."""
        self.current_phase = WorkflowPhase.OPTIMIZATION
        logger.info(f"Phase: Optimization (Iteration {self.iteration_count + 1})")

        # Human review checkpoint (periodic)
        if (
            self.enable_human_review
            and self.iteration_count > 0
            and self.iteration_count % 10 == 0
        ):
            self._request_human_review("Optimization Progress")

        # Get Performance Optimizer agent
        optimizers = self.comm_hub.get_agents_by_type("PerformanceOptimizer")
        if not optimizers:
            raise RuntimeError("No Performance Optimizer agent registered")

        optimizer = optimizers[0]

        # Request optimization
        task = {
            "type": "optimize_design",
            "current_design": self.current_design,
            "performance_history": self.performance_history,
            "requirements": self.requirements,
        }

        result = optimizer.execute_task(task)

        # Update design with optimized parameters
        if result.get("improved_design"):
            # Save current design to history
            self.design_history.append(self.current_design.copy())

            # Update to improved design
            self.current_design.update(result["improved_design"])

        logger.info("Optimization complete")

    def _execute_validation(self) -> None:
        """Execute validation phase."""
        self.current_phase = WorkflowPhase.VALIDATION
        logger.info(f"Phase: Validation (Iteration {self.iteration_count + 1})")

        # Get Validation agent
        validators = self.comm_hub.get_agents_by_type("ValidationAgent")
        if not validators:
            raise RuntimeError("No Validation agent registered")

        validator = validators[0]

        # Request validation
        task = {
            "type": "validate_design",
            "design": self.current_design,
            "requirements": self.requirements,
        }

        result = validator.execute_task(task)

        # Store validation results
        self.current_design["validation_results"] = result.get("validation", {})

        # Check for validation failures
        if not result.get("is_valid", True):
            logger.warning("Design failed validation")
            self.termination_condition = TerminationCondition.VALIDATION_FAILURE
            self.termination_reason = result.get("failure_reason", "Unknown")

        logger.info("Validation complete")

    def _execute_finalization(self) -> None:
        """Execute finalization phase."""
        self.current_phase = WorkflowPhase.FINALIZATION
        logger.info("Phase: Finalization")

        # Final human review
        if self.enable_human_review:
            self._request_human_review("Final Design Review")

        logger.info("Finalization complete")

    def _should_terminate(self) -> bool:
        """
        Check if workflow should terminate.

        Returns:
            True if termination condition met, False otherwise
        """
        # Check if already terminated
        if self.termination_condition is not None:
            return True

        # Check iteration limit
        if self.iteration_count >= self.max_iterations:
            self.termination_condition = TerminationCondition.ITERATION_LIMIT
            self.termination_reason = (
                f"Reached maximum iterations ({self.max_iterations})"
            )
            logger.info(self.termination_reason)
            return True

        # Check convergence
        if len(self.performance_history) >= 2:
            current_perf = self.performance_history[-1]["performance"]
            previous_perf = self.performance_history[-2]["performance"]

            # Simple convergence check (can be enhanced)
            if self._check_convergence(current_perf, previous_perf):
                self.termination_condition = TerminationCondition.CONVERGENCE
                self.termination_reason = "Performance converged"
                logger.info(self.termination_reason)
                return True

        # Check requirements satisfaction
        if self._check_requirements_met():
            self.termination_condition = TerminationCondition.REQUIREMENTS_MET
            self.termination_reason = "All requirements satisfied"
            logger.info(self.termination_reason)
            return True

        return False

    def _check_convergence(
        self, current: Dict[str, Any], previous: Dict[str, Any]
    ) -> bool:
        """
        Check if performance has converged.

        Args:
            current: Current performance metrics
            previous: Previous performance metrics

        Returns:
            True if converged, False otherwise
        """
        # Simple implementation - check if primary metric changed by less than threshold
        if "gain_dbi" in current and "gain_dbi" in previous:
            improvement = abs(current["gain_dbi"] - previous["gain_dbi"])
            return improvement < self.convergence_threshold

        return False

    def _check_requirements_met(self) -> bool:
        """
        Check if all requirements are satisfied.

        Returns:
            True if all requirements met, False otherwise
        """
        validation = self.current_design.get("validation_results", {})
        return validation.get("requirements_satisfied", False)

    def _request_human_review(self, topic: str) -> None:
        """
        Request human review at a checkpoint.

        Args:
            topic: Review topic
        """
        logger.info(f"Human review checkpoint: {topic}")

        # In a real implementation, this would pause and wait for human input
        # For now, we just log it
        # This can be extended to integrate with a UI or notification system

    def _generate_final_package(self) -> Dict[str, Any]:
        """
        Generate final design package with all artifacts.

        Returns:
            Complete design package
        """
        return {
            "workflow_id": str(self.workflow_id),
            "requirements": self.requirements,
            "final_design": self.current_design,
            "design_history": self.design_history,
            "performance_history": self.performance_history,
            "iterations": self.iteration_count,
            "termination_condition": (
                self.termination_condition.value
                if self.termination_condition
                else None
            ),
            "termination_reason": self.termination_reason,
            "duration_seconds": (
                (self.end_time - self.start_time).total_seconds()
                if self.start_time and self.end_time
                else None
            ),
            "communication_stats": self.comm_hub.get_statistics(),
        }

    def get_status(self) -> Dict[str, Any]:
        """
        Get current workflow status.

        Returns:
            Status dictionary
        """
        return {
            "workflow_id": str(self.workflow_id),
            "current_phase": self.current_phase.value,
            "iteration_count": self.iteration_count,
            "max_iterations": self.max_iterations,
            "elapsed_time": (
                (datetime.now() - self.start_time).total_seconds()
                if self.start_time
                else 0
            ),
            "agents_active": len(self.comm_hub.agents),
        }
