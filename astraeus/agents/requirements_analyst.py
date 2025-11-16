"""Requirements Analyst Agent - Translates mission requirements into technical specifications."""

from typing import Any, Dict, List, Optional

from loguru import logger

from astraeus.core.agent_base import BaseAgent
from astraeus.core.message import Message, MessagePriority, MessageType
from astraeus.data.parameters import (
    DesignConstraints,
    MissionRequirements,
    AntennaType,
    RadarMode,
)
from astraeus.data.knowledge_base import KnowledgeBase


class RequirementsAnalystAgent(BaseAgent):
    """
    Agent responsible for analyzing and validating mission requirements.

    Primary Responsibilities:
    - Parse high-level mission requirements into technical specifications
    - Identify constraints from mission profile and platform limitations
    - Generate requirement traceability matrices
    - Flag ambiguous, conflicting, or incomplete requirements
    - Validate requirements against physical feasibility
    """

    def _initialize(self) -> None:
        """Initialize the Requirements Analyst agent."""
        self.agent_type = "RequirementsAnalyst"
        self.knowledge_domains = [
            "radar_equation",
            "link_budget",
            "antenna_theory",
            "mission_requirements",
            "systems_engineering",
        ]
        self.capabilities = [
            "requirements_parsing",
            "constraint_analysis",
            "feasibility_assessment",
            "traceability_matrix_generation",
        ]

        # Load knowledge base
        self.knowledge_base = KnowledgeBase()

        # Requirement validation criteria
        self.validation_criteria = {
            "frequency_range": (0.1, 100.0),  # GHz
            "gain_range": (0.0, 60.0),  # dBi
            "beamwidth_range": (0.1, 180.0),  # degrees
            "efficiency_range": (0.0, 100.0),  # percent
        }

        logger.info("Requirements Analyst agent initialized")

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
        elif message.message_type == MessageType.REQUEST_CLARIFICATION:
            return self._handle_clarification_request(message)
        else:
            logger.debug(f"Unhandled message type: {message.message_type}")
            return None

    def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute requirements analysis task.

        Args:
            task: Task specification

        Returns:
            Analysis results
        """
        task_type = task.get("type")

        if task_type == "analyze_requirements":
            return self._analyze_requirements(task["requirements"])
        elif task_type == "validate_requirements":
            return self._validate_requirements(task["requirements"])
        elif task_type == "generate_constraints":
            return self._generate_constraints(task["requirements"])
        else:
            raise ValueError(f"Unknown task type: {task_type}")

    def _analyze_requirements(
        self, requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze and validate mission requirements.

        Args:
            requirements: Raw requirements dictionary

        Returns:
            Validated and expanded requirements
        """
        logger.info("Analyzing mission requirements")

        # Parse requirements into structured format
        if isinstance(requirements, MissionRequirements):
            mission_req = requirements
        else:
            mission_req = self._parse_requirements(requirements)

        # Validate requirements
        validation_results = self._validate_requirements(mission_req)

        # Check for conflicts
        conflicts = self._detect_conflicts(mission_req)

        # Generate constraints
        constraints = self._generate_constraints(mission_req)

        # Assess feasibility
        feasibility = self._assess_feasibility(mission_req)

        # Create traceability matrix
        traceability = self._create_traceability_matrix(mission_req)

        # Log decision
        self.log_decision(
            decision="Requirements validated and analyzed",
            rationale=f"Processed {len(validation_results)} validation checks, "
            f"found {len(conflicts)} conflicts",
            metadata={
                "validation_passed": validation_results.get("is_valid", False),
                "conflicts": conflicts,
                "feasibility_score": feasibility.get("score", 0.0),
            },
        )

        return {
            "validated_requirements": mission_req,
            "validation_results": validation_results,
            "conflicts": conflicts,
            "constraints": constraints,
            "feasibility": feasibility,
            "traceability_matrix": traceability,
        }

    def _parse_requirements(
        self, requirements: Dict[str, Any]
    ) -> MissionRequirements:
        """
        Parse raw requirements into MissionRequirements object.

        Args:
            requirements: Raw requirements dictionary

        Returns:
            Structured MissionRequirements object
        """
        # This is a simplified parser - in production would be more sophisticated
        from astraeus.data.parameters import (
            FrequencySpec,
            RadiationPattern,
            Polarization,
        )

        freq_spec = FrequencySpec(
            center_frequency_ghz=requirements.get("frequency_ghz", 10.0),
            bandwidth_mhz=requirements.get("bandwidth_mhz"),
            frequency_band=requirements.get("frequency_band"),
        )

        rad_pattern = RadiationPattern(
            gain_dbi=requirements.get("gain_dbi", 30.0),
            beamwidth_azimuth_deg=requirements.get("beamwidth_deg"),
            beamwidth_elevation_deg=requirements.get("beamwidth_deg"),
            sidelobe_level_db=requirements.get("sidelobe_level_db", -20.0),
        )

        pol_str = requirements.get("polarization", "linear_horizontal")
        polarization = Polarization[pol_str.upper()]

        mission_type_str = requirements.get("mission_type", "sar")
        mission_type = RadarMode[mission_type_str.upper()]

        return MissionRequirements(
            mission_name=requirements.get("mission_name", "Unnamed Mission"),
            mission_type=mission_type,
            frequency=freq_spec,
            radiation_pattern=rad_pattern,
            polarization=polarization,
        )

    def _validate_requirements(
        self, requirements: MissionRequirements
    ) -> Dict[str, Any]:
        """
        Validate requirements against feasibility criteria.

        Args:
            requirements: Requirements to validate

        Returns:
            Validation results
        """
        issues = []
        warnings = []

        # Validate frequency
        freq = requirements.frequency.center_frequency_ghz
        if not (
            self.validation_criteria["frequency_range"][0]
            <= freq
            <= self.validation_criteria["frequency_range"][1]
        ):
            issues.append(
                f"Frequency {freq} GHz outside valid range "
                f"{self.validation_criteria['frequency_range']}"
            )

        # Validate gain
        gain = requirements.radiation_pattern.gain_dbi
        if not (
            self.validation_criteria["gain_range"][0]
            <= gain
            <= self.validation_criteria["gain_range"][1]
        ):
            issues.append(
                f"Gain {gain} dBi outside valid range "
                f"{self.validation_criteria['gain_range']}"
            )

        # Validate beamwidth (if specified)
        if requirements.radiation_pattern.beamwidth_azimuth_deg:
            bw = requirements.radiation_pattern.beamwidth_azimuth_deg
            if not (
                self.validation_criteria["beamwidth_range"][0]
                <= bw
                <= self.validation_criteria["beamwidth_range"][1]
            ):
                issues.append(f"Beamwidth {bw}° outside valid range")

        # Check gain-beamwidth consistency
        if requirements.radiation_pattern.beamwidth_azimuth_deg:
            estimated_gain = self._estimate_gain_from_beamwidth(
                requirements.radiation_pattern.beamwidth_azimuth_deg,
                requirements.radiation_pattern.beamwidth_elevation_deg
                or requirements.radiation_pattern.beamwidth_azimuth_deg,
            )
            gain_diff = abs(estimated_gain - gain)
            if gain_diff > 5.0:
                warnings.append(
                    f"Specified gain ({gain} dBi) differs significantly from "
                    f"estimated gain ({estimated_gain:.1f} dBi) based on beamwidth"
                )

        return {
            "is_valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "checks_performed": 4,
        }

    def _detect_conflicts(
        self, requirements: MissionRequirements
    ) -> List[Dict[str, str]]:
        """
        Detect conflicting requirements.

        Args:
            requirements: Requirements to check

        Returns:
            List of detected conflicts
        """
        conflicts = []

        # Example: High gain + wide beamwidth is conflicting
        if (
            requirements.radiation_pattern.gain_dbi > 40.0
            and requirements.radiation_pattern.beamwidth_azimuth_deg
            and requirements.radiation_pattern.beamwidth_azimuth_deg > 10.0
        ):
            conflicts.append(
                {
                    "type": "performance_conflict",
                    "description": "High gain requirement conflicts with wide beamwidth",
                    "severity": "medium",
                }
            )

        # Example: Low mass + high gain for space mission
        if (
            requirements.physical.max_mass_kg
            and requirements.physical.max_mass_kg < 2.0
            and requirements.radiation_pattern.gain_dbi > 35.0
        ):
            conflicts.append(
                {
                    "type": "physical_constraint_conflict",
                    "description": "Low mass constraint may be challenging for high gain requirement",
                    "severity": "high",
                }
            )

        return conflicts

    def _generate_constraints(
        self, requirements: MissionRequirements
    ) -> DesignConstraints:
        """
        Generate design constraints from requirements.

        Args:
            requirements: Mission requirements

        Returns:
            Design constraints
        """
        # Calculate wavelength
        wavelength_m = requirements.frequency.get_wavelength_m()

        # Estimate required aperture size for gain
        import math

        aperture_efficiency = 0.6  # Typical
        required_gain_linear = 10 ** (requirements.radiation_pattern.gain_dbi / 10.0)
        required_aperture_m2 = (
            required_gain_linear * wavelength_m**2 / (4 * math.pi * aperture_efficiency)
        )
        required_aperture_diameter_m = math.sqrt(4 * required_aperture_m2 / math.pi)

        # Set frequency range (with margin)
        center_freq = requirements.frequency.center_frequency_ghz
        freq_range = (center_freq * 0.9, center_freq * 1.1)

        # Set gain range (with margin)
        target_gain = requirements.radiation_pattern.gain_dbi
        gain_range = (target_gain, target_gain + 5.0)

        return DesignConstraints(
            frequency_range_ghz=freq_range,
            gain_range_dbi=gain_range,
            mass_limit_kg=requirements.physical.max_mass_kg,
            volume_limit_m3=requirements.physical.max_volume_m3,
            dimensional_limits_m=(
                requirements.physical.max_length_m,
                requirements.physical.max_width_m,
                requirements.physical.max_height_m,
            )
            if requirements.physical.max_length_m
            else None,
            metadata={
                "estimated_aperture_diameter_m": required_aperture_diameter_m,
                "wavelength_m": wavelength_m,
            },
        )

    def _assess_feasibility(
        self, requirements: MissionRequirements
    ) -> Dict[str, Any]:
        """
        Assess overall feasibility of requirements.

        Args:
            requirements: Requirements to assess

        Returns:
            Feasibility assessment
        """
        # Simple feasibility scoring (can be enhanced)
        feasibility_factors = []

        # Check if similar designs exist in knowledge base
        similar_patterns = self.knowledge_base.search_patterns(
            frequency_ghz=requirements.frequency.center_frequency_ghz,
            mission_type=requirements.mission_type,
        )

        if similar_patterns:
            feasibility_factors.append(0.8)  # Heritage increases feasibility
        else:
            feasibility_factors.append(0.4)  # Novel design reduces confidence

        # Check physical constraints
        if requirements.physical.max_mass_kg and requirements.physical.max_mass_kg < 1.0:
            feasibility_factors.append(0.6)  # Tight mass constraint
        else:
            feasibility_factors.append(0.9)

        # Overall feasibility score
        feasibility_score = sum(feasibility_factors) / len(feasibility_factors)

        return {
            "score": feasibility_score,
            "confidence": "high" if feasibility_score > 0.7 else "medium",
            "similar_heritage_designs": len(similar_patterns),
            "risk_level": "low" if feasibility_score > 0.7 else "medium",
        }

    def _create_traceability_matrix(
        self, requirements: MissionRequirements
    ) -> Dict[str, List[str]]:
        """
        Create requirement traceability matrix.

        Args:
            requirements: Mission requirements

        Returns:
            Traceability matrix mapping requirements to design features
        """
        matrix = {}

        # Map high-level requirements to design parameters
        matrix["gain_requirement"] = [
            "aperture_size",
            "aperture_efficiency",
            "antenna_type",
        ]
        matrix["beamwidth_requirement"] = ["aperture_size", "feed_taper"]
        matrix["polarization_requirement"] = ["feed_design", "element_design"]
        matrix["frequency_requirement"] = [
            "element_dimensions",
            "substrate_selection",
        ]
        matrix["mass_requirement"] = ["material_selection", "structural_design"]

        return matrix

    def _estimate_gain_from_beamwidth(
        self, beamwidth_az_deg: float, beamwidth_el_deg: float
    ) -> float:
        """
        Estimate gain from beamwidth using approximate formula.

        Args:
            beamwidth_az_deg: Azimuth beamwidth in degrees
            beamwidth_el_deg: Elevation beamwidth in degrees

        Returns:
            Estimated gain in dBi
        """
        import math

        # Kraus approximation: G ≈ 41253 / (θ_az * θ_el)
        gain_linear = 41253.0 / (beamwidth_az_deg * beamwidth_el_deg)
        gain_dbi = 10 * math.log10(gain_linear)
        return gain_dbi

    def _handle_query(self, message: Message) -> List[Message]:
        """Handle query messages."""
        # Placeholder for query handling
        response = message.create_reply(
            sender=self.agent_id,
            message_type=MessageType.DATA_TRANSFER,
            payload={"status": "Requirements analysis capability available"},
            rationale="Responding to query",
        )
        return [response]

    def _handle_clarification_request(self, message: Message) -> List[Message]:
        """Handle clarification requests."""
        # Placeholder for clarification handling
        response = message.create_reply(
            sender=self.agent_id,
            message_type=MessageType.DATA_TRANSFER,
            payload={"clarification": "Please provide more specific information"},
            rationale="Requesting additional details",
        )
        return [response]
