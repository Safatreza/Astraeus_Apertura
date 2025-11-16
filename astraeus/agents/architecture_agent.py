"""Architecture Agent - Selects optimal antenna architecture for mission requirements."""

from typing import Any, Dict, List, Optional

from loguru import logger

from astraeus.core.agent_base import BaseAgent
from astraeus.core.message import Message, MessagePriority, MessageType
from astraeus.data.parameters import (
    AntennaType,
    DesignConstraints,
    MissionRequirements,
)
from astraeus.data.knowledge_base import KnowledgeBase


class ArchitectureAgent(BaseAgent):
    """
    Agent responsible for selecting the optimal antenna architecture.

    Primary Responsibilities:
    - Evaluate antenna architectures against mission requirements
    - Consider trade-offs between performance, mass, complexity, and cost
    - Select antenna type (patch array, reflector, phased array, etc.)
    - Define high-level architectural parameters
    - Provide architectural recommendations with rationale
    """

    def _initialize(self) -> None:
        """Initialize the Architecture Agent."""
        self.agent_type = "ArchitectureAgent"
        self.knowledge_domains = [
            "antenna_architectures",
            "system_design",
            "trade_studies",
            "performance_modeling",
            "technology_readiness",
        ]
        self.capabilities = [
            "architecture_selection",
            "trade_space_analysis",
            "technology_assessment",
            "configuration_optimization",
        ]

        # Load knowledge base
        self.knowledge_base = KnowledgeBase()

        # Architecture selection criteria weights
        self.selection_weights = {
            "performance": 0.35,
            "mass": 0.25,
            "complexity": 0.15,
            "cost": 0.15,
            "heritage": 0.10,
        }

        # Technology readiness level thresholds
        self.trl_thresholds = {
            "space_qualification": 8,
            "flight_ready": 9,
        }

        logger.info("Architecture Agent initialized")

    def process_message(self, message: Message) -> Optional[List[Message]]:
        """
        Process incoming messages.

        Args:
            message: Message to process

        Returns:
            List of response messages
        """
        if message.message_type == MessageType.QUERY:
            return self._handle_query(message)
        elif message.message_type == MessageType.REQUEST_TASK:
            return self._handle_task_request(message)
        else:
            logger.debug(f"Unhandled message type: {message.message_type}")
            return None

    def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute architecture selection task.

        Args:
            task: Task specification

        Returns:
            Architecture selection results
        """
        task_type = task.get("type")

        if task_type == "select_architecture":
            return self._select_architecture(
                task["requirements"], task.get("constraints")
            )
        elif task_type == "trade_study":
            return self._conduct_trade_study(
                task["requirements"], task.get("architectures")
            )
        elif task_type == "evaluate_architecture":
            return self._evaluate_architecture(
                task["architecture"], task["requirements"]
            )
        else:
            raise ValueError(f"Unknown task type: {task_type}")

    def _select_architecture(
        self,
        requirements: MissionRequirements,
        constraints: Optional[DesignConstraints] = None,
    ) -> Dict[str, Any]:
        """
        Select optimal antenna architecture.

        Args:
            requirements: Mission requirements
            constraints: Design constraints

        Returns:
            Selected architecture and rationale
        """
        logger.info("Selecting antenna architecture")

        # Identify candidate architectures
        candidates = self._identify_candidates(requirements)

        # Score each candidate
        scored_architectures = []
        for candidate in candidates:
            score_result = self._score_architecture(
                candidate, requirements, constraints
            )
            scored_architectures.append(score_result)

        # Sort by total score
        scored_architectures.sort(key=lambda x: x["total_score"], reverse=True)

        # Select top architecture
        selected = scored_architectures[0]

        # Log decision
        self.log_decision(
            decision=f"Selected {selected['architecture'].value} architecture",
            rationale=selected["rationale"],
            alternatives_considered=[
                arch["architecture"].value for arch in scored_architectures[1:4]
            ],
            metadata={
                "total_score": selected["total_score"],
                "performance_score": selected["scores"]["performance"],
                "mass_score": selected["scores"]["mass"],
            },
        )

        return {
            "selected_architecture": selected["architecture"],
            "configuration": selected["configuration"],
            "rationale": selected["rationale"],
            "all_candidates": scored_architectures,
            "trade_space": self._generate_trade_space(scored_architectures),
        }

    def _identify_candidates(
        self, requirements: MissionRequirements
    ) -> List[AntennaType]:
        """
        Identify candidate architectures based on requirements.

        Args:
            requirements: Mission requirements

        Returns:
            List of candidate antenna types
        """
        candidates = []
        freq = requirements.frequency.center_frequency_ghz
        gain = requirements.radiation_pattern.gain_dbi

        # Patch arrays: Good for low to medium gain, moderate frequency
        if 2.0 <= freq <= 40.0 and gain <= 35.0:
            candidates.append(AntennaType.PATCH_ARRAY)

        # Phased arrays: High performance, high complexity
        if freq >= 1.0 and gain >= 20.0:
            candidates.append(AntennaType.PHASED_ARRAY)

        # Reflector antennas: High gain applications
        if gain >= 30.0:
            candidates.extend([
                AntennaType.REFLECTOR_PARABOLIC,
                AntennaType.REFLECTOR_CASSEGRAIN,
            ])

        # Reflectarrays: Lightweight alternative to reflectors
        if freq >= 5.0 and gain >= 25.0:
            candidates.append(AntennaType.REFLECTARRAY)

        # Horn antennas: Simple, moderate gain
        if freq >= 1.0 and gain <= 25.0:
            candidates.append(AntennaType.HORN)

        # Ensure at least some candidates
        if not candidates:
            candidates = [AntennaType.PATCH_ARRAY, AntennaType.HORN]

        logger.debug(f"Identified {len(candidates)} candidate architectures")
        return candidates

    def _score_architecture(
        self,
        architecture: AntennaType,
        requirements: MissionRequirements,
        constraints: Optional[DesignConstraints],
    ) -> Dict[str, Any]:
        """
        Score an architecture against requirements.

        Args:
            architecture: Architecture to score
            requirements: Mission requirements
            constraints: Design constraints

        Returns:
            Architecture score and details
        """
        scores = {}

        # Performance score (0-1)
        scores["performance"] = self._score_performance(architecture, requirements)

        # Mass score (0-1, higher is better/lighter)
        scores["mass"] = self._score_mass(architecture, requirements)

        # Complexity score (0-1, higher is simpler)
        scores["complexity"] = self._score_complexity(architecture)

        # Cost score (0-1, higher is cheaper)
        scores["cost"] = self._score_cost(architecture)

        # Heritage score (0-1, higher means more heritage)
        scores["heritage"] = self._score_heritage(architecture, requirements)

        # Calculate weighted total
        total_score = sum(
            scores[key] * self.selection_weights[key]
            for key in self.selection_weights
        )

        # Generate rationale
        rationale = self._generate_rationale(architecture, scores)

        # Generate configuration
        configuration = self._generate_configuration(architecture, requirements)

        return {
            "architecture": architecture,
            "scores": scores,
            "total_score": total_score,
            "rationale": rationale,
            "configuration": configuration,
        }

    def _score_performance(
        self, architecture: AntennaType, requirements: MissionRequirements
    ) -> float:
        """Score architecture performance capability."""
        # Simplified scoring based on architecture capabilities
        performance_map = {
            AntennaType.PHASED_ARRAY: 1.0,
            AntennaType.REFLECTOR_CASSEGRAIN: 0.95,
            AntennaType.REFLECTOR_PARABOLIC: 0.90,
            AntennaType.REFLECTARRAY: 0.85,
            AntennaType.PATCH_ARRAY: 0.75,
            AntennaType.HORN: 0.60,
        }
        return performance_map.get(architecture, 0.5)

    def _score_mass(
        self, architecture: AntennaType, requirements: MissionRequirements
    ) -> float:
        """Score architecture mass efficiency (higher is lighter)."""
        # Lighter architectures score higher
        mass_map = {
            AntennaType.REFLECTARRAY: 1.0,
            AntennaType.PATCH_ARRAY: 0.90,
            AntennaType.PHASED_ARRAY: 0.70,
            AntennaType.HORN: 0.80,
            AntennaType.REFLECTOR_PARABOLIC: 0.50,
            AntennaType.REFLECTOR_CASSEGRAIN: 0.45,
        }
        return mass_map.get(architecture, 0.5)

    def _score_complexity(self, architecture: AntennaType) -> float:
        """Score architecture complexity (higher is simpler)."""
        complexity_map = {
            AntennaType.HORN: 1.0,
            AntennaType.PATCH_ARRAY: 0.80,
            AntennaType.REFLECTOR_PARABOLIC: 0.70,
            AntennaType.REFLECTARRAY: 0.60,
            AntennaType.REFLECTOR_CASSEGRAIN: 0.50,
            AntennaType.PHASED_ARRAY: 0.30,
        }
        return complexity_map.get(architecture, 0.5)

    def _score_cost(self, architecture: AntennaType) -> float:
        """Score architecture cost (higher is cheaper)."""
        cost_map = {
            AntennaType.HORN: 1.0,
            AntennaType.PATCH_ARRAY: 0.85,
            AntennaType.REFLECTOR_PARABOLIC: 0.70,
            AntennaType.REFLECTARRAY: 0.65,
            AntennaType.REFLECTOR_CASSEGRAIN: 0.55,
            AntennaType.PHASED_ARRAY: 0.40,
        }
        return cost_map.get(architecture, 0.5)

    def _score_heritage(
        self, architecture: AntennaType, requirements: MissionRequirements
    ) -> float:
        """Score architecture heritage for this application."""
        # Search knowledge base for similar designs
        similar_designs = self.knowledge_base.search_patterns(
            frequency_ghz=requirements.frequency.center_frequency_ghz,
            mission_type=requirements.mission_type,
        )

        # Filter for this architecture
        matching = [d for d in similar_designs if d.get("architecture") == architecture]

        # Score based on number of heritage designs
        if len(matching) >= 5:
            return 1.0
        elif len(matching) >= 3:
            return 0.8
        elif len(matching) >= 1:
            return 0.6
        else:
            return 0.3

    def _generate_rationale(
        self, architecture: AntennaType, scores: Dict[str, float]
    ) -> str:
        """Generate human-readable rationale for architecture selection."""
        strengths = []
        weaknesses = []

        for criterion, score in scores.items():
            if score >= 0.8:
                strengths.append(f"excellent {criterion}")
            elif score <= 0.4:
                weaknesses.append(f"limited {criterion}")

        rationale = f"{architecture.value} architecture selected. "
        if strengths:
            rationale += f"Strengths: {', '.join(strengths)}. "
        if weaknesses:
            rationale += f"Considerations: {', '.join(weaknesses)}."

        return rationale

    def _generate_configuration(
        self, architecture: AntennaType, requirements: MissionRequirements
    ) -> Dict[str, Any]:
        """Generate initial configuration for selected architecture."""
        config = {
            "architecture_type": architecture,
            "operating_frequency_ghz": requirements.frequency.center_frequency_ghz,
            "target_gain_dbi": requirements.radiation_pattern.gain_dbi,
        }

        # Add architecture-specific parameters
        if architecture in [
            AntennaType.PATCH_ARRAY,
            AntennaType.PHASED_ARRAY,
        ]:
            # Estimate array size
            import math

            wavelength = requirements.frequency.get_wavelength_m()
            gain_linear = 10 ** (requirements.radiation_pattern.gain_dbi / 10.0)
            aperture_area = gain_linear * wavelength**2 / (4 * math.pi * 0.6)
            elements_estimate = int(aperture_area / (wavelength / 2) ** 2)

            config.update({
                "estimated_elements": elements_estimate,
                "element_spacing_wavelengths": 0.5,
                "feed_network": "corporate" if architecture == AntennaType.PATCH_ARRAY else "phased",
            })

        elif architecture in [
            AntennaType.REFLECTOR_PARABOLIC,
            AntennaType.REFLECTOR_CASSEGRAIN,
        ]:
            # Estimate reflector size
            import math

            wavelength = requirements.frequency.get_wavelength_m()
            gain_linear = 10 ** (requirements.radiation_pattern.gain_dbi / 10.0)
            aperture_area = gain_linear * wavelength**2 / (4 * math.pi * 0.55)
            diameter = math.sqrt(4 * aperture_area / math.pi)

            config.update({
                "reflector_diameter_m": diameter,
                "f_over_d_ratio": 0.4 if architecture == AntennaType.REFLECTOR_CASSEGRAIN else 0.35,
                "feed_type": "horn",
            })

        return config

    def _conduct_trade_study(
        self,
        requirements: MissionRequirements,
        architectures: Optional[List[AntennaType]] = None,
    ) -> Dict[str, Any]:
        """
        Conduct comprehensive trade study.

        Args:
            requirements: Mission requirements
            architectures: Specific architectures to compare (or all if None)

        Returns:
            Trade study results
        """
        logger.info("Conducting architecture trade study")

        if architectures is None:
            architectures = self._identify_candidates(requirements)

        # Score all architectures
        results = []
        for arch in architectures:
            score_result = self._score_architecture(arch, requirements, None)
            results.append(score_result)

        # Sort by score
        results.sort(key=lambda x: x["total_score"], reverse=True)

        return {
            "architectures_evaluated": len(results),
            "results": results,
            "recommendation": results[0]["architecture"],
            "trade_space": self._generate_trade_space(results),
        }

    def _evaluate_architecture(
        self, architecture: AntennaType, requirements: MissionRequirements
    ) -> Dict[str, Any]:
        """
        Evaluate a specific architecture.

        Args:
            architecture: Architecture to evaluate
            requirements: Mission requirements

        Returns:
            Evaluation results
        """
        logger.info(f"Evaluating {architecture.value} architecture")

        score_result = self._score_architecture(architecture, requirements, None)

        return {
            "architecture": architecture,
            "evaluation": score_result,
            "suitability": "high" if score_result["total_score"] > 0.7 else "medium",
        }

    def _generate_trade_space(
        self, scored_architectures: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate trade space visualization data."""
        return {
            "dimensions": list(self.selection_weights.keys()),
            "architectures": [
                {
                    "name": arch["architecture"].value,
                    "scores": arch["scores"],
                    "total": arch["total_score"],
                }
                for arch in scored_architectures
            ],
        }

    def _handle_query(self, message: Message) -> List[Message]:
        """Handle query messages."""
        response = message.create_reply(
            sender=self.agent_id,
            message_type=MessageType.DATA_TRANSFER,
            payload={"status": "Architecture selection capability available"},
            rationale="Responding to query",
        )
        return [response]

    def _handle_task_request(self, message: Message) -> List[Message]:
        """Handle task request messages."""
        task_data = message.payload.get("task")
        if task_data:
            result = self.execute_task(task_data)
            response = message.create_reply(
                sender=self.agent_id,
                message_type=MessageType.DATA_TRANSFER,
                payload={"result": result},
                rationale="Task completed",
            )
            return [response]
        return []
