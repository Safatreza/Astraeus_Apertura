"""Plotting utilities for antenna design visualization."""

from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path


class PatternPlotter:
    """Radiation pattern plotting utilities."""

    @staticmethod
    def plot_2d_pattern(
        angles_deg: np.ndarray,
        pattern_db: np.ndarray,
        title: str = "Radiation Pattern",
        save_path: Optional[str] = None
    ) -> None:
        """
        Plot 2D radiation pattern.

        Args:
            angles_deg: Angle array in degrees
            pattern_db: Pattern in dB
            title: Plot title
            save_path: Path to save figure
        """
        fig, ax = plt.subplots(figsize=(10, 6))

        ax.plot(angles_deg, pattern_db, 'b-', linewidth=2)
        ax.grid(True, alpha=0.3)
        ax.set_xlabel('Angle (degrees)', fontsize=12)
        ax.set_ylabel('Gain (dBi)', fontsize=12)
        ax.set_title(title, fontsize=14, fontweight='bold')

        # Mark 3-dB beamwidth
        max_gain = np.max(pattern_db)
        ax.axhline(y=max_gain - 3, color='r', linestyle='--', alpha=0.5, label='-3 dB')
        ax.legend()

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        else:
            plt.show()

        plt.close()

    @staticmethod
    def plot_polar_pattern(
        angles_deg: np.ndarray,
        pattern_db: np.ndarray,
        title: str = "Polar Pattern",
        save_path: Optional[str] = None
    ) -> None:
        """
        Plot radiation pattern in polar coordinates.

        Args:
            angles_deg: Angle array in degrees
            pattern_db: Pattern in dB
            title: Plot title
            save_path: Path to save figure
        """
        fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(projection='polar'))

        # Convert to radians
        angles_rad = np.deg2rad(angles_deg)

        # Normalize pattern to 0 dB max
        pattern_norm = pattern_db - np.max(pattern_db)

        ax.plot(angles_rad, pattern_norm, 'b-', linewidth=2)
        ax.set_theta_zero_location('N')
        ax.set_theta_direction(-1)
        ax.set_ylim([-40, 0])
        ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
        ax.grid(True, alpha=0.3)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        else:
            plt.show()

        plt.close()

    @staticmethod
    def plot_3d_pattern(
        theta: np.ndarray,
        phi: np.ndarray,
        pattern: np.ndarray,
        title: str = "3D Radiation Pattern",
        save_path: Optional[str] = None
    ) -> None:
        """
        Plot 3D radiation pattern.

        Args:
            theta: Theta angles in degrees
            phi: Phi angles in degrees
            pattern: Pattern gain in dB
            title: Plot title
            save_path: Path to save figure
        """
        from mpl_toolkits.mplot3d import Axes3D

        fig = plt.figure(figsize=(10, 8))
        ax = fig.add_subplot(111, projection='3d')

        # Convert to linear scale for 3D plotting
        pattern_linear = 10 ** (pattern / 20.0)

        # Convert to Cartesian coordinates
        theta_rad = np.deg2rad(theta)
        phi_rad = np.deg2rad(phi)

        x = pattern_linear * np.sin(theta_rad) * np.cos(phi_rad)
        y = pattern_linear * np.sin(theta_rad) * np.sin(phi_rad)
        z = pattern_linear * np.cos(theta_rad)

        ax.plot_surface(x, y, z, cmap='viridis', alpha=0.8)
        ax.set_xlabel('X')
        ax.set_ylabel('Y')
        ax.set_zlabel('Z')
        ax.set_title(title, fontsize=14, fontweight='bold')

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        else:
            plt.show()

        plt.close()


class PerformancePlotter:
    """Performance metric plotting utilities."""

    @staticmethod
    def plot_convergence(
        iterations: List[int],
        performance_values: List[float],
        metric_name: str = "Gain",
        metric_unit: str = "dBi",
        save_path: Optional[str] = None
    ) -> None:
        """
        Plot optimization convergence history.

        Args:
            iterations: Iteration numbers
            performance_values: Performance metric values
            metric_name: Name of metric
            metric_unit: Unit of metric
            save_path: Path to save figure
        """
        fig, ax = plt.subplots(figsize=(10, 6))

        ax.plot(iterations, performance_values, 'b-o', linewidth=2, markersize=6)
        ax.grid(True, alpha=0.3)
        ax.set_xlabel('Iteration', fontsize=12)
        ax.set_ylabel(f'{metric_name} ({metric_unit})', fontsize=12)
        ax.set_title(f'Optimization Convergence: {metric_name}', fontsize=14, fontweight='bold')

        # Add final value annotation
        final_value = performance_values[-1]
        ax.annotate(
            f'Final: {final_value:.2f} {metric_unit}',
            xy=(iterations[-1], final_value),
            xytext=(10, 10),
            textcoords='offset points',
            bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.5),
            arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0')
        )

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        else:
            plt.show()

        plt.close()

    @staticmethod
    def plot_pareto_front(
        objective1_values: List[float],
        objective2_values: List[float],
        objective1_name: str = "Gain",
        objective2_name: str = "Mass",
        save_path: Optional[str] = None
    ) -> None:
        """
        Plot Pareto front for multi-objective optimization.

        Args:
            objective1_values: First objective values
            objective2_values: Second objective values
            objective1_name: Name of first objective
            objective2_name: Name of second objective
            save_path: Path to save figure
        """
        fig, ax = plt.subplots(figsize=(10, 8))

        ax.scatter(objective1_values, objective2_values, c='blue', s=100, alpha=0.6,
                   edgecolors='black', linewidth=1.5)

        ax.grid(True, alpha=0.3)
        ax.set_xlabel(objective1_name, fontsize=12)
        ax.set_ylabel(objective2_name, fontsize=12)
        ax.set_title(f'Pareto Front: {objective1_name} vs {objective2_name}',
                     fontsize=14, fontweight='bold')

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        else:
            plt.show()

        plt.close()

    @staticmethod
    def plot_sensitivity_analysis(
        parameter_names: List[str],
        sensitivity_values: List[float],
        save_path: Optional[str] = None
    ) -> None:
        """
        Plot sensitivity analysis results.

        Args:
            parameter_names: Names of parameters
            sensitivity_values: Sensitivity coefficients
            save_path: Path to save figure
        """
        fig, ax = plt.subplots(figsize=(10, 6))

        colors = ['green' if v > 0 else 'red' for v in sensitivity_values]

        ax.barh(parameter_names, sensitivity_values, color=colors, alpha=0.7,
                edgecolor='black', linewidth=1.5)

        ax.axvline(x=0, color='black', linestyle='-', linewidth=1)
        ax.grid(True, alpha=0.3, axis='x')
        ax.set_xlabel('Sensitivity Coefficient', fontsize=12)
        ax.set_title('Parameter Sensitivity Analysis', fontsize=14, fontweight='bold')

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        else:
            plt.show()

        plt.close()

    @staticmethod
    def plot_comparison_radar(
        categories: List[str],
        design1_values: List[float],
        design2_values: List[float],
        design1_name: str = "AI Design",
        design2_name: str = "Baseline",
        save_path: Optional[str] = None
    ) -> None:
        """
        Plot radar chart comparing two designs.

        Args:
            categories: Category names
            design1_values: Values for first design (0-1 normalized)
            design2_values: Values for second design (0-1 normalized)
            design1_name: Name of first design
            design2_name: Name of second design
            save_path: Path to save figure
        """
        import matplotlib.pyplot as plt
        from math import pi

        # Number of variables
        num_vars = len(categories)

        # Compute angle for each axis
        angles = [n / float(num_vars) * 2 * pi for n in range(num_vars)]
        design1_values += design1_values[:1]
        design2_values += design2_values[:1]
        angles += angles[:1]

        # Initialize figure
        fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='polar'))

        # Plot data
        ax.plot(angles, design1_values, 'o-', linewidth=2, label=design1_name, color='blue')
        ax.fill(angles, design1_values, alpha=0.25, color='blue')

        ax.plot(angles, design2_values, 'o-', linewidth=2, label=design2_name, color='red')
        ax.fill(angles, design2_values, alpha=0.25, color='red')

        # Fix axis to go from 0 to 1
        ax.set_ylim(0, 1)

        # Add labels
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories, fontsize=10)

        # Add legend
        ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))

        ax.set_title('Design Comparison', fontsize=14, fontweight='bold', pad=20)
        ax.grid(True)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        else:
            plt.show()

        plt.close()
