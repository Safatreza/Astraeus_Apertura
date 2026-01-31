"""Base agent class implementing the ReAct paradigm.

This module provides the foundational classes for building agents
that follow the Reason + Act pattern for systems engineering tasks.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TypeVar

from pydantic import BaseModel, Field


# Configure logging for reasoning traces
logger = logging.getLogger("astraeus.agents")


class TaskStatus(str, Enum):
    """Status of a task."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class Task(BaseModel):
    """A task for an agent to execute.

    Attributes:
        id: Unique task identifier.
        name: Human-readable task name.
        description: Detailed description of what to accomplish.
        inputs: Input data for the task.
        expected_outputs: Description of expected outputs.
        status: Current task status.
        created_at: When the task was created.
    """

    id: str
    name: str
    description: str
    inputs: Dict[str, Any] = Field(default_factory=dict)
    expected_outputs: List[str] = Field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.now)


class Thought(BaseModel):
    """A reasoning step in the ReAct loop.

    Represents the agent's internal reasoning about the current
    state, what action to take, and why.

    Attributes:
        content: The reasoning text.
        observation_summary: Summary of what was observed.
        next_action_rationale: Why the next action was chosen.
        confidence: Confidence level (0-1) in the reasoning.
        timestamp: When this thought occurred.
    """

    content: str
    observation_summary: Optional[str] = None
    next_action_rationale: Optional[str] = None
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    timestamp: datetime = Field(default_factory=datetime.now)


class Action(BaseModel):
    """An action to be executed by the agent.

    Attributes:
        tool_name: Name of the tool to invoke.
        parameters: Parameters to pass to the tool.
        rationale: Why this action was chosen.
    """

    tool_name: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    rationale: str = ""


class ToolResult(BaseModel):
    """Result from executing a tool.

    Attributes:
        success: Whether the tool executed successfully.
        data: Output data from the tool.
        error: Error message if failed.
    """

    success: bool
    data: Any = None
    error: Optional[str] = None


class Observation(BaseModel):
    """An observation from executing an action.

    Represents what the agent observed after taking an action.

    Attributes:
        action: The action that was executed.
        result: Result from the tool execution.
        interpretation: Agent's interpretation of the result.
        timestamp: When this observation was made.
    """

    action: Action
    result: ToolResult
    interpretation: str = ""
    timestamp: datetime = Field(default_factory=datetime.now)


class Result(BaseModel):
    """Final result of task execution.

    Attributes:
        task_id: ID of the task that was executed.
        success: Whether the task completed successfully.
        outputs: Output data from the task.
        thoughts: List of reasoning steps.
        observations: List of observations made.
        error: Error message if failed.
        execution_time_seconds: Total execution time.
    """

    task_id: str
    success: bool
    outputs: Dict[str, Any] = Field(default_factory=dict)
    thoughts: List[Thought] = Field(default_factory=list)
    observations: List[Observation] = Field(default_factory=list)
    error: Optional[str] = None
    execution_time_seconds: float = 0.0


@dataclass
class Tool:
    """A tool that an agent can use.

    Attributes:
        name: Unique tool identifier.
        description: What the tool does.
        parameters_schema: JSON schema for parameters.
        function: The callable that implements the tool.
    """

    name: str
    description: str
    parameters_schema: Dict[str, Any]
    function: Callable[..., ToolResult]

    def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given parameters."""
        try:
            return self.function(**kwargs)
        except Exception as e:
            logger.error(f"Tool {self.name} failed: {e}")
            return ToolResult(success=False, error=str(e))


class BaseAgent(ABC):
    """Base class for ReAct agents.

    Implements the core Reason + Act loop pattern. Subclasses should
    implement the abstract methods to provide domain-specific behavior.

    Attributes:
        name: Agent name for identification and logging.
        tools: List of tools available to this agent.
        max_iterations: Maximum ReAct loop iterations.
        trace_enabled: Whether to log detailed reasoning traces.
    """

    def __init__(
        self,
        name: str,
        tools: Optional[List[Tool]] = None,
        max_iterations: int = 10,
        trace_enabled: bool = True,
    ):
        """Initialize the agent.

        Args:
            name: Agent name.
            tools: List of available tools.
            max_iterations: Max iterations before stopping.
            trace_enabled: Enable reasoning trace logging.
        """
        self.name = name
        self.tools = {tool.name: tool for tool in (tools or [])}
        self.max_iterations = max_iterations
        self.trace_enabled = trace_enabled
        self._current_context: Dict[str, Any] = {}
        self._thought_history: List[Thought] = []
        self._observation_history: List[Observation] = []

        self.logger = logging.getLogger(f"astraeus.agents.{name}")

    def add_tool(self, tool: Tool) -> None:
        """Add a tool to the agent's toolkit."""
        self.tools[tool.name] = tool
        self.logger.info(f"Added tool: {tool.name}")

    def get_tool(self, tool_name: str) -> Optional[Tool]:
        """Get a tool by name."""
        return self.tools.get(tool_name)

    def list_tools(self) -> List[str]:
        """List available tool names."""
        return list(self.tools.keys())

    @abstractmethod
    def reason(self, context: Dict[str, Any]) -> Thought:
        """Generate a reasoning step based on current context.

        This is the "Reason" part of ReAct. Subclasses should implement
        domain-specific reasoning logic.

        Args:
            context: Current execution context including task,
                    previous thoughts, and observations.

        Returns:
            A Thought containing the reasoning.
        """
        pass

    @abstractmethod
    def select_action(self, thought: Thought, context: Dict[str, Any]) -> Optional[Action]:
        """Select the next action based on reasoning.

        Subclasses should implement logic to choose the appropriate
        tool and parameters based on the current thought.

        Args:
            thought: The current reasoning step.
            context: Current execution context.

        Returns:
            An Action to execute, or None if task is complete.
        """
        pass

    def act(self, action: Action) -> Observation:
        """Execute an action and return the observation.

        This is the "Act" part of ReAct.

        Args:
            action: The action to execute.

        Returns:
            An Observation of the action's result.
        """
        self.logger.info(f"Executing action: {action.tool_name}")

        tool = self.get_tool(action.tool_name)
        if tool is None:
            result = ToolResult(
                success=False,
                error=f"Unknown tool: {action.tool_name}"
            )
        else:
            result = tool.execute(**action.parameters)

        observation = Observation(
            action=action,
            result=result,
            interpretation=self._interpret_result(action, result),
        )

        self._observation_history.append(observation)
        self.logger.debug(f"Observation: {observation.interpretation}")

        return observation

    def _interpret_result(self, action: Action, result: ToolResult) -> str:
        """Generate an interpretation of a tool result.

        Can be overridden by subclasses for domain-specific interpretation.
        """
        if result.success:
            return f"Successfully executed {action.tool_name}"
        else:
            return f"Failed to execute {action.tool_name}: {result.error}"

    def _is_task_complete(self, context: Dict[str, Any]) -> bool:
        """Check if the current task is complete.

        Can be overridden by subclasses for custom completion logic.
        """
        return context.get("task_complete", False)

    def _build_context(self, task: Task) -> Dict[str, Any]:
        """Build the execution context for a task."""
        return {
            "task": task,
            "thoughts": self._thought_history.copy(),
            "observations": self._observation_history.copy(),
            "iteration": 0,
            "task_complete": False,
        }

    def _log_trace(self, iteration: int, thought: Thought, action: Optional[Action], observation: Optional[Observation]) -> None:
        """Log a reasoning trace for debugging and auditing."""
        if not self.trace_enabled:
            return

        self.logger.info(
            f"\n{'='*60}\n"
            f"ITERATION {iteration}\n"
            f"{'='*60}\n"
            f"THOUGHT:\n{thought.content}\n"
            f"{'-'*30}\n"
            f"ACTION: {action.tool_name if action else 'None'}\n"
            f"PARAMETERS: {action.parameters if action else {}}\n"
            f"{'-'*30}\n"
            f"OBSERVATION: {observation.interpretation if observation else 'None'}\n"
            f"{'='*60}"
        )

    def run(self, task: Task) -> Result:
        """Execute a task using the ReAct loop.

        The core execution loop:
        1. Reason about current state
        2. Select an action
        3. Execute the action
        4. Observe the result
        5. Repeat until complete or max iterations

        Args:
            task: The task to execute.

        Returns:
            Result containing outputs and execution trace.
        """
        start_time = datetime.now()
        self.logger.info(f"Starting task: {task.name}")

        # Initialize
        self._thought_history = []
        self._observation_history = []
        context = self._build_context(task)

        try:
            for iteration in range(self.max_iterations):
                context["iteration"] = iteration
                self.logger.debug(f"Iteration {iteration + 1}/{self.max_iterations}")

                # Reason
                thought = self.reason(context)
                self._thought_history.append(thought)
                context["thoughts"] = self._thought_history.copy()

                # Check completion
                if self._is_task_complete(context):
                    self.logger.info("Task completed successfully")
                    break

                # Select action
                action = self.select_action(thought, context)
                if action is None:
                    # No action means task is complete
                    context["task_complete"] = True
                    self._log_trace(iteration, thought, None, None)
                    break

                # Act
                observation = self.act(action)
                context["observations"] = self._observation_history.copy()

                # Log trace
                self._log_trace(iteration, thought, action, observation)

                # Update context based on observation
                self._update_context(context, observation)

            else:
                self.logger.warning(f"Max iterations ({self.max_iterations}) reached")

            # Build result
            execution_time = (datetime.now() - start_time).total_seconds()
            return Result(
                task_id=task.id,
                success=context.get("task_complete", False),
                outputs=context.get("outputs", {}),
                thoughts=self._thought_history,
                observations=self._observation_history,
                execution_time_seconds=execution_time,
            )

        except Exception as e:
            self.logger.error(f"Task failed with error: {e}")
            execution_time = (datetime.now() - start_time).total_seconds()
            return Result(
                task_id=task.id,
                success=False,
                outputs={},
                thoughts=self._thought_history,
                observations=self._observation_history,
                error=str(e),
                execution_time_seconds=execution_time,
            )

    def _update_context(self, context: Dict[str, Any], observation: Observation) -> None:
        """Update context based on an observation.

        Subclasses can override to implement custom context updates.
        """
        # Check if the observation indicates completion
        if observation.result.success:
            outputs = context.get("outputs", {})
            if observation.result.data:
                if isinstance(observation.result.data, dict):
                    outputs.update(observation.result.data)
                else:
                    outputs[observation.action.tool_name] = observation.result.data
            context["outputs"] = outputs

    def reset(self) -> None:
        """Reset agent state for a new task."""
        self._thought_history = []
        self._observation_history = []
        self._current_context = {}
        self.logger.debug("Agent state reset")
