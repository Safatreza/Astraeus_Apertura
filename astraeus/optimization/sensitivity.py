"""Sensitivity analysis for antenna design parameters."""

import numpy as np
from typing import Callable, Dict, List, Tuple, Optional
from loguru import logger


class SensitivityAnalyzer:
    """
    Sensitivity analysis for design parameters.

    Provides:
    - Local sensitivity analysis (derivatives)
    - Global sensitivity analysis (Sobol indices)
    - Parameter importance ranking
    """

    def __init__(self):
        """Initialize sensitivity analyzer."""
        self.results: Dict[str, any] = {}

    def local_sensitivity(
        self,
        objective_func: Callable,
        nominal_point: np.ndarray,
        param_names: List[str],
        perturbation: float = 0.01
    ) -> Dict[str, float]:
        """
        Compute local sensitivity (finite difference derivatives).

        Args:
            objective_func: Objective function
            nominal_point: Nominal design point
            param_names: Names of parameters
            perturbation: Perturbation fraction for finite differences

        Returns:
            Dictionary of parameter sensitivities
        """
        logger.info("Computing local sensitivity analysis...")

        n_params = len(nominal_point)
        sensitivities = {}

        # Evaluate at nominal point
        f_nominal = objective_func(nominal_point)

        for i in range(n_params):
            # Perturb parameter
            perturbed_point = nominal_point.copy()
            delta = perturbation * abs(nominal_point[i]) if nominal_point[i] != 0 else perturbation

            # Forward difference
            perturbed_point[i] = nominal_point[i] + delta
            f_plus = objective_func(perturbed_point)

            # Backward difference
            perturbed_point[i] = nominal_point[i] - delta
            f_minus = objective_func(perturbed_point)

            # Central difference
            derivative = (f_plus - f_minus) / (2 * delta)

            # Normalized sensitivity
            if f_nominal != 0:
                normalized_sensitivity = (derivative * delta) / f_nominal
            else:
                normalized_sensitivity = derivative * delta

            sensitivities[param_names[i]] = {
                'derivative': derivative,
                'normalized': normalized_sensitivity,
                'absolute': abs(normalized_sensitivity)
            }

            logger.debug(f"{param_names[i]}: sensitivity = {normalized_sensitivity:.6f}")

        # Rank by absolute sensitivity
        ranked = sorted(
            sensitivities.items(),
            key=lambda x: x[1]['absolute'],
            reverse=True
        )

        self.results['local_sensitivity'] = {
            'nominal_point': nominal_point,
            'nominal_value': f_nominal,
            'sensitivities': sensitivities,
            'ranked': [(name, data['normalized']) for name, data in ranked]
        }

        logger.info("Local sensitivity analysis complete")

        return sensitivities

    def morris_screening(
        self,
        objective_func: Callable,
        bounds: List[Tuple[float, float]],
        param_names: List[str],
        num_trajectories: int = 10,
        num_levels: int = 4
    ) -> Dict[str, Dict[str, float]]:
        """
        Morris screening method for global sensitivity.

        Efficient method for identifying important parameters
        in high-dimensional problems.

        Args:
            objective_func: Objective function
            bounds: Parameter bounds
            param_names: Parameter names
            num_trajectories: Number of trajectories
            num_levels: Number of grid levels

        Returns:
            Dictionary of parameter sensitivities (mu, mu_star, sigma)
        """
        logger.info(f"Computing Morris screening with {num_trajectories} trajectories...")

        n_params = len(bounds)
        bounds_array = np.array(bounds)

        # Storage for elementary effects
        elementary_effects = {name: [] for name in param_names}

        # Generate trajectories
        for traj in range(num_trajectories):
            # Random starting point on grid
            point = self._random_grid_point(bounds_array, num_levels)

            # Random parameter ordering
            param_order = np.random.permutation(n_params)

            # Evaluate starting point
            f_current = objective_func(point)

            # One-at-a-time parameter changes
            for i in param_order:
                # Perturb parameter
                point_perturbed = point.copy()
                delta = (bounds_array[i, 1] - bounds_array[i, 0]) / (num_levels - 1)

                # Move to adjacent grid point
                if np.random.random() < 0.5:
                    point_perturbed[i] = min(point[i] + delta, bounds_array[i, 1])
                else:
                    point_perturbed[i] = max(point[i] - delta, bounds_array[i, 0])

                # Evaluate perturbed point
                f_perturbed = objective_func(point_perturbed)

                # Compute elementary effect
                actual_delta = point_perturbed[i] - point[i]
                if actual_delta != 0:
                    ee = (f_perturbed - f_current) / actual_delta
                    elementary_effects[param_names[i]].append(ee)

                # Update current point and value
                point = point_perturbed
                f_current = f_perturbed

        # Compute Morris measures
        sensitivities = {}
        for name in param_names:
            effects = np.array(elementary_effects[name])
            if len(effects) > 0:
                mu = np.mean(effects)  # Mean
                mu_star = np.mean(np.abs(effects))  # Mean absolute
                sigma = np.std(effects)  # Standard deviation

                sensitivities[name] = {
                    'mu': mu,
                    'mu_star': mu_star,  # Overall sensitivity
                    'sigma': sigma,  # Non-linearity/interaction
                    'importance': mu_star  # Ranking criterion
                }
            else:
                sensitivities[name] = {
                    'mu': 0.0,
                    'mu_star': 0.0,
                    'sigma': 0.0,
                    'importance': 0.0
                }

        # Rank by importance
        ranked = sorted(
            sensitivities.items(),
            key=lambda x: x[1]['importance'],
            reverse=True
        )

        self.results['morris_screening'] = {
            'sensitivities': sensitivities,
            'ranked': [(name, data['mu_star']) for name, data in ranked]
        }

        logger.info("Morris screening complete")

        return sensitivities

    def _random_grid_point(
        self,
        bounds: np.ndarray,
        num_levels: int
    ) -> np.ndarray:
        """Generate random point on grid."""
        n_params = bounds.shape[0]
        point = np.zeros(n_params)

        for i in range(n_params):
            level = np.random.randint(0, num_levels)
            point[i] = bounds[i, 0] + level * (bounds[i, 1] - bounds[i, 0]) / (num_levels - 1)

        return point

    def parameter_sweep(
        self,
        objective_func: Callable,
        nominal_point: np.ndarray,
        param_idx: int,
        param_name: str,
        bounds: Tuple[float, float],
        num_points: int = 50
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Sweep a single parameter while keeping others fixed.

        Args:
            objective_func: Objective function
            nominal_point: Nominal design point
            param_idx: Index of parameter to sweep
            param_name: Name of parameter
            bounds: (min, max) for sweep
            num_points: Number of sweep points

        Returns:
            Tuple of (parameter_values, objective_values)
        """
        logger.info(f"Sweeping parameter: {param_name}")

        param_values = np.linspace(bounds[0], bounds[1], num_points)
        objective_values = np.zeros(num_points)

        for i, value in enumerate(param_values):
            point = nominal_point.copy()
            point[param_idx] = value
            objective_values[i] = objective_func(point)

        return param_values, objective_values

    def get_results(self) -> Dict[str, any]:
        """Get all sensitivity analysis results."""
        return self.results
