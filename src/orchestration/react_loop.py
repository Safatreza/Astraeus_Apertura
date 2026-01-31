"""ReAct loop implementation for agent execution.

This module provides a standalone ReAct loop executor that can be used
to run any agent with detailed trace logging and configurable behavior.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from agents.base_agent import (
    Action,
    BaseAgent,
    Observation,
    Result,
    Task,
    Thought,
)


logger = logging.getLogger("astraeus.orchestration.react")


@dataclass
class TraceEntry:
    """A single entry in the reasoning trace."""

    iteration: int
    timestamp: datetime
    thought: Thought
    action: Optional[Action]
    observation: Optional[Observation]
    context_snapshot: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "iteration": self.iteration,
            "timestamp": self.timestamp.isoformat(),
            "thought": {
                "content": self.thought.content,
                "observation_summary": self.thought.observation_summary,
                "next_action_rationale": self.thought.next_action_rationale,
                "confidence": self.thought.confidence,
            },
            "action": {
                "tool_name": self.action.tool_name,
                "parameters": self.action.parameters,
                "rationale": self.action.rationale,
            } if self.action else None,
            "observation": {
                "success": self.observation.result.success,
                "interpretation": self.observation.interpretation,
                "error": self.observation.result.error,
            } if self.observation else None,
        }


class ReActLoop:
    """Standalone ReAct loop executor.

    Provides a configurable execution environment for running agents
    with detailed trace logging, callbacks, and termination conditions.

    Attributes:
        agent: The agent to execute.
        max_iterations: Maximum number of iterations.
        trace_enabled: Whether to record detailed traces.
        on_thought: Callback for each thought.
        on_action: Callback for each action.
        on_observation: Callback for each observation.
    """

    def __init__(
        self,
        agent: BaseAgent,
        max_iterations: int = 10,
        trace_enabled: bool = True,
        on_thought: Optional[Callable[[Thought, int], None]] = None,
        on_action: Optional[Callable[[Action, int], None]] = None,
        on_observation: Optional[Callable[[Observation, int], None]] = None,
        termination_check: Optional[Callable[[Dict[str, Any]], bool]] = None,
    ):
        """Initialize the ReAct loop.

        Args:
            agent: The agent to execute tasks with.
            max_iterations: Maximum iterations before stopping.
            trace_enabled: Enable detailed trace recording.
            on_thought: Callback invoked after each thought.
            on_action: Callback invoked before each action.
            on_observation: Callback invoked after each observation.
            termination_check: Custom function to check if task is complete.
        """
        self.agent = agent
        self.max_iterations = max_iterations
        self.trace_enabled = trace_enabled
        self.on_thought = on_thought
        self.on_action = on_action
        self.on_observation = on_observation
        self.termination_check = termination_check

        self._trace: List[TraceEntry] = []
        self._context: Dict[str, Any] = {}

    def execute(self, task: Task) -> Result:
        """Execute a task using the ReAct loop.

        The execution follows the pattern:
        1. Reason about the current state (Thought)
        2. Select an action based on reasoning (Action)
        3. Execute the action and observe results (Observation)
        4. Repeat until complete or max iterations

        Args:
            task: The task to execute.

        Returns:
            Result containing outputs and execution trace.
        """
        start_time = datetime.now()
        logger.info(f"ReActLoop starting task: {task.name}")

        # Initialize
        self._trace = []
        self._context = self._build_initial_context(task)
        self.agent.reset()

        try:
            for iteration in range(self.max_iterations):
                self._context["iteration"] = iteration
                logger.debug(f"Iteration {iteration + 1}/{self.max_iterations}")

                # Phase 1: Reason
                thought = self.agent.reason(self._context)
                self._context["thoughts"].append(thought)

                if self.on_thought:
                    self.on_thought(thought, iteration)

                logger.info(f"[Thought {iteration}] {thought.content[:200]}...")

                # Check custom termination
                if self._should_terminate():
                    logger.info("Custom termination condition met")
                    break

                # Phase 2: Select Action
                action = self.agent.select_action(thought, self._context)

                if action is None:
                    # No action means task is complete
                    self._record_trace(iteration, thought, None, None)
                    self._context["task_complete"] = True
                    logger.info("No action selected - task complete")
                    break

                if self.on_action:
                    self.on_action(action, iteration)

                logger.info(f"[Action {iteration}] {action.tool_name}({list(action.parameters.keys())})")

                # Phase 3: Execute Action
                observation = self.agent.act(action)
                self._context["observations"].append(observation)

                if self.on_observation:
                    self.on_observation(observation, iteration)

                logger.info(
                    f"[Observation {iteration}] "
                    f"{'Success' if observation.result.success else 'Failed'}: "
                    f"{observation.interpretation[:100]}..."
                )

                # Record trace
                self._record_trace(iteration, thought, action, observation)

                # Update context
                self._update_context(observation)

            else:
                logger.warning(f"Max iterations ({self.max_iterations}) reached")

            # Build result
            execution_time = (datetime.now() - start_time).total_seconds()

            return Result(
                task_id=task.id,
                success=self._context.get("task_complete", False),
                outputs=self._context.get("outputs", {}),
                thoughts=self._context.get("thoughts", []),
                observations=self._context.get("observations", []),
                execution_time_seconds=execution_time,
            )

        except Exception as e:
            logger.error(f"ReActLoop failed: {e}", exc_info=True)
            execution_time = (datetime.now() - start_time).total_seconds()

            return Result(
                task_id=task.id,
                success=False,
                outputs={},
                thoughts=self._context.get("thoughts", []),
                observations=self._context.get("observations", []),
                error=str(e),
                execution_time_seconds=execution_time,
            )

    def _build_initial_context(self, task: Task) -> Dict[str, Any]:
        """Build the initial execution context."""
        return {
            "task": task,
            "thoughts": [],
            "observations": [],
            "outputs": {},
            "iteration": 0,
            "task_complete": False,
        }

    def _should_terminate(self) -> bool:
        """Check if execution should terminate."""
        if self._context.get("task_complete", False):
            return True

        if self.termination_check:
            return self.termination_check(self._context)

        return False

    def _record_trace(
        self,
        iteration: int,
        thought: Thought,
        action: Optional[Action],
        observation: Optional[Observation],
    ) -> None:
        """Record a trace entry."""
        if not self.trace_enabled:
            return

        entry = TraceEntry(
            iteration=iteration,
            timestamp=datetime.now(),
            thought=thought,
            action=action,
            observation=observation,
            context_snapshot={
                "outputs_keys": list(self._context.get("outputs", {}).keys()),
                "thought_count": len(self._context.get("thoughts", [])),
                "observation_count": len(self._context.get("observations", [])),
            },
        )
        self._trace.append(entry)

    def _update_context(self, observation: Observation) -> None:
        """Update context based on observation."""
        if observation.result.success and observation.result.data:
            outputs = self._context.get("outputs", {})
            if isinstance(observation.result.data, dict):
                outputs.update(observation.result.data)
            else:
                outputs[observation.action.tool_name] = observation.result.data
            self._context["outputs"] = outputs

    def get_trace(self) -> List[TraceEntry]:
        """Get the execution trace."""
        return self._trace.copy()

    def get_trace_as_dicts(self) -> List[Dict[str, Any]]:
        """Get the execution trace as dictionaries."""
        return [entry.to_dict() for entry in self._trace]

    def print_trace(self) -> None:
        """Print a formatted trace to the logger."""
        for entry in self._trace:
            logger.info(
                f"\n{'='*60}\n"
                f"ITERATION {entry.iteration}\n"
                f"{'='*60}\n"
                f"THOUGHT: {entry.thought.content}\n"
                f"ACTION: {entry.action.tool_name if entry.action else 'None'}\n"
                f"OBSERVATION: {entry.observation.interpretation if entry.observation else 'None'}\n"
            )


class ReActLoopBuilder:
    """Builder for configuring ReActLoop instances."""

    def __init__(self, agent: BaseAgent):
        """Initialize builder with an agent."""
        self._agent = agent
        self._max_iterations = 10
        self._trace_enabled = True
        self._on_thought = None
        self._on_action = None
        self._on_observation = None
        self._termination_check = None

    def max_iterations(self, n: int) -> "ReActLoopBuilder":
        """Set maximum iterations."""
        self._max_iterations = n
        return self

    def disable_trace(self) -> "ReActLoopBuilder":
        """Disable trace recording."""
        self._trace_enabled = False
        return self

    def on_thought(self, callback: Callable[[Thought, int], None]) -> "ReActLoopBuilder":
        """Set thought callback."""
        self._on_thought = callback
        return self

    def on_action(self, callback: Callable[[Action, int], None]) -> "ReActLoopBuilder":
        """Set action callback."""
        self._on_action = callback
        return self

    def on_observation(self, callback: Callable[[Observation, int], None]) -> "ReActLoopBuilder":
        """Set observation callback."""
        self._on_observation = callback
        return self

    def termination_check(self, check: Callable[[Dict[str, Any]], bool]) -> "ReActLoopBuilder":
        """Set custom termination check."""
        self._termination_check = check
        return self

    def build(self) -> ReActLoop:
        """Build the configured ReActLoop."""
        return ReActLoop(
            agent=self._agent,
            max_iterations=self._max_iterations,
            trace_enabled=self._trace_enabled,
            on_thought=self._on_thought,
            on_action=self._on_action,
            on_observation=self._on_observation,
            termination_check=self._termination_check,
        )
