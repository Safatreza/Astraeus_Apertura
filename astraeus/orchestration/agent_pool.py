"""
Agent Pool Management for hosting multiple agents per task.

Manages pools of agents from different providers, with strategies for
selecting and executing tasks across the pool.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
import time
from concurrent.futures import ThreadPoolExecutor, Future, as_completed
from loguru import logger

from astraeus.core.agent_base import Agent
from astraeus.core.message import Message, MessageType
from astraeus.orchestration.agent_registry import (
    AgentRegistry,
    AgentCapability,
    LLMProvider,
    get_global_registry,
)


class PoolStrategy(Enum):
    """Strategy for executing tasks across agent pool."""

    # Execute on single agent
    SINGLE_BEST = "single_best"  # Use best performing agent
    SINGLE_FASTEST = "single_fastest"  # Use fastest agent
    SINGLE_CHEAPEST = "single_cheapest"  # Use cheapest agent
    SINGLE_ROUND_ROBIN = "single_round_robin"  # Rotate through agents

    # Execute on multiple agents
    ALL_PARALLEL = "all_parallel"  # Execute on all agents in parallel
    RACE = "race"  # Use first successful response
    MAJORITY_VOTE = "majority_vote"  # Execute on multiple, use consensus
    ENSEMBLE = "ensemble"  # Combine outputs from multiple agents


@dataclass
class AgentPoolConfig:
    """Configuration for agent pool."""

    capability: AgentCapability
    strategy: PoolStrategy = PoolStrategy.SINGLE_BEST
    max_agents: int = 5
    timeout_seconds: float = 60.0
    enable_fallback: bool = True
    min_reliability: float = 0.7
    preferred_providers: List[LLMProvider] = field(default_factory=list)


@dataclass
class ExecutionResult:
    """Result from executing a task on an agent."""

    agent_id: str
    provider: LLMProvider
    success: bool
    result: Any
    error: Optional[str] = None
    latency_ms: float = 0.0
    tokens_used: int = 0
    cost: float = 0.0


@dataclass
class PoolExecutionResult:
    """Result from executing a task on an agent pool."""

    success: bool
    final_result: Any
    individual_results: List[ExecutionResult] = field(default_factory=list)
    strategy_used: PoolStrategy = PoolStrategy.SINGLE_BEST
    total_latency_ms: float = 0.0
    total_cost: float = 0.0
    agents_used: int = 0


class AgentPool:
    """
    Manages a pool of agents for a specific capability.

    Supports multiple execution strategies including single-agent selection,
    parallel execution, racing, and consensus-based approaches.
    """

    def __init__(
        self,
        config: AgentPoolConfig,
        registry: Optional[AgentRegistry] = None,
    ):
        self.config = config
        self.registry = registry or get_global_registry()

        # Active agent instances
        self._agents: Dict[str, Agent] = {}

        # Execution statistics
        self._execution_count: Dict[str, int] = {}
        self._success_count: Dict[str, int] = {}
        self._total_latency: Dict[str, float] = {}

        # Round-robin counter
        self._round_robin_index = 0

        # Thread pool for parallel execution
        self._executor = ThreadPoolExecutor(max_workers=config.max_agents)

        logger.info(f"Created agent pool for {config.capability.value} with strategy {config.strategy.value}")

    def initialize(self) -> int:
        """
        Initialize the pool by discovering and creating agent instances.

        Returns:
            Number of agents initialized
        """
        # Find matching agents in registry
        registrations = self.registry.find_by_capability(
            capability=self.config.capability,
            min_reliability=self.config.min_reliability,
        )

        # Filter by preferred providers if specified
        if self.config.preferred_providers:
            registrations = [
                reg for reg in registrations
                if reg.provider in self.config.preferred_providers
            ]

        # Limit to max_agents
        registrations = registrations[:self.config.max_agents]

        # Create agent instances
        for reg in registrations:
            try:
                agent = reg.create_agent()
                self._agents[reg.agent_id] = agent
                self._execution_count[reg.agent_id] = 0
                self._success_count[reg.agent_id] = 0
                self._total_latency[reg.agent_id] = 0.0
                logger.info(f"Initialized agent {reg.agent_id} in pool")
            except Exception as e:
                logger.error(f"Failed to initialize agent {reg.agent_id}: {e}")

        logger.info(f"Pool initialized with {len(self._agents)} agents")
        return len(self._agents)

    def execute(self, message: Message, **kwargs) -> PoolExecutionResult:
        """
        Execute a task using the configured strategy.

        Args:
            message: Input message for agents
            **kwargs: Additional arguments for agents

        Returns:
            Pool execution result
        """
        start_time = time.time()

        if not self._agents:
            logger.error("No agents available in pool")
            return PoolExecutionResult(
                success=False,
                final_result=None,
                strategy_used=self.config.strategy,
            )

        # Execute based on strategy
        if self.config.strategy == PoolStrategy.SINGLE_BEST:
            result = self._execute_single_best(message, **kwargs)
        elif self.config.strategy == PoolStrategy.SINGLE_FASTEST:
            result = self._execute_single_fastest(message, **kwargs)
        elif self.config.strategy == PoolStrategy.SINGLE_CHEAPEST:
            result = self._execute_single_cheapest(message, **kwargs)
        elif self.config.strategy == PoolStrategy.SINGLE_ROUND_ROBIN:
            result = self._execute_round_robin(message, **kwargs)
        elif self.config.strategy == PoolStrategy.ALL_PARALLEL:
            result = self._execute_all_parallel(message, **kwargs)
        elif self.config.strategy == PoolStrategy.RACE:
            result = self._execute_race(message, **kwargs)
        elif self.config.strategy == PoolStrategy.MAJORITY_VOTE:
            result = self._execute_majority_vote(message, **kwargs)
        elif self.config.strategy == PoolStrategy.ENSEMBLE:
            result = self._execute_ensemble(message, **kwargs)
        else:
            result = self._execute_single_best(message, **kwargs)

        # Update result timing
        result.total_latency_ms = (time.time() - start_time) * 1000
        result.strategy_used = self.config.strategy

        # Update pool statistics
        self._update_statistics(result)

        return result

    def _execute_single_best(self, message: Message, **kwargs) -> PoolExecutionResult:
        """Execute on the best performing agent."""
        agent_id = self._select_best_agent()
        return self._execute_single(agent_id, message, **kwargs)

    def _execute_single_fastest(self, message: Message, **kwargs) -> PoolExecutionResult:
        """Execute on the fastest agent."""
        agent_id = self._select_fastest_agent()
        return self._execute_single(agent_id, message, **kwargs)

    def _execute_single_cheapest(self, message: Message, **kwargs) -> PoolExecutionResult:
        """Execute on the cheapest agent."""
        agent_id = self._select_cheapest_agent()
        return self._execute_single(agent_id, message, **kwargs)

    def _execute_round_robin(self, message: Message, **kwargs) -> PoolExecutionResult:
        """Execute using round-robin selection."""
        agent_ids = list(self._agents.keys())
        agent_id = agent_ids[self._round_robin_index % len(agent_ids)]
        self._round_robin_index += 1
        return self._execute_single(agent_id, message, **kwargs)

    def _execute_single(self, agent_id: str, message: Message, **kwargs) -> PoolExecutionResult:
        """Execute on a single agent."""
        exec_result = self._execute_on_agent(agent_id, message, **kwargs)

        # Fallback if failed and enabled
        if not exec_result.success and self.config.enable_fallback:
            logger.warning(f"Agent {agent_id} failed, trying fallback")
            for fallback_id in self._agents.keys():
                if fallback_id != agent_id:
                    exec_result = self._execute_on_agent(fallback_id, message, **kwargs)
                    if exec_result.success:
                        break

        return PoolExecutionResult(
            success=exec_result.success,
            final_result=exec_result.result,
            individual_results=[exec_result],
            agents_used=1,
            total_cost=exec_result.cost,
        )

    def _execute_all_parallel(self, message: Message, **kwargs) -> PoolExecutionResult:
        """Execute on all agents in parallel."""
        futures: Dict[Future, str] = {}

        for agent_id in self._agents.keys():
            future = self._executor.submit(self._execute_on_agent, agent_id, message, **kwargs)
            futures[future] = agent_id

        results = []
        for future in as_completed(futures.keys(), timeout=self.config.timeout_seconds):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                agent_id = futures[future]
                logger.error(f"Agent {agent_id} execution failed: {e}")

        # Use first successful result
        final_result = None
        for result in results:
            if result.success:
                final_result = result.result
                break

        return PoolExecutionResult(
            success=any(r.success for r in results),
            final_result=final_result,
            individual_results=results,
            agents_used=len(results),
            total_cost=sum(r.cost for r in results),
        )

    def _execute_race(self, message: Message, **kwargs) -> PoolExecutionResult:
        """Execute on all agents, use first successful response."""
        futures: Dict[Future, str] = {}

        for agent_id in self._agents.keys():
            future = self._executor.submit(self._execute_on_agent, agent_id, message, **kwargs)
            futures[future] = agent_id

        # Get first successful result
        first_result = None
        all_results = []

        for future in as_completed(futures.keys(), timeout=self.config.timeout_seconds):
            try:
                result = future.result()
                all_results.append(result)

                if result.success and first_result is None:
                    first_result = result
                    # Cancel remaining futures
                    for f in futures.keys():
                        f.cancel()
                    break
            except Exception as e:
                agent_id = futures[future]
                logger.error(f"Agent {agent_id} race failed: {e}")

        return PoolExecutionResult(
            success=first_result is not None and first_result.success,
            final_result=first_result.result if first_result else None,
            individual_results=all_results,
            agents_used=len(all_results),
            total_cost=sum(r.cost for r in all_results),
        )

    def _execute_majority_vote(self, message: Message, **kwargs) -> PoolExecutionResult:
        """Execute on multiple agents and use majority vote."""
        # Execute on all agents
        pool_result = self._execute_all_parallel(message, **kwargs)

        # This is a placeholder - actual voting logic would depend on result type
        # For now, just use the most common result
        results = [r.result for r in pool_result.individual_results if r.success]

        if not results:
            return pool_result

        # Simple majority vote (would need more sophisticated logic for complex results)
        from collections import Counter
        result_counts = Counter(str(r) for r in results)
        most_common = result_counts.most_common(1)[0][0]

        # Find the actual result object
        final_result = None
        for r in results:
            if str(r) == most_common:
                final_result = r
                break

        pool_result.final_result = final_result
        return pool_result

    def _execute_ensemble(self, message: Message, **kwargs) -> PoolExecutionResult:
        """Execute on multiple agents and combine outputs."""
        # Execute on all agents
        pool_result = self._execute_all_parallel(message, **kwargs)

        # Combine results (implementation depends on result type)
        # For now, just aggregate all results
        results = [r.result for r in pool_result.individual_results if r.success]

        pool_result.final_result = {
            'ensemble_results': results,
            'count': len(results),
        }
        return pool_result

    def _execute_on_agent(self, agent_id: str, message: Message, **kwargs) -> ExecutionResult:
        """Execute task on a specific agent."""
        agent = self._agents[agent_id]
        reg = self.registry.get(agent_id)

        start_time = time.time()
        success = False
        result = None
        error = None

        try:
            response = agent.process_message(message, **kwargs)
            result = response
            success = True
        except Exception as e:
            error = str(e)
            logger.error(f"Agent {agent_id} execution error: {e}")

        latency_ms = (time.time() - start_time) * 1000

        return ExecutionResult(
            agent_id=agent_id,
            provider=reg.provider if reg else LLMProvider.CUSTOM,
            success=success,
            result=result,
            error=error,
            latency_ms=latency_ms,
            tokens_used=0,  # Would need to track from LLM response
            cost=0.0,  # Would calculate based on tokens and pricing
        )

    def _select_best_agent(self) -> str:
        """Select the best performing agent based on success rate."""
        best_agent = None
        best_score = -1.0

        for agent_id in self._agents.keys():
            executions = self._execution_count.get(agent_id, 0)
            if executions == 0:
                score = 1.0  # Give new agents a chance
            else:
                successes = self._success_count.get(agent_id, 0)
                score = successes / executions

            if score > best_score:
                best_score = score
                best_agent = agent_id

        return best_agent or list(self._agents.keys())[0]

    def _select_fastest_agent(self) -> str:
        """Select the fastest agent based on average latency."""
        fastest_agent = None
        fastest_latency = float('inf')

        for agent_id in self._agents.keys():
            executions = self._execution_count.get(agent_id, 0)
            if executions == 0:
                # Check registry for estimated latency
                reg = self.registry.get(agent_id)
                latency = reg.avg_latency_ms if reg else 1000.0
            else:
                total_latency = self._total_latency.get(agent_id, 0.0)
                latency = total_latency / executions

            if latency < fastest_latency:
                fastest_latency = latency
                fastest_agent = agent_id

        return fastest_agent or list(self._agents.keys())[0]

    def _select_cheapest_agent(self) -> str:
        """Select the cheapest agent based on cost per token."""
        cheapest_agent = None
        cheapest_cost = float('inf')

        for agent_id in self._agents.keys():
            reg = self.registry.get(agent_id)
            if reg and reg.cost_per_1k_tokens < cheapest_cost:
                cheapest_cost = reg.cost_per_1k_tokens
                cheapest_agent = agent_id

        return cheapest_agent or list(self._agents.keys())[0]

    def _update_statistics(self, result: PoolExecutionResult) -> None:
        """Update pool statistics based on execution result."""
        for exec_result in result.individual_results:
            agent_id = exec_result.agent_id

            self._execution_count[agent_id] = self._execution_count.get(agent_id, 0) + 1

            if exec_result.success:
                self._success_count[agent_id] = self._success_count.get(agent_id, 0) + 1

            self._total_latency[agent_id] = self._total_latency.get(agent_id, 0.0) + exec_result.latency_ms

            # Update registry metrics
            executions = self._execution_count[agent_id]
            avg_latency = self._total_latency[agent_id] / executions
            reliability = self._success_count[agent_id] / executions

            self.registry.update_metrics(
                agent_id=agent_id,
                avg_latency_ms=avg_latency,
                reliability_score=reliability,
            )

    def get_statistics(self) -> Dict[str, Any]:
        """Get pool execution statistics."""
        stats = {}
        for agent_id in self._agents.keys():
            executions = self._execution_count.get(agent_id, 0)
            stats[agent_id] = {
                'executions': executions,
                'successes': self._success_count.get(agent_id, 0),
                'success_rate': self._success_count.get(agent_id, 0) / executions if executions > 0 else 0.0,
                'avg_latency_ms': self._total_latency.get(agent_id, 0.0) / executions if executions > 0 else 0.0,
            }
        return stats

    def shutdown(self) -> None:
        """Shutdown the pool and cleanup resources."""
        self._executor.shutdown(wait=True)
        self._agents.clear()
        logger.info(f"Agent pool for {self.config.capability.value} shutdown")

    def __len__(self) -> int:
        """Number of agents in pool."""
        return len(self._agents)
