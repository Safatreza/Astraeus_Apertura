# Multi-Agent Orchestration Architecture

Comprehensive guide to the multi-agent system for hosting multiple LLM agents (OpenAI, Claude, etc.) for antenna design tasks.

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     User/Application Layer                       │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
              ┌──────────────────────────┐
              │  Multi-Agent Executor    │
              │  (High-level Interface)  │
              └─────────┬────────────────┘
                        │
           ┌────────────┼────────────┐
           │            │            │
           ▼            ▼            ▼
    ┌──────────┐  ┌─────────┐  ┌───────────┐
    │  Router  │  │  Pools  │  │ Consensus │
    │          │  │         │  │  Engine   │
    └────┬─────┘  └────┬────┘  └─────┬─────┘
         │             │              │
         └─────────────┼──────────────┘
                       │
                       ▼
              ┌────────────────┐
              │ Agent Registry │
              │  (Discovery)   │
              └────────┬───────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        ▼              ▼              ▼
   ┌─────────┐   ┌─────────┐   ┌─────────┐
   │ OpenAI  │   │ Claude  │   │  Local  │
   │ Agents  │   │ Agents  │   │ Agents  │
   └─────────┘   └─────────┘   └─────────┘
```

## 📋 Core Components

### 1. Agent Registry

Central registry for discovering and managing agents from different providers.

**Features:**
- Register agents with capabilities, providers, and performance metrics
- Query agents by capability, provider, reliability
- Track performance metrics (latency, reliability, cost)
- Automatic metric updates based on execution history

**Usage:**
```python
from astraeus.orchestration import AgentRegistry, AgentRegistration
from astraeus.orchestration.agent_registry import AgentCapability, LLMProvider

# Create registration
registration = AgentRegistration(
    agent_id="openai_requirements_analyst",
    agent_class=RequirementsAnalyst,
    provider=LLMProvider.OPENAI,
    capability=AgentCapability.REQUIREMENTS_ANALYSIS,
    avg_latency_ms=1500,
    cost_per_1k_tokens=0.03,
    reliability_score=0.95,
)

# Register agent
registry = AgentRegistry()
registry.register(registration)

# Find agents
agents = registry.find_by_capability(
    AgentCapability.REQUIREMENTS_ANALYSIS,
    min_reliability=0.9,
)
```

### 2. Agent Pool

Manages pools of agents for each capability with various execution strategies.

**Pool Strategies:**
- `SINGLE_BEST`: Execute on best performing agent
- `SINGLE_FASTEST`: Execute on fastest agent
- `SINGLE_CHEAPEST`: Execute on cheapest agent
- `SINGLE_ROUND_ROBIN`: Rotate through agents
- `ALL_PARALLEL`: Execute on all agents in parallel
- `RACE`: Use first successful response
- `MAJORITY_VOTE`: Execute on multiple, use consensus
- `ENSEMBLE`: Combine outputs from multiple agents

**Usage:**
```python
from astraeus.orchestration import AgentPool, AgentPoolConfig
from astraeus.orchestration.agent_pool import PoolStrategy

config = AgentPoolConfig(
    capability=AgentCapability.REQUIREMENTS_ANALYSIS,
    strategy=PoolStrategy.ALL_PARALLEL,
    max_agents=5,
    timeout_seconds=60.0,
)

pool = AgentPool(config=config)
pool.initialize()

result = pool.execute(message)
```

### 3. Consensus Engine

Combines outputs from multiple agents using various voting strategies.

**Voting Strategies:**
- `MAJORITY`: Simple majority vote
- `WEIGHTED`: Weighted by reliability/confidence
- `UNANIMOUS`: Require all agents to agree
- `CONFIDENCE_THRESHOLD`: Require minimum confidence
- `BORDA_COUNT`: Ranked voting
- `MEDIAN`: Median value for numerical results
- `AVERAGE`: Weighted average for numerical results

**Usage:**
```python
from astraeus.orchestration import ConsensusEngine
from astraeus.orchestration.consensus import VotingStrategy, AgentOutput

engine = ConsensusEngine(
    strategy=VotingStrategy.WEIGHTED,
    confidence_threshold=0.7,
)

outputs = [
    AgentOutput(agent_id="openai_agent", result=result1, confidence=0.9),
    AgentOutput(agent_id="claude_agent", result=result2, confidence=0.95),
]

consensus = engine.reach_consensus(outputs)
print(f"Final result: {consensus.final_result}")
print(f"Agreement: {consensus.agreement_level:.1%}")
```

### 4. Agent Router

Intelligently routes tasks to appropriate agents based on task characteristics.

**Routing Strategies:**
- `QUALITY_OPTIMIZED`: Best quality, regardless of cost
- `COST_OPTIMIZED`: Lowest cost
- `LATENCY_OPTIMIZED`: Fastest response
- `BALANCED`: Balance cost, latency, quality
- `TASK_SPECIFIC`: Route based on task characteristics
- `LOAD_BALANCED`: Distribute load evenly
- `PROVIDER_PREFERENCE`: Prefer specific providers

**Usage:**
```python
from astraeus.orchestration import AgentRouter
from astraeus.orchestration.router import RoutingStrategy, TaskCharacteristics

router = AgentRouter(default_strategy=RoutingStrategy.BALANCED)

task_chars = TaskCharacteristics(
    complexity=0.9,  # High complexity
    urgency=0.5,     # Medium urgency
    quality_requirement=0.95,  # High quality needed
    requires_reasoning=True,
)

decision = router.route(
    capability=AgentCapability.ARCHITECTURE_DESIGN,
    task_chars=task_chars,
    num_agents=3,
)
```

### 5. Multi-Agent Executor

High-level interface for orchestrating multiple agents.

**Usage:**
```python
from astraeus.orchestration import MultiAgentExecutor, MultiAgentConfig

config = MultiAgentConfig(
    pool_strategy=PoolStrategy.ALL_PARALLEL,
    voting_strategy=VotingStrategy.WEIGHTED,
    routing_strategy=RoutingStrategy.BALANCED,
)

executor = MultiAgentExecutor(config=config)

# Execute with consensus
result = executor.execute(
    capability=AgentCapability.REQUIREMENTS_ANALYSIS,
    message=message,
    use_consensus=True,
)

# Execute with intelligent routing
result = executor.execute_with_routing(
    capability=AgentCapability.OPTIMIZATION,
    message=message,
    task_chars=task_characteristics,
)

# Execute with fallback
result = executor.execute_with_fallback(
    capability=AgentCapability.SIMULATION,
    message=message,
    max_attempts=3,
)
```

### 6. Agent Comparison Framework

Benchmark and compare agents from different providers.

**Usage:**
```python
from astraeus.orchestration.agent_comparison import (
    AgentComparisonFramework,
    BenchmarkTask,
)

framework = AgentComparisonFramework()

# Add benchmark tasks
task = BenchmarkTask(
    task_id="req_analysis_1",
    description="Analyze satellite requirements",
    message=message,
    capability=AgentCapability.REQUIREMENTS_ANALYSIS,
)
framework.add_benchmark_task(task)

# Run comparison
report = framework.run_comparison(AgentCapability.REQUIREMENTS_ANALYSIS)

# Find best agent
best_agent = framework.get_best_agent_for_capability(
    capability=AgentCapability.REQUIREMENTS_ANALYSIS,
    optimize_for='quality',  # or 'latency', 'cost', 'balanced'
)
```

## 🚀 Quick Start

### 1. Register All Agents

```python
from astraeus.orchestration.agent_factory import register_all_agents

# Register all agent variations (OpenAI + Claude)
register_all_agents()
```

This registers 16 agents (8 capabilities × 2 providers):
- Requirements Analyst (OpenAI, Claude)
- Architecture Agent (OpenAI, Claude)
- Geometry Generator (OpenAI, Claude)
- Material Selector (OpenAI, Claude)
- Simulation Agent (OpenAI, Claude)
- Performance Optimizer (OpenAI, Claude)
- Validation Agent (OpenAI, Claude)
- Supervisor Agent (OpenAI, Claude)

### 2. Basic Multi-Agent Execution

```python
from astraeus.orchestration import MultiAgentExecutor
from astraeus.orchestration.agent_registry import AgentCapability
from astraeus.core.message import Message, MessageType

executor = MultiAgentExecutor()

message = Message(
    message_type=MessageType.TASK_ASSIGNMENT,
    sender_id="user",
    receiver_id="requirements_analyst",
    content={'frequency_ghz': 10.0, 'gain_db': 30},
)

result = executor.execute(
    capability=AgentCapability.REQUIREMENTS_ANALYSIS,
    message=message,
    use_consensus=True,
)

print(f"Result: {result.final_result}")
print(f"Confidence: {result.consensus_result.confidence:.2f}")
```

### 3. Compare OpenAI vs Claude

```python
comparison = executor.compare_agents(
    capability=AgentCapability.REQUIREMENTS_ANALYSIS,
    message=message,
)

for result in comparison['results']:
    print(f"{result['provider']:10} - "
          f"Success: {result['success']:5} - "
          f"Latency: {result['latency_ms']:7.1f}ms")
```

## 📊 Use Cases

### Use Case 1: High-Quality Critical Tasks

Use multiple agents with consensus for critical decisions:

```python
config = MultiAgentConfig(
    pool_strategy=PoolStrategy.ALL_PARALLEL,
    voting_strategy=VotingStrategy.UNANIMOUS,  # Require agreement
    routing_strategy=RoutingStrategy.QUALITY_OPTIMIZED,
)

executor = MultiAgentExecutor(config=config)
```

### Use Case 2: Cost-Sensitive Batch Processing

Minimize costs for large-scale batch processing:

```python
config = MultiAgentConfig(
    pool_strategy=PoolStrategy.SINGLE_CHEAPEST,
    routing_strategy=RoutingStrategy.COST_OPTIMIZED,
)

executor = MultiAgentExecutor(config=config)
```

### Use Case 3: Low-Latency Real-Time Systems

Minimize response time:

```python
config = MultiAgentConfig(
    pool_strategy=PoolStrategy.RACE,  # First response wins
    routing_strategy=RoutingStrategy.LATENCY_OPTIMIZED,
)

executor = MultiAgentExecutor(config=config)
```

### Use Case 4: Balanced Production System

Balance quality, cost, and latency:

```python
config = MultiAgentConfig(
    pool_strategy=PoolStrategy.SINGLE_BEST,
    routing_strategy=RoutingStrategy.BALANCED,
    enable_fallback=True,
)

executor = MultiAgentExecutor(config=config)
```

## 🔧 Configuration

### Environment Variables

```bash
# API Keys
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...

# Multi-Agent Configuration
POOL_STRATEGY=all_parallel  # or single_best, race, etc.
VOTING_STRATEGY=weighted  # or majority, unanimous, etc.
ROUTING_STRATEGY=balanced  # or cost_optimized, quality_optimized, etc.
CONSENSUS_THRESHOLD=0.7
ENABLE_FALLBACK=true
MAX_AGENTS_PER_POOL=5
```

### Programmatic Configuration

```python
from astraeus.orchestration import MultiAgentConfig
from astraeus.orchestration.agent_pool import PoolStrategy
from astraeus.orchestration.consensus import VotingStrategy
from astraeus.orchestration.router import RoutingStrategy

config = MultiAgentConfig(
    # Pool configuration
    pool_strategy=PoolStrategy.ALL_PARALLEL,

    # Consensus configuration
    voting_strategy=VotingStrategy.WEIGHTED,
    consensus_threshold=0.7,

    # Routing configuration
    routing_strategy=RoutingStrategy.BALANCED,

    # Performance configuration
    timeout_seconds=60.0,
    max_retries=3,
    enable_fallback=True,

    # Cost controls
    max_cost_per_task=1.0,
    prefer_cost_optimization=False,
)
```

## 📈 Performance Monitoring

### Pool Statistics

```python
# Get pool performance statistics
stats = executor.get_pool_statistics()

for capability, agent_stats in stats.items():
    print(f"{capability}:")
    for agent_id, metrics in agent_stats.items():
        print(f"  {agent_id}:")
        print(f"    Success rate: {metrics['success_rate']:.1%}")
        print(f"    Avg latency: {metrics['avg_latency_ms']:.1f}ms")
```

### Registry Statistics

```python
# Get registry statistics
stats = executor.get_registry_statistics()

print(f"Total agents: {stats['total_agents']}")
print(f"By capability: {stats['by_capability']}")
print(f"By provider: {stats['by_provider']}")
print(f"Avg reliability: {stats['avg_reliability']:.2f}")
```

### Benchmarking

```python
from astraeus.orchestration.agent_comparison import create_comparison_framework

framework = create_comparison_framework(executor)

# Benchmark latency
latency_stats = framework.benchmark_latency(
    capability=AgentCapability.OPTIMIZATION,
    message=message,
    num_runs=10,
)

# Compare providers
provider_comparison = framework.compare_providers(
    capability=AgentCapability.REQUIREMENTS_ANALYSIS,
    tasks=benchmark_tasks,
)
```

## 🎯 Best Practices

### 1. Agent Selection

- **Complex reasoning tasks**: Use Claude (Anthropic)
- **Code generation**: Use GPT-4 (OpenAI)
- **Cost-sensitive tasks**: Start with cheaper models, fallback to expensive
- **Critical decisions**: Use consensus from multiple agents

### 2. Consensus Strategies

- **Numerical results**: Use `MEDIAN` or `AVERAGE`
- **Classification**: Use `MAJORITY` or `WEIGHTED`
- **Critical decisions**: Use `UNANIMOUS`
- **Quick decisions**: Use `CONFIDENCE_THRESHOLD`

### 3. Routing Strategies

- **Development**: Use `BALANCED`
- **Production (quality)**: Use `QUALITY_OPTIMIZED`
- **Production (cost)**: Use `COST_OPTIMIZED`
- **Production (latency)**: Use `LATENCY_OPTIMIZED`
- **Complex workflows**: Use `TASK_SPECIFIC`

### 4. Error Handling

- Always enable fallback for production
- Set appropriate timeouts
- Monitor success rates and adjust strategies
- Use retry logic for transient failures

### 5. Cost Optimization

- Use `COST_OPTIMIZED` routing for non-critical tasks
- Implement cost limits per task
- Monitor cost metrics in benchmarks
- Use cheaper models when quality requirements allow

## 📚 Examples

See comprehensive examples in:
- `examples/multi_agent_orchestration.py` - 9 orchestration examples
- `examples/agent_benchmarking.py` - 8 benchmarking examples

## 🔗 API Reference

### Classes

- `AgentRegistry`: Central registry for agent discovery
- `AgentPool`: Manages pools of agents with execution strategies
- `ConsensusEngine`: Combines outputs using voting strategies
- `AgentRouter`: Routes tasks to appropriate agents
- `MultiAgentExecutor`: High-level multi-agent orchestration
- `AgentComparisonFramework`: Benchmarking and comparison
- `AgentFactory`: Creates agents with different LLM backends

### Enums

- `LLMProvider`: OpenAI, Anthropic, Local, Custom
- `AgentCapability`: Requirements Analysis, Architecture Design, etc.
- `PoolStrategy`: Execution strategies for agent pools
- `VotingStrategy`: Consensus strategies
- `RoutingStrategy`: Routing strategies

## 🚨 Troubleshooting

### Issue: Agents not found

**Solution:**
```python
from astraeus.orchestration.agent_factory import register_all_agents
register_all_agents()  # Make sure to call this first
```

### Issue: Low consensus confidence

**Solution:**
- Reduce `consensus_threshold`
- Use different `voting_strategy`
- Check individual agent results for disagreement reasons

### Issue: High costs

**Solution:**
- Use `COST_OPTIMIZED` routing
- Set `max_cost_per_task` limits
- Prefer cheaper providers for simple tasks
- Use `SINGLE_CHEAPEST` pool strategy

### Issue: High latency

**Solution:**
- Use `LATENCY_OPTIMIZED` routing
- Use `RACE` pool strategy
- Reduce number of parallel agents
- Set stricter timeouts

## 📝 License

MIT License - see LICENSE file for details

---

**Last Updated**: 2025-01-17
**Version**: 2.0.0
