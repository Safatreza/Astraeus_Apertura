"""
Agent Factory for creating agents with different LLM backends.

Provides factories to create specialized agents (requirements, architecture, etc.)
backed by different LLM providers (OpenAI, Claude, local models).
"""

from typing import Optional, Dict, Any
from loguru import logger

from astraeus.core.agent_base import Agent
from astraeus.llm.llm_interface import (
    LLMInterface,
    OpenAILLM,
    AnthropicLLM,
    LLMConfig,
    create_llm_interface,
)
from astraeus.orchestration.agent_registry import (
    AgentRegistration,
    AgentCapability,
    LLMProvider,
    register_agent,
)

# Import existing agents
from astraeus.agents.requirements_analyst import RequirementsAnalyst
from astraeus.agents.architecture_agent import ArchitectureAgent
from astraeus.agents.geometry_generator import GeometryGenerator
from astraeus.agents.material_selector import MaterialSelector
from astraeus.agents.simulation_agent import SimulationAgent
from astraeus.agents.performance_optimizer import PerformanceOptimizer
from astraeus.agents.validation_agent import ValidationAgent
from astraeus.agents.supervisor_agent import SupervisorAgent


class LLMBackedAgent(Agent):
    """
    Base class for agents backed by LLM interfaces.

    Wraps existing agents to use configurable LLM backends.
    """

    def __init__(
        self,
        agent_class: type,
        llm: LLMInterface,
        agent_id: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize LLM-backed agent.

        Args:
            agent_class: Original agent class to wrap
            llm: LLM interface for reasoning
            agent_id: Optional agent identifier
            **kwargs: Additional arguments for base agent
        """
        super().__init__(agent_id=agent_id or f"{agent_class.__name__}_{llm.__class__.__name__}")

        self.base_agent = agent_class(**kwargs)
        self.llm = llm

        logger.info(f"Created {self.agent_id} backed by {llm.__class__.__name__}")

    def process_message(self, message, **kwargs):
        """Process message using LLM-enhanced logic."""
        # Delegate to base agent but could enhance with LLM reasoning
        return self.base_agent.process_message(message, **kwargs)

    def _llm_reason(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Use LLM for reasoning."""
        response = self.llm.generate(prompt=prompt, system_prompt=system_prompt)
        return response.content


class AgentFactory:
    """
    Factory for creating agents with different LLM backends.

    Supports creating agents backed by OpenAI GPT, Anthropic Claude,
    and other LLM providers.
    """

    @staticmethod
    def create_requirements_analyst(
        provider: LLMProvider = LLMProvider.ANTHROPIC,
        model: Optional[str] = None,
        **kwargs
    ) -> Agent:
        """Create requirements analyst agent."""
        llm = AgentFactory._create_llm(provider, model)

        agent = LLMBackedAgent(
            agent_class=RequirementsAnalyst,
            llm=llm,
            agent_id=f"{provider.value}_requirements_analyst",
            **kwargs
        )

        return agent

    @staticmethod
    def create_architecture_agent(
        provider: LLMProvider = LLMProvider.ANTHROPIC,
        model: Optional[str] = None,
        **kwargs
    ) -> Agent:
        """Create architecture design agent."""
        llm = AgentFactory._create_llm(provider, model)

        agent = LLMBackedAgent(
            agent_class=ArchitectureAgent,
            llm=llm,
            agent_id=f"{provider.value}_architecture_agent",
            **kwargs
        )

        return agent

    @staticmethod
    def create_geometry_generator(
        provider: LLMProvider = LLMProvider.OPENAI,
        model: Optional[str] = None,
        **kwargs
    ) -> Agent:
        """Create geometry generator agent."""
        llm = AgentFactory._create_llm(provider, model)

        agent = LLMBackedAgent(
            agent_class=GeometryGenerator,
            llm=llm,
            agent_id=f"{provider.value}_geometry_generator",
            **kwargs
        )

        return agent

    @staticmethod
    def create_material_selector(
        provider: LLMProvider = LLMProvider.ANTHROPIC,
        model: Optional[str] = None,
        **kwargs
    ) -> Agent:
        """Create material selection agent."""
        llm = AgentFactory._create_llm(provider, model)

        agent = LLMBackedAgent(
            agent_class=MaterialSelector,
            llm=llm,
            agent_id=f"{provider.value}_material_selector",
            **kwargs
        )

        return agent

    @staticmethod
    def create_simulation_agent(
        provider: LLMProvider = LLMProvider.OPENAI,
        model: Optional[str] = None,
        **kwargs
    ) -> Agent:
        """Create simulation agent."""
        llm = AgentFactory._create_llm(provider, model)

        agent = LLMBackedAgent(
            agent_class=SimulationAgent,
            llm=llm,
            agent_id=f"{provider.value}_simulation_agent",
            **kwargs
        )

        return agent

    @staticmethod
    def create_optimizer(
        provider: LLMProvider = LLMProvider.ANTHROPIC,
        model: Optional[str] = None,
        **kwargs
    ) -> Agent:
        """Create performance optimizer agent."""
        llm = AgentFactory._create_llm(provider, model)

        agent = LLMBackedAgent(
            agent_class=PerformanceOptimizer,
            llm=llm,
            agent_id=f"{provider.value}_optimizer",
            **kwargs
        )

        return agent

    @staticmethod
    def create_validator(
        provider: LLMProvider = LLMProvider.ANTHROPIC,
        model: Optional[str] = None,
        **kwargs
    ) -> Agent:
        """Create validation agent."""
        llm = AgentFactory._create_llm(provider, model)

        agent = LLMBackedAgent(
            agent_class=ValidationAgent,
            llm=llm,
            agent_id=f"{provider.value}_validator",
            **kwargs
        )

        return agent

    @staticmethod
    def create_supervisor(
        provider: LLMProvider = LLMProvider.ANTHROPIC,
        model: Optional[str] = None,
        **kwargs
    ) -> Agent:
        """Create supervisor agent."""
        llm = AgentFactory._create_llm(provider, model)

        agent = LLMBackedAgent(
            agent_class=SupervisorAgent,
            llm=llm,
            agent_id=f"{provider.value}_supervisor",
            **kwargs
        )

        return agent

    @staticmethod
    def _create_llm(provider: LLMProvider, model: Optional[str] = None) -> LLMInterface:
        """Create LLM interface based on provider."""

        if provider == LLMProvider.OPENAI:
            config = LLMConfig(
                provider="openai",
                model=model or "gpt-4",
                max_tokens=4096,
                temperature=0.7,
            )
        elif provider == LLMProvider.ANTHROPIC:
            config = LLMConfig(
                provider="anthropic",
                model=model or "claude-3-5-sonnet-20241022",
                max_tokens=4096,
                temperature=0.7,
            )
        else:
            # Default to Anthropic
            config = LLMConfig(
                provider="anthropic",
                model="claude-3-5-sonnet-20241022",
                max_tokens=4096,
                temperature=0.7,
            )

        return create_llm_interface(config)


def register_all_agents() -> None:
    """
    Register all agent variations in the global registry.

    Creates and registers agents with different LLM backends.
    """
    logger.info("Registering all agent variations")

    # Requirements Analyst - Both providers
    register_agent(AgentRegistration(
        agent_id="openai_requirements_analyst",
        agent_class=RequirementsAnalyst,
        provider=LLMProvider.OPENAI,
        capability=AgentCapability.REQUIREMENTS_ANALYSIS,
        avg_latency_ms=1500,
        cost_per_1k_tokens=0.03,  # GPT-4 pricing
        reliability_score=0.95,
        supports_function_calling=True,
        description="Requirements analysis using OpenAI GPT-4",
        factory=lambda **kw: AgentFactory.create_requirements_analyst(LLMProvider.OPENAI, **kw),
    ))

    register_agent(AgentRegistration(
        agent_id="anthropic_requirements_analyst",
        agent_class=RequirementsAnalyst,
        provider=LLMProvider.ANTHROPIC,
        capability=AgentCapability.REQUIREMENTS_ANALYSIS,
        avg_latency_ms=1200,
        cost_per_1k_tokens=0.015,  # Claude pricing
        reliability_score=0.97,
        max_tokens=8192,
        description="Requirements analysis using Anthropic Claude",
        factory=lambda **kw: AgentFactory.create_requirements_analyst(LLMProvider.ANTHROPIC, **kw),
    ))

    # Architecture Agent - Both providers
    register_agent(AgentRegistration(
        agent_id="openai_architecture_agent",
        agent_class=ArchitectureAgent,
        provider=LLMProvider.OPENAI,
        capability=AgentCapability.ARCHITECTURE_DESIGN,
        avg_latency_ms=1800,
        cost_per_1k_tokens=0.03,
        reliability_score=0.93,
        supports_function_calling=True,
        description="Architecture design using OpenAI GPT-4",
        factory=lambda **kw: AgentFactory.create_architecture_agent(LLMProvider.OPENAI, **kw),
    ))

    register_agent(AgentRegistration(
        agent_id="anthropic_architecture_agent",
        agent_class=ArchitectureAgent,
        provider=LLMProvider.ANTHROPIC,
        capability=AgentCapability.ARCHITECTURE_DESIGN,
        avg_latency_ms=1400,
        cost_per_1k_tokens=0.015,
        reliability_score=0.96,
        max_tokens=8192,
        description="Architecture design using Anthropic Claude",
        factory=lambda **kw: AgentFactory.create_architecture_agent(LLMProvider.ANTHROPIC, **kw),
    ))

    # Geometry Generator - Both providers
    register_agent(AgentRegistration(
        agent_id="openai_geometry_generator",
        agent_class=GeometryGenerator,
        provider=LLMProvider.OPENAI,
        capability=AgentCapability.GEOMETRY_GENERATION,
        avg_latency_ms=2000,
        cost_per_1k_tokens=0.03,
        reliability_score=0.92,
        supports_function_calling=True,
        description="Geometry generation using OpenAI GPT-4",
        factory=lambda **kw: AgentFactory.create_geometry_generator(LLMProvider.OPENAI, **kw),
    ))

    register_agent(AgentRegistration(
        agent_id="anthropic_geometry_generator",
        agent_class=GeometryGenerator,
        provider=LLMProvider.ANTHROPIC,
        capability=AgentCapability.GEOMETRY_GENERATION,
        avg_latency_ms=1600,
        cost_per_1k_tokens=0.015,
        reliability_score=0.94,
        max_tokens=8192,
        description="Geometry generation using Anthropic Claude",
        factory=lambda **kw: AgentFactory.create_geometry_generator(LLMProvider.ANTHROPIC, **kw),
    ))

    # Material Selector - Both providers
    register_agent(AgentRegistration(
        agent_id="openai_material_selector",
        agent_class=MaterialSelector,
        provider=LLMProvider.OPENAI,
        capability=AgentCapability.MATERIAL_SELECTION,
        avg_latency_ms=1300,
        cost_per_1k_tokens=0.03,
        reliability_score=0.94,
        description="Material selection using OpenAI GPT-4",
        factory=lambda **kw: AgentFactory.create_material_selector(LLMProvider.OPENAI, **kw),
    ))

    register_agent(AgentRegistration(
        agent_id="anthropic_material_selector",
        agent_class=MaterialSelector,
        provider=LLMProvider.ANTHROPIC,
        capability=AgentCapability.MATERIAL_SELECTION,
        avg_latency_ms=1100,
        cost_per_1k_tokens=0.015,
        reliability_score=0.96,
        max_tokens=8192,
        description="Material selection using Anthropic Claude",
        factory=lambda **kw: AgentFactory.create_material_selector(LLMProvider.ANTHROPIC, **kw),
    ))

    # Optimizer - Both providers
    register_agent(AgentRegistration(
        agent_id="openai_optimizer",
        agent_class=PerformanceOptimizer,
        provider=LLMProvider.OPENAI,
        capability=AgentCapability.OPTIMIZATION,
        avg_latency_ms=2500,
        cost_per_1k_tokens=0.03,
        reliability_score=0.91,
        description="Performance optimization using OpenAI GPT-4",
        factory=lambda **kw: AgentFactory.create_optimizer(LLMProvider.OPENAI, **kw),
    ))

    register_agent(AgentRegistration(
        agent_id="anthropic_optimizer",
        agent_class=PerformanceOptimizer,
        provider=LLMProvider.ANTHROPIC,
        capability=AgentCapability.OPTIMIZATION,
        avg_latency_ms=2000,
        cost_per_1k_tokens=0.015,
        reliability_score=0.95,
        max_tokens=8192,
        description="Performance optimization using Anthropic Claude",
        factory=lambda **kw: AgentFactory.create_optimizer(LLMProvider.ANTHROPIC, **kw),
    ))

    # Validator - Both providers
    register_agent(AgentRegistration(
        agent_id="openai_validator",
        agent_class=ValidationAgent,
        provider=LLMProvider.OPENAI,
        capability=AgentCapability.VALIDATION,
        avg_latency_ms=1600,
        cost_per_1k_tokens=0.03,
        reliability_score=0.93,
        description="Validation using OpenAI GPT-4",
        factory=lambda **kw: AgentFactory.create_validator(LLMProvider.OPENAI, **kw),
    ))

    register_agent(AgentRegistration(
        agent_id="anthropic_validator",
        agent_class=ValidationAgent,
        provider=LLMProvider.ANTHROPIC,
        capability=AgentCapability.VALIDATION,
        avg_latency_ms=1300,
        cost_per_1k_tokens=0.015,
        reliability_score=0.96,
        max_tokens=8192,
        description="Validation using Anthropic Claude",
        factory=lambda **kw: AgentFactory.create_validator(LLMProvider.ANTHROPIC, **kw),
    ))

    # Supervisor - Both providers
    register_agent(AgentRegistration(
        agent_id="openai_supervisor",
        agent_class=SupervisorAgent,
        provider=LLMProvider.OPENAI,
        capability=AgentCapability.SUPERVISION,
        avg_latency_ms=1400,
        cost_per_1k_tokens=0.03,
        reliability_score=0.94,
        description="Supervision using OpenAI GPT-4",
        factory=lambda **kw: AgentFactory.create_supervisor(LLMProvider.OPENAI, **kw),
    ))

    register_agent(AgentRegistration(
        agent_id="anthropic_supervisor",
        agent_class=SupervisorAgent,
        provider=LLMProvider.ANTHROPIC,
        capability=AgentCapability.SUPERVISION,
        avg_latency_ms=1200,
        cost_per_1k_tokens=0.015,
        reliability_score=0.97,
        max_tokens=8192,
        description="Supervision using Anthropic Claude",
        factory=lambda **kw: AgentFactory.create_supervisor(LLMProvider.ANTHROPIC, **kw),
    ))

    logger.info("All agents registered successfully")
