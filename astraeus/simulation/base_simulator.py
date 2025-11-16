"""Base simulator abstraction layer for EM simulation tools."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import numpy as np


@dataclass
class SimulationResult:
    """
    Container for simulation results.

    Provides standardized format regardless of backend simulator.
    """

    simulation_id: str
    success: bool
    timestamp: datetime = field(default_factory=datetime.now)

    # S-parameters
    s_parameters: Dict[str, np.ndarray] = field(default_factory=dict)
    frequency_points_ghz: np.ndarray = field(default_factory=lambda: np.array([]))

    # Radiation patterns
    radiation_pattern_theta: Optional[np.ndarray] = None
    radiation_pattern_phi: Optional[np.ndarray] = None
    theta_angles_deg: Optional[np.ndarray] = None
    phi_angles_deg: Optional[np.ndarray] = None

    # Performance metrics
    gain_dbi: Optional[float] = None
    directivity_dbi: Optional[float] = None
    efficiency_percent: Optional[float] = None
    beamwidth_3db_deg: Optional[Tuple[float, float]] = None  # (az, el)
    sidelobe_level_db: Optional[float] = None

    # Impedance metrics
    vswr: Optional[float] = None
    return_loss_db: Optional[float] = None
    input_impedance_ohm: Optional[complex] = None

    # Additional data
    metadata: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    runtime_seconds: Optional[float] = None
    memory_mb: Optional[float] = None


class BaseSimulator(ABC):
    """
    Abstract base class for EM simulation backends.

    Provides unified interface for different simulation tools
    (HFSS, CST, OpenEMS, FEKO, etc.)
    """

    def __init__(self, simulator_name: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize simulator.

        Args:
            simulator_name: Name of the simulator backend
            config: Configuration dictionary
        """
        self.simulator_name = simulator_name
        self.config = config or {}
        self.is_initialized = False

    @abstractmethod
    def initialize(self) -> bool:
        """
        Initialize the simulator backend.

        Returns:
            True if initialization successful
        """
        pass

    @abstractmethod
    def setup_geometry(self, geometry: Dict[str, Any]) -> bool:
        """
        Set up simulation geometry.

        Args:
            geometry: Geometry specification

        Returns:
            True if setup successful
        """
        pass

    @abstractmethod
    def set_materials(self, materials: Dict[str, Any]) -> bool:
        """
        Set material properties.

        Args:
            materials: Material specifications

        Returns:
            True if setup successful
        """
        pass

    @abstractmethod
    def set_boundary_conditions(self, boundaries: Dict[str, Any]) -> bool:
        """
        Set boundary conditions.

        Args:
            boundaries: Boundary condition specifications

        Returns:
            True if setup successful
        """
        pass

    @abstractmethod
    def set_excitation(self, excitation: Dict[str, Any]) -> bool:
        """
        Set excitation/source.

        Args:
            excitation: Excitation specifications

        Returns:
            True if setup successful
        """
        pass

    @abstractmethod
    def run_simulation(self, **kwargs) -> SimulationResult:
        """
        Run the simulation.

        Args:
            **kwargs: Additional simulation parameters

        Returns:
            Simulation results
        """
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Clean up simulation resources."""
        pass

    def validate_setup(self) -> Tuple[bool, List[str]]:
        """
        Validate simulation setup before running.

        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        # Base implementation - can be overridden
        issues = []

        if not self.is_initialized:
            issues.append("Simulator not initialized")

        return (len(issues) == 0, issues)
