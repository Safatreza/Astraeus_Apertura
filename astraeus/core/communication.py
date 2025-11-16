"""Communication hub for managing inter-agent message routing."""

from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from uuid import UUID

from loguru import logger

from astraeus.core.message import (
    ConversationThread,
    Message,
    MessagePriority,
    MessageType,
)


class CommunicationHub:
    """
    Central communication hub for routing messages between agents.

    Manages:
    - Agent registration and discovery
    - Message routing and delivery
    - Conversation tracking
    - Message history and audit trail
    - Conflict detection
    """

    def __init__(self):
        """Initialize the communication hub."""
        self.agents: Dict[str, Any] = {}  # agent_id -> agent instance
        self.message_history: List[Message] = []
        self.conversations: Dict[UUID, ConversationThread] = {}
        self.broadcast_subscribers: Set[str] = set()

        # Statistics
        self.stats = {
            "total_messages": 0,
            "messages_by_type": defaultdict(int),
            "messages_by_agent": defaultdict(int),
        }

        logger.info("Communication hub initialized")

    def register_agent(self, agent) -> None:
        """
        Register an agent with the communication hub.

        Args:
            agent: Agent instance to register
        """
        if agent.agent_id in self.agents:
            logger.warning(f"Agent {agent.agent_id} already registered")
            return

        self.agents[agent.agent_id] = agent
        agent._communication_hub = self
        self.broadcast_subscribers.add(agent.agent_id)

        logger.info(
            f"Registered agent: {agent.agent_id} (type: {agent.agent_type})"
        )

    def unregister_agent(self, agent_id: str) -> None:
        """
        Unregister an agent from the communication hub.

        Args:
            agent_id: ID of agent to unregister
        """
        if agent_id in self.agents:
            del self.agents[agent_id]
            self.broadcast_subscribers.discard(agent_id)
            logger.info(f"Unregistered agent: {agent_id}")
        else:
            logger.warning(f"Attempted to unregister unknown agent: {agent_id}")

    def route_message(self, message: Message) -> None:
        """
        Route a message to its intended recipient(s).

        Args:
            message: Message to route
        """
        # Update statistics
        self.stats["total_messages"] += 1
        self.stats["messages_by_type"][message.message_type.value] += 1
        self.stats["messages_by_agent"][message.sender] += 1

        # Store in message history
        self.message_history.append(message)

        # Track conversation
        if message.conversation_id not in self.conversations:
            self.conversations[message.conversation_id] = ConversationThread(
                conversation_id=message.conversation_id,
                topic=f"Conversation_{message.conversation_id.hex[:8]}",
            )
        self.conversations[message.conversation_id].add_message(message)

        # Determine recipients
        if message.is_broadcast():
            recipients = list(self.broadcast_subscribers - {message.sender})
            logger.debug(
                f"Broadcasting message from {message.sender} "
                f"to {len(recipients)} agents"
            )
        else:
            recipients = message.recipients
            logger.debug(
                f"Routing message from {message.sender} "
                f"to {recipients}"
            )

        # Deliver to recipients
        for recipient_id in recipients:
            if recipient_id in self.agents:
                self.agents[recipient_id].receive_message(message)
            else:
                logger.warning(
                    f"Message intended for unknown agent: {recipient_id}"
                )

        # Log high-priority messages
        if message.priority in [MessagePriority.URGENT, MessagePriority.HIGH]:
            logger.warning(
                f"HIGH PRIORITY: {message.message_type.value} "
                f"from {message.sender} - {message.rationale}"
            )

    def get_agent(self, agent_id: str) -> Optional[Any]:
        """
        Retrieve an agent by ID.

        Args:
            agent_id: ID of agent to retrieve

        Returns:
            Agent instance if found, None otherwise
        """
        return self.agents.get(agent_id)

    def get_agents_by_type(self, agent_type: str) -> List[Any]:
        """
        Get all agents of a specific type.

        Args:
            agent_type: Type of agents to retrieve

        Returns:
            List of agents matching the type
        """
        return [
            agent
            for agent in self.agents.values()
            if agent.agent_type == agent_type
        ]

    def get_agents_by_capability(self, capability: str) -> List[Any]:
        """
        Find agents that have a specific capability.

        Args:
            capability: Capability to search for

        Returns:
            List of agents with the capability
        """
        return [
            agent
            for agent in self.agents.values()
            if capability in agent.capabilities
        ]

    def get_conversation(self, conversation_id: UUID) -> Optional[ConversationThread]:
        """
        Retrieve a conversation thread.

        Args:
            conversation_id: UUID of the conversation

        Returns:
            ConversationThread if found, None otherwise
        """
        return self.conversations.get(conversation_id)

    def get_message_history(
        self,
        sender: Optional[str] = None,
        recipient: Optional[str] = None,
        message_type: Optional[MessageType] = None,
        since: Optional[datetime] = None,
    ) -> List[Message]:
        """
        Query message history with filters.

        Args:
            sender: Filter by sender agent ID
            recipient: Filter by recipient agent ID
            message_type: Filter by message type
            since: Filter by timestamp (messages after this time)

        Returns:
            List of messages matching the filters
        """
        messages = self.message_history

        if sender:
            messages = [m for m in messages if m.sender == sender]

        if recipient:
            messages = [m for m in messages if recipient in m.recipients]

        if message_type:
            messages = [m for m in messages if m.message_type == message_type]

        if since:
            messages = [m for m in messages if m.timestamp >= since]

        return messages

    def detect_conflicts(self) -> List[Dict[str, Any]]:
        """
        Detect conflicting messages or recommendations.

        Analyzes recent messages to identify disagreements between agents
        that may require supervisor intervention.

        Returns:
            List of detected conflicts with details
        """
        conflicts = []

        # Group recent proposals by conversation
        for conversation in self.conversations.values():
            proposals = [
                m
                for m in conversation.messages
                if m.message_type == MessageType.PROPOSAL
            ]

            # Check for contradictory proposals in the same conversation
            if len(proposals) > 1:
                # Simplified conflict detection - can be enhanced
                # Look for rejections of proposals
                rejections = [
                    m
                    for m in conversation.messages
                    if m.message_type == MessageType.REJECTION
                ]

                for rejection in rejections:
                    if rejection.in_reply_to:
                        conflicts.append(
                            {
                                "conversation_id": conversation.conversation_id,
                                "type": "proposal_rejection",
                                "agents_involved": [
                                    rejection.sender,
                                    rejection.recipients[0]
                                    if rejection.recipients
                                    else "unknown",
                                ],
                                "details": rejection.payload,
                                "timestamp": rejection.timestamp,
                            }
                        )

        return conflicts

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get communication statistics.

        Returns:
            Dictionary with statistics
        """
        return {
            "total_messages": self.stats["total_messages"],
            "messages_by_type": dict(self.stats["messages_by_type"]),
            "messages_by_agent": dict(self.stats["messages_by_agent"]),
            "active_agents": len(self.agents),
            "active_conversations": len(self.conversations),
            "message_history_size": len(self.message_history),
        }

    def export_conversation(
        self, conversation_id: UUID, format: str = "dict"
    ) -> Any:
        """
        Export a conversation in various formats.

        Args:
            conversation_id: UUID of conversation to export
            format: Export format ('dict', 'json', 'markdown')

        Returns:
            Conversation data in requested format
        """
        conversation = self.conversations.get(conversation_id)
        if not conversation:
            return None

        if format == "dict":
            return {
                "conversation_id": str(conversation.conversation_id),
                "topic": conversation.topic,
                "participants": list(conversation.participants),
                "status": conversation.status,
                "created_at": conversation.created_at.isoformat(),
                "messages": [m.to_dict() for m in conversation.messages],
            }

        elif format == "markdown":
            lines = [
                f"# Conversation: {conversation.topic}",
                f"**ID**: {conversation.conversation_id}",
                f"**Participants**: {', '.join(conversation.participants)}",
                f"**Status**: {conversation.status}",
                f"**Created**: {conversation.created_at.isoformat()}",
                "",
                "## Messages",
                "",
            ]

            for msg in conversation.get_chronological_messages():
                lines.extend(
                    [
                        f"### [{msg.timestamp.strftime('%H:%M:%S')}] "
                        f"{msg.sender} → {msg.recipients or 'ALL'}",
                        f"**Type**: {msg.message_type.value}",
                        f"**Priority**: {msg.priority.value}",
                        f"**Rationale**: {msg.rationale}",
                        f"**Payload**: {msg.payload}",
                        "",
                    ]
                )

            return "\n".join(lines)

        else:
            raise ValueError(f"Unsupported export format: {format}")

    def clear_history(self, before: Optional[datetime] = None) -> int:
        """
        Clear message history (for memory management).

        Args:
            before: Only clear messages before this timestamp

        Returns:
            Number of messages cleared
        """
        if before is None:
            count = len(self.message_history)
            self.message_history.clear()
            logger.info(f"Cleared {count} messages from history")
            return count
        else:
            original_count = len(self.message_history)
            self.message_history = [
                m for m in self.message_history if m.timestamp >= before
            ]
            cleared = original_count - len(self.message_history)
            logger.info(f"Cleared {cleared} messages before {before}")
            return cleared

    def shutdown(self) -> None:
        """Shutdown the communication hub."""
        logger.info("Shutting down communication hub")

        # Notify all agents
        for agent in self.agents.values():
            agent.shutdown()

        logger.info(
            f"Communication hub shutdown complete. "
            f"Processed {self.stats['total_messages']} total messages."
        )
