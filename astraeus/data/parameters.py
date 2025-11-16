"""Data structures for antenna design parameters and requirements."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class AntennaType(Enum):
    """Types of antenna architectures."""

    HORN = "horn"
    PATCH = "patch"
    PATCH_ARRAY = "patch_array"
    PHASED_ARRAY = "phased_array"
    REFLECTOR_PARABOLIC = "reflector_parabolic"
    REFLECTOR_CASSEGRAIN = "reflector_cassegrain"
    REFLECTOR_GREGORIAN = "reflector_gregorian"
    DIPOLE = "dipole"
    DIPOLE_ARRAY = "dipole_array"
    SPIRAL = "spiral"
    HELIX = "helix"
    SLOT = "slot"
    SLOT_ARRAY = "slot_array"
    MICROSTRIP = "microstrip"
    REFLECTARRAY = "reflectarray"
    LENS_ANTENNA = "lens_antenna"


class Polarization(Enum):
    """Polarization types."""

    LINEAR_HORIZONTAL = "linear_horizontal"
    LINEAR_VERTICAL = "linear_vertical"
    LINEAR_SLANT_45 = "linear_slant_45"
    CIRCULAR_RIGHT = "circular_right"
    CIRCULAR_LEFT = "circular_left"
    DUAL_LINEAR = "dual_linear"
    DUAL_CIRCULAR = "dual_circular"


class RadarMode(Enum):
    """Radar operational modes."""

    SAR = "sar"  # Synthetic Aperture Radar
    ISAR = "isar"  # Inverse SAR
    MTI = "mti"  # Moving Target Indicator
    WEATHER = "weather"  # Weather radar
    ALTIMETER = "altimeter"  # Radar altimeter
    SCATTEROMETER = "scatterometer"  # Scatterometer
    COMMUNICATION = "communication"  # Communication antenna


@dataclass
class FrequencySpec:
    """Frequency specification."""

    center_frequency_ghz: float
    bandwidth_mhz: Optional[float] = None
    frequency_band: Optional[str] = None  # L, S, C, X, Ku, Ka, etc.
    harmonic_suppression_dbc: float = 40.0  # dB below carrier

    def get_wavelength_m(self) -> float:
        """Calculate wavelength in meters."""
        c = 2.998e8  # Speed of light m/s
        return c / (self.center_frequency_ghz * 1e9)


@dataclass
class RadiationPattern:
    """Radiation pattern requirements."""

    gain_dbi: float  # Boresight gain in dBi
    beamwidth_azimuth_deg: Optional[float] = None  # 3-dB beamwidth
    beamwidth_elevation_deg: Optional[float] = None  # 3-dB beamwidth
    sidelobe_level_db: float = -20.0  # Peak sidelobe level relative to main beam
    cross_pol_discrimination_db: float = 20.0  # Co-pol to cross-pol ratio
    front_to_back_ratio_db: Optional[float] = None
    beam_steering_range_deg: Optional[Tuple[float, float]] = None  # (azimuth, elevation)


@dataclass
class ImpedanceSpec:
    """Impedance and matching requirements."""

    input_impedance_ohm: float = 50.0
    vswr_max: float = 2.0  # Maximum VSWR
    return_loss_db: float = -10.0  # Minimum return loss
    port_isolation_db: Optional[float] = None  # For multi-port systems


@dataclass
class EfficiencySpec:
    """Efficiency requirements."""

    radiation_efficiency_percent: float = 90.0
    aperture_efficiency_percent: Optional[float] = None  # For reflectors/arrays
    total_efficiency_percent: float = 85.0


@dataclass
class PhysicalConstraints:
    """Physical size and mass constraints."""

    max_length_m: Optional[float] = None
    max_width_m: Optional[float] = None
    max_height_m: Optional[float] = None
    max_mass_kg: Optional[float] = None
    max_volume_m3: Optional[float] = None
    deployable: bool = False
    stowed_dimensions_m: Optional[Tuple[float, float, float]] = None


@dataclass
class EnvironmentalSpec:
    """Environmental operating conditions."""

    operating_temp_min_c: float = -40.0
    operating_temp_max_c: float = 85.0
    survival_temp_min_c: float = -55.0
    survival_temp_max_c: float = 125.0
    vibration_grms: Optional[float] = None  # Launch vibration
    shock_g: Optional[float] = None
    thermal_cycles: Optional[int] = None
    total_ionizing_dose_rad: Optional[float] = None  # For space applications
    vacuum_exposure: bool = False
    atomic_oxygen_exposure: bool = False


@dataclass
class ElectricalInterface:
    """Electrical interface requirements."""

    input_power_w: Optional[float] = None
    connector_type: str = "SMA"
    impedance_ohm: float = 50.0
    polarization_control: bool = False
    digital_beamforming: bool = False


@dataclass
class MissionRequirements:
    """
    Complete mission requirements for antenna design.

    This is the top-level requirements specification that drives the design.
    """

    mission_name: str
    mission_type: RadarMode
    frequency: FrequencySpec
    radiation_pattern: RadiationPattern
    polarization: Polarization

    # Optional specifications
    impedance: ImpedanceSpec = field(default_factory=ImpedanceSpec)
    efficiency: EfficiencySpec = field(default_factory=EfficiencySpec)
    physical: PhysicalConstraints = field(default_factory=PhysicalConstraints)
    environmental: EnvironmentalSpec = field(default_factory=EnvironmentalSpec)
    electrical: ElectricalInterface = field(default_factory=ElectricalInterface)

    # Performance requirements
    radar_range_km: Optional[float] = None
    angular_resolution_deg: Optional[float] = None
    sensitivity_dbm: Optional[float] = None

    # Additional constraints
    cost_constraint_usd: Optional[float] = None
    schedule_constraint_months: Optional[int] = None
    heritage_design: Optional[str] = None  # Reference to heritage design

    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert requirements to dictionary."""
        return {
            "mission_name": self.mission_name,
            "mission_type": self.mission_type.value,
            "frequency": {
                "center_frequency_ghz": self.frequency.center_frequency_ghz,
                "bandwidth_mhz": self.frequency.bandwidth_mhz,
                "frequency_band": self.frequency.frequency_band,
            },
            "radiation_pattern": {
                "gain_dbi": self.radiation_pattern.gain_dbi,
                "beamwidth_azimuth_deg": self.radiation_pattern.beamwidth_azimuth_deg,
                "beamwidth_elevation_deg": self.radiation_pattern.beamwidth_elevation_deg,
                "sidelobe_level_db": self.radiation_pattern.sidelobe_level_db,
            },
            "polarization": self.polarization.value,
            "physical": {
                "max_mass_kg": self.physical.max_mass_kg,
                "max_length_m": self.physical.max_length_m,
                "max_width_m": self.physical.max_width_m,
                "max_height_m": self.physical.max_height_m,
            },
            "metadata": self.metadata,
        }


@dataclass
class DesignParameters:
    """
    Physical design parameters for the antenna.

    This represents the actual design that the agents create and optimize.
    """

    antenna_type: AntennaType
    frequency_spec: FrequencySpec

    # Geometry parameters (specific to antenna type)
    geometry: Dict[str, Any] = field(default_factory=dict)

    # Material specifications
    materials: Dict[str, str] = field(default_factory=dict)

    # Array parameters (if applicable)
    array_config: Optional[Dict[str, Any]] = None

    # Feed network parameters
    feed_network: Optional[Dict[str, Any]] = None

    # Beamforming parameters (for phased arrays)
    beamforming: Optional[Dict[str, Any]] = None

    # Physical properties
    estimated_mass_kg: Optional[float] = None
    estimated_volume_m3: Optional[float] = None
    center_of_gravity_m: Optional[Tuple[float, float, float]] = None

    # Manufacturing info
    fabrication_method: Optional[str] = None
    assembly_complexity: Optional[str] = None  # low, medium, high

    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceMetrics:
    """
    Simulated or measured performance metrics.

    Results from electromagnetic simulation or testing.
    """

    # Radiation pattern metrics
    realized_gain_dbi: Optional[float] = None
    directivity_dbi: Optional[float] = None
    beamwidth_azimuth_deg: Optional[float] = None
    beamwidth_elevation_deg: Optional[float] = None
    peak_sidelobe_level_db: Optional[float] = None
    average_sidelobe_level_db: Optional[float] = None
    cross_pol_level_db: Optional[float] = None
    front_to_back_ratio_db: Optional[float] = None

    # Impedance metrics
    vswr: Optional[float] = None
    return_loss_db: Optional[float] = None
    input_impedance: Optional[complex] = None
    bandwidth_mhz: Optional[float] = None  # Impedance bandwidth

    # Efficiency metrics
    radiation_efficiency_percent: Optional[float] = None
    aperture_efficiency_percent: Optional[float] = None
    total_efficiency_percent: Optional[float] = None

    # Polarization metrics (for circular polarization)
    axial_ratio_db: Optional[float] = None
    polarization_purity_db: Optional[float] = None

    # System-level metrics
    antenna_temperature_k: Optional[float] = None
    g_over_t_db: Optional[float] = None  # G/T ratio

    # Additional data
    frequency_points_ghz: List[float] = field(default_factory=list)
    s_parameters: Dict[str, List[complex]] = field(default_factory=dict)

    metadata: Dict[str, Any] = field(default_factory=dict)

    def meets_requirements(self, requirements: MissionRequirements) -> bool:
        """
        Check if performance meets requirements.

        Args:
            requirements: Mission requirements to check against

        Returns:
            True if all requirements are met
        """
        checks = []

        # Check gain
        if self.realized_gain_dbi is not None:
            checks.append(
                self.realized_gain_dbi >= requirements.radiation_pattern.gain_dbi
            )

        # Check VSWR
        if self.vswr is not None:
            checks.append(self.vswr <= requirements.impedance.vswr_max)

        # Check efficiency
        if self.total_efficiency_percent is not None:
            checks.append(
                self.total_efficiency_percent
                >= requirements.efficiency.total_efficiency_percent
            )

        # Check sidelobe level
        if self.peak_sidelobe_level_db is not None:
            checks.append(
                self.peak_sidelobe_level_db
                <= requirements.radiation_pattern.sidelobe_level_db
            )

        # All checks must pass
        return all(checks) if checks else False

    def get_score(self, requirements: MissionRequirements) -> float:
        """
        Calculate a composite score for this design.

        Args:
            requirements: Mission requirements for scoring

        Returns:
            Score between 0 and 1 (1 = perfect)
        """
        scores = []

        # Gain score (normalized)
        if self.realized_gain_dbi is not None:
            target_gain = requirements.radiation_pattern.gain_dbi
            gain_score = min(1.0, self.realized_gain_dbi / target_gain)
            scores.append(gain_score)

        # Efficiency score
        if self.total_efficiency_percent is not None:
            target_eff = requirements.efficiency.total_efficiency_percent
            eff_score = min(1.0, self.total_efficiency_percent / target_eff)
            scores.append(eff_score)

        # VSWR score (inverted - lower is better)
        if self.vswr is not None:
            target_vswr = requirements.impedance.vswr_max
            vswr_score = min(1.0, target_vswr / self.vswr)
            scores.append(vswr_score)

        # Average scores
        return sum(scores) / len(scores) if scores else 0.0


@dataclass
class DesignConstraints:
    """
    Consolidated constraints from requirements and feasibility analysis.

    Used by agents to understand the solution space boundaries.
    """

    frequency_range_ghz: Tuple[float, float]
    gain_range_dbi: Tuple[float, float]
    mass_limit_kg: Optional[float] = None
    volume_limit_m3: Optional[float] = None
    dimensional_limits_m: Optional[Tuple[float, float, float]] = None

    # Manufacturing constraints
    minimum_feature_size_mm: float = 0.5
    maximum_aspect_ratio: float = 100.0
    available_materials: List[str] = field(default_factory=list)

    # Regulatory constraints
    frequency_allocations: List[Tuple[float, float]] = field(default_factory=list)
    eirp_limit_dbw: Optional[float] = None

    # Cost constraints
    budget_usd: Optional[float] = None
    schedule_months: Optional[int] = None

    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_feasible(self, design: DesignParameters) -> Tuple[bool, List[str]]:
        """
        Check if a design is feasible given constraints.

        Args:
            design: Design to check

        Returns:
            Tuple of (is_feasible, list_of_violations)
        """
        violations = []

        # Check mass
        if self.mass_limit_kg and design.estimated_mass_kg:
            if design.estimated_mass_kg > self.mass_limit_kg:
                violations.append(
                    f"Mass {design.estimated_mass_kg} kg exceeds limit "
                    f"{self.mass_limit_kg} kg"
                )

        # Check volume
        if self.volume_limit_m3 and design.estimated_volume_m3:
            if design.estimated_volume_m3 > self.volume_limit_m3:
                violations.append(
                    f"Volume {design.estimated_volume_m3} m³ exceeds limit "
                    f"{self.volume_limit_m3} m³"
                )

        # Check materials
        if self.available_materials and design.materials:
            for material in design.materials.values():
                if material not in self.available_materials:
                    violations.append(
                        f"Material '{material}' not in available materials list"
                    )

        return (len(violations) == 0, violations)
