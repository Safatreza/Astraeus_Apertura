"""
Antenna geometry and performance visualization.

Provides visualization tools for antenna geometries, performance metrics,
and design comparisons.
"""

import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, Any, List, Optional
from loguru import logger

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False


class AntennaVisualizer:
    """
    Visualizer for antenna designs and performance.
    
    Capabilities:
    - Geometry visualization
    - Performance comparison
    - Design space exploration
    - Multi-objective optimization results
    """
    
    def __init__(self, use_plotly: bool = True):
        """
        Initialize visualizer.
        
        Args:
            use_plotly: Use Plotly for interactive plots
        """
        self.use_plotly = use_plotly and PLOTLY_AVAILABLE
    
    def plot_performance_comparison(
        self,
        designs: List[Dict[str, Any]],
        metrics: List[str] = None,
        title: str = "Performance Comparison",
        save_path: Optional[str] = None
    ):
        """
        Plot performance comparison across multiple designs.
        
        Args:
            designs: List of design dictionaries with performance metrics
            metrics: Metrics to compare
            title: Plot title
            save_path: Optional save path
        """
        if metrics is None:
            metrics = ['gain_dbi', 'vswr', 'efficiency', 'bandwidth_mhz']
        
        if self.use_plotly:
            self._plot_comparison_plotly(designs, metrics, title, save_path)
        else:
            self._plot_comparison_matplotlib(designs, metrics, title, save_path)
    
    def _plot_comparison_plotly(self, designs, metrics, title, save_path):
        """Plot comparison using Plotly."""
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=tuple(m.replace('_', ' ').title() for m in metrics[:4])
        )
        
        design_names = [d.get('name', f"Design {i}") for i, d in enumerate(designs, 1)]
        
        positions = [(1,1), (1,2), (2,1), (2,2)]
        
        for idx, metric in enumerate(metrics[:4]):
            row, col = positions[idx]
            values = [d.get(metric, 0) for d in designs]
            
            fig.add_trace(
                go.Bar(
                    x=design_names,
                    y=values,
                    name=metric.replace('_', ' ').title(),
                    showlegend=False
                ),
                row=row, col=col
            )
        
        fig.update_layout(
            title_text=title,
            height=700,
            showlegend=False
        )
        
        if save_path:
            fig.write_html(save_path)
        else:
            fig.show()
    
    def _plot_comparison_matplotlib(self, designs, metrics, title, save_path):
        """Plot comparison using Matplotlib."""
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        fig.suptitle(title, fontsize=14, fontweight='bold')
        
        design_names = [d.get('name', f"Design {i}") for i, d in enumerate(designs, 1)]
        
        for idx, (ax, metric) in enumerate(zip(axes.flat, metrics[:4])):
            values = [d.get(metric, 0) for d in designs]
            
            ax.bar(design_names, values, color=plt.cm.viridis(idx/4))
            ax.set_ylabel(metric.replace('_', ' ').title())
            ax.grid(axis='y', alpha=0.3)
            ax.tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        else:
            plt.show()
    
    def plot_pareto_front(
        self,
        designs: List[Dict[str, Any]],
        objective1: str,
        objective2: str,
        title: str = "Pareto Front",
        save_path: Optional[str] = None
    ):
        """
        Plot Pareto front for multi-objective optimization.
        
        Args:
            designs: List of designs
            objective1: First objective metric
            objective2: Second objective metric
            title: Plot title
            save_path: Save path
        """
        x = [d.get(objective1, 0) for d in designs]
        y = [d.get(objective2, 0) for d in designs]
        names = [d.get('name', f"D{i}") for i, d in enumerate(designs, 1)]
        
        if self.use_plotly:
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=x, y=y,
                mode='markers+text',
                text=names,
                textposition="top center",
                marker=dict(size=10, color='blue'),
                name='Designs'
            ))
            
            fig.update_layout(
                title=title,
                xaxis_title=objective1.replace('_', ' ').title(),
                yaxis_title=objective2.replace('_', ' ').title(),
                height=600
            )
            
            if save_path:
                fig.write_html(save_path)
            else:
                fig.show()
        
        else:
            plt.figure(figsize=(10, 7))
            plt.scatter(x, y, s=100, c='blue', alpha=0.6)
            
            for i, name in enumerate(names):
                plt.annotate(name, (x[i], y[i]), xytext=(5, 5),
                           textcoords='offset points', fontsize=9)
            
            plt.xlabel(objective1.replace('_', ' ').title(), fontsize=12)
            plt.ylabel(objective2.replace('_', ' ').title(), fontsize=12)
            plt.title(title, fontsize=14, fontweight='bold')
            plt.grid(alpha=0.3)
            
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
            else:
                plt.show()
