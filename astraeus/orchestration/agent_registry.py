"""
Agent Registry for managing multiple agent implementations.

Supports registering and discovering agents from different LLM providers
(OpenAI, Claude, local models) for each agent type/role.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any, Type
from enum import Enum
from loguru import logger

from astraeus.core.agent_base import Agent


class LLMProvider(Enum):
    """LLM provider types."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"
    CUSTOM = "custom"


class AgentCapability(Enum):
    """Agent capability types."""
    REQUIREMENTS_ANALYSIS = "requirements_analysis"
    ARCHITECTURE_DESIGN = "architecture_design"
    GEOMETRY_GENERATION = "geometry_generation"
    MATERIAL_SELECTION = "material_selection"
    SIMULATION = "simulation"
    OPTIMIZATION = "optimization"
    VALIDATION = "validation"
    SUPERVISION = "supervision"
    REASONING = "reasoning"
    CODE_GENERATION = "code_generation"


@dataclass
class AgentRegistration:
    """Registration information for an agent."""

    agent_id: str
    agent_class: Type[Agent]
    provider: LLMProvider
    capability: AgentCapability

    # Performance characteristics
    avg_latency_ms: float = 0.0
    cost_per_1k_tokens: float = 0.0
    reliability_score: float = 1.0  # 0.0 to 1.0

    # Constraints
    max_tokens: int = 4096
    supports_streaming: bool = False
    supports_function_calling: bool = False

    # Metadata
    version: str = "1.0.0"
    description: str = ""
    tags: List[str] = field(default_factory=list)

    # Factory function for creating instances
    factory: Optional[Callable[..., Agent]] = None

    def create_agent(self, **kwargs) -> Agent:
        """Create an instance of the registered agent."""
        if self.factory:
            return self.factory(**kwargs)
        return self.agent_class(**kwargs)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'agent_id': self.agent_id,
            'provider': self.provider.value,
            'capability': self.capability.value,
            'avg_latency_ms': self.avg_latency_ms,
            'cost_per_1k_tokens': self.cost_per_1k_tokens,
            'reliability_score': self.reliability_score,
            'max_tokens': self.max_tokens,
            'supports_streaming': self.supports_streaming,
            'supports_function_calling': self.supports_function_calling,
            'version': self.version,
            'description': self.description,
            'tags': self.tags,
        }


class AgentRegistry:
    """
    Registry for managing multiple agent implementations.

    Allows registering agents from different providers and querying
    them based on capability, provider, performance characteristics, etc.
    """

    def __init__(self):
        self._registry: Dict[str, AgentRegistration] = {}
        self._by_capability: Dict[AgentCapability, List[str]] = {}
        self._by_provider: Dict[LLMProvider, List[str]] = {}

    def register(self, registration: AgentRegistration) -> None:
        """
        Register an agent.

        Args:
            registration: Agent registration information
        """
        agent_id = registration.agent_id

        if agent_id in self._registry:
            logger.warning(f"Agent {agent_id} already registered, overwriting")

        self._registry[agent_id] = registration

        # Index by capability
        if registration.capability not in self._by_capability:
            self._by_capability[registration.capability] = []
        if agent_id not in self._by_capability[registration.capability]:
            self._by_capability[registration.capability].append(agent_id)

        # Index by provider
        if registration.provider not in self._by_provider:
            self._by_provider[registration.provider] = []
        if agent_id not in self._by_provider[registration.provider]:
            self._by_provider[registration.provider].append(agent_id)

        logger.info(f"Registered agent: {agent_id} ({registration.provider.value}, {registration.capability.value})")

    def unregister(self, agent_id: str) -> bool:
        """
        Unregister an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            True if agent was unregistered
        """
        if agent_id not in self._registry:
            return False

        registration = self._registry[agent_id]

        # Remove from indices
        if registration.capability in self._by_capability:
            self._by_capability[registration.capability].remove(agent_id)
        if registration.provider in self._by_provider:
            self._by_provider[registration.provider].remove(agent_id)

        del self._registry[agent_id]
        logger.info(f"Unregistered agent: {agent_id}")
        return True

    def get(self, agent_id: str) -> Optional[AgentRegistration]:
        """Get agent registration by ID."""
        return self._registry.get(agent_id)

    def find_by_capability(
        self,
        capability: AgentCapability,
        provider: Optional[LLMProvider] = None,
        min_reliability: float = 0.0,
        max_latency_ms: Optional[float] = None,
    ) -> List[AgentRegistration]:
        """
        Find agents by capability and optional filters.

        Args:
            capability: Required capability
            provider: Optional provider filter
            min_reliability: Minimum reliability score
            max_latency_ms: Maximum acceptable latency

        Returns:
            List of matching agent registrations
        """
        agent_ids = self._by_capability.get(capability, [])
        results = []

        for agent_id in agent_ids:
            reg = self._registry[agent_id]

            # Apply filters
            if provider and reg.provider != provider:
                continue
            if reg.reliability_score < min_reliability:
                continue
            if max_latency_ms and reg.avg_latency_ms > max_latency_ms:
                continue

            results.append(reg)

        # Sort by reliability and latency
        results.sort(key=lambda r: (-r.reliability_score, r.avg_latency_ms))
        return results

    def find_by_provider(self, provider: LLMProvider) -> List[AgentRegistration]:
        """Find all agents from a specific provider."""
        agent_ids = self._by_provider.get(provider, [])
        return [self._registry[agent_id] for agent_id in agent_ids]

    def get_all(self) -> List[AgentRegistration]:
        """Get all registered agents."""
        return list(self._registry.values())

    def get_providers_for_capability(self, capability: AgentCapability) -> List[LLMProvider]:
        """Get all providers that support a specific capability."""
        agent_ids = self._by_capability.get(capability, [])
        providers = set()
        for agent_id in agent_ids:
            providers.add(self._registry[agent_id].provider)
        return list(providers)

    def update_metrics(
        self,
        agent_id: str,
        avg_latency_ms: Optional[float] = None,
        reliability_score: Optional[float] = None,
    ) -> bool:
        """
        Update performance metrics for an agent.

        Args:
            agent_id: Agent identifier
            avg_latency_ms: New average latency
            reliability_score: New reliability score

        Returns:
            True if updated successfully
        """
        if agent_id not in self._registry:
            return False

        reg = self._registry[agent_id]

        if avg_latency_ms is not None:
            reg.avg_latency_ms = avg_latency_ms
        if reliability_score is not None:
            reg.reliability_score = max(0.0, min(1.0, reliability_score))

        logger.debug(f"Updated metrics for {agent_id}: latency={reg.avg_latency_ms}ms, reliability={reg.reliability_score}")
        return True

    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        return {
            'total_agents': len(self._registry),
            'by_capability': {cap.value: len(ids) for cap, ids in self._by_capability.items()},
            'by_provider': {prov.value: len(ids) for prov, ids in self._by_provider.items()},
            'avg_reliability': sum(r.reliability_score for r in self._registry.values()) / len(self._registry) if self._registry else 0.0,
        }

    def __len__(self) -> int:
        """Number of registered agents."""
        return len(self._registry)

    def __contains__(self, agent_id: str) -> bool:
        """Check if agent is registered."""
        return agent_id in self._registry


# Global registry instance
_global_registry: Optional[AgentRegistry] = None


def get_global_registry() -> AgentRegistry:
    """Get the global agent registry."""
    global _global_registry
    if _global_registry is None:
        _global_registry = AgentRegistry()
    return _global_registry


def register_agent(registration: AgentRegistration) -> None:
    """Register an agent in the global registry."""
    get_global_registry().register(registration)
