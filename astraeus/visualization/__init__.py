"""
Interactive visualization and dashboards for antenna design.

This module provides web-based interactive visualizations using Plotly Dash
for exploring antenna designs, simulation results, and design space.
"""

from .dashboard import AntennaDashboard, create_dashboard
from .antenna_visualizer import AntennaVisualizer
from .pattern_plotter import PatternPlotter3D

__all__ = [
    'AntennaDashboard',
    'create_dashboard',
    'AntennaVisualizer',
    'PatternPlotter3D',
]
