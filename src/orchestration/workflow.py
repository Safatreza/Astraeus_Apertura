"""Systems Engineering Workflow Orchestration.

This module provides the high-level workflow that orchestrates
multiple agents through the full SE pipeline:
Mission Inputs -> Requirements -> PBS -> WBS -> Dependencies -> Timeline
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from agents.base_agent import BaseAgent, Result, Task
from agents.decomposition_agent import DecompositionAgent
from agents.requirements_agent import RequirementsAgent
from agents.scheduling_agent import SchedulingAgent
from orchestration.react_loop import ReActLoop


logger = logging.getLogger("astraeus.orchestration.workflow")


class StageResult(BaseModel):
    """Result from executing a workflow stage.

    Attributes:
        stage_name: Name of the stage.
        success: Whether the stage completed successfully.
        outputs: Output data from the stage.
        execution_time_seconds: Stage execution time.
        error: Error message if failed.
        reasoning_trace: Summary of agent reasoning.
    """

    stage_name: str
    success: bool
    outputs: Dict[str, Any] = Field(default_factory=dict)
    execution_time_seconds: float = 0.0
    error: Optional[str] = None
    reasoning_trace: List[Dict[str, Any]] = Field(default_factory=list)


class WorkflowResult(BaseModel):
    """Result from executing the complete workflow.

    Attributes:
        mission_name: Name of the mission.
        success: Whether all stages completed successfully.
        stage_results: Results from each stage.
        final_artifacts: All generated artifacts.
        total_execution_time_seconds: Total execution time.
        summary: Summary statistics.
    """

    mission_name: str
    success: bool
    stage_results: Dict[str, StageResult] = Field(default_factory=dict)
    final_artifacts: Dict[str, Any] = Field(default_factory=dict)
    total_execution_time_seconds: float = 0.0
    summary: Dict[str, Any] = Field(default_factory=dict)


class SEWorkflow:
    """Systems Engineering Workflow Orchestrator.

    Manages the complete pipeline from mission inputs to execution timeline,
    coordinating multiple specialized agents.

    Pipeline Stages:
    1. Requirements Extraction (RequirementsAgent)
    2. Decomposition (DecompositionAgent) -> PBS + WBS
    3. Scheduling (SchedulingAgent) -> Dependencies + Timeline

    Attributes:
        agents: Dictionary of agents by stage name.
        max_iterations_per_stage: Max ReAct iterations per stage.
        output_dir: Directory for saving artifacts.
    """

    STAGES = ["requirements", "decomposition", "scheduling"]

    def __init__(
        self,
        agents: Optional[Dict[str, BaseAgent]] = None,
        max_iterations_per_stage: int = 15,
        output_dir: Optional[Path] = None,
    ):
        """Initialize the workflow.

        Args:
            agents: Custom agents for each stage. If not provided,
                   default agents are created.
            max_iterations_per_stage: Max iterations for each agent.
            output_dir: Directory to save output artifacts.
        """
        self.max_iterations_per_stage = max_iterations_per_stage
        self.output_dir = output_dir

        # Initialize default agents if not provided
        self.agents = agents or {
            "requirements": RequirementsAgent(
                max_iterations=max_iterations_per_stage
            ),
            "decomposition": DecompositionAgent(
                max_iterations=max_iterations_per_stage
            ),
            "scheduling": SchedulingAgent(
                max_iterations=max_iterations_per_stage
            ),
        }

        self._stage_results: Dict[str, StageResult] = {}
        self._artifacts: Dict[str, Any] = {}

    def run_pipeline(self, mission_inputs: Dict[str, Any]) -> WorkflowResult:
        """Run the complete SE pipeline.

        Args:
            mission_inputs: Mission input data including objectives,
                          constraints, and payload requirements.

        Returns:
            WorkflowResult containing all stage results and artifacts.
        """
        start_time = datetime.now()
        mission_name = mission_inputs.get("mission_name", "Unknown")
        logger.info(f"Starting SE pipeline for mission: {mission_name}")

        self._stage_results = {}
        self._artifacts = {"mission_inputs": mission_inputs}

        try:
            # Stage 1: Requirements
            logger.info("=" * 60)
            logger.info("STAGE 1: Requirements Extraction")
            logger.info("=" * 60)
            req_result = self.run_stage("requirements", {
                "mission_input": mission_inputs
            })
            if not req_result.success:
                return self._build_workflow_result(
                    mission_name, False, start_time,
                    error=f"Requirements stage failed: {req_result.error}"
                )

            # Extract requirements set for next stage
            requirements_set = req_result.outputs.get("requirements_set", {})
            self._artifacts["requirements"] = requirements_set

            # Stage 2: Decomposition
            logger.info("=" * 60)
            logger.info("STAGE 2: Decomposition (PBS + WBS)")
            logger.info("=" * 60)
            decomp_result = self.run_stage("decomposition", {
                "mission_name": mission_name,
                "requirements_set": requirements_set,
            })
            if not decomp_result.success:
                return self._build_workflow_result(
                    mission_name, False, start_time,
                    error=f"Decomposition stage failed: {decomp_result.error}"
                )

            # Extract PBS and WBS for next stage
            pbs = decomp_result.outputs.get("pbs", {})
            wbs = decomp_result.outputs.get("wbs", {})
            self._artifacts["pbs"] = pbs
            self._artifacts["wbs"] = wbs

            # Stage 3: Scheduling
            logger.info("=" * 60)
            logger.info("STAGE 3: Scheduling (Dependencies + Timeline)")
            logger.info("=" * 60)
            schedule_result = self.run_stage("scheduling", {
                "wbs": wbs,
                "start_date": mission_inputs.get("launch_target", None),
            })
            if not schedule_result.success:
                return self._build_workflow_result(
                    mission_name, False, start_time,
                    error=f"Scheduling stage failed: {schedule_result.error}"
                )

            # Extract final artifacts
            dependency_graph = schedule_result.outputs.get("dependency_graph", {})
            timeline = schedule_result.outputs.get("timeline", {})
            self._artifacts["dependency_graph"] = dependency_graph
            self._artifacts["timeline"] = timeline

            # Save artifacts if output directory specified
            if self.output_dir:
                self._save_artifacts()

            return self._build_workflow_result(
                mission_name, True, start_time
            )

        except Exception as e:
            logger.error(f"Pipeline failed with error: {e}", exc_info=True)
            return self._build_workflow_result(
                mission_name, False, start_time, error=str(e)
            )

    def run_stage(self, stage_name: str, inputs: Dict[str, Any]) -> StageResult:
        """Run a single stage of the pipeline.

        Args:
            stage_name: Name of the stage to run.
            inputs: Input data for the stage.

        Returns:
            StageResult from the stage execution.
        """
        if stage_name not in self.agents:
            return StageResult(
                stage_name=stage_name,
                success=False,
                error=f"Unknown stage: {stage_name}",
            )

        agent = self.agents[stage_name]
        start_time = datetime.now()

        # Create task for the agent
        task = Task(
            id=f"task-{stage_name}-{start_time.strftime('%Y%m%d%H%M%S')}",
            name=f"{stage_name.title()} Stage",
            description=f"Execute {stage_name} stage of SE pipeline",
            inputs=inputs,
        )

        # Execute using ReAct loop
        react_loop = ReActLoop(
            agent=agent,
            max_iterations=self.max_iterations_per_stage,
            trace_enabled=True,
        )

        result = react_loop.execute(task)

        # Build stage result
        execution_time = (datetime.now() - start_time).total_seconds()
        stage_result = StageResult(
            stage_name=stage_name,
            success=result.success,
            outputs=result.outputs,
            execution_time_seconds=execution_time,
            error=result.error,
            reasoning_trace=react_loop.get_trace_as_dicts(),
        )

        self._stage_results[stage_name] = stage_result
        logger.info(
            f"Stage '{stage_name}' completed: "
            f"{'success' if result.success else 'failed'} "
            f"({execution_time:.2f}s)"
        )

        return stage_result

    def _build_workflow_result(
        self,
        mission_name: str,
        success: bool,
        start_time: datetime,
        error: Optional[str] = None,
    ) -> WorkflowResult:
        """Build the final workflow result."""
        total_time = (datetime.now() - start_time).total_seconds()

        # Build summary
        summary = {
            "stages_completed": sum(
                1 for r in self._stage_results.values() if r.success
            ),
            "total_stages": len(self.STAGES),
        }

        if "requirements" in self._artifacts:
            reqs = self._artifacts["requirements"]
            summary["total_requirements"] = len(reqs.get("requirements", []))

        if "pbs" in self._artifacts:
            pbs = self._artifacts["pbs"]
            summary["total_pbs_nodes"] = len(pbs.get("nodes", {}))

        if "wbs" in self._artifacts:
            wbs = self._artifacts["wbs"]
            summary["total_work_packages"] = len(wbs.get("work_packages", {}))

        if "timeline" in self._artifacts:
            timeline = self._artifacts["timeline"]
            summary["project_duration_days"] = timeline.get("total_duration_days", 0)
            summary["project_end_date"] = timeline.get("project_end_date", "N/A")

        if error:
            summary["error"] = error

        return WorkflowResult(
            mission_name=mission_name,
            success=success,
            stage_results=self._stage_results,
            final_artifacts=self._artifacts,
            total_execution_time_seconds=total_time,
            summary=summary,
        )

    def _save_artifacts(self) -> None:
        """Save all artifacts to the output directory."""
        if not self.output_dir:
            return

        self.output_dir.mkdir(parents=True, exist_ok=True)

        for artifact_name, artifact_data in self._artifacts.items():
            if artifact_name == "mission_inputs":
                continue  # Don't re-save inputs

            file_path = self.output_dir / f"{artifact_name}.json"
            with open(file_path, "w") as f:
                json.dump(artifact_data, f, indent=2, default=str)

            logger.info(f"Saved artifact: {file_path}")

    def get_artifact(self, artifact_name: str) -> Optional[Any]:
        """Get a specific artifact by name."""
        return self._artifacts.get(artifact_name)

    def get_all_artifacts(self) -> Dict[str, Any]:
        """Get all generated artifacts."""
        return self._artifacts.copy()

    def get_stage_result(self, stage_name: str) -> Optional[StageResult]:
        """Get result from a specific stage."""
        return self._stage_results.get(stage_name)


def main():
    """CLI entry point for running the workflow."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Run the Astraeus Apertura SE workflow"
    )
    parser.add_argument(
        "mission_file",
        type=str,
        help="Path to mission inputs JSON file",
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default="./outputs",
        help="Output directory for artifacts",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    )

    # Load mission inputs
    try:
        with open(args.mission_file, "r") as f:
            mission_inputs = json.load(f)
    except Exception as e:
        print(f"Error loading mission file: {e}")
        sys.exit(1)

    # Run workflow
    workflow = SEWorkflow(output_dir=Path(args.output))
    result = workflow.run_pipeline(mission_inputs)

    # Print summary
    print("\n" + "=" * 60)
    print("WORKFLOW SUMMARY")
    print("=" * 60)
    print(f"Mission: {result.mission_name}")
    print(f"Success: {result.success}")
    print(f"Total Time: {result.total_execution_time_seconds:.2f}s")
    print("\nSummary:")
    for key, value in result.summary.items():
        print(f"  {key}: {value}")

    sys.exit(0 if result.success else 1)


if __name__ == "__main__":
    main()
