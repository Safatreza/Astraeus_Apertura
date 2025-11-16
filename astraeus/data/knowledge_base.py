"""Knowledge base for design patterns and expert heuristics."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from astraeus.data.parameters import AntennaType, Polarization, RadarMode


@dataclass
class DesignPattern:
    """
    Represents a proven design pattern or solution.

    Captures successful design approaches that can be adapted
    to new problems.
    """

    pattern_id: str
    name: str
    description: str
    antenna_type: AntennaType
    applicable_frequencies_ghz: Tuple[float, float]

    # Performance characteristics
    typical_gain_dbi: float
    typical_beamwidth_deg: float
    bandwidth_percent: float

    # Design parameters
    key_parameters: Dict[str, Any] = field(default_factory=dict)

    # Applicability
    suitable_for_missions: List[RadarMode] = field(default_factory=list)
    suitable_for_polarizations: List[Polarization] = field(default_factory=list)

    # Lessons learned
    advantages: List[str] = field(default_factory=list)
    disadvantages: List[str] = field(default_factory=list)
    design_guidelines: List[str] = field(default_factory=list)

    # Heritage
    heritage_missions: List[str] = field(default_factory=list)
    references: List[str] = field(default_factory=list)

    confidence_score: float = 0.5  # 0 to 1

    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DesignRule:
    """
    Design rule or heuristic.

    Codifies expert knowledge as actionable rules.
    """

    rule_id: str
    name: str
    description: str
    category: str  # geometry, material, performance, etc.

    # Rule logic (can be evaluated programmatically)
    condition: str  # Description of when rule applies
    recommendation: str  # What to do

    # Importance
    criticality: str = "medium"  # low, medium, high, critical

    # Applicability
    applicable_antenna_types: List[AntennaType] = field(default_factory=list)

    # Examples
    examples: List[str] = field(default_factory=list)

    # References
    references: List[str] = field(default_factory=list)


class KnowledgeBase:
    """
    Repository of design patterns, rules, and expert knowledge.

    Provides search and retrieval capabilities for agents.
    """

    def __init__(self):
        """Initialize knowledge base."""
        self.design_patterns: Dict[str, DesignPattern] = {}
        self.design_rules: Dict[str, DesignRule] = {}
        self._initialize_knowledge()

    def _initialize_knowledge(self) -> None:
        """Initialize knowledge base with foundational patterns and rules."""

        # Design Patterns
        self.add_pattern(
            DesignPattern(
                pattern_id="gregorian_reflector_widebeam",
                name="Gregorian Reflector for Wide Field-of-View",
                description="Dual-reflector Gregorian configuration for wide coverage",
                antenna_type=AntennaType.REFLECTOR_GREGORIAN,
                applicable_frequencies_ghz=(1.0, 40.0),
                typical_gain_dbi=35.0,
                typical_beamwidth_deg=10.0,
                bandwidth_percent=20.0,
                key_parameters={
                    "main_reflector_f_over_d": 0.6,
                    "subreflector_eccentricity": 1.2,
                    "magnification": 2.5,
                },
                suitable_for_missions=[RadarMode.SAR, RadarMode.COMMUNICATION],
                suitable_for_polarizations=[
                    Polarization.LINEAR_HORIZONTAL,
                    Polarization.CIRCULAR_RIGHT,
                    Polarization.CIRCULAR_LEFT,
                ],
                advantages=[
                    "Low spillover losses",
                    "Good aperture efficiency (60-70%)",
                    "Compact feed location",
                    "Wide scan capability",
                ],
                disadvantages=[
                    "More complex than parabolic reflector",
                    "Requires accurate subreflector positioning",
                    "Subreflector blockage",
                ],
                design_guidelines=[
                    "Keep subreflector blockage < 10% of aperture area",
                    "Use feed with ~10dB edge taper on subreflector",
                    "Maintain surface accuracy < λ/16 RMS",
                ],
                heritage_missions=["GOES satellites", "Deep Space Network"],
                confidence_score=0.9,
            )
        )

        self.add_pattern(
            DesignPattern(
                pattern_id="microstrip_patch_array_sar",
                name="Microstrip Patch Array for SAR",
                description="Corporate-fed microstrip patch array for SAR applications",
                antenna_type=AntennaType.PATCH_ARRAY,
                applicable_frequencies_ghz=(5.0, 20.0),
                typical_gain_dbi=30.0,
                typical_beamwidth_deg=5.0,
                bandwidth_percent=5.0,
                key_parameters={
                    "element_spacing_wavelengths": 0.5,
                    "feed_network_type": "corporate",
                    "taper_type": "taylor",
                    "sidelobe_level_db": -25.0,
                },
                suitable_for_missions=[RadarMode.SAR, RadarMode.ISAR],
                suitable_for_polarizations=[
                    Polarization.LINEAR_HORIZONTAL,
                    Polarization.LINEAR_VERTICAL,
                    Polarization.DUAL_LINEAR,
                ],
                advantages=[
                    "Low profile and mass",
                    "Manufacturable with PCB processes",
                    "Scalable to large arrays",
                    "Electronic beam steering possible",
                ],
                disadvantages=[
                    "Narrow bandwidth (~5%)",
                    "Dielectric losses at higher frequencies",
                    "Thermal sensitivity",
                ],
                design_guidelines=[
                    "Use element spacing = 0.5λ to avoid grating lobes",
                    "Apply Taylor or Chebyshev taper for sidelobe control",
                    "Use low-loss substrate (tan δ < 0.003)",
                    "Implement proper grounding to reduce spurious radiation",
                ],
                heritage_missions=["RADARSAT", "TerraSAR-X"],
                confidence_score=0.95,
            )
        )

        self.add_pattern(
            DesignPattern(
                pattern_id="horn_antenna_simple",
                name="Pyramidal Horn for Moderate Gain",
                description="Simple pyramidal horn for moderate gain applications",
                antenna_type=AntennaType.HORN,
                applicable_frequencies_ghz=(1.0, 100.0),
                typical_gain_dbi=20.0,
                typical_beamwidth_deg=30.0,
                bandwidth_percent=40.0,
                key_parameters={
                    "flare_angle_deg": 25.0,
                    "aperture_dimensions_wavelengths": (3.0, 4.0),
                    "feed_type": "waveguide",
                },
                suitable_for_missions=[
                    RadarMode.ALTIMETER,
                    RadarMode.COMMUNICATION,
                    RadarMode.WEATHER,
                ],
                suitable_for_polarizations=[
                    Polarization.LINEAR_HORIZONTAL,
                    Polarization.LINEAR_VERTICAL,
                    Polarization.CIRCULAR_RIGHT,
                ],
                advantages=[
                    "Very wide bandwidth",
                    "Simple and robust design",
                    "Predictable performance",
                    "Low VSWR",
                ],
                disadvantages=[
                    "Bulky for high gain",
                    "Limited gain per aperture size",
                ],
                design_guidelines=[
                    "Keep flare angle < 30° for good efficiency",
                    "Optimize for ~10dB edge taper",
                    "Use smooth transitions to minimize reflections",
                ],
                heritage_missions=["Standard gain horns", "Feed horns"],
                confidence_score=1.0,
            )
        )

        # Design Rules
        self.add_rule(
            DesignRule(
                rule_id="array_grating_lobe_rule",
                name="Array Element Spacing to Avoid Grating Lobes",
                description="Array element spacing must be less than one wavelength to avoid grating lobes in visible space",
                category="geometry",
                condition="When designing antenna arrays with regular lattice",
                recommendation="Set element spacing d ≤ 0.5λ for broadside arrays, d ≤ λ/(1 + sin(θ_max)) for scanned arrays",
                criticality="critical",
                applicable_antenna_types=[
                    AntennaType.PATCH_ARRAY,
                    AntennaType.PHASED_ARRAY,
                    AntennaType.DIPOLE_ARRAY,
                ],
                examples=[
                    "For 10 GHz array: λ = 3 cm, so d ≤ 1.5 cm",
                    "For array scanning to ±45°: d ≤ λ/(1 + 0.707) = 0.586λ",
                ],
                references=["Balanis, Antenna Theory, Chapter 6"],
            )
        )

        self.add_rule(
            DesignRule(
                rule_id="reflector_surface_accuracy",
                name="Reflector Surface Accuracy Requirement",
                description="Surface RMS error affects gain and sidelobe performance",
                category="geometry",
                condition="When designing reflector antennas",
                recommendation="Maintain surface RMS error < λ/16 for > 95% efficiency, λ/32 for > 98%",
                criticality="high",
                applicable_antenna_types=[
                    AntennaType.REFLECTOR_PARABOLIC,
                    AntennaType.REFLECTOR_CASSEGRAIN,
                    AntennaType.REFLECTOR_GREGORIAN,
                ],
                examples=[
                    "For X-band (10 GHz): λ = 3 cm, so RMS < 1.9 mm for 95% efficiency",
                    "For Ka-band (35 GHz): λ = 8.6 mm, so RMS < 0.54 mm",
                ],
                references=["Ruze equation for surface error effects"],
            )
        )

        self.add_rule(
            DesignRule(
                rule_id="substrate_loss_tangent",
                name="Low-Loss Substrate Selection",
                description="Substrate loss tangent affects radiation efficiency",
                category="material",
                condition="When selecting dielectric substrates for microstrip/patch antennas",
                recommendation="Use substrate with tan(δ) < 0.003 for good efficiency at microwave frequencies",
                criticality="high",
                applicable_antenna_types=[
                    AntennaType.PATCH,
                    AntennaType.PATCH_ARRAY,
                    AntennaType.MICROSTRIP,
                ],
                examples=[
                    "Rogers RO4003C: tan(δ) = 0.0027 ✓",
                    "FR-4: tan(δ) = 0.02 (avoid for RF > 1 GHz)",
                ],
                references=["IPC-4101 substrate specifications"],
            )
        )

        self.add_rule(
            DesignRule(
                rule_id="beamwidth_gain_relationship",
                name="Beamwidth-Gain Relationship",
                description="Approximate relationship between beamwidth and gain",
                category="performance",
                condition="For any antenna type",
                recommendation="Gain (dBi) ≈ 10*log10(41253 / (θ_az * θ_el)) where θ in degrees",
                criticality="medium",
                applicable_antenna_types=list(AntennaType),
                examples=[
                    "For 3° x 3° beam: G ≈ 36.6 dBi",
                    "For 10° x 10° beam: G ≈ 26.1 dBi",
                ],
                references=["Antenna Engineering Handbook, Kraus"],
            )
        )

    def add_pattern(self, pattern: DesignPattern) -> None:
        """Add a design pattern to the knowledge base."""
        self.design_patterns[pattern.pattern_id] = pattern

    def add_rule(self, rule: DesignRule) -> None:
        """Add a design rule to the knowledge base."""
        self.design_rules[rule.rule_id] = rule

    def search_patterns(
        self,
        antenna_type: Optional[AntennaType] = None,
        mission_type: Optional[RadarMode] = None,
        frequency_ghz: Optional[float] = None,
        min_confidence: float = 0.0,
    ) -> List[DesignPattern]:
        """
        Search for applicable design patterns.

        Args:
            antenna_type: Filter by antenna type
            mission_type: Filter by mission type
            frequency_ghz: Filter by frequency
            min_confidence: Minimum confidence score

        Returns:
            List of matching design patterns
        """
        results = []

        for pattern in self.design_patterns.values():
            # Filter by antenna type
            if antenna_type and pattern.antenna_type != antenna_type:
                continue

            # Filter by mission type
            if mission_type and mission_type not in pattern.suitable_for_missions:
                continue

            # Filter by frequency
            if frequency_ghz:
                f_min, f_max = pattern.applicable_frequencies_ghz
                if not (f_min <= frequency_ghz <= f_max):
                    continue

            # Filter by confidence
            if pattern.confidence_score < min_confidence:
                continue

            results.append(pattern)

        # Sort by confidence score (highest first)
        results.sort(key=lambda p: p.confidence_score, reverse=True)

        return results

    def get_rules_for_antenna_type(
        self, antenna_type: AntennaType, min_criticality: str = "low"
    ) -> List[DesignRule]:
        """
        Get applicable design rules for an antenna type.

        Args:
            antenna_type: Antenna type
            min_criticality: Minimum criticality level

        Returns:
            List of applicable design rules
        """
        criticality_levels = ["low", "medium", "high", "critical"]
        min_level_idx = criticality_levels.index(min_criticality)

        results = []

        for rule in self.design_rules.values():
            # Check if rule applies to this antenna type
            if rule.applicable_antenna_types and antenna_type not in rule.applicable_antenna_types:
                if rule.applicable_antenna_types != list(AntennaType):
                    continue

            # Check criticality
            rule_level_idx = criticality_levels.index(rule.criticality)
            if rule_level_idx < min_level_idx:
                continue

            results.append(rule)

        # Sort by criticality (most critical first)
        results.sort(
            key=lambda r: criticality_levels.index(r.criticality), reverse=True
        )

        return results

    def get_pattern(self, pattern_id: str) -> Optional[DesignPattern]:
        """Get a design pattern by ID."""
        return self.design_patterns.get(pattern_id)

    def get_rule(self, rule_id: str) -> Optional[DesignRule]:
        """Get a design rule by ID."""
        return self.design_rules.get(rule_id)

    def get_all_patterns(self) -> List[DesignPattern]:
        """Get all design patterns."""
        return list(self.design_patterns.values())

    def get_all_rules(self) -> List[DesignRule]:
        """Get all design rules."""
        return list(self.design_rules.values())
