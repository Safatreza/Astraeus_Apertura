"""
Multi-agent orchestration system.

Provides infrastructure for hosting and coordinating multiple agents
from different LLM providers (OpenAI, Claude, etc.) for each task.
"""

from astraeus.orchestration.agent_registry import AgentRegistry, AgentRegistration
from astraeus.orchestration.agent_pool import AgentPool, PoolStrategy
from astraeus.orchestration.consensus import ConsensusEngine, VotingStrategy
from astraeus.orchestration.router import AgentRouter, RoutingStrategy
from astraeus.orchestration.multi_agent_executor import MultiAgentExecutor

__all__ = [
    'AgentRegistry',
    'AgentRegistration',
    'AgentPool',
    'PoolStrategy',
    'ConsensusEngine',
    'VotingStrategy',
    'AgentRouter',
    'RoutingStrategy',
    'MultiAgentExecutor',
]
