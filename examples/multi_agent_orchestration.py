"""
Multi-Agent Orchestration Examples.

Demonstrates how to use multiple agents from OpenAI and Claude
for antenna design tasks with consensus, routing, and comparison.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger

from astraeus.core.message import Message, MessageType
from astraeus.data.parameters import AntennaParameters
from astraeus.orchestration.agent_registry import AgentCapability, LLMProvider
from astraeus.orchestration.agent_factory import register_all_agents
from astraeus.orchestration.agent_pool import PoolStrategy, AgentPoolConfig
from astraeus.orchestration.consensus import VotingStrategy
from astraeus.orchestration.router import RoutingStrategy, TaskCharacteristics
from astraeus.orchestration.multi_agent_executor import (
    MultiAgentExecutor,
    MultiAgentConfig,
)


def example_1_basic_multi_agent():
    """Example 1: Basic multi-agent execution with consensus."""
    print("\n" + "=" * 80)
    print("Example 1: Basic Multi-Agent Execution with Consensus")
    print("=" * 80 + "\n")

    # Register all agents (OpenAI + Claude variants)
    register_all_agents()

    # Create multi-agent executor
    config = MultiAgentConfig(
        pool_strategy=PoolStrategy.ALL_PARALLEL,  # Execute on all agents
        voting_strategy=VotingStrategy.WEIGHTED,   # Use weighted voting
        routing_strategy=RoutingStrategy.BALANCED,
    )

    executor = MultiAgentExecutor(config=config)

    # Create requirements analysis message
    requirements = {
        'frequency_ghz': 10.0,
        'bandwidth_mhz': 500,
        'gain_db': 30,
        'application': 'Satellite communication',
    }

    message = Message(
        message_type=MessageType.TASK_ASSIGNMENT,
        sender_id="user",
        receiver_id="requirements_analyst",
        content=requirements,
        metadata={'task': 'analyze_requirements'},
    )

    # Execute with consensus from multiple agents
    result = executor.execute(
        capability=AgentCapability.REQUIREMENTS_ANALYSIS,
        message=message,
        use_consensus=True,
    )

    print(f"Success: {result.success}")
    print(f"Agents used: {result.agents_used}")
    print(f"Total latency: {result.total_latency_ms:.1f}ms")

    if result.consensus_result:
        print(f"Consensus confidence: {result.consensus_result.confidence:.2f}")
        print(f"Agreement level: {result.consensus_result.agreement_level:.2f}")
        print(f"\nFinal result: {result.final_result}")


def example_2_intelligent_routing():
    """Example 2: Intelligent routing based on task characteristics."""
    print("\n" + "=" * 80)
    print("Example 2: Intelligent Routing Based on Task Characteristics")
    print("=" * 80 + "\n")

    register_all_agents()

    executor = MultiAgentExecutor()

    # Complex task - route to most capable agent
    task_chars = TaskCharacteristics(
        complexity=0.9,  # High complexity
        urgency=0.5,     # Medium urgency
        cost_sensitivity=0.3,  # Not very cost sensitive
        quality_requirement=0.95,  # High quality needed
        requires_reasoning=True,
    )

    message = Message(
        message_type=MessageType.TASK_ASSIGNMENT,
        sender_id="user",
        receiver_id="architecture_agent",
        content={'design_type': 'reflector', 'diameter_m': 3.0},
    )

    result = executor.execute_with_routing(
        capability=AgentCapability.ARCHITECTURE_DESIGN,
        message=message,
        task_chars=task_chars,
    )

    print(f"Routing decision: {result.routing_decision}")
    print(f"Success: {result.success}")
    print(f"Total cost: ${result.total_cost:.4f}")


def example_3_cost_vs_quality():
    """Example 3: Compare cost-optimized vs quality-optimized routing."""
    print("\n" + "=" * 80)
    print("Example 3: Cost-Optimized vs Quality-Optimized Routing")
    print("=" * 80 + "\n")

    register_all_agents()

    message = Message(
        message_type=MessageType.TASK_ASSIGNMENT,
        sender_id="user",
        receiver_id="optimizer",
        content={'optimize': 'gain', 'constraints': {'size_max_m': 2.0}},
    )

    # Cost-optimized execution
    print("Cost-Optimized Execution:")
    cost_executor = MultiAgentExecutor(
        config=MultiAgentConfig(
            routing_strategy=RoutingStrategy.COST_OPTIMIZED,
            pool_strategy=PoolStrategy.SINGLE_CHEAPEST,
        )
    )

    cost_result = cost_executor.execute_with_routing(
        capability=AgentCapability.OPTIMIZATION,
        message=message,
    )

    print(f"  Cost: ${cost_result.total_cost:.4f}")
    print(f"  Latency: {cost_result.total_latency_ms:.1f}ms")

    # Quality-optimized execution
    print("\nQuality-Optimized Execution:")
    quality_executor = MultiAgentExecutor(
        config=MultiAgentConfig(
            routing_strategy=RoutingStrategy.QUALITY_OPTIMIZED,
            pool_strategy=PoolStrategy.SINGLE_BEST,
        )
    )

    quality_result = quality_executor.execute_with_routing(
        capability=AgentCapability.OPTIMIZATION,
        message=message,
    )

    print(f"  Cost: ${quality_result.total_cost:.4f}")
    print(f"  Latency: {quality_result.total_latency_ms:.1f}ms")


def example_4_racing_agents():
    """Example 4: Racing multiple agents for fastest response."""
    print("\n" + "=" * 80)
    print("Example 4: Racing Agents for Fastest Response")
    print("=" * 80 + "\n")

    register_all_agents()

    # Use RACE strategy - first successful response wins
    config = MultiAgentConfig(
        pool_strategy=PoolStrategy.RACE,
        routing_strategy=RoutingStrategy.LATENCY_OPTIMIZED,
    )

    executor = MultiAgentExecutor(config=config)

    message = Message(
        message_type=MessageType.TASK_ASSIGNMENT,
        sender_id="user",
        receiver_id="validator",
        content={'design': {}, 'requirements': {}},
    )

    result = executor.execute(
        capability=AgentCapability.VALIDATION,
        message=message,
    )

    print(f"Fastest response in: {result.total_latency_ms:.1f}ms")
    print(f"Agents started: {len(result.pool_result.individual_results) if result.pool_result else 0}")


def example_5_fallback_mechanism():
    """Example 5: Automatic fallback if primary agent fails."""
    print("\n" + "=" * 80)
    print("Example 5: Automatic Fallback on Failure")
    print("=" * 80 + "\n")

    register_all_agents()

    executor = MultiAgentExecutor(
        config=MultiAgentConfig(enable_fallback=True)
    )

    message = Message(
        message_type=MessageType.TASK_ASSIGNMENT,
        sender_id="user",
        receiver_id="simulation_agent",
        content={'simulation_type': 'hfss', 'params': {}},
    )

    result = executor.execute_with_fallback(
        capability=AgentCapability.SIMULATION,
        message=message,
        max_attempts=3,
    )

    print(f"Success: {result.success}")
    print(f"Attempts needed: {len(result.pool_result.individual_results) if result.pool_result else 0}")


def example_6_compare_providers():
    """Example 6: Compare OpenAI vs Claude performance."""
    print("\n" + "=" * 80)
    print("Example 6: Compare OpenAI vs Claude Performance")
    print("=" * 80 + "\n")

    register_all_agents()

    executor = MultiAgentExecutor()

    message = Message(
        message_type=MessageType.TASK_ASSIGNMENT,
        sender_id="user",
        receiver_id="material_selector",
        content={'frequency_ghz': 10.0, 'application': 'space'},
    )

    # Compare all agents
    comparison = executor.compare_agents(
        capability=AgentCapability.MATERIAL_SELECTION,
        message=message,
    )

    print(f"Total agents compared: {comparison['num_agents']}")
    print(f"Successful: {comparison['successful']}")
    print(f"Failed: {comparison['failed']}\n")

    print("Results by provider:")
    for result in comparison['results']:
        print(f"  {result['provider']:15} - Success: {result['success']:5} - Latency: {result['latency_ms']:7.1f}ms")


def example_7_majority_voting():
    """Example 7: Majority voting across multiple agents."""
    print("\n" + "=" * 80)
    print("Example 7: Majority Voting Consensus")
    print("=" * 80 + "\n")

    register_all_agents()

    config = MultiAgentConfig(
        pool_strategy=PoolStrategy.MAJORITY_VOTE,
        voting_strategy=VotingStrategy.MAJORITY,
    )

    executor = MultiAgentExecutor(config=config)

    message = Message(
        message_type=MessageType.TASK_ASSIGNMENT,
        sender_id="user",
        receiver_id="requirements_analyst",
        content={'frequency_ghz': 5.0, 'application': 'radar'},
    )

    result = executor.execute(
        capability=AgentCapability.REQUIREMENTS_ANALYSIS,
        message=message,
        use_consensus=True,
    )

    if result.consensus_result:
        print(f"Voting strategy: {result.consensus_result.strategy_used.value}")
        print(f"Agreement level: {result.consensus_result.agreement_level:.2%}")
        print(f"Number of agents: {result.consensus_result.num_agents}")


def example_8_task_specific_routing():
    """Example 8: Task-specific routing based on requirements."""
    print("\n" + "=" * 80)
    print("Example 8: Task-Specific Routing")
    print("=" * 80 + "\n")

    register_all_agents()

    executor = MultiAgentExecutor(
        config=MultiAgentConfig(
            routing_strategy=RoutingStrategy.TASK_SPECIFIC,
        )
    )

    # Simple task - route to faster/cheaper agent
    simple_task = TaskCharacteristics(
        complexity=0.2,  # Low complexity
        urgency=0.8,     # High urgency
        cost_sensitivity=0.9,  # Very cost sensitive
    )

    # Complex task - route to more capable agent
    complex_task = TaskCharacteristics(
        complexity=0.9,  # High complexity
        quality_requirement=0.95,  # High quality
        requires_reasoning=True,
    )

    message = Message(
        message_type=MessageType.TASK_ASSIGNMENT,
        sender_id="user",
        receiver_id="optimizer",
        content={},
    )

    print("Simple task routing:")
    simple_result = executor.execute_with_routing(
        capability=AgentCapability.OPTIMIZATION,
        message=message,
        task_chars=simple_task,
    )
    print(f"  {simple_result.routing_decision}")

    print("\nComplex task routing:")
    complex_result = executor.execute_with_routing(
        capability=AgentCapability.OPTIMIZATION,
        message=message,
        task_chars=complex_task,
    )
    print(f"  {complex_result.routing_decision}")


def example_9_pool_statistics():
    """Example 9: Monitor pool performance statistics."""
    print("\n" + "=" * 80)
    print("Example 9: Pool Performance Statistics")
    print("=" * 80 + "\n")

    register_all_agents()

    executor = MultiAgentExecutor()

    # Run several tasks
    for i in range(3):
        message = Message(
            message_type=MessageType.TASK_ASSIGNMENT,
            sender_id="user",
            receiver_id="validator",
            content={'task': f'validation_{i}'},
        )

        executor.execute(
            capability=AgentCapability.VALIDATION,
            message=message,
        )

    # Get statistics
    stats = executor.get_pool_statistics()

    print("Pool Statistics:")
    for capability, agent_stats in stats.items():
        print(f"\n{capability}:")
        for agent_id, metrics in agent_stats.items():
            print(f"  {agent_id}:")
            print(f"    Executions: {metrics['executions']}")
            print(f"    Success rate: {metrics['success_rate']:.1%}")
            print(f"    Avg latency: {metrics['avg_latency_ms']:.1f}ms")


def main():
    """Run all examples."""
    logger.info("Starting multi-agent orchestration examples")

    try:
        example_1_basic_multi_agent()
        example_2_intelligent_routing()
        example_3_cost_vs_quality()
        example_4_racing_agents()
        example_5_fallback_mechanism()
        example_6_compare_providers()
        example_7_majority_voting()
        example_8_task_specific_routing()
        example_9_pool_statistics()

        print("\n" + "=" * 80)
        print("All examples completed successfully!")
        print("=" * 80)

    except Exception as e:
        logger.error(f"Example failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
