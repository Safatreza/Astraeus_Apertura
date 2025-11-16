"""Tests for specialized agents."""

import pytest
from astraeus.core.communication import CommunicationHub
from astraeus.core.message import Message, MessageType
from astraeus.agents import RequirementsAnalystAgent
from astraeus.data.parameters import (
    MissionRequirements,
    FrequencySpec,
    RadiationPattern,
    Polarization,
    RadarMode,
)


def test_requirements_analyst_initialization():
    """Test Requirements Analyst agent initialization."""
    agent = RequirementsAnalystAgent()

    assert agent.agent_type == "RequirementsAnalyst"
    assert "requirements_parsing" in agent.capabilities
    assert "radar_equation" in agent.knowledge_domains


def test_requirements_analyst_task_execution():
    """Test Requirements Analyst agent task execution."""
    agent = RequirementsAnalystAgent()

    requirements = MissionRequirements(
        mission_name="Test Mission",
        mission_type=RadarMode.SAR,
        frequency=FrequencySpec(center_frequency_ghz=10.0),
        radiation_pattern=RadiationPattern(gain_dbi=35.0),
        polarization=Polarization.LINEAR_HORIZONTAL,
    )

    task = {
        "type": "analyze_requirements",
        "requirements": requirements,
    }

    result = agent.execute_task(task)

    assert "validated_requirements" in result
    assert "validation_results" in result
    assert "constraints" in result
    assert "feasibility" in result


def test_agent_communication():
    """Test agent communication through hub."""
    hub = CommunicationHub()

    agent1 = RequirementsAnalystAgent(agent_id="agent1")
    hub.register_agent(agent1)

    # Create and send message
    msg = Message(
        sender="test_sender",
        recipients=["agent1"],
        message_type=MessageType.QUERY,
        payload={"test": "data"},
        rationale="Test message",
    )

    hub.route_message(msg)

    # Verify message was received
    assert len(agent1.message_queue) == 1
    received_msg = agent1.message_queue[0]
    assert received_msg.payload == {"test": "data"}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
