"""Automated simulation workflow management."""

from typing import Any, Dict, List, Optional
from loguru import logger
import time

from astraeus.simulation.base_simulator import BaseSimulator, SimulationResult


class SimulationWorkflow:
    """
    Manages automated simulation workflows.

    Handles:
    - Pre-processing (geometry validation, mesh generation)
    - Execution monitoring
    - Post-processing (metric extraction)
    - Error handling and retry logic
    """

    def __init__(self, simulator: BaseSimulator):
        """
        Initialize simulation workflow.

        Args:
            simulator: Simulator backend instance
        """
        self.simulator = simulator
        self.simulation_history: List[SimulationResult] = []

    def run_complete_workflow(
        self,
        geometry: Dict[str, Any],
        materials: Dict[str, Any],
        excitation: Dict[str, Any],
        frequency_range_ghz: tuple,
        **kwargs
    ) -> SimulationResult:
        """
        Run complete simulation workflow.

        Args:
            geometry: Geometry specification
            materials: Material properties
            excitation: Excitation configuration
            frequency_range_ghz: (min_freq, max_freq) in GHz
            **kwargs: Additional parameters

        Returns:
            Simulation result
        """
        logger.info(f"Starting simulation workflow with {self.simulator.simulator_name}")

        start_time = time.time()

        try:
            # Pre-processing
            if not self._preprocessing(geometry, materials, excitation):
                logger.error("Pre-processing failed")
                return self._create_failed_result("Pre-processing failed")

            # Setup simulation parameters
            self.simulator.set_boundary_conditions({
                "type": "radiation",
                "frequency_range_ghz": frequency_range_ghz
            })

            # Run simulation
            result = self.simulator.run_simulation(**kwargs)

            # Post-processing
            result = self._postprocessing(result)

            # Store in history
            self.simulation_history.append(result)

            runtime = time.time() - start_time
            result.runtime_seconds = runtime

            logger.info(f"Simulation completed in {runtime:.1f}s")

            return result

        except Exception as e:
            logger.error(f"Simulation workflow failed: {e}", exc_info=True)
            return self._create_failed_result(str(e))

    def _preprocessing(
        self,
        geometry: Dict[str, Any],
        materials: Dict[str, Any],
        excitation: Dict[str, Any]
    ) -> bool:
        """
        Pre-processing steps.

        Args:
            geometry: Geometry specification
            materials: Material properties
            excitation: Excitation configuration

        Returns:
            True if successful
        """
        # Initialize simulator
        if not self.simulator.is_initialized:
            if not self.simulator.initialize():
                return False

        # Setup geometry
        if not self.simulator.setup_geometry(geometry):
            logger.error("Geometry setup failed")
            return False

        # Set materials
        if not self.simulator.set_materials(materials):
            logger.error("Material setup failed")
            return False

        # Set excitation
        if not self.simulator.set_excitation(excitation):
            logger.error("Excitation setup failed")
            return False

        # Validate setup
        is_valid, issues = self.simulator.validate_setup()
        if not is_valid:
            logger.error(f"Setup validation failed: {issues}")
            return False

        return True

    def _postprocessing(self, result: SimulationResult) -> SimulationResult:
        """
        Post-processing of simulation results.

        Args:
            result: Raw simulation result

        Returns:
            Processed result with extracted metrics
        """
        # Extract additional metrics if not already present
        if result.success:
            # Calculate beamwidth from radiation pattern if available
            if (result.radiation_pattern_theta is not None and
                result.beamwidth_3db_deg is None):
                result.beamwidth_3db_deg = self._calculate_beamwidth(
                    result.radiation_pattern_theta,
                    result.theta_angles_deg
                )

            # Calculate sidelobe level if not present
            if (result.radiation_pattern_theta is not None and
                result.sidelobe_level_db is None):
                result.sidelobe_level_db = self._calculate_sidelobe_level(
                    result.radiation_pattern_theta
                )

        return result

    def _calculate_beamwidth(
        self,
        pattern: Any,
        angles: Any
    ) -> Optional[Tuple[float, float]]:
        """Calculate 3-dB beamwidth from radiation pattern."""
        # Simplified implementation
        # In production, would analyze pattern to find -3dB points
        return None

    def _calculate_sidelobe_level(self, pattern: Any) -> Optional[float]:
        """Calculate peak sidelobe level."""
        # Simplified implementation
        return None

    def _create_failed_result(self, error_message: str) -> SimulationResult:
        """Create a failed simulation result."""
        return SimulationResult(
            simulation_id=f"failed_{int(time.time())}",
            success=False,
            errors=[error_message]
        )

    def run_parametric_sweep(
        self,
        base_design: Dict[str, Any],
        parameter_ranges: Dict[str, List[float]],
        **kwargs
    ) -> List[SimulationResult]:
        """
        Run parametric sweep over design variables.

        Args:
            base_design: Base design configuration
            parameter_ranges: Dictionary of parameter names to value lists
            **kwargs: Additional parameters

        Returns:
            List of simulation results
        """
        results = []

        # Generate parameter combinations
        import itertools
        param_names = list(parameter_ranges.keys())
        param_values = list(parameter_ranges.values())

        combinations = list(itertools.product(*param_values))

        logger.info(f"Running parametric sweep with {len(combinations)} combinations")

        for i, combo in enumerate(combinations):
            # Create design variant
            design = base_design.copy()
            for param_name, param_value in zip(param_names, combo):
                design[param_name] = param_value

            logger.info(f"Sweep {i+1}/{len(combinations)}: {dict(zip(param_names, combo))}")

            # Run simulation
            result = self.run_complete_workflow(
                geometry=design.get("geometry", {}),
                materials=design.get("materials", {}),
                excitation=design.get("excitation", {}),
                frequency_range_ghz=design.get("frequency_range_ghz", (10.0, 11.0)),
                **kwargs
            )

            # Store parameter values in metadata
            result.metadata["parameters"] = dict(zip(param_names, combo))

            results.append(result)

        logger.info(f"Parametric sweep completed: {len(results)} simulations")

        return results
