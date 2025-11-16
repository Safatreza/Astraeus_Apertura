"""Message protocol for inter-agent communication."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4


class MessageType(Enum):
    """Types of messages that can be exchanged between agents."""

    QUERY = "query"  # Request for information
    PROPOSAL = "proposal"  # Design proposal or recommendation
    CRITIQUE = "critique"  # Critical evaluation of a proposal
    APPROVAL = "approval"  # Approval of a proposal
    REJECTION = "rejection"  # Rejection of a proposal
    DATA_TRANSFER = "data_transfer"  # Transfer of design data or results
    STATUS_UPDATE = "status_update"  # Progress update
    REQUEST_CLARIFICATION = "request_clarification"  # Request for clarification
    CONFLICT_ALERT = "conflict_alert"  # Alert about conflicting requirements
    VALIDATION_RESULT = "validation_result"  # Results from validation
    SIMULATION_REQUEST = "simulation_request"  # Request for simulation
    SIMULATION_RESULT = "simulation_result"  # Simulation results
    OPTIMIZATION_REQUEST = "optimization_request"  # Request for optimization
    HUMAN_REVIEW_REQUEST = "human_review_request"  # Request for human intervention


class MessagePriority(Enum):
    """Priority levels for messages."""

    URGENT = "urgent"  # Requires immediate attention
    HIGH = "high"  # High priority
    NORMAL = "normal"  # Normal priority
    LOW = "low"  # Low priority
    INFORMATIONAL = "informational"  # For logging/auditing only


@dataclass
class Message:
    """
    Message structure for inter-agent communication.

    Attributes:
        sender: Identifier of the sending agent
        recipients: List of recipient agent identifiers (empty for broadcast)
        message_type: Type of message
        payload: Message content (design parameters, results, recommendations, etc.)
        priority: Priority level of the message
        conversation_id: UUID linking related messages in a conversation
        in_reply_to: UUID of message this is replying to (if applicable)
        rationale: Explanation or justification for the message content
        timestamp: When the message was created
        metadata: Additional metadata (tags, context, etc.)
    """

    sender: str
    message_type: MessageType
    payload: Any
    recipients: List[str] = field(default_factory=list)
    priority: MessagePriority = MessagePriority.NORMAL
    conversation_id: UUID = field(default_factory=uuid4)
    in_reply_to: Optional[UUID] = None
    rationale: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    message_id: UUID = field(default_factory=uuid4)

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary representation."""
        return {
            "message_id": str(self.message_id),
            "sender": self.sender,
            "recipients": self.recipients,
            "message_type": self.message_type.value,
            "payload": self.payload,
            "priority": self.priority.value,
            "conversation_id": str(self.conversation_id),
            "in_reply_to": str(self.in_reply_to) if self.in_reply_to else None,
            "rationale": self.rationale,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """Create message from dictionary representation."""
        return cls(
            message_id=UUID(data["message_id"]),
            sender=data["sender"],
            recipients=data["recipients"],
            message_type=MessageType(data["message_type"]),
            payload=data["payload"],
            priority=MessagePriority(data["priority"]),
            conversation_id=UUID(data["conversation_id"]),
            in_reply_to=UUID(data["in_reply_to"]) if data["in_reply_to"] else None,
            rationale=data["rationale"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=data["metadata"],
        )

    def is_broadcast(self) -> bool:
        """Check if this is a broadcast message."""
        return len(self.recipients) == 0

    def is_for_agent(self, agent_id: str) -> bool:
        """Check if this message is intended for a specific agent."""
        return self.is_broadcast() or agent_id in self.recipients

    def create_reply(
        self,
        sender: str,
        message_type: MessageType,
        payload: Any,
        rationale: str = "",
        **kwargs
    ) -> "Message":
        """
        Create a reply to this message.

        Args:
            sender: ID of the replying agent
            message_type: Type of reply message
            payload: Reply content
            rationale: Explanation for the reply
            **kwargs: Additional message parameters

        Returns:
            New message that is a reply to this one
        """
        return Message(
            sender=sender,
            recipients=[self.sender],  # Reply to original sender
            message_type=message_type,
            payload=payload,
            rationale=rationale,
            conversation_id=self.conversation_id,
            in_reply_to=self.message_id,
            **kwargs
        )


@dataclass
class ConversationThread:
    """
    Represents a conversation thread between agents.

    Maintains chronological ordering and hierarchical structure
    of related messages.
    """

    conversation_id: UUID
    messages: List[Message] = field(default_factory=list)
    participants: set = field(default_factory=set)
    topic: str = ""
    status: str = "active"  # active, resolved, escalated, archived
    created_at: datetime = field(default_factory=datetime.now)

    def add_message(self, message: Message) -> None:
        """Add a message to the conversation thread."""
        if message.conversation_id != self.conversation_id:
            raise ValueError("Message does not belong to this conversation")

        self.messages.append(message)
        self.participants.add(message.sender)
        self.participants.update(message.recipients)

    def get_message_tree(self) -> Dict[UUID, List[Message]]:
        """
        Build a tree structure of messages showing reply relationships.

        Returns:
            Dictionary mapping message IDs to list of direct replies
        """
        tree = {}
        for msg in self.messages:
            if msg.in_reply_to:
                if msg.in_reply_to not in tree:
                    tree[msg.in_reply_to] = []
                tree[msg.in_reply_to].append(msg)
        return tree

    def get_chronological_messages(self) -> List[Message]:
        """Get messages in chronological order."""
        return sorted(self.messages, key=lambda m: m.timestamp)

    def get_messages_by_sender(self, sender: str) -> List[Message]:
        """Get all messages from a specific sender."""
        return [msg for msg in self.messages if msg.sender == sender]

    def get_unresolved_queries(self) -> List[Message]:
        """Get queries that haven't received a response."""
        query_ids = {
            msg.message_id
            for msg in self.messages
            if msg.message_type == MessageType.QUERY
        }
        replied_ids = {
            msg.in_reply_to
            for msg in self.messages
            if msg.in_reply_to is not None
        }
        unresolved = query_ids - replied_ids
        return [msg for msg in self.messages if msg.message_id in unresolved]
