"""Base agent class for the multi-agent system."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from uuid import UUID, uuid4

from loguru import logger

from astraeus.core.message import (
    ConversationThread,
    Message,
    MessagePriority,
    MessageType,
)


class AgentState:
    """Represents the current state of an agent."""

    INITIALIZING = "initializing"
    IDLE = "idle"
    PROCESSING = "processing"
    WAITING_FOR_INPUT = "waiting_for_input"
    ERROR = "error"
    TERMINATED = "terminated"


class BaseAgent(ABC):
    """
    Abstract base class for all agents in the multi-agent system.

    All specialized agents must inherit from this class and implement
    the required abstract methods.

    Attributes:
        agent_id: Unique identifier for this agent instance
        agent_type: Type/role of the agent (e.g., "RequirementsAnalyst")
        state: Current state of the agent
        knowledge_domains: List of knowledge domains this agent specializes in
        capabilities: List of capabilities this agent provides
        message_queue: Queue of received messages awaiting processing
        conversation_threads: Active conversation threads
        decision_log: Log of all decisions made by this agent
    """

    def __init__(
        self,
        agent_type: str,
        agent_id: Optional[str] = None,
        knowledge_domains: Optional[List[str]] = None,
        capabilities: Optional[List[str]] = None,
    ):
        """
        Initialize base agent.

        Args:
            agent_type: Type/role of the agent
            agent_id: Unique identifier (auto-generated if not provided)
            knowledge_domains: List of knowledge domains
            capabilities: List of capabilities
        """
        self.agent_id = agent_id or f"{agent_type}_{uuid4().hex[:8]}"
        self.agent_type = agent_type
        self.state = AgentState.INITIALIZING
        self.knowledge_domains = knowledge_domains or []
        self.capabilities = capabilities or []

        # Communication infrastructure
        self.message_queue: List[Message] = []
        self.conversation_threads: Dict[UUID, ConversationThread] = {}
        self.sent_messages: List[Message] = []

        # Decision tracking
        self.decision_log: List[Dict[str, Any]] = []
        self.performance_metrics: Dict[str, Any] = {}

        # Configuration
        self.config: Dict[str, Any] = {}

        # Communication hub reference (set by hub during registration)
        self._communication_hub = None

        logger.info(
            f"Initialized agent: {self.agent_id} (type: {self.agent_type})"
        )

        # Perform agent-specific initialization
        self._initialize()
        self.state = AgentState.IDLE

    @abstractmethod
    def _initialize(self) -> None:
        """
        Agent-specific initialization logic.

        Subclasses must implement this method to perform any
        necessary setup (loading knowledge bases, initializing models, etc.).
        """
        pass

    @abstractmethod
    def process_message(self, message: Message) -> Optional[List[Message]]:
        """
        Process an incoming message and generate response(s).

        Args:
            message: The message to process

        Returns:
            List of response messages (or None if no response needed)
        """
        pass

    @abstractmethod
    def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a specific task assigned to this agent.

        Args:
            task: Task specification dictionary

        Returns:
            Task results dictionary
        """
        pass

    def receive_message(self, message: Message) -> None:
        """
        Receive and queue a message for processing.

        Args:
            message: The message to receive
        """
        if not message.is_for_agent(self.agent_id):
            logger.warning(
                f"Agent {self.agent_id} received message not intended for it"
            )
            return

        self.message_queue.append(message)

        # Add to conversation thread
        if message.conversation_id not in self.conversation_threads:
            self.conversation_threads[message.conversation_id] = ConversationThread(
                conversation_id=message.conversation_id,
                topic=f"Conversation_{message.conversation_id.hex[:8]}",
            )

        self.conversation_threads[message.conversation_id].add_message(message)

        logger.debug(
            f"Agent {self.agent_id} received {message.message_type.value} "
            f"message from {message.sender}"
        )

    def send_message(self, message: Message) -> None:
        """
        Send a message through the communication hub.

        Args:
            message: The message to send
        """
        if self._communication_hub is None:
            logger.error(
                f"Agent {self.agent_id} not registered with communication hub"
            )
            raise RuntimeError("Agent not registered with communication hub")

        # Ensure sender is set correctly
        message.sender = self.agent_id

        # Track sent message
        self.sent_messages.append(message)

        # Send through hub
        self._communication_hub.route_message(message)

        logger.debug(
            f"Agent {self.agent_id} sent {message.message_type.value} "
            f"message to {message.recipients or 'broadcast'}"
        )

    def process_message_queue(self) -> List[Message]:
        """
        Process all messages in the queue.

        Returns:
            List of all response messages generated
        """
        all_responses = []

        while self.message_queue:
            message = self.message_queue.pop(0)
            self.state = AgentState.PROCESSING

            try:
                responses = self.process_message(message)
                if responses:
                    all_responses.extend(responses)
                    for response in responses:
                        self.send_message(response)

            except Exception as e:
                logger.error(
                    f"Agent {self.agent_id} error processing message: {e}",
                    exc_info=True,
                )
                self.state = AgentState.ERROR

                # Send error notification
                error_msg = Message(
                    sender=self.agent_id,
                    recipients=[message.sender],
                    message_type=MessageType.STATUS_UPDATE,
                    payload={"error": str(e), "original_message": message.to_dict()},
                    priority=MessagePriority.URGENT,
                    conversation_id=message.conversation_id,
                    rationale=f"Error processing message: {e}",
                )
                self.send_message(error_msg)

        self.state = AgentState.IDLE
        return all_responses

    def log_decision(
        self,
        decision: str,
        rationale: str,
        alternatives_considered: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log a design decision for traceability.

        Args:
            decision: The decision made
            rationale: Justification for the decision
            alternatives_considered: Other options that were evaluated
            metadata: Additional context information
        """
        decision_entry = {
            "timestamp": datetime.now().isoformat(),
            "agent_id": self.agent_id,
            "decision": decision,
            "rationale": rationale,
            "alternatives_considered": alternatives_considered or [],
            "metadata": metadata or {},
        }

        self.decision_log.append(decision_entry)

        logger.info(
            f"Agent {self.agent_id} decision: {decision} | Rationale: {rationale}"
        )

    def request_human_review(
        self,
        topic: str,
        options: List[Dict[str, Any]],
        rationale: str,
        priority: MessagePriority = MessagePriority.HIGH,
    ) -> None:
        """
        Request human review/decision at a checkpoint.

        Args:
            topic: What needs to be reviewed
            options: Available options for decision
            rationale: Why human input is needed
            priority: Urgency of the review
        """
        review_request = Message(
            sender=self.agent_id,
            recipients=["HumanReviewer"],
            message_type=MessageType.HUMAN_REVIEW_REQUEST,
            payload={
                "topic": topic,
                "options": options,
                "recommendation": self._generate_recommendation(options),
            },
            priority=priority,
            rationale=rationale,
        )

        self.send_message(review_request)
        self.state = AgentState.WAITING_FOR_INPUT

        logger.info(
            f"Agent {self.agent_id} requested human review: {topic}"
        )

    def _generate_recommendation(
        self, options: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Generate a recommendation from available options.

        Can be overridden by subclasses for domain-specific logic.

        Args:
            options: Available options

        Returns:
            Recommended option with justification
        """
        # Default: no recommendation, let human decide
        return None

    def get_conversation_history(
        self, conversation_id: UUID
    ) -> Optional[ConversationThread]:
        """
        Retrieve a conversation thread by ID.

        Args:
            conversation_id: UUID of the conversation

        Returns:
            ConversationThread if found, None otherwise
        """
        return self.conversation_threads.get(conversation_id)

    def get_agent_info(self) -> Dict[str, Any]:
        """
        Get information about this agent.

        Returns:
            Dictionary with agent information
        """
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "state": self.state,
            "knowledge_domains": self.knowledge_domains,
            "capabilities": self.capabilities,
            "messages_received": len(self.sent_messages),
            "messages_sent": len(self.sent_messages),
            "decisions_logged": len(self.decision_log),
            "active_conversations": len(self.conversation_threads),
        }

    def shutdown(self) -> None:
        """Gracefully shutdown the agent."""
        logger.info(f"Shutting down agent: {self.agent_id}")
        self.state = AgentState.TERMINATED

        # Process any remaining messages
        if self.message_queue:
            logger.warning(
                f"Agent {self.agent_id} has {len(self.message_queue)} "
                "unprocessed messages at shutdown"
            )

    def __repr__(self) -> str:
        """String representation of the agent."""
        return (
            f"{self.__class__.__name__}(id={self.agent_id}, "
            f"type={self.agent_type}, state={self.state})"
        )
