"""
Agent Comparison Framework for evaluating and benchmarking agents.

Provides tools for comparing agents from different providers on various
metrics including quality, latency, cost, and task-specific performance.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
import time
import json
from pathlib import Path
from loguru import logger

from astraeus.core.message import Message
from astraeus.orchestration.agent_registry import AgentCapability, LLMProvider
from astraeus.orchestration.multi_agent_executor import MultiAgentExecutor, MultiAgentConfig


@dataclass
class BenchmarkTask:
    """A task for benchmarking agents."""

    task_id: str
    description: str
    message: Message
    expected_result: Optional[Any] = None
    evaluation_fn: Optional[Callable[[Any, Any], float]] = None  # Returns score 0-1
    capability: AgentCapability = AgentCapability.REASONING
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentPerformance:
    """Performance metrics for a single agent on a task."""

    agent_id: str
    provider: LLMProvider
    task_id: str

    # Results
    success: bool
    result: Any
    error: Optional[str] = None

    # Performance metrics
    latency_ms: float = 0.0
    tokens_used: int = 0
    cost: float = 0.0

    # Quality metrics
    correctness_score: float = 0.0  # 0-1
    quality_score: float = 0.0  # 0-1
    relevance_score: float = 0.0  # 0-1

    # Metadata
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ComparisonReport:
    """Report comparing multiple agents."""

    benchmark_id: str
    num_tasks: int
    num_agents: int

    # Overall statistics
    agent_rankings: List[Dict[str, Any]] = field(default_factory=list)
    performance_by_task: Dict[str, List[AgentPerformance]] = field(default_factory=dict)
    performance_by_agent: Dict[str, List[AgentPerformance]] = field(default_factory=dict)

    # Aggregate metrics
    avg_latency_by_agent: Dict[str, float] = field(default_factory=dict)
    avg_cost_by_agent: Dict[str, float] = field(default_factory=dict)
    avg_quality_by_agent: Dict[str, float] = field(default_factory=dict)
    success_rate_by_agent: Dict[str, float] = field(default_factory=dict)

    # Provider comparisons
    performance_by_provider: Dict[str, Dict[str, float]] = field(default_factory=dict)

    timestamp: datetime = field(default_factory=datetime.now)


class AgentComparisonFramework:
    """
    Framework for comparing and benchmarking agents.

    Allows systematic evaluation of agents from different providers
    (OpenAI, Claude, etc.) across various tasks and metrics.
    """

    def __init__(self, executor: Optional[MultiAgentExecutor] = None):
        self.executor = executor or MultiAgentExecutor()

        # Benchmark tasks
        self.tasks: Dict[str, BenchmarkTask] = {}

        # Performance history
        self.performance_history: List[AgentPerformance] = []

        logger.info("Agent comparison framework initialized")

    def add_benchmark_task(self, task: BenchmarkTask) -> None:
        """Add a benchmark task."""
        self.tasks[task.task_id] = task
        logger.info(f"Added benchmark task: {task.task_id}")

    def run_comparison(
        self,
        capability: AgentCapability,
        task_ids: Optional[List[str]] = None,
    ) -> ComparisonReport:
        """
        Run comparison across all agents for a capability.

        Args:
            capability: Agent capability to test
            task_ids: Specific tasks to run (or all if None)

        Returns:
            Comparison report
        """
        # Select tasks
        if task_ids:
            tasks = [self.tasks[tid] for tid in task_ids if tid in self.tasks]
        else:
            tasks = [t for t in self.tasks.values() if t.capability == capability]

        if not tasks:
            logger.warning(f"No tasks found for capability {capability.value}")
            return ComparisonReport(
                benchmark_id=f"comparison_{datetime.now().isoformat()}",
                num_tasks=0,
                num_agents=0,
            )

        logger.info(f"Running comparison on {len(tasks)} tasks for {capability.value}")

        # Run all tasks and collect performance
        all_performance: List[AgentPerformance] = []

        for task in tasks:
            logger.info(f"Running task: {task.task_id}")

            # Compare agents on this task
            comparison = self.executor.compare_agents(
                capability=capability,
                message=task.message,
            )

            # Process results
            for result in comparison['results']:
                performance = self._evaluate_performance(task, result)
                all_performance.append(performance)
                self.performance_history.append(performance)

        # Generate report
        report = self._generate_report(
            tasks=tasks,
            performance_data=all_performance,
        )

        logger.info(f"Comparison complete: {len(all_performance)} agent-task combinations")
        return report

    def run_single_task_comparison(
        self,
        task: BenchmarkTask,
    ) -> Dict[str, AgentPerformance]:
        """
        Run comparison on a single task.

        Returns:
            Dict mapping agent_id to performance
        """
        logger.info(f"Running single task comparison: {task.task_id}")

        comparison = self.executor.compare_agents(
            capability=task.capability,
            message=task.message,
        )

        results = {}
        for result in comparison['results']:
            performance = self._evaluate_performance(task, result)
            results[performance.agent_id] = performance
            self.performance_history.append(performance)

        return results

    def benchmark_latency(
        self,
        capability: AgentCapability,
        message: Message,
        num_runs: int = 5,
    ) -> Dict[str, List[float]]:
        """
        Benchmark latency across multiple runs.

        Returns:
            Dict mapping agent_id to list of latencies
        """
        logger.info(f"Benchmarking latency with {num_runs} runs")

        latencies: Dict[str, List[float]] = {}

        for run in range(num_runs):
            logger.info(f"Latency benchmark run {run + 1}/{num_runs}")

            comparison = self.executor.compare_agents(
                capability=capability,
                message=message,
            )

            for result in comparison['results']:
                agent_id = result['agent_id']
                if agent_id not in latencies:
                    latencies[agent_id] = []
                latencies[agent_id].append(result['latency_ms'])

        # Calculate statistics
        stats = {}
        for agent_id, times in latencies.items():
            stats[agent_id] = {
                'min': min(times),
                'max': max(times),
                'avg': sum(times) / len(times),
                'median': sorted(times)[len(times) // 2],
                'runs': times,
            }

        return stats

    def evaluate_quality(
        self,
        task: BenchmarkTask,
        agent_results: Dict[str, Any],
    ) -> Dict[str, float]:
        """
        Evaluate quality of agent results.

        Returns:
            Dict mapping agent_id to quality score
        """
        quality_scores = {}

        for agent_id, result in agent_results.items():
            if not result['success']:
                quality_scores[agent_id] = 0.0
                continue

            # Use task-specific evaluation if available
            if task.evaluation_fn and task.expected_result:
                score = task.evaluation_fn(result['result'], task.expected_result)
            else:
                # Default: just check if result exists
                score = 1.0 if result['result'] else 0.0

            quality_scores[agent_id] = score

        return quality_scores

    def compare_providers(
        self,
        capability: AgentCapability,
        tasks: List[BenchmarkTask],
    ) -> Dict[str, Dict[str, float]]:
        """
        Compare performance across different providers.

        Returns:
            Dict mapping provider to performance metrics
        """
        logger.info(f"Comparing providers for {capability.value}")

        # Run comparison
        report = self.run_comparison(capability, [t.task_id for t in tasks])

        return report.performance_by_provider

    def _evaluate_performance(
        self,
        task: BenchmarkTask,
        result: Dict[str, Any],
    ) -> AgentPerformance:
        """Evaluate performance of an agent on a task."""
        success = result['success']
        agent_result = result['result']

        # Calculate quality scores
        correctness = 0.0
        quality = 0.0
        relevance = 0.0

        if success:
            # Use task-specific evaluation
            if task.evaluation_fn and task.expected_result:
                correctness = task.evaluation_fn(agent_result, task.expected_result)
                quality = correctness  # Simplified
                relevance = correctness  # Simplified
            else:
                # Default scoring
                correctness = 1.0 if agent_result else 0.0
                quality = 0.8  # Assume decent quality if successful
                relevance = 0.8

        # Parse provider from agent_id (format: "provider_capability_xxx")
        provider = LLMProvider.CUSTOM
        agent_id = result['agent_id']
        if 'openai' in agent_id.lower():
            provider = LLMProvider.OPENAI
        elif 'anthropic' in agent_id.lower() or 'claude' in agent_id.lower():
            provider = LLMProvider.ANTHROPIC

        return AgentPerformance(
            agent_id=agent_id,
            provider=provider,
            task_id=task.task_id,
            success=success,
            result=agent_result if success else None,
            error=result.get('error') if not success else None,
            latency_ms=result['latency_ms'],
            correctness_score=correctness,
            quality_score=quality,
            relevance_score=relevance,
        )

    def _generate_report(
        self,
        tasks: List[BenchmarkTask],
        performance_data: List[AgentPerformance],
    ) -> ComparisonReport:
        """Generate comparison report from performance data."""

        # Organize by task and agent
        by_task: Dict[str, List[AgentPerformance]] = {}
        by_agent: Dict[str, List[AgentPerformance]] = {}
        by_provider: Dict[str, List[AgentPerformance]] = {}

        for perf in performance_data:
            # By task
            if perf.task_id not in by_task:
                by_task[perf.task_id] = []
            by_task[perf.task_id].append(perf)

            # By agent
            if perf.agent_id not in by_agent:
                by_agent[perf.agent_id] = []
            by_agent[perf.agent_id].append(perf)

            # By provider
            provider_key = perf.provider.value
            if provider_key not in by_provider:
                by_provider[provider_key] = []
            by_provider[provider_key].append(perf)

        # Calculate aggregate metrics
        avg_latency = {}
        avg_cost = {}
        avg_quality = {}
        success_rate = {}

        for agent_id, perfs in by_agent.items():
            avg_latency[agent_id] = sum(p.latency_ms for p in perfs) / len(perfs)
            avg_cost[agent_id] = sum(p.cost for p in perfs) / len(perfs)
            avg_quality[agent_id] = sum(p.quality_score for p in perfs) / len(perfs)
            success_rate[agent_id] = sum(1 for p in perfs if p.success) / len(perfs)

        # Calculate provider metrics
        provider_metrics = {}
        for provider, perfs in by_provider.items():
            provider_metrics[provider] = {
                'avg_latency_ms': sum(p.latency_ms for p in perfs) / len(perfs),
                'avg_cost': sum(p.cost for p in perfs) / len(perfs),
                'avg_quality': sum(p.quality_score for p in perfs) / len(perfs),
                'success_rate': sum(1 for p in perfs if p.success) / len(perfs),
                'num_tasks': len(perfs),
            }

        # Generate rankings
        rankings = []
        for agent_id in by_agent.keys():
            rankings.append({
                'agent_id': agent_id,
                'avg_latency_ms': avg_latency[agent_id],
                'avg_cost': avg_cost[agent_id],
                'avg_quality': avg_quality[agent_id],
                'success_rate': success_rate[agent_id],
                'composite_score': (
                    avg_quality[agent_id] * 0.5 +
                    success_rate[agent_id] * 0.3 +
                    (1.0 - min(1.0, avg_latency[agent_id] / 10000)) * 0.2
                ),
            })

        # Sort by composite score
        rankings.sort(key=lambda r: r['composite_score'], reverse=True)

        return ComparisonReport(
            benchmark_id=f"comparison_{datetime.now().isoformat()}",
            num_tasks=len(tasks),
            num_agents=len(by_agent),
            agent_rankings=rankings,
            performance_by_task=by_task,
            performance_by_agent=by_agent,
            avg_latency_by_agent=avg_latency,
            avg_cost_by_agent=avg_cost,
            avg_quality_by_agent=avg_quality,
            success_rate_by_agent=success_rate,
            performance_by_provider=provider_metrics,
        )

    def save_report(self, report: ComparisonReport, output_path: Path) -> None:
        """Save comparison report to file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        report_data = {
            'benchmark_id': report.benchmark_id,
            'num_tasks': report.num_tasks,
            'num_agents': report.num_agents,
            'timestamp': report.timestamp.isoformat(),
            'agent_rankings': report.agent_rankings,
            'avg_latency_by_agent': report.avg_latency_by_agent,
            'avg_cost_by_agent': report.avg_cost_by_agent,
            'avg_quality_by_agent': report.avg_quality_by_agent,
            'success_rate_by_agent': report.success_rate_by_agent,
            'performance_by_provider': report.performance_by_provider,
        }

        with open(output_path, 'w') as f:
            json.dump(report_data, f, indent=2)

        logger.info(f"Report saved to {output_path}")

    def get_best_agent_for_capability(
        self,
        capability: AgentCapability,
        optimize_for: str = 'quality',  # 'quality', 'latency', 'cost', 'balanced'
    ) -> Optional[str]:
        """
        Get the best performing agent for a capability based on historical data.

        Args:
            capability: Agent capability
            optimize_for: Optimization criterion

        Returns:
            Best agent ID or None
        """
        # Filter performance history by capability
        relevant_perfs = [
            p for p in self.performance_history
            if self.tasks.get(p.task_id) and self.tasks[p.task_id].capability == capability
        ]

        if not relevant_perfs:
            return None

        # Group by agent
        by_agent: Dict[str, List[AgentPerformance]] = {}
        for perf in relevant_perfs:
            if perf.agent_id not in by_agent:
                by_agent[perf.agent_id] = []
            by_agent[perf.agent_id].append(perf)

        # Calculate scores based on optimization criterion
        scores = {}
        for agent_id, perfs in by_agent.items():
            if optimize_for == 'quality':
                scores[agent_id] = sum(p.quality_score for p in perfs) / len(perfs)
            elif optimize_for == 'latency':
                avg_latency = sum(p.latency_ms for p in perfs) / len(perfs)
                scores[agent_id] = 1.0 / (1.0 + avg_latency / 1000)  # Inverse of latency
            elif optimize_for == 'cost':
                avg_cost = sum(p.cost for p in perfs) / len(perfs)
                scores[agent_id] = 1.0 / (1.0 + avg_cost)  # Inverse of cost
            else:  # balanced
                avg_quality = sum(p.quality_score for p in perfs) / len(perfs)
                avg_latency = sum(p.latency_ms for p in perfs) / len(perfs)
                avg_cost = sum(p.cost for p in perfs) / len(perfs)
                scores[agent_id] = (
                    avg_quality * 0.5 +
                    (1.0 / (1.0 + avg_latency / 1000)) * 0.3 +
                    (1.0 / (1.0 + avg_cost)) * 0.2
                )

        # Return agent with best score
        return max(scores.keys(), key=lambda k: scores[k])


def create_comparison_framework(
    executor: Optional[MultiAgentExecutor] = None,
) -> AgentComparisonFramework:
    """Create an agent comparison framework."""
    return AgentComparisonFramework(executor=executor)
