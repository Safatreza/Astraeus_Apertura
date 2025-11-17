"""
3D antenna radiation pattern visualization.

Provides high-quality 3D plotting of antenna radiation patterns with
interactive controls and multiple pattern representations.
"""

import numpy as np
from typing import Optional, Tuple, Dict, Any
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from loguru import logger

try:
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False


class PatternPlotter3D:
    """
    Advanced 3D radiation pattern plotter.
    
    Supports:
    - Multiple pattern representations (rectangular, polar, 3D)
    - Cut planes (E-plane, H-plane, arbitrary)
    - Pattern overlays
    - Directivity visualization
    """
    
    def __init__(self, use_plotly: bool = True):
        """
        Initialize plotter.
        
        Args:
            use_plotly: Use Plotly for interactive plots (if available)
        """
        self.use_plotly = use_plotly and PLOTLY_AVAILABLE
        
        if use_plotly and not PLOTLY_AVAILABLE:
            logger.warning("Plotly not available, falling back to matplotlib")
            self.use_plotly = False
    
    def plot_3d_pattern(
        self,
        theta: np.ndarray,
        phi: np.ndarray,
        pattern: np.ndarray,
        title: str = "3D Radiation Pattern",
        db_scale: bool = True,
        save_path: Optional[str] = None
    ):
        """
        Plot 3D radiation pattern.
        
        Args:
            theta: Theta angles (0 to π)
            phi: Phi angles (0 to 2π)
            pattern: Pattern values (2D array)
            title: Plot title
            db_scale: Use dB scale
            save_path: Optional path to save figure
        """
        if db_scale:
            pattern_plot = 10 * np.log10(pattern + 1e-10)
            colorbar_title = "Gain (dB)"
        else:
            pattern_plot = pattern
            colorbar_title = "Normalized Gain"
        
        if self.use_plotly:
            self._plot_3d_plotly(theta, phi, pattern_plot, title, colorbar_title, save_path)
        else:
            self._plot_3d_matplotlib(theta, phi, pattern_plot, title, colorbar_title, save_path)
    
    def _plot_3d_plotly(
        self,
        theta: np.ndarray,
        phi: np.ndarray,
        pattern: np.ndarray,
        title: str,
        colorbar_title: str,
        save_path: Optional[str]
    ):
        """Plot using Plotly."""
        THETA, PHI = np.meshgrid(theta, phi)
        
        # Convert to Cartesian coordinates
        R = pattern
        X = R * np.sin(THETA) * np.cos(PHI)
        Y = R * np.sin(THETA) * np.sin(PHI)
        Z = R * np.cos(THETA)
        
        fig = go.Figure(data=[go.Surface(
            x=X, y=Y, z=Z,
            surfacecolor=pattern,
            colorscale='Viridis',
            colorbar=dict(title=colorbar_title),
            hovertemplate='θ: %{customdata[0]:.1f}°<br>φ: %{customdata[1]:.1f}°<br>Gain: %{surfacecolor:.2f}<extra></extra>',
            customdata=np.dstack([np.degrees(THETA), np.degrees(PHI)])
        )])
        
        fig.update_layout(
            title=title,
            scene=dict(
                xaxis_title="X",
                yaxis_title="Y",
                zaxis_title="Z",
                aspectmode='cube',
                camera=dict(
                    eye=dict(x=1.5, y=1.5, z=1.5)
                )
            ),
            width=800,
            height=700
        )
        
        if save_path:
            fig.write_html(save_path)
            logger.info(f"Saved plot to {save_path}")
        else:
            fig.show()
    
    def _plot_3d_matplotlib(
        self,
        theta: np.ndarray,
        phi: np.ndarray,
        pattern: np.ndarray,
        title: str,
        colorbar_title: str,
        save_path: Optional[str]
    ):
        """Plot using Matplotlib."""
        fig = plt.figure(figsize=(10, 8))
        ax = fig.add_subplot(111, projection='3d')
        
        THETA, PHI = np.meshgrid(theta, phi)
        
        # Convert to Cartesian
        R = pattern
        X = R * np.sin(THETA) * np.cos(PHI)
        Y = R * np.sin(THETA) * np.sin(PHI)
        Z = R * np.cos(THETA)
        
        surf = ax.plot_surface(X, Y, Z, facecolors=plt.cm.viridis((pattern - pattern.min()) / (pattern.max() - pattern.min())),
                              rstride=1, cstride=1, linewidth=0, antialiased=True)
        
        ax.set_xlabel('X')
        ax.set_ylabel('Y')
        ax.set_zlabel('Z')
        ax.set_title(title)
        
        # Add colorbar
        m = plt.cm.ScalarMappable(cmap=plt.cm.viridis)
        m.set_array(pattern)
        plt.colorbar(m, ax=ax, label=colorbar_title, shrink=0.5)
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Saved plot to {save_path}")
        else:
            plt.show()
    
    def plot_cut_planes(
        self,
        theta: np.ndarray,
        pattern_e: np.ndarray,
        pattern_h: np.ndarray,
        title: str = "Pattern Cut Planes",
        save_path: Optional[str] = None
    ):
        """
        Plot E-plane and H-plane pattern cuts.
        
        Args:
            theta: Theta angles (degrees or radians)
            pattern_e: E-plane pattern
            pattern_h: H-plane pattern
            title: Plot title
            save_path: Save path
        """
        # Convert to degrees if in radians
        if np.max(theta) <= 2 * np.pi:
            theta_deg = np.degrees(theta)
        else:
            theta_deg = theta
        
        # Convert to dB
        pattern_e_db = 10 * np.log10(pattern_e + 1e-10)
        pattern_h_db = 10 * np.log10(pattern_h + 1e-10)
        
        # Normalize to peak
        pattern_e_db -= np.max(pattern_e_db)
        pattern_h_db -= np.max(pattern_h_db)
        
        if self.use_plotly:
            fig = go.Figure()
            
            fig.add_trace(go.Scatterpolar(
                r=pattern_e_db,
                theta=theta_deg,
                mode='lines',
                name='E-plane',
                line=dict(color='blue', width=2)
            ))
            
            fig.add_trace(go.Scatterpolar(
                r=pattern_h_db,
                theta=theta_deg,
                mode='lines',
                name='H-plane',
                line=dict(color='red', width=2)
            ))
            
            fig.update_layout(
                title=title,
                polar=dict(
                    radialaxis=dict(
                        title="Gain (dB)",
                        range=[-40, 0]
                    )
                ),
                showlegend=True
            )
            
            if save_path:
                fig.write_html(save_path)
            else:
                fig.show()
        
        else:
            fig, ax = plt.subplots(subplot_kw={'projection': 'polar'}, figsize=(10, 8))
            
            theta_rad = np.radians(theta_deg)
            ax.plot(theta_rad, pattern_e_db, 'b-', linewidth=2, label='E-plane')
            ax.plot(theta_rad, pattern_h_db, 'r-', linewidth=2, label='H-plane')
            
            ax.set_ylim([-40, 0])
            ax.set_ylabel('Gain (dB)', labelpad=30)
            ax.set_title(title, pad=20)
            ax.legend(loc='upper right')
            ax.grid(True)
            
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
            else:
                plt.show()
    
    def create_example_pattern(
        self,
        pattern_type: str = 'directive',
        beamwidth: float = 30.0
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Create example radiation pattern.
        
        Args:
            pattern_type: Type of pattern ('directive', 'omnidirectional', 'fan')
            beamwidth: Beamwidth in degrees
        
        Returns:
            Tuple of (theta, phi, pattern)
        """
        theta = np.linspace(0, np.pi, 100)
        phi = np.linspace(0, 2*np.pi, 100)
        THETA, PHI = np.meshgrid(theta, phi)
        
        bw_rad = np.radians(beamwidth)
        
        if pattern_type == 'directive':
            # Gaussian beam
            pattern = np.exp(-(THETA**2) / (2 * bw_rad**2))
        
        elif pattern_type == 'omnidirectional':
            # Omnidirectional in azimuth
            pattern = np.cos(THETA)**2
        
        elif pattern_type == 'fan':
            # Fan beam (narrow in one plane, wide in other)
            pattern = np.exp(-(THETA**2) / (2 * bw_rad**2)) * np.cos(PHI)**2
        
        else:
            # Isotropic
            pattern = np.ones_like(THETA)
        
        return theta, phi, pattern


def demo_pattern_plotting():
    """Demo function showing pattern plotting capabilities."""
    print("="*70)
    print("3D ANTENNA PATTERN PLOTTER DEMO")
    print("="*70)
    print()
    
    plotter = PatternPlotter3D(use_plotly=True)
    
    # Create example pattern
    print("Creating directive beam pattern (30° beamwidth)...")
    theta, phi, pattern = plotter.create_example_pattern('directive', beamwidth=30)
    
    # Plot 3D pattern
    print("Plotting 3D pattern...")
    plotter.plot_3d_pattern(
        theta, phi, pattern,
        title="Directive Antenna Pattern (30° beamwidth)",
        db_scale=True,
        save_path="pattern_3d.html"
    )
    
    # Create cut plane patterns
    print("Creating pattern cut planes...")
    theta_deg = np.linspace(-90, 90, 181)
    theta_rad = np.radians(theta_deg)
    
    # E-plane and H-plane cuts
    pattern_e = np.exp(-(theta_rad**2) / (2 * np.radians(30)**2))
    pattern_h = np.exp(-(theta_rad**2) / (2 * np.radians(40)**2))
    
    plotter.plot_cut_planes(
        theta_deg, pattern_e, pattern_h,
        title="E-plane and H-plane Cuts",
        save_path="pattern_cuts.html"
    )
    
    print()
    print("Plots saved:")
    print("  - pattern_3d.html")
    print("  - pattern_cuts.html")
    print()


if __name__ == '__main__':
    demo_pattern_plotting()
