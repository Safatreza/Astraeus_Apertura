"""
Consensus mechanisms for combining outputs from multiple agents.

Provides various voting and aggregation strategies for multi-agent systems.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from enum import Enum
from collections import Counter
import json
from loguru import logger


class VotingStrategy(Enum):
    """Strategy for combining agent outputs."""

    MAJORITY = "majority"  # Simple majority vote
    WEIGHTED = "weighted"  # Weighted by reliability/confidence
    UNANIMOUS = "unanimous"  # Require all agents to agree
    CONFIDENCE_THRESHOLD = "confidence_threshold"  # Require minimum confidence
    BORDA_COUNT = "borda_count"  # Ranked voting
    MEDIAN = "median"  # Median value for numerical results
    AVERAGE = "average"  # Average value for numerical results
    CUSTOM = "custom"  # Custom consensus function


@dataclass
class AgentOutput:
    """Output from a single agent."""

    agent_id: str
    result: Any
    confidence: float = 1.0  # 0.0 to 1.0
    reliability: float = 1.0  # From agent's historical performance
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConsensusResult:
    """Result of consensus process."""

    final_result: Any
    confidence: float
    agreement_level: float  # How much agents agreed (0.0 to 1.0)
    num_agents: int
    strategy_used: VotingStrategy
    individual_outputs: List[AgentOutput] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


class ConsensusEngine:
    """
    Engine for reaching consensus among multiple agents.

    Supports various voting and aggregation strategies to combine
    outputs from multiple LLM agents.
    """

    def __init__(
        self,
        strategy: VotingStrategy = VotingStrategy.WEIGHTED,
        confidence_threshold: float = 0.7,
        min_agreement: float = 0.5,
    ):
        self.strategy = strategy
        self.confidence_threshold = confidence_threshold
        self.min_agreement = min_agreement

        # Custom consensus function
        self._custom_fn: Optional[Callable[[List[AgentOutput]], ConsensusResult]] = None

    def reach_consensus(
        self,
        outputs: List[AgentOutput],
        strategy: Optional[VotingStrategy] = None,
    ) -> ConsensusResult:
        """
        Reach consensus from multiple agent outputs.

        Args:
            outputs: List of agent outputs
            strategy: Override default strategy

        Returns:
            Consensus result
        """
        if not outputs:
            return ConsensusResult(
                final_result=None,
                confidence=0.0,
                agreement_level=0.0,
                num_agents=0,
                strategy_used=self.strategy,
            )

        strategy = strategy or self.strategy

        # Route to appropriate consensus method
        if strategy == VotingStrategy.MAJORITY:
            result = self._majority_vote(outputs)
        elif strategy == VotingStrategy.WEIGHTED:
            result = self._weighted_vote(outputs)
        elif strategy == VotingStrategy.UNANIMOUS:
            result = self._unanimous_vote(outputs)
        elif strategy == VotingStrategy.CONFIDENCE_THRESHOLD:
            result = self._confidence_threshold_vote(outputs)
        elif strategy == VotingStrategy.BORDA_COUNT:
            result = self._borda_count(outputs)
        elif strategy == VotingStrategy.MEDIAN:
            result = self._median_aggregation(outputs)
        elif strategy == VotingStrategy.AVERAGE:
            result = self._average_aggregation(outputs)
        elif strategy == VotingStrategy.CUSTOM and self._custom_fn:
            result = self._custom_fn(outputs)
        else:
            result = self._weighted_vote(outputs)

        result.individual_outputs = outputs
        result.num_agents = len(outputs)
        result.strategy_used = strategy

        logger.info(
            f"Consensus reached: {result.final_result} "
            f"(confidence={result.confidence:.2f}, agreement={result.agreement_level:.2f})"
        )

        return result

    def set_custom_function(self, fn: Callable[[List[AgentOutput]], ConsensusResult]) -> None:
        """Set custom consensus function."""
        self._custom_fn = fn
        logger.info("Custom consensus function registered")

    def _majority_vote(self, outputs: List[AgentOutput]) -> ConsensusResult:
        """Simple majority voting."""
        # Convert outputs to strings for comparison
        votes = [self._serialize_result(output.result) for output in outputs]
        vote_counts = Counter(votes)

        if not vote_counts:
            return ConsensusResult(
                final_result=None,
                confidence=0.0,
                agreement_level=0.0,
                num_agents=len(outputs),
                strategy_used=VotingStrategy.MAJORITY,
            )

        # Most common result
        most_common_vote, count = vote_counts.most_common(1)[0]
        agreement_level = count / len(votes)

        # Find original result object
        final_result = None
        for output in outputs:
            if self._serialize_result(output.result) == most_common_vote:
                final_result = output.result
                break

        return ConsensusResult(
            final_result=final_result,
            confidence=agreement_level,
            agreement_level=agreement_level,
            num_agents=len(outputs),
            strategy_used=VotingStrategy.MAJORITY,
            details={'vote_distribution': dict(vote_counts)},
        )

    def _weighted_vote(self, outputs: List[AgentOutput]) -> ConsensusResult:
        """Weighted voting based on confidence and reliability."""
        # Group by result value
        result_groups: Dict[str, List[AgentOutput]] = {}

        for output in outputs:
            key = self._serialize_result(output.result)
            if key not in result_groups:
                result_groups[key] = []
            result_groups[key].append(output)

        # Calculate weighted scores
        weighted_scores: Dict[str, float] = {}
        for key, group in result_groups.items():
            total_weight = sum(
                output.confidence * output.reliability
                for output in group
            )
            weighted_scores[key] = total_weight

        if not weighted_scores:
            return ConsensusResult(
                final_result=None,
                confidence=0.0,
                agreement_level=0.0,
                num_agents=len(outputs),
                strategy_used=VotingStrategy.WEIGHTED,
            )

        # Find result with highest weighted score
        best_result_key = max(weighted_scores.keys(), key=lambda k: weighted_scores[k])
        best_score = weighted_scores[best_result_key]

        # Total possible weight
        total_weight = sum(output.confidence * output.reliability for output in outputs)
        agreement_level = best_score / total_weight if total_weight > 0 else 0.0

        # Get original result
        final_result = None
        for output in outputs:
            if self._serialize_result(output.result) == best_result_key:
                final_result = output.result
                break

        return ConsensusResult(
            final_result=final_result,
            confidence=agreement_level,
            agreement_level=agreement_level,
            num_agents=len(outputs),
            strategy_used=VotingStrategy.WEIGHTED,
            details={'weighted_scores': weighted_scores},
        )

    def _unanimous_vote(self, outputs: List[AgentOutput]) -> ConsensusResult:
        """Require unanimous agreement."""
        if not outputs:
            return ConsensusResult(
                final_result=None,
                confidence=0.0,
                agreement_level=0.0,
                num_agents=0,
                strategy_used=VotingStrategy.UNANIMOUS,
            )

        # Check if all results are the same
        first_result = self._serialize_result(outputs[0].result)
        all_same = all(
            self._serialize_result(output.result) == first_result
            for output in outputs
        )

        if all_same:
            avg_confidence = sum(output.confidence for output in outputs) / len(outputs)
            return ConsensusResult(
                final_result=outputs[0].result,
                confidence=avg_confidence,
                agreement_level=1.0,
                num_agents=len(outputs),
                strategy_used=VotingStrategy.UNANIMOUS,
            )
        else:
            return ConsensusResult(
                final_result=None,
                confidence=0.0,
                agreement_level=0.0,
                num_agents=len(outputs),
                strategy_used=VotingStrategy.UNANIMOUS,
                details={'reason': 'No unanimous agreement'},
            )

    def _confidence_threshold_vote(self, outputs: List[AgentOutput]) -> ConsensusResult:
        """Filter by confidence threshold and use majority vote."""
        # Filter outputs by confidence
        high_confidence = [
            output for output in outputs
            if output.confidence >= self.confidence_threshold
        ]

        if not high_confidence:
            logger.warning(f"No outputs meet confidence threshold {self.confidence_threshold}")
            high_confidence = outputs  # Fall back to all outputs

        # Use majority vote on filtered outputs
        return self._majority_vote(high_confidence)

    def _borda_count(self, outputs: List[AgentOutput]) -> ConsensusResult:
        """
        Borda count voting (ranked voting).

        Assumes outputs contain rankings or can be scored.
        """
        # This is a simplified implementation
        # In practice, would need ranked preferences from each agent

        # For now, use confidence as ranking score
        scored_results: Dict[str, float] = {}

        for output in outputs:
            key = self._serialize_result(output.result)
            score = output.confidence * output.reliability

            if key not in scored_results:
                scored_results[key] = 0.0
            scored_results[key] += score

        if not scored_results:
            return ConsensusResult(
                final_result=None,
                confidence=0.0,
                agreement_level=0.0,
                num_agents=len(outputs),
                strategy_used=VotingStrategy.BORDA_COUNT,
            )

        # Result with highest Borda score
        best_result_key = max(scored_results.keys(), key=lambda k: scored_results[k])
        best_score = scored_results[best_result_key]
        total_score = sum(scored_results.values())

        agreement_level = best_score / total_score if total_score > 0 else 0.0

        # Get original result
        final_result = None
        for output in outputs:
            if self._serialize_result(output.result) == best_result_key:
                final_result = output.result
                break

        return ConsensusResult(
            final_result=final_result,
            confidence=agreement_level,
            agreement_level=agreement_level,
            num_agents=len(outputs),
            strategy_used=VotingStrategy.BORDA_COUNT,
            details={'borda_scores': scored_results},
        )

    def _median_aggregation(self, outputs: List[AgentOutput]) -> ConsensusResult:
        """Median aggregation for numerical results."""
        try:
            values = [float(output.result) for output in outputs]
        except (ValueError, TypeError):
            logger.warning("Cannot compute median for non-numerical results")
            return self._majority_vote(outputs)

        values.sort()
        n = len(values)

        if n % 2 == 0:
            median = (values[n // 2 - 1] + values[n // 2]) / 2
        else:
            median = values[n // 2]

        # Calculate variance as measure of agreement
        mean = sum(values) / n
        variance = sum((v - mean) ** 2 for v in values) / n
        agreement_level = max(0.0, 1.0 - min(1.0, variance / (mean ** 2) if mean != 0 else 1.0))

        return ConsensusResult(
            final_result=median,
            confidence=agreement_level,
            agreement_level=agreement_level,
            num_agents=len(outputs),
            strategy_used=VotingStrategy.MEDIAN,
            details={'median': median, 'mean': mean, 'variance': variance},
        )

    def _average_aggregation(self, outputs: List[AgentOutput]) -> ConsensusResult:
        """Average aggregation for numerical results."""
        try:
            values = [float(output.result) for output in outputs]
        except (ValueError, TypeError):
            logger.warning("Cannot compute average for non-numerical results")
            return self._majority_vote(outputs)

        # Weighted average
        total_weight = sum(output.confidence * output.reliability for output in outputs)
        if total_weight == 0:
            average = sum(values) / len(values)
            agreement_level = 0.5
        else:
            average = sum(
                float(output.result) * output.confidence * output.reliability
                for output in outputs
            ) / total_weight

            # Calculate agreement level
            variance = sum(
                ((float(output.result) - average) ** 2) * output.confidence * output.reliability
                for output in outputs
            ) / total_weight
            agreement_level = max(0.0, 1.0 - min(1.0, variance / (average ** 2) if average != 0 else 1.0))

        return ConsensusResult(
            final_result=average,
            confidence=agreement_level,
            agreement_level=agreement_level,
            num_agents=len(outputs),
            strategy_used=VotingStrategy.AVERAGE,
            details={'average': average, 'values': values},
        )

    def _serialize_result(self, result: Any) -> str:
        """Serialize result for comparison."""
        if isinstance(result, (str, int, float, bool)):
            return str(result)
        try:
            return json.dumps(result, sort_keys=True)
        except (TypeError, ValueError):
            return str(result)


def create_consensus_engine(
    strategy: VotingStrategy = VotingStrategy.WEIGHTED,
    **kwargs
) -> ConsensusEngine:
    """Create a consensus engine with specified strategy."""
    return ConsensusEngine(strategy=strategy, **kwargs)
