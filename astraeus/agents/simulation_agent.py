"""Simulation Agent - Manages electromagnetic and multiphysics simulations."""

from typing import Any, Dict, List, Optional
import time

from loguru import logger
import numpy as np

from astraeus.core.agent_base import BaseAgent
from astraeus.core.message import Message, MessagePriority, MessageType
from astraeus.data.parameters import AntennaType, MissionRequirements


class SimulationAgent(BaseAgent):
    """
    Agent responsible for electromagnetic and multiphysics simulations.

    Primary Responsibilities:
    - Set up and execute electromagnetic simulations (HFSS, CST, FEKO)
    - Perform thermal analysis for power dissipation and temperature gradients
    - Conduct structural analysis for mechanical integrity
    - Run coupled multiphysics simulations
    - Extract performance metrics (gain, radiation pattern, S-parameters)
    - Manage computational resources and simulation workflows
    """

    def _initialize(self) -> None:
        """Initialize the Simulation Agent."""
        self.agent_type = "SimulationAgent"
        self.knowledge_domains = [
            "electromagnetic_simulation",
            "method_of_moments",
            "finite_element_method",
            "fdtd",
            "thermal_analysis",
            "structural_analysis",
            "multiphysics",
        ]
        self.capabilities = [
            "em_simulation",
            "thermal_simulation",
            "structural_simulation",
            "coupled_analysis",
            "performance_extraction",
            "mesh_refinement",
        ]

        # Available simulation tools
        self.simulation_tools = {
            "em": ["HFSS", "CST", "FEKO", "OpenEMS"],
            "thermal": ["ANSYS Thermal", "COMSOL"],
            "structural": ["ANSYS Mechanical", "Nastran"],
        }

        # Simulation settings
        self.convergence_criteria = {
            "s_parameters": 0.001,  # Max delta
            "gain": 0.1,  # dB
            "radiation_pattern": 0.5,  # dB
        }

        # Resource limits
        self.resource_limits = {
            "max_mesh_elements": 10_000_000,
            "max_simulation_time_hours": 24,
            "max_memory_gb": 64,
        }

        logger.info("Simulation Agent initialized")

    def process_message(self, message: Message) -> Optional[List[Message]]:
        """
        Process incoming messages.

        Args:
            message: Message to process

        Returns:
            List of response messages
        """
        if message.message_type == MessageType.REQUEST_TASK:
            return self._handle_task_request(message)
        elif message.message_type == MessageType.QUERY:
            return self._handle_query(message)
        elif message.message_type == MessageType.STATUS_UPDATE:
            return self._handle_status_update(message)
        else:
            logger.debug(f"Unhandled message type: {message.message_type}")
            return None

    def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute simulation task.

        Args:
            task: Task specification

        Returns:
            Simulation results
        """
        task_type = task.get("type")

        if task_type == "run_em_simulation":
            return self._run_em_simulation(
                task["geometry"],
                task["materials"],
                task.get("frequency_points"),
            )
        elif task_type == "run_thermal_simulation":
            return self._run_thermal_simulation(
                task["geometry"],
                task["materials"],
                task["power_dissipation"],
            )
        elif task_type == "run_structural_simulation":
            return self._run_structural_simulation(
                task["geometry"], task["materials"], task["loads"]
            )
        elif task_type == "run_multiphysics":
            return self._run_multiphysics_simulation(
                task["geometry"], task["materials"], task["analysis_types"]
            )
        elif task_type == "extract_metrics":
            return self._extract_performance_metrics(task["simulation_results"])
        else:
            raise ValueError(f"Unknown task type: {task_type}")

    def _run_em_simulation(
        self,
        geometry: Dict[str, Any],
        materials: Dict[str, Any],
        frequency_points: Optional[List[float]] = None,
    ) -> Dict[str, Any]:
        """
        Run electromagnetic simulation.

        Args:
            geometry: Antenna geometry
            materials: Material properties
            frequency_points: Frequency points to simulate (GHz)

        Returns:
            Simulation results
        """
        logger.info("Running electromagnetic simulation")

        # Select appropriate simulation tool
        tool = self._select_em_tool(geometry)

        # Set up simulation
        sim_setup = self._setup_em_simulation(geometry, materials, frequency_points)

        # Run simulation (simplified - would actually call external solver)
        start_time = time.time()
        results = self._execute_em_simulation(sim_setup, tool)
        simulation_time = time.time() - start_time

        # Extract performance metrics
        metrics = self._extract_em_metrics(results)

        # Check convergence
        convergence = self._check_convergence(results)

        # Log decision
        self.log_decision(
            decision=f"Completed EM simulation using {tool}",
            rationale=f"Simulated {len(frequency_points or [1])} frequency points",
            metadata={
                "simulation_time_s": simulation_time,
                "converged": convergence["converged"],
                "mesh_elements": sim_setup["mesh"]["num_elements"],
            },
        )

        return {
            "simulation_type": "electromagnetic",
            "tool": tool,
            "results": results,
            "metrics": metrics,
            "convergence": convergence,
            "simulation_time_s": simulation_time,
            "setup": sim_setup,
        }

    def _run_thermal_simulation(
        self,
        geometry: Dict[str, Any],
        materials: Dict[str, Any],
        power_dissipation: Dict[str, float],
    ) -> Dict[str, Any]:
        """
        Run thermal analysis simulation.

        Args:
            geometry: Antenna geometry
            materials: Material properties
            power_dissipation: Power dissipation map (W)

        Returns:
            Thermal simulation results
        """
        logger.info("Running thermal simulation")

        # Set up thermal simulation
        sim_setup = self._setup_thermal_simulation(
            geometry, materials, power_dissipation
        )

        # Execute simulation
        start_time = time.time()
        results = self._execute_thermal_simulation(sim_setup)
        simulation_time = time.time() - start_time

        # Extract thermal metrics
        metrics = {
            "max_temperature_c": results["max_temperature_c"],
            "min_temperature_c": results["min_temperature_c"],
            "temperature_gradient_c_per_m": results["max_gradient"],
            "hot_spots": results["hot_spots"],
        }

        self.log_decision(
            decision="Completed thermal simulation",
            rationale=f"Max temperature: {metrics['max_temperature_c']:.1f}°C",
            metadata=metrics,
        )

        return {
            "simulation_type": "thermal",
            "results": results,
            "metrics": metrics,
            "simulation_time_s": simulation_time,
            "setup": sim_setup,
        }

    def _run_structural_simulation(
        self,
        geometry: Dict[str, Any],
        materials: Dict[str, Any],
        loads: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Run structural analysis simulation.

        Args:
            geometry: Antenna geometry
            materials: Material properties
            loads: Applied loads and boundary conditions

        Returns:
            Structural simulation results
        """
        logger.info("Running structural simulation")

        # Set up structural simulation
        sim_setup = self._setup_structural_simulation(geometry, materials, loads)

        # Execute simulation
        start_time = time.time()
        results = self._execute_structural_simulation(sim_setup)
        simulation_time = time.time() - start_time

        # Extract structural metrics
        metrics = {
            "max_stress_mpa": results["max_stress"],
            "max_displacement_mm": results["max_displacement"],
            "safety_factor": results["safety_factor"],
            "natural_frequencies_hz": results["modal_frequencies"],
        }

        self.log_decision(
            decision="Completed structural simulation",
            rationale=f"Safety factor: {metrics['safety_factor']:.2f}",
            metadata=metrics,
        )

        return {
            "simulation_type": "structural",
            "results": results,
            "metrics": metrics,
            "simulation_time_s": simulation_time,
            "setup": sim_setup,
        }

    def _run_multiphysics_simulation(
        self,
        geometry: Dict[str, Any],
        materials: Dict[str, Any],
        analysis_types: List[str],
    ) -> Dict[str, Any]:
        """
        Run coupled multiphysics simulation.

        Args:
            geometry: Antenna geometry
            materials: Material properties
            analysis_types: Types of analysis to couple

        Returns:
            Multiphysics simulation results
        """
        logger.info(f"Running multiphysics simulation: {', '.join(analysis_types)}")

        results = {}

        # Run coupled simulations
        if "electromagnetic" in analysis_types and "thermal" in analysis_types:
            # EM-Thermal coupling
            em_results = self._run_em_simulation(geometry, materials, None)
            power_dissipation = self._calculate_power_dissipation(em_results)
            thermal_results = self._run_thermal_simulation(
                geometry, materials, power_dissipation
            )

            results["electromagnetic"] = em_results
            results["thermal"] = thermal_results

        return {
            "simulation_type": "multiphysics",
            "coupled_analyses": analysis_types,
            "results": results,
        }

    def _select_em_tool(self, geometry: Dict[str, Any]) -> str:
        """
        Select appropriate EM simulation tool.

        Args:
            geometry: Antenna geometry

        Returns:
            Selected tool name
        """
        # Selection logic based on geometry type and complexity
        geo_type = geometry.get("type")

        if geo_type in ["patch_array", "phased_array"]:
            return "HFSS"  # Good for planar structures
        elif geo_type in ["reflector_parabolic", "reflector_cassegrain"]:
            return "FEKO"  # Good for electrically large structures
        elif geo_type == "horn":
            return "CST"  # Good for waveguide structures
        else:
            return "HFSS"  # Default

    def _setup_em_simulation(
        self,
        geometry: Dict[str, Any],
        materials: Dict[str, Any],
        frequency_points: Optional[List[float]],
    ) -> Dict[str, Any]:
        """Set up EM simulation parameters."""
        if frequency_points is None:
            # Default to single frequency
            frequency_points = [10.0]  # GHz

        return {
            "geometry": geometry,
            "materials": materials,
            "frequency_points_ghz": frequency_points,
            "mesh": {
                "type": "adaptive",
                "num_elements": 50000,  # Initial estimate
                "max_refinement_passes": 10,
            },
            "boundary_conditions": {
                "type": "radiation",
                "distance_wavelengths": 0.25,
            },
            "excitation": {
                "type": "waveport",
                "impedance_ohm": 50.0,
            },
            "convergence": self.convergence_criteria,
        }

    def _execute_em_simulation(
        self, setup: Dict[str, Any], tool: str
    ) -> Dict[str, Any]:
        """
        Execute EM simulation (simplified mock).

        In production, this would interface with actual EM solver.
        """
        logger.debug(f"Executing EM simulation with {tool}")

        # Simplified simulation - generate realistic-looking results
        frequency_points = setup["frequency_points_ghz"]

        # Generate S-parameters
        s_parameters = []
        for freq in frequency_points:
            s11_mag = -15.0 + np.random.randn() * 2.0  # Return loss
            s11_phase = np.random.rand() * 360.0
            s_parameters.append({
                "frequency_ghz": freq,
                "s11_db": s11_mag,
                "s11_phase_deg": s11_phase,
            })

        # Generate radiation pattern (simplified)
        theta = np.linspace(0, 180, 181)
        phi = np.linspace(0, 360, 361)

        # Simplified gain pattern
        gain_pattern = self._generate_radiation_pattern(theta, setup["geometry"])

        return {
            "s_parameters": s_parameters,
            "radiation_pattern": {
                "theta_deg": theta.tolist(),
                "phi_deg": phi.tolist(),
                "gain_dbi": gain_pattern.tolist(),
            },
            "field_data": {
                "available": True,
                "num_points": 100000,
            },
        }

    def _execute_thermal_simulation(self, setup: Dict[str, Any]) -> Dict[str, Any]:
        """Execute thermal simulation (simplified mock)."""
        logger.debug("Executing thermal simulation")

        # Simplified results
        return {
            "max_temperature_c": 85.0 + np.random.randn() * 10.0,
            "min_temperature_c": -20.0 + np.random.randn() * 5.0,
            "max_gradient": 50.0,
            "hot_spots": [
                {"location": [0, 0, 0], "temperature_c": 85.0},
            ],
            "temperature_distribution": {
                "available": True,
                "num_nodes": 50000,
            },
        }

    def _execute_structural_simulation(self, setup: Dict[str, Any]) -> Dict[str, Any]:
        """Execute structural simulation (simplified mock)."""
        logger.debug("Executing structural simulation")

        # Simplified results
        yield_strength = 300.0  # MPa
        max_stress = 120.0 + np.random.randn() * 20.0

        return {
            "max_stress": max_stress,
            "max_displacement": 0.5 + np.random.randn() * 0.1,
            "safety_factor": yield_strength / max_stress,
            "modal_frequencies": [50.0, 120.0, 200.0],  # First 3 modes
            "stress_distribution": {
                "available": True,
                "num_nodes": 30000,
            },
        }

    def _setup_thermal_simulation(
        self,
        geometry: Dict[str, Any],
        materials: Dict[str, Any],
        power_dissipation: Dict[str, float],
    ) -> Dict[str, Any]:
        """Set up thermal simulation parameters."""
        return {
            "geometry": geometry,
            "materials": materials,
            "power_dissipation": power_dissipation,
            "boundary_conditions": {
                "ambient_temperature_c": 20.0,
                "radiation_emissivity": 0.8,
                "convection_coefficient": 10.0,  # W/m^2/K
            },
        }

    def _setup_structural_simulation(
        self,
        geometry: Dict[str, Any],
        materials: Dict[str, Any],
        loads: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Set up structural simulation parameters."""
        return {
            "geometry": geometry,
            "materials": materials,
            "loads": loads,
            "boundary_conditions": {
                "fixed_supports": loads.get("fixed_locations", []),
            },
            "analysis_type": "static",
        }

    def _extract_em_metrics(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Extract key EM performance metrics from simulation results."""
        s_params = results["s_parameters"]
        rad_pattern = results["radiation_pattern"]

        # Extract metrics
        s11_db = [sp["s11_db"] for sp in s_params]
        frequencies = [sp["frequency_ghz"] for sp in s_params]

        # Find worst-case S11
        worst_s11 = max(s11_db)
        best_s11 = min(s11_db)

        # Extract peak gain
        gain_array = np.array(rad_pattern["gain_dbi"])
        peak_gain = np.max(gain_array)

        # Estimate beamwidth (simplified)
        beamwidth = self._estimate_beamwidth(gain_array)

        return {
            "peak_gain_dbi": float(peak_gain),
            "s11_worst_db": float(worst_s11),
            "s11_best_db": float(best_s11),
            "vswr_max": self._db_to_vswr(worst_s11),
            "beamwidth_deg": beamwidth,
            "frequency_range_ghz": (min(frequencies), max(frequencies)),
        }

    def _extract_performance_metrics(
        self, simulation_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Extract all performance metrics from simulation results.

        Args:
            simulation_results: Complete simulation results

        Returns:
            Extracted metrics
        """
        metrics = {}

        if "electromagnetic" in simulation_results:
            metrics["electromagnetic"] = self._extract_em_metrics(
                simulation_results["electromagnetic"]["results"]
            )

        if "thermal" in simulation_results:
            metrics["thermal"] = simulation_results["thermal"]["metrics"]

        if "structural" in simulation_results:
            metrics["structural"] = simulation_results["structural"]["metrics"]

        return metrics

    def _check_convergence(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Check if simulation has converged."""
        # Simplified convergence check
        converged = True
        iterations = 5

        return {
            "converged": converged,
            "iterations": iterations,
            "final_delta": 0.0005,
            "convergence_criteria": self.convergence_criteria,
        }

    def _calculate_power_dissipation(
        self, em_results: Dict[str, Any]
    ) -> Dict[str, float]:
        """Calculate power dissipation from EM results."""
        # Simplified power dissipation calculation
        return {
            "total_power_w": 10.0,
            "conductor_losses_w": 2.0,
            "dielectric_losses_w": 1.0,
        }

    def _generate_radiation_pattern(
        self, theta: np.ndarray, geometry: Dict[str, Any]
    ) -> np.ndarray:
        """Generate simplified radiation pattern."""
        # Simplified pattern - cosine-like main beam
        target_gain = geometry.get("total_dimensions", {}).get("length", 30.0)

        # Main beam
        pattern = target_gain * (np.cos(np.radians(theta)) ** 4)

        # Floor at sidelobe level
        sidelobe_level = target_gain - 20.0
        pattern = np.maximum(pattern, sidelobe_level)

        return pattern

    def _estimate_beamwidth(self, gain_pattern: np.ndarray) -> float:
        """Estimate 3-dB beamwidth from gain pattern."""
        peak_gain = np.max(gain_pattern)
        half_power = peak_gain - 3.0

        # Find points where gain crosses half-power level
        # Simplified - just use approximate value
        beamwidth = 65.0 / np.sqrt(10 ** (peak_gain / 10.0))

        return beamwidth

    def _db_to_vswr(self, s11_db: float) -> float:
        """Convert S11 in dB to VSWR."""
        reflection_coef = 10 ** (s11_db / 20.0)
        vswr = (1 + reflection_coef) / (1 - reflection_coef)
        return vswr

    def _handle_query(self, message: Message) -> List[Message]:
        """Handle query messages."""
        response = message.create_reply(
            sender=self.agent_id,
            message_type=MessageType.DATA_TRANSFER,
            payload={
                "status": "Simulation capability available",
                "tools": self.simulation_tools,
            },
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
                rationale="Simulation task completed",
            )
            return [response]
        return []

    def _handle_status_update(self, message: Message) -> List[Message]:
        """Handle status update messages."""
        # Acknowledge status updates
        logger.debug(f"Received status update: {message.payload}")
        return []
