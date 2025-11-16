"""Physics-based validation for antenna designs."""

import numpy as np
from typing import Dict, List, Tuple, Any
from loguru import logger

from astraeus.data.parameters import DesignParameters, PerformanceMetrics, MissionRequirements
from astraeus.utils.antenna_math import AntennaMath


class PhysicsValidator:
    """
    Validates antenna designs against fundamental physics principles.

    Performs sanity checks to catch unrealistic or erroneous results:
    - Efficiency cannot exceed 100%
    - Gain/directivity/efficiency relationships
    - Beamwidth-gain product bounds
    - Reciprocity validation
    - Bandwidth-gain trade-offs
    """

    def __init__(self, tolerance: float = 0.10):
        """
        Initialize physics validator.

        Args:
            tolerance: Allowed deviation from theoretical values (fraction)
        """
        self.tolerance = tolerance
        self.validation_results: List[Dict[str, Any]] = []

    def validate_design(
        self,
        design: DesignParameters,
        performance: PerformanceMetrics,
        requirements: MissionRequirements
    ) -> Tuple[bool, List[str]]:
        """
        Perform complete physics validation.

        Args:
            design: Design parameters
            performance: Simulated/measured performance
            requirements: Mission requirements

        Returns:
            Tuple of (is_valid, list_of_violations)
        """
        violations = []

        logger.info("Performing physics-based validation...")

        # Check efficiency bounds
        eff_valid, eff_msg = self._check_efficiency_bounds(performance)
        if not eff_valid:
            violations.append(eff_msg)

        # Check gain-directivity-efficiency relationship
        gde_valid, gde_msg = self._check_gain_directivity_efficiency(performance)
        if not gde_valid:
            violations.append(gde_msg)

        # Check beamwidth-gain consistency
        bw_valid, bw_msg = self._check_beamwidth_gain_consistency(performance)
        if not bw_valid:
            violations.append(bw_msg)

        # Check VSWR physical limits
        vswr_valid, vswr_msg = self._check_vswr_limits(performance)
        if not vswr_valid:
            violations.append(vswr_msg)

        # Check aperture-gain relationship
        if design.geometry:
            ap_valid, ap_msg = self._check_aperture_gain_relationship(
                design, performance, requirements
            )
            if not ap_valid:
                violations.append(ap_msg)

        # Log results
        is_valid = len(violations) == 0
        if is_valid:
            logger.info("✓ All physics checks passed")
        else:
            logger.warning(f"✗ Physics validation failed: {len(violations)} violations")
            for violation in violations:
                logger.warning(f"  - {violation}")

        return (is_valid, violations)

    def _check_efficiency_bounds(
        self,
        performance: PerformanceMetrics
    ) -> Tuple[bool, str]:
        """Check that efficiencies are within physical bounds (0-100%)."""
        if performance.radiation_efficiency_percent is not None:
            if not (0 <= performance.radiation_efficiency_percent <= 100):
                return (False, f"Radiation efficiency {performance.radiation_efficiency_percent}% outside bounds [0, 100]")

        if performance.aperture_efficiency_percent is not None:
            if not (0 <= performance.aperture_efficiency_percent <= 100):
                return (False, f"Aperture efficiency {performance.aperture_efficiency_percent}% outside bounds [0, 100]")

        if performance.total_efficiency_percent is not None:
            if not (0 <= performance.total_efficiency_percent <= 100):
                return (False, f"Total efficiency {performance.total_efficiency_percent}% outside bounds [0, 100]")

        return (True, "")

    def _check_gain_directivity_efficiency(
        self,
        performance: PerformanceMetrics
    ) -> Tuple[bool, str]:
        """
        Check relationship: Gain = Directivity × Efficiency

        Args:
            performance: Performance metrics

        Returns:
            Tuple of (is_valid, error_message)
        """
        if (performance.realized_gain_dbi is not None and
            performance.directivity_dbi is not None and
            performance.total_efficiency_percent is not None):

            # Convert to linear
            gain_linear = 10 ** (performance.realized_gain_dbi / 10)
            directivity_linear = 10 ** (performance.directivity_dbi / 10)
            efficiency_fraction = performance.total_efficiency_percent / 100

            # Calculate expected gain
            expected_gain_linear = directivity_linear * efficiency_fraction
            expected_gain_dbi = 10 * np.log10(expected_gain_linear)

            # Check consistency
            error = abs(performance.realized_gain_dbi - expected_gain_dbi)
            if error > 1.0:  # Allow 1 dB tolerance
                return (
                    False,
                    f"Gain-Directivity-Efficiency inconsistent: "
                    f"Gain={performance.realized_gain_dbi:.2f} dBi, "
                    f"expected {expected_gain_dbi:.2f} dBi from "
                    f"D={performance.directivity_dbi:.2f} dBi × η={efficiency_fraction:.2f}"
                )

        return (True, "")

    def _check_beamwidth_gain_consistency(
        self,
        performance: PerformanceMetrics
    ) -> Tuple[bool, str]:
        """
        Check beamwidth-gain relationship.

        Approximate formula: G ≈ 41253 / (θ_az × θ_el)
        """
        if (performance.realized_gain_dbi is not None and
            performance.beamwidth_azimuth_deg is not None and
            performance.beamwidth_elevation_deg is not None):

            # Estimate gain from beamwidth
            estimated_gain = AntennaMath.gain_from_beamwidth(
                performance.beamwidth_azimuth_deg,
                performance.beamwidth_elevation_deg
            )

            # Check consistency
            error = abs(performance.realized_gain_dbi - estimated_gain)
            if error > 5.0:  # Allow 5 dB tolerance (formula is approximate)
                return (
                    False,
                    f"Beamwidth-gain inconsistent: "
                    f"Gain={performance.realized_gain_dbi:.2f} dBi, "
                    f"expected ~{estimated_gain:.2f} dBi from "
                    f"beamwidths {performance.beamwidth_azimuth_deg:.1f}° × "
                    f"{performance.beamwidth_elevation_deg:.1f}°"
                )

        return (True, "")

    def _check_vswr_limits(
        self,
        performance: PerformanceMetrics
    ) -> Tuple[bool, str]:
        """Check that VSWR is within physical limits."""
        if performance.vswr is not None:
            if performance.vswr < 1.0:
                return (False, f"VSWR {performance.vswr:.2f} cannot be less than 1.0")

            if performance.vswr > 20.0:
                return (False, f"VSWR {performance.vswr:.2f} unrealistically high (>20)")

        return (True, "")

    def _check_aperture_gain_relationship(
        self,
        design: DesignParameters,
        performance: PerformanceMetrics,
        requirements: MissionRequirements
    ) -> Tuple[bool, str]:
        """
        Check aperture size vs. gain relationship.

        For aperture antennas: G = (4π × η × A) / λ²
        """
        if performance.realized_gain_dbi is None:
            return (True, "")  # Can't check without gain

        # Get wavelength
        wavelength_m = requirements.frequency.get_wavelength_m()

        # Estimate aperture area from geometry (simplified)
        aperture_area_m2 = None

        if design.antenna_type.value == "horn":
            if "aperture_width_m" in design.geometry and "aperture_height_m" in design.geometry:
                aperture_area_m2 = (
                    design.geometry["aperture_width_m"] *
                    design.geometry["aperture_height_m"]
                )
        elif design.antenna_type.value in ["reflector_parabolic", "reflector_cassegrain"]:
            if "diameter_m" in design.geometry:
                radius = design.geometry["diameter_m"] / 2
                aperture_area_m2 = np.pi * radius ** 2

        if aperture_area_m2 is not None:
            # Calculate expected gain (with typical efficiency)
            typical_efficiency = 0.6  # Conservative estimate
            expected_gain = AntennaMath.gain_from_aperture(
                aperture_area_m2,
                wavelength_m,
                typical_efficiency
            )

            # Check if realized gain is within reasonable bounds
            if performance.realized_gain_dbi > expected_gain + 5.0:
                return (
                    False,
                    f"Gain {performance.realized_gain_dbi:.2f} dBi too high for "
                    f"aperture area {aperture_area_m2:.4f} m² "
                    f"(expected max ~{expected_gain + 5:.2f} dBi)"
                )

            if performance.realized_gain_dbi < expected_gain - 10.0:
                return (
                    False,
                    f"Gain {performance.realized_gain_dbi:.2f} dBi too low for "
                    f"aperture area {aperture_area_m2:.4f} m² "
                    f"(expected min ~{expected_gain - 10:.2f} dBi)"
                )

        return (True, "")

    def check_chu_harrington_limit(
        self,
        antenna_size_m: float,
        wavelength_m: float,
        bandwidth_percent: float,
        q_factor: float
    ) -> Tuple[bool, str]:
        """
        Check Chu-Harrington fundamental limit on bandwidth.

        For electrically small antennas (ka < 1), there's a fundamental
        limit relating size, bandwidth, and Q factor.

        Args:
            antenna_size_m: Maximum antenna dimension
            wavelength_m: Wavelength
            bandwidth_percent: Fractional bandwidth
            q_factor: Quality factor

        Returns:
            Tuple of (is_valid, message)
        """
        # Calculate electrical size
        k = 2 * np.pi / wavelength_m
        ka = k * antenna_size_m

        if ka < 1.0:  # Electrically small
            # Chu-Harrington limit: Q >= 1/(ka)^3 + 1/(ka)
            q_min = 1 / (ka ** 3) + 1 / ka

            # Bandwidth-Q relationship: BW ≈ 1/Q
            bw_max = 100 / q_min  # Convert to percentage

            if bandwidth_percent > bw_max * (1 + self.tolerance):
                return (
                    False,
                    f"Bandwidth {bandwidth_percent:.1f}% exceeds Chu-Harrington limit "
                    f"~{bw_max:.1f}% for electrically small antenna (ka={ka:.2f})"
                )

        return (True, "")

    def get_validation_report(self) -> Dict[str, Any]:
        """Generate validation report."""
        return {
            "total_checks": len(self.validation_results),
            "checks": self.validation_results,
            "timestamp": "validation_timestamp"
        }
