"""
Intelligent routing for directing tasks to appropriate agents.

Provides smart routing based on task characteristics, cost, latency,
and quality requirements.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from enum import Enum
from loguru import logger

from astraeus.orchestration.agent_registry import (
    AgentRegistry,
    AgentRegistration,
    AgentCapability,
    LLMProvider,
    get_global_registry,
)
from astraeus.core.message import Message


class RoutingStrategy(Enum):
    """Strategy for routing tasks to agents."""

    QUALITY_OPTIMIZED = "quality_optimized"  # Best quality, regardless of cost
    COST_OPTIMIZED = "cost_optimized"  # Lowest cost
    LATENCY_OPTIMIZED = "latency_optimized"  # Fastest response
    BALANCED = "balanced"  # Balance cost, latency, quality
    TASK_SPECIFIC = "task_specific"  # Route based on task characteristics
    LOAD_BALANCED = "load_balanced"  # Distribute load evenly
    PROVIDER_PREFERENCE = "provider_preference"  # Prefer specific providers


@dataclass
class RoutingDecision:
    """Decision about which agent(s) to use."""

    selected_agents: List[str]
    strategy_used: RoutingStrategy
    reasoning: str
    confidence: float = 1.0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class TaskCharacteristics:
    """Characteristics of a task for routing decisions."""

    complexity: float = 0.5  # 0.0 (simple) to 1.0 (complex)
    urgency: float = 0.5  # 0.0 (low) to 1.0 (high)
    cost_sensitivity: float = 0.5  # 0.0 (cost not important) to 1.0 (very cost sensitive)
    quality_requirement: float = 0.7  # 0.0 (low) to 1.0 (high)
    estimated_tokens: int = 1000
    requires_reasoning: bool = False
    requires_code: bool = False
    domain: Optional[str] = None


class AgentRouter:
    """
    Intelligent router for directing tasks to appropriate agents.

    Uses task characteristics, agent capabilities, and routing strategy
    to make optimal agent selection decisions.
    """

    def __init__(
        self,
        registry: Optional[AgentRegistry] = None,
        default_strategy: RoutingStrategy = RoutingStrategy.BALANCED,
    ):
        self.registry = registry or get_global_registry()
        self.default_strategy = default_strategy

        # Load tracking for load balancing
        self._agent_load: Dict[str, int] = {}

        # Provider preferences
        self._provider_preferences: List[LLMProvider] = []

        logger.info(f"Agent router initialized with strategy: {default_strategy.value}")

    def route(
        self,
        capability: AgentCapability,
        task_chars: Optional[TaskCharacteristics] = None,
        strategy: Optional[RoutingStrategy] = None,
        num_agents: int = 1,
    ) -> RoutingDecision:
        """
        Route a task to appropriate agent(s).

        Args:
            capability: Required agent capability
            task_chars: Task characteristics for routing
            strategy: Routing strategy (overrides default)
            num_agents: Number of agents to select

        Returns:
            Routing decision with selected agents
        """
        strategy = strategy or self.default_strategy
        task_chars = task_chars or TaskCharacteristics()

        # Get candidate agents
        candidates = self.registry.find_by_capability(capability)

        if not candidates:
            logger.warning(f"No agents found for capability {capability.value}")
            return RoutingDecision(
                selected_agents=[],
                strategy_used=strategy,
                reasoning="No agents available for capability",
                confidence=0.0,
            )

        # Apply routing strategy
        if strategy == RoutingStrategy.QUALITY_OPTIMIZED:
            decision = self._route_quality_optimized(candidates, task_chars, num_agents)
        elif strategy == RoutingStrategy.COST_OPTIMIZED:
            decision = self._route_cost_optimized(candidates, task_chars, num_agents)
        elif strategy == RoutingStrategy.LATENCY_OPTIMIZED:
            decision = self._route_latency_optimized(candidates, task_chars, num_agents)
        elif strategy == RoutingStrategy.BALANCED:
            decision = self._route_balanced(candidates, task_chars, num_agents)
        elif strategy == RoutingStrategy.TASK_SPECIFIC:
            decision = self._route_task_specific(candidates, task_chars, num_agents)
        elif strategy == RoutingStrategy.LOAD_BALANCED:
            decision = self._route_load_balanced(candidates, task_chars, num_agents)
        elif strategy == RoutingStrategy.PROVIDER_PREFERENCE:
            decision = self._route_provider_preference(candidates, task_chars, num_agents)
        else:
            decision = self._route_balanced(candidates, task_chars, num_agents)

        decision.strategy_used = strategy

        # Update load tracking
        for agent_id in decision.selected_agents:
            self._agent_load[agent_id] = self._agent_load.get(agent_id, 0) + 1

        logger.info(
            f"Routed to {len(decision.selected_agents)} agent(s) using {strategy.value}: "
            f"{decision.reasoning}"
        )

        return decision

    def _route_quality_optimized(
        self,
        candidates: List[AgentRegistration],
        task_chars: TaskCharacteristics,
        num_agents: int,
    ) -> RoutingDecision:
        """Route to highest quality agents."""
        # Sort by reliability score
        sorted_agents = sorted(candidates, key=lambda a: a.reliability_score, reverse=True)
        selected = sorted_agents[:num_agents]

        return RoutingDecision(
            selected_agents=[a.agent_id for a in selected],
            strategy_used=RoutingStrategy.QUALITY_OPTIMIZED,
            reasoning=f"Selected {len(selected)} highest reliability agents",
            confidence=sum(a.reliability_score for a in selected) / len(selected) if selected else 0.0,
            metadata={'reliability_scores': [a.reliability_score for a in selected]},
        )

    def _route_cost_optimized(
        self,
        candidates: List[AgentRegistration],
        task_chars: TaskCharacteristics,
        num_agents: int,
    ) -> RoutingDecision:
        """Route to lowest cost agents."""
        # Sort by cost per token
        sorted_agents = sorted(candidates, key=lambda a: a.cost_per_1k_tokens)
        selected = sorted_agents[:num_agents]

        estimated_cost = sum(
            a.cost_per_1k_tokens * (task_chars.estimated_tokens / 1000)
            for a in selected
        )

        return RoutingDecision(
            selected_agents=[a.agent_id for a in selected],
            strategy_used=RoutingStrategy.COST_OPTIMIZED,
            reasoning=f"Selected {len(selected)} lowest cost agents (estimated ${estimated_cost:.4f})",
            confidence=0.8,
            metadata={'estimated_cost': estimated_cost, 'costs': [a.cost_per_1k_tokens for a in selected]},
        )

    def _route_latency_optimized(
        self,
        candidates: List[AgentRegistration],
        task_chars: TaskCharacteristics,
        num_agents: int,
    ) -> RoutingDecision:
        """Route to fastest agents."""
        # Sort by latency
        sorted_agents = sorted(candidates, key=lambda a: a.avg_latency_ms)
        selected = sorted_agents[:num_agents]

        avg_latency = sum(a.avg_latency_ms for a in selected) / len(selected) if selected else 0.0

        return RoutingDecision(
            selected_agents=[a.agent_id for a in selected],
            strategy_used=RoutingStrategy.LATENCY_OPTIMIZED,
            reasoning=f"Selected {len(selected)} fastest agents (avg {avg_latency:.1f}ms)",
            confidence=0.9,
            metadata={'avg_latency_ms': avg_latency, 'latencies': [a.avg_latency_ms for a in selected]},
        )

    def _route_balanced(
        self,
        candidates: List[AgentRegistration],
        task_chars: TaskCharacteristics,
        num_agents: int,
    ) -> RoutingDecision:
        """Route with balanced consideration of cost, latency, and quality."""

        # Calculate composite score
        def score_agent(agent: AgentRegistration) -> float:
            # Normalize metrics (0 to 1, higher is better)
            max_latency = max((a.avg_latency_ms for a in candidates), default=1000.0)
            max_cost = max((a.cost_per_1k_tokens for a in candidates), default=1.0)

            latency_score = 1.0 - (agent.avg_latency_ms / max_latency) if max_latency > 0 else 1.0
            cost_score = 1.0 - (agent.cost_per_1k_tokens / max_cost) if max_cost > 0 else 1.0
            quality_score = agent.reliability_score

            # Weighted combination
            weights = {
                'quality': 0.4,
                'latency': 0.3,
                'cost': 0.3,
            }

            composite = (
                weights['quality'] * quality_score +
                weights['latency'] * latency_score +
                weights['cost'] * cost_score
            )

            return composite

        # Sort by composite score
        sorted_agents = sorted(candidates, key=score_agent, reverse=True)
        selected = sorted_agents[:num_agents]

        avg_score = sum(score_agent(a) for a in selected) / len(selected) if selected else 0.0

        return RoutingDecision(
            selected_agents=[a.agent_id for a in selected],
            strategy_used=RoutingStrategy.BALANCED,
            reasoning=f"Selected {len(selected)} agents with balanced cost/latency/quality (score: {avg_score:.2f})",
            confidence=avg_score,
            metadata={'composite_scores': [score_agent(a) for a in selected]},
        )

    def _route_task_specific(
        self,
        candidates: List[AgentRegistration],
        task_chars: TaskCharacteristics,
        num_agents: int,
    ) -> RoutingDecision:
        """Route based on specific task characteristics."""

        def score_agent(agent: AgentRegistration) -> float:
            score = 0.0

            # High complexity tasks -> prefer high-capability models
            if task_chars.complexity > 0.7:
                if agent.provider == LLMProvider.ANTHROPIC:
                    score += 0.3  # Claude excels at complex reasoning
                if agent.max_tokens >= 8192:
                    score += 0.2  # Need larger context

            # High urgency -> prefer fast models
            if task_chars.urgency > 0.7:
                max_latency = max((a.avg_latency_ms for a in candidates), default=1000.0)
                latency_score = 1.0 - (agent.avg_latency_ms / max_latency) if max_latency > 0 else 1.0
                score += 0.3 * latency_score

            # Cost sensitive -> prefer cheaper models
            if task_chars.cost_sensitivity > 0.7:
                max_cost = max((a.cost_per_1k_tokens for a in candidates), default=1.0)
                cost_score = 1.0 - (agent.cost_per_1k_tokens / max_cost) if max_cost > 0 else 1.0
                score += 0.3 * cost_score

            # High quality requirement -> prefer reliable models
            if task_chars.quality_requirement > 0.7:
                score += 0.4 * agent.reliability_score

            # Reasoning tasks -> prefer specific models
            if task_chars.requires_reasoning:
                if agent.provider in [LLMProvider.ANTHROPIC, LLMProvider.OPENAI]:
                    score += 0.2

            # Code generation -> prefer code-capable models
            if task_chars.requires_code:
                if agent.supports_function_calling:
                    score += 0.2

            # Base reliability
            score += 0.2 * agent.reliability_score

            return score

        # Sort by task-specific score
        sorted_agents = sorted(candidates, key=score_agent, reverse=True)
        selected = sorted_agents[:num_agents]

        return RoutingDecision(
            selected_agents=[a.agent_id for a in selected],
            strategy_used=RoutingStrategy.TASK_SPECIFIC,
            reasoning=f"Selected {len(selected)} agents optimized for task characteristics",
            confidence=0.85,
            metadata={
                'task_complexity': task_chars.complexity,
                'task_urgency': task_chars.urgency,
                'scores': [score_agent(a) for a in selected],
            },
        )

    def _route_load_balanced(
        self,
        candidates: List[AgentRegistration],
        task_chars: TaskCharacteristics,
        num_agents: int,
    ) -> RoutingDecision:
        """Route to distribute load evenly across agents."""

        # Sort by current load (ascending)
        sorted_agents = sorted(
            candidates,
            key=lambda a: self._agent_load.get(a.agent_id, 0)
        )
        selected = sorted_agents[:num_agents]

        current_loads = [self._agent_load.get(a.agent_id, 0) for a in selected]

        return RoutingDecision(
            selected_agents=[a.agent_id for a in selected],
            strategy_used=RoutingStrategy.LOAD_BALANCED,
            reasoning=f"Selected {len(selected)} least loaded agents",
            confidence=0.8,
            metadata={'current_loads': current_loads},
        )

    def _route_provider_preference(
        self,
        candidates: List[AgentRegistration],
        task_chars: TaskCharacteristics,
        num_agents: int,
    ) -> RoutingDecision:
        """Route with provider preferences."""

        # Filter by preferred providers if set
        if self._provider_preferences:
            preferred = [
                a for a in candidates
                if a.provider in self._provider_preferences
            ]
            if preferred:
                candidates = preferred

        # Use balanced routing on filtered candidates
        return self._route_balanced(candidates, task_chars, num_agents)

    def set_provider_preferences(self, preferences: List[LLMProvider]) -> None:
        """Set preferred providers for routing."""
        self._provider_preferences = preferences
        logger.info(f"Set provider preferences: {[p.value for p in preferences]}")

    def reset_load_tracking(self) -> None:
        """Reset load tracking counters."""
        self._agent_load.clear()
        logger.info("Load tracking reset")

    def get_load_statistics(self) -> Dict[str, int]:
        """Get current load statistics."""
        return dict(self._agent_load)

    def decrement_load(self, agent_id: str) -> None:
        """Decrement load for an agent (when task completes)."""
        if agent_id in self._agent_load:
            self._agent_load[agent_id] = max(0, self._agent_load[agent_id] - 1)


def create_router(
    strategy: RoutingStrategy = RoutingStrategy.BALANCED,
    registry: Optional[AgentRegistry] = None,
) -> AgentRouter:
    """Create an agent router with specified strategy."""
    return AgentRouter(registry=registry, default_strategy=strategy)
