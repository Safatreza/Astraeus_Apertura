"""
Agent Benchmarking and Comparison Examples.

Demonstrates how to benchmark and compare agents from different providers
to find the best performing agent for specific tasks.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger

from astraeus.core.message import Message, MessageType
from astraeus.orchestration.agent_registry import AgentCapability
from astraeus.orchestration.agent_factory import register_all_agents
from astraeus.orchestration.agent_comparison import (
    AgentComparisonFramework,
    BenchmarkTask,
    create_comparison_framework,
)
from astraeus.orchestration.multi_agent_executor import MultiAgentExecutor


def example_1_simple_benchmark():
    """Example 1: Simple benchmark of all agents."""
    print("\n" + "=" * 80)
    print("Example 1: Simple Benchmark")
    print("=" * 80 + "\n")

    # Register agents
    register_all_agents()

    # Create comparison framework
    framework = create_comparison_framework()

    # Add benchmark tasks
    task1 = BenchmarkTask(
        task_id="req_analysis_1",
        description="Analyze satellite antenna requirements",
        message=Message(
            message_type=MessageType.TASK_ASSIGNMENT,
            sender_id="benchmarker",
            receiver_id="requirements_analyst",
            content={
                'frequency_ghz': 12.0,
                'application': 'Ka-band satellite',
                'gain_db': 35,
            },
        ),
        capability=AgentCapability.REQUIREMENTS_ANALYSIS,
    )

    framework.add_benchmark_task(task1)

    # Run comparison
    report = framework.run_comparison(AgentCapability.REQUIREMENTS_ANALYSIS)

    print(f"Benchmarked {report.num_agents} agents on {report.num_tasks} tasks\n")
    print("Agent Rankings:")
    for i, ranking in enumerate(report.agent_rankings[:5], 1):
        print(f"{i}. {ranking['agent_id']:30} - Score: {ranking['composite_score']:.3f}")
        print(f"   Quality: {ranking['avg_quality']:.2f}, "
              f"Latency: {ranking['avg_latency_ms']:.0f}ms, "
              f"Success: {ranking['success_rate']:.1%}")


def example_2_latency_benchmark():
    """Example 2: Benchmark latency across multiple runs."""
    print("\n" + "=" * 80)
    print("Example 2: Latency Benchmark (5 runs)")
    print("=" * 80 + "\n")

    register_all_agents()

    framework = create_comparison_framework()

    message = Message(
        message_type=MessageType.TASK_ASSIGNMENT,
        sender_id="benchmarker",
        receiver_id="material_selector",
        content={'frequency_ghz': 10.0},
    )

    # Benchmark latency
    stats = framework.benchmark_latency(
        capability=AgentCapability.MATERIAL_SELECTION,
        message=message,
        num_runs=5,
    )

    print("Latency Statistics (milliseconds):")
    for agent_id, metrics in sorted(stats.items(), key=lambda x: x[1]['avg']):
        print(f"\n{agent_id}:")
        print(f"  Min:    {metrics['min']:7.1f}ms")
        print(f"  Max:    {metrics['max']:7.1f}ms")
        print(f"  Avg:    {metrics['avg']:7.1f}ms")
        print(f"  Median: {metrics['median']:7.1f}ms")


def example_3_provider_comparison():
    """Example 3: Compare OpenAI vs Claude."""
    print("\n" + "=" * 80)
    print("Example 3: Provider Comparison (OpenAI vs Claude)")
    print("=" * 80 + "\n")

    register_all_agents()

    framework = create_comparison_framework()

    # Create multiple benchmark tasks
    tasks = []
    for i in range(3):
        tasks.append(BenchmarkTask(
            task_id=f"arch_design_{i}",
            description=f"Architecture design task {i}",
            message=Message(
                message_type=MessageType.TASK_ASSIGNMENT,
                sender_id="benchmarker",
                receiver_id="architecture_agent",
                content={'design_type': 'patch', 'variant': i},
            ),
            capability=AgentCapability.ARCHITECTURE_DESIGN,
        ))
        framework.add_benchmark_task(tasks[i])

    # Run comparison
    report = framework.run_comparison(AgentCapability.ARCHITECTURE_DESIGN)

    print("Performance by Provider:\n")
    for provider, metrics in report.performance_by_provider.items():
        print(f"{provider.upper()}:")
        print(f"  Avg Latency:  {metrics['avg_latency_ms']:7.1f}ms")
        print(f"  Avg Quality:  {metrics['avg_quality']:7.2f}")
        print(f"  Success Rate: {metrics['success_rate']:7.1%}")
        print(f"  Avg Cost:     ${metrics['avg_cost']:7.4f}")
        print()


def example_4_quality_evaluation():
    """Example 4: Evaluate quality with custom scoring."""
    print("\n" + "=" * 80)
    print("Example 4: Quality Evaluation with Custom Scoring")
    print("=" * 80 + "\n")

    register_all_agents()

    framework = create_comparison_framework()

    # Custom evaluation function
    def evaluate_optimization(result, expected):
        """Score optimization results."""
        # This is a simplified example
        # In practice, would compare actual vs expected performance
        if result is None:
            return 0.0
        # Assume result has some quality metric
        return 0.85  # Placeholder score

    task = BenchmarkTask(
        task_id="optimization_1",
        description="Optimize antenna gain",
        message=Message(
            message_type=MessageType.TASK_ASSIGNMENT,
            sender_id="benchmarker",
            receiver_id="optimizer",
            content={'objective': 'maximize_gain'},
        ),
        capability=AgentCapability.OPTIMIZATION,
        expected_result={'gain_db': 32.5},
        evaluation_fn=evaluate_optimization,
    )

    framework.add_benchmark_task(task)

    # Run single task comparison
    results = framework.run_single_task_comparison(task)

    print("Quality Scores:")
    for agent_id, performance in sorted(
        results.items(),
        key=lambda x: x[1].quality_score,
        reverse=True
    ):
        print(f"{agent_id:30} - Quality: {performance.quality_score:.2f}, "
              f"Correctness: {performance.correctness_score:.2f}")


def example_5_save_benchmark_report():
    """Example 5: Save comprehensive benchmark report."""
    print("\n" + "=" * 80)
    print("Example 5: Save Benchmark Report")
    print("=" * 80 + "\n")

    register_all_agents()

    framework = create_comparison_framework()

    # Create comprehensive benchmark
    tasks = []
    capabilities = [
        AgentCapability.REQUIREMENTS_ANALYSIS,
        AgentCapability.ARCHITECTURE_DESIGN,
        AgentCapability.GEOMETRY_GENERATION,
    ]

    for i, capability in enumerate(capabilities):
        task = BenchmarkTask(
            task_id=f"task_{capability.value}_{i}",
            description=f"Benchmark {capability.value}",
            message=Message(
                message_type=MessageType.TASK_ASSIGNMENT,
                sender_id="benchmarker",
                receiver_id=capability.value,
                content={'task': i},
            ),
            capability=capability,
        )
        tasks.append(task)
        framework.add_benchmark_task(task)

    # Run benchmarks for each capability
    for capability in capabilities:
        report = framework.run_comparison(capability)

        # Save report
        output_path = Path(f"benchmark_results/{capability.value}_report.json")
        framework.save_report(report, output_path)

        print(f"Saved report for {capability.value}: {output_path}")


def example_6_find_best_agent():
    """Example 6: Find best agent for specific criteria."""
    print("\n" + "=" * 80)
    print("Example 6: Find Best Agent for Different Criteria")
    print("=" * 80 + "\n")

    register_all_agents()

    framework = create_comparison_framework()

    # Add benchmark tasks
    for i in range(5):
        task = BenchmarkTask(
            task_id=f"validation_{i}",
            description=f"Validation task {i}",
            message=Message(
                message_type=MessageType.TASK_ASSIGNMENT,
                sender_id="benchmarker",
                receiver_id="validator",
                content={'design': {}, 'requirements': {}},
            ),
            capability=AgentCapability.VALIDATION,
        )
        framework.add_benchmark_task(task)

    # Run benchmark
    framework.run_comparison(AgentCapability.VALIDATION)

    # Find best agents for different criteria
    criteria = ['quality', 'latency', 'cost', 'balanced']

    print("Best agents by criterion:\n")
    for criterion in criteria:
        best_agent = framework.get_best_agent_for_capability(
            capability=AgentCapability.VALIDATION,
            optimize_for=criterion,
        )
        print(f"{criterion.capitalize():15} -> {best_agent}")


def example_7_continuous_benchmarking():
    """Example 7: Continuous benchmarking over time."""
    print("\n" + "=" * 80)
    print("Example 7: Continuous Benchmarking")
    print("=" * 80 + "\n")

    register_all_agents()

    framework = create_comparison_framework()

    # Run multiple rounds of benchmarks
    num_rounds = 3

    for round_num in range(num_rounds):
        print(f"\nRound {round_num + 1}/{num_rounds}:")

        task = BenchmarkTask(
            task_id=f"geometry_round_{round_num}",
            description=f"Geometry generation round {round_num}",
            message=Message(
                message_type=MessageType.TASK_ASSIGNMENT,
                sender_id="benchmarker",
                receiver_id="geometry_generator",
                content={'shape': 'patch', 'round': round_num},
            ),
            capability=AgentCapability.GEOMETRY_GENERATION,
        )

        results = framework.run_single_task_comparison(task)

        # Show top performer this round
        best_agent = max(
            results.items(),
            key=lambda x: x[1].quality_score if x[1].success else 0
        )

        print(f"  Best performer: {best_agent[0]}")
        print(f"  Quality: {best_agent[1].quality_score:.2f}")
        print(f"  Latency: {best_agent[1].latency_ms:.1f}ms")

    # Historical analysis
    print("\n\nHistorical Performance:")
    print(f"Total measurements: {len(framework.performance_history)}")

    # Best overall agent
    best_overall = framework.get_best_agent_for_capability(
        capability=AgentCapability.GEOMETRY_GENERATION,
        optimize_for='balanced',
    )
    print(f"Best overall agent: {best_overall}")


def example_8_detailed_comparison():
    """Example 8: Detailed agent-by-agent comparison."""
    print("\n" + "=" * 80)
    print("Example 8: Detailed Agent Comparison")
    print("=" * 80 + "\n")

    register_all_agents()

    framework = create_comparison_framework()

    # Single task for detailed comparison
    task = BenchmarkTask(
        task_id="supervisor_task",
        description="Supervisor coordination task",
        message=Message(
            message_type=MessageType.TASK_ASSIGNMENT,
            sender_id="benchmarker",
            receiver_id="supervisor",
            content={'coordinate': True},
        ),
        capability=AgentCapability.SUPERVISION,
    )

    results = framework.run_single_task_comparison(task)

    print("Detailed Agent Comparison:\n")
    print(f"{'Agent ID':35} {'Success':8} {'Latency':10} {'Quality':8} {'Result'}")
    print("-" * 80)

    for agent_id, perf in sorted(results.items()):
        result_preview = str(perf.result)[:30] if perf.result else "Failed"
        print(f"{agent_id:35} {str(perf.success):8} "
              f"{perf.latency_ms:9.1f}ms "
              f"{perf.quality_score:7.2f} {result_preview}")


def main():
    """Run all benchmarking examples."""
    logger.info("Starting agent benchmarking examples")

    try:
        example_1_simple_benchmark()
        example_2_latency_benchmark()
        example_3_provider_comparison()
        example_4_quality_evaluation()
        example_5_save_benchmark_report()
        example_6_find_best_agent()
        example_7_continuous_benchmarking()
        example_8_detailed_comparison()

        print("\n" + "=" * 80)
        print("All benchmarking examples completed!")
        print("=" * 80)

    except Exception as e:
        logger.error(f"Benchmarking example failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
