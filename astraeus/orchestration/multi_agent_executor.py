"""
Multi-Agent Executor - High-level orchestration of multiple agents.

Combines routing, pooling, and consensus to execute tasks using
multiple LLM agents from different providers.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from loguru import logger

from astraeus.core.message import Message, MessageType
from astraeus.orchestration.agent_registry import (
    AgentRegistry,
    AgentCapability,
    get_global_registry,
)
from astraeus.orchestration.agent_pool import (
    AgentPool,
    AgentPoolConfig,
    PoolStrategy,
    PoolExecutionResult,
)
from astraeus.orchestration.consensus import (
    ConsensusEngine,
    VotingStrategy,
    AgentOutput,
    ConsensusResult,
)
from astraeus.orchestration.router import (
    AgentRouter,
    RoutingStrategy,
    TaskCharacteristics,
)


@dataclass
class MultiAgentConfig:
    """Configuration for multi-agent execution."""

    # Routing
    routing_strategy: RoutingStrategy = RoutingStrategy.BALANCED

    # Pool strategy
    pool_strategy: PoolStrategy = PoolStrategy.SINGLE_BEST

    # Consensus
    voting_strategy: VotingStrategy = VotingStrategy.WEIGHTED
    consensus_threshold: float = 0.7

    # Performance
    timeout_seconds: float = 60.0
    max_retries: int = 3
    enable_fallback: bool = True

    # Cost controls
    max_cost_per_task: Optional[float] = None
    prefer_cost_optimization: bool = False


@dataclass
class MultiAgentResult:
    """Result from multi-agent execution."""

    success: bool
    final_result: Any
    consensus_result: Optional[ConsensusResult] = None
    pool_result: Optional[PoolExecutionResult] = None

    # Metadata
    agents_used: List[str] = field(default_factory=list)
    total_latency_ms: float = 0.0
    total_cost: float = 0.0
    routing_decision: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class MultiAgentExecutor:
    """
    High-level executor for multi-agent tasks.

    Orchestrates routing, pooling, and consensus across multiple
    LLM agents from OpenAI, Anthropic, and other providers.
    """

    def __init__(
        self,
        config: Optional[MultiAgentConfig] = None,
        registry: Optional[AgentRegistry] = None,
    ):
        self.config = config or MultiAgentConfig()
        self.registry = registry or get_global_registry()

        # Create router
        self.router = AgentRouter(
            registry=self.registry,
            default_strategy=self.config.routing_strategy,
        )

        # Create consensus engine
        self.consensus = ConsensusEngine(
            strategy=self.config.voting_strategy,
            confidence_threshold=self.config.consensus_threshold,
        )

        # Agent pools by capability
        self._pools: Dict[AgentCapability, AgentPool] = {}

        logger.info("Multi-agent executor initialized")

    def execute(
        self,
        capability: AgentCapability,
        message: Message,
        task_chars: Optional[TaskCharacteristics] = None,
        use_consensus: bool = False,
        **kwargs
    ) -> MultiAgentResult:
        """
        Execute a task using multiple agents.

        Args:
            capability: Required agent capability
            message: Input message
            task_chars: Task characteristics for routing
            use_consensus: Whether to use consensus from multiple agents
            **kwargs: Additional arguments for agents

        Returns:
            Multi-agent result
        """
        logger.info(f"Executing task with capability: {capability.value}")

        # Get or create pool for capability
        pool = self._get_or_create_pool(capability)

        if len(pool) == 0:
            logger.error(f"No agents available for capability {capability.value}")
            return MultiAgentResult(
                success=False,
                final_result=None,
                metadata={'error': 'No agents available'},
            )

        # Execute on pool
        pool_result = pool.execute(message, **kwargs)

        # If using consensus, process multiple results
        if use_consensus and len(pool_result.individual_results) > 1:
            # Convert to AgentOutput format
            agent_outputs = []
            for exec_result in pool_result.individual_results:
                if exec_result.success:
                    agent_outputs.append(AgentOutput(
                        agent_id=exec_result.agent_id,
                        result=exec_result.result,
                        confidence=0.8,  # Could extract from result
                        reliability=self.registry.get(exec_result.agent_id).reliability_score if self.registry.get(exec_result.agent_id) else 1.0,
                    ))

            # Reach consensus
            consensus_result = self.consensus.reach_consensus(agent_outputs)

            return MultiAgentResult(
                success=consensus_result.confidence >= self.config.consensus_threshold,
                final_result=consensus_result.final_result,
                consensus_result=consensus_result,
                pool_result=pool_result,
                agents_used=[o.agent_id for o in agent_outputs],
                total_latency_ms=pool_result.total_latency_ms,
                total_cost=pool_result.total_cost,
                metadata={
                    'consensus_confidence': consensus_result.confidence,
                    'agreement_level': consensus_result.agreement_level,
                },
            )
        else:
            # Single agent or all-parallel without consensus
            return MultiAgentResult(
                success=pool_result.success,
                final_result=pool_result.final_result,
                pool_result=pool_result,
                agents_used=[r.agent_id for r in pool_result.individual_results],
                total_latency_ms=pool_result.total_latency_ms,
                total_cost=pool_result.total_cost,
            )

    def execute_with_routing(
        self,
        capability: AgentCapability,
        message: Message,
        task_chars: Optional[TaskCharacteristics] = None,
        **kwargs
    ) -> MultiAgentResult:
        """
        Execute with intelligent routing.

        Routes to best agent(s) based on task characteristics.
        """
        task_chars = task_chars or TaskCharacteristics()

        # Get routing decision
        num_agents = 1
        if self.config.pool_strategy in [PoolStrategy.ALL_PARALLEL, PoolStrategy.RACE, PoolStrategy.MAJORITY_VOTE]:
            num_agents = 3  # Default to 3 agents for multi-agent strategies

        routing_decision = self.router.route(
            capability=capability,
            task_chars=task_chars,
            num_agents=num_agents,
        )

        logger.info(f"Routing decision: {routing_decision.reasoning}")

        # Execute on selected agents
        result = self.execute(
            capability=capability,
            message=message,
            task_chars=task_chars,
            use_consensus=(num_agents > 1),
            **kwargs
        )

        result.routing_decision = routing_decision.reasoning
        return result

    def execute_with_fallback(
        self,
        capability: AgentCapability,
        message: Message,
        max_attempts: int = 3,
        **kwargs
    ) -> MultiAgentResult:
        """
        Execute with automatic fallback on failure.

        Tries multiple agents if initial attempts fail.
        """
        pool = self._get_or_create_pool(capability)

        last_result = None
        for attempt in range(max_attempts):
            logger.info(f"Execution attempt {attempt + 1}/{max_attempts}")

            result = self.execute(
                capability=capability,
                message=message,
                **kwargs
            )

            if result.success:
                return result

            last_result = result
            logger.warning(f"Attempt {attempt + 1} failed, trying fallback")

        return last_result or MultiAgentResult(
            success=False,
            final_result=None,
            metadata={'error': 'All attempts failed'},
        )

    def compare_agents(
        self,
        capability: AgentCapability,
        message: Message,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute task on all available agents and compare results.

        Useful for benchmarking and evaluation.
        """
        pool = self._get_or_create_pool(capability)

        # Temporarily set to ALL_PARALLEL
        original_strategy = pool.config.strategy
        pool.config.strategy = PoolStrategy.ALL_PARALLEL

        result = pool.execute(message, **kwargs)

        # Restore original strategy
        pool.config.strategy = original_strategy

        # Analyze results
        comparison = {
            'num_agents': len(result.individual_results),
            'successful': sum(1 for r in result.individual_results if r.success),
            'failed': sum(1 for r in result.individual_results if not r.success),
            'results': [],
        }

        for exec_result in result.individual_results:
            comparison['results'].append({
                'agent_id': exec_result.agent_id,
                'provider': exec_result.provider.value,
                'success': exec_result.success,
                'latency_ms': exec_result.latency_ms,
                'result': exec_result.result if exec_result.success else exec_result.error,
            })

        return comparison

    def _get_or_create_pool(self, capability: AgentCapability) -> AgentPool:
        """Get or create agent pool for capability."""
        if capability not in self._pools:
            config = AgentPoolConfig(
                capability=capability,
                strategy=self.config.pool_strategy,
                timeout_seconds=self.config.timeout_seconds,
                enable_fallback=self.config.enable_fallback,
            )

            pool = AgentPool(config=config, registry=self.registry)
            pool.initialize()

            self._pools[capability] = pool
            logger.info(f"Created pool for {capability.value} with {len(pool)} agents")

        return self._pools[capability]

    def get_pool_statistics(self) -> Dict[str, Any]:
        """Get statistics for all pools."""
        stats = {}
        for capability, pool in self._pools.items():
            stats[capability.value] = pool.get_statistics()
        return stats

    def get_registry_statistics(self) -> Dict[str, Any]:
        """Get registry statistics."""
        return self.registry.get_stats()

    def shutdown(self) -> None:
        """Shutdown all pools and cleanup."""
        for pool in self._pools.values():
            pool.shutdown()
        self._pools.clear()
        logger.info("Multi-agent executor shutdown complete")


def create_multi_agent_executor(
    config: Optional[MultiAgentConfig] = None,
    registry: Optional[AgentRegistry] = None,
) -> MultiAgentExecutor:
    """Create a multi-agent executor."""
    return MultiAgentExecutor(config=config, registry=registry)
