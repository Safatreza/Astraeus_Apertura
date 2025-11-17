"""
Interactive web dashboard for antenna design visualization and exploration.

Provides a Plotly Dash-based web interface for:
- Design parameter exploration
- Simulation results visualization
- Performance comparison
- Real-time optimization monitoring
"""

import json
from typing import Dict, Any, List, Optional
from pathlib import Path
import numpy as np
import pandas as pd
from loguru import logger

try:
    import dash
    from dash import dcc, html, Input, Output, State, callback
    import plotly.graph_objects as go
    import plotly.express as px
    DASH_AVAILABLE = True
except ImportError:
    DASH_AVAILABLE = False
    logger.warning("Dash not available. Install with: pip install dash plotly")


class AntennaDashboard:
    """
    Interactive dashboard for antenna design exploration.
    
    Features:
    - Real-time parameter adjustment
    - Performance visualization
    - Design comparison
    - Optimization progress tracking
    """
    
    def __init__(
        self,
        title: str = "Astraeus Apertura - Antenna Design Dashboard",
        port: int = 8050,
        debug: bool = False
    ):
        """
        Initialize dashboard.
        
        Args:
            title: Dashboard title
            port: Port to run server on
            debug: Enable debug mode
        """
        if not DASH_AVAILABLE:
            raise ImportError("Dash not installed. Install with: pip install dash plotly")
        
        self.title = title
        self.port = port
        self.debug = debug
        
        # Initialize Dash app
        self.app = dash.Dash(__name__, title=title)
        
        # Data storage
        self.designs: List[Dict[str, Any]] = []
        self.simulation_results: List[Dict[str, Any]] = []
        
        # Build layout
        self._build_layout()
        self._setup_callbacks()
        
        logger.info(f"Dashboard initialized on port {port}")
    
    def _build_layout(self):
        """Build dashboard layout."""
        self.app.layout = html.Div([
            # Header
            html.Div([
                html.H1(self.title, style={'textAlign': 'center', 'color': '#2c3e50'}),
                html.Hr(),
            ]),
            
            # Main content
            html.Div([
                # Left panel: Parameters
                html.Div([
                    html.H3("Design Parameters"),
                    
                    html.Label("Frequency (GHz):"),
                    dcc.Slider(
                        id='freq-slider',
                        min=1, max=30, step=0.1, value=10.0,
                        marks={i: f'{i}' for i in range(1, 31, 5)},
                        tooltip={"placement": "bottom", "always_visible": True}
                    ),
                    
                    html.Label("Target Gain (dBi):"),
                    dcc.Slider(
                        id='gain-slider',
                        min=0, max=60, step=1, value=30,
                        marks={i: f'{i}' for i in range(0, 61, 10)},
                        tooltip={"placement": "bottom", "always_visible": True}
                    ),
                    
                    html.Label("Antenna Type:"),
                    dcc.Dropdown(
                        id='antenna-type-dropdown',
                        options=[
                            {'label': 'Horn Antenna', 'value': 'horn'},
                            {'label': 'Patch Antenna', 'value': 'patch'},
                            {'label': 'Parabolic Reflector', 'value': 'reflector'},
                            {'label': 'Phased Array', 'value': 'array'},
                        ],
                        value='horn'
                    ),
                    
                    html.Br(),
                    html.Button('Calculate Performance', id='calculate-btn', n_clicks=0,
                               style={'width': '100%', 'padding': '10px'}),
                    
                    html.Br(),
                    html.Br(),
                    html.Div(id='performance-output')
                    
                ], style={'width': '30%', 'display': 'inline-block', 'verticalAlign': 'top', 'padding': '20px'}),
                
                # Right panel: Visualizations
                html.Div([
                    html.H3("Visualization"),
                    
                    dcc.Tabs(id='viz-tabs', value='pattern', children=[
                        dcc.Tab(label='Radiation Pattern', value='pattern'),
                        dcc.Tab(label='Performance Metrics', value='metrics'),
                        dcc.Tab(label='Design Comparison', value='comparison'),
                        dcc.Tab(label='Parametric Sweep', value='sweep'),
                    ]),
                    
                    html.Div(id='viz-content', style={'padding': '20px'})
                    
                ], style={'width': '65%', 'display': 'inline-block', 'verticalAlign': 'top', 'padding': '20px'}),
            ]),
            
            # Footer
            html.Hr(),
            html.Div([
                html.P("Astraeus Apertura Multi-Agent Antenna Design System",
                      style={'textAlign': 'center', 'color': '#7f8c8d'})
            ])
        ], style={'fontFamily': 'Arial, sans-serif', 'margin': '20px'})
    
    def _setup_callbacks(self):
        """Setup dashboard callbacks."""
        
        @self.app.callback(
            Output('performance-output', 'children'),
            Input('calculate-btn', 'n_clicks'),
            State('freq-slider', 'value'),
            State('gain-slider', 'value'),
            State('antenna-type-dropdown', 'value')
        )
        def calculate_performance(n_clicks, freq, gain, antenna_type):
            if n_clicks == 0:
                return html.Div()
            
            # Calculate estimated performance
            performance = self._estimate_performance(freq, gain, antenna_type)
            
            return html.Div([
                html.H4("Estimated Performance:"),
                html.Table([
                    html.Tr([html.Td("Gain:"), html.Td(f"{performance['gain']:.1f} dBi")]),
                    html.Tr([html.Td("Beamwidth:"), html.Td(f"{performance['beamwidth']:.1f}°")]),
                    html.Tr([html.Td("VSWR:"), html.Td(f"{performance['vswr']:.2f}")]),
                    html.Tr([html.Td("Efficiency:"), html.Td(f"{performance['efficiency']:.1%}")]),
                    html.Tr([html.Td("Bandwidth:"), html.Td(f"{performance['bandwidth']:.0f} MHz")]),
                ], style={'width': '100%', 'borderSpacing': '10px'})
            ], style={'backgroundColor': '#ecf0f1', 'padding': '15px', 'borderRadius': '5px'})
        
        @self.app.callback(
            Output('viz-content', 'children'),
            Input('viz-tabs', 'value'),
            State('freq-slider', 'value'),
            State('gain-slider', 'value'),
            State('antenna-type-dropdown', 'value')
        )
        def update_visualization(tab, freq, gain, antenna_type):
            if tab == 'pattern':
                return self._create_radiation_pattern(freq, gain, antenna_type)
            elif tab == 'metrics':
                return self._create_metrics_chart(freq, gain, antenna_type)
            elif tab == 'comparison':
                return self._create_comparison_chart()
            elif tab == 'sweep':
                return self._create_parametric_sweep_viz()
            
            return html.Div("Select a tab")
    
    def _estimate_performance(self, freq_ghz: float, gain_dbi: float, antenna_type: str) -> Dict[str, float]:
        """Estimate antenna performance (simplified analytical model)."""
        c = 3e8  # Speed of light
        wavelength_m = c / (freq_ghz * 1e9)
        
        # Beamwidth from gain (approximation)
        beamwidth = 70 / (10 ** (gain_dbi / 20))
        
        # VSWR (better at lower frequencies, varies by type)
        vswr_base = {'horn': 1.3, 'patch': 1.5, 'reflector': 1.2, 'array': 1.4}
        vswr = vswr_base.get(antenna_type, 1.5) * (1 + 0.01 * freq_ghz)
        
        # Efficiency (varies by type)
        eff_base = {'horn': 0.85, 'patch': 0.75, 'reflector': 0.65, 'array': 0.70}
        efficiency = eff_base.get(antenna_type, 0.75)
        
        # Bandwidth (percentage)
        bw_pct = {'horn': 0.20, 'patch': 0.05, 'reflector': 0.10, 'array': 0.15}
        bandwidth = freq_ghz * 1000 * bw_pct.get(antenna_type, 0.10)  # MHz
        
        return {
            'gain': gain_dbi,
            'beamwidth': beamwidth,
            'vswr': vswr,
            'efficiency': efficiency,
            'bandwidth': bandwidth
        }
    
    def _create_radiation_pattern(self, freq, gain, antenna_type):
        """Create 3D radiation pattern visualization."""
        # Generate pattern data
        theta = np.linspace(0, np.pi, 50)
        phi = np.linspace(0, 2*np.pi, 50)
        THETA, PHI = np.meshgrid(theta, phi)
        
        # Simple pattern model based on gain
        # Higher gain = narrower beam
        beamwidth_rad = np.radians(70 / (10 ** (gain / 20)))
        
        # Gaussian beam pattern
        pattern = np.exp(-(THETA**2) / (2 * beamwidth_rad**2))
        pattern_db = 10 * np.log10(pattern + 1e-10)  # Convert to dB
        
        # Convert to Cartesian for 3D plot
        X = pattern * np.sin(THETA) * np.cos(PHI)
        Y = pattern * np.sin(THETA) * np.sin(PHI)
        Z = pattern * np.cos(THETA)
        
        fig = go.Figure(data=[go.Surface(
            x=X, y=Y, z=Z,
            surfacecolor=pattern_db,
            colorscale='Viridis',
            colorbar=dict(title="Gain (dB)")
        )])
        
        fig.update_layout(
            title=f"3D Radiation Pattern - {antenna_type.title()}",
            scene=dict(
                xaxis_title="X",
                yaxis_title="Y",
                zaxis_title="Z",
                aspectmode='cube'
            ),
            height=600
        )
        
        return dcc.Graph(figure=fig)
    
    def _create_metrics_chart(self, freq, gain, antenna_type):
        """Create performance metrics chart."""
        perf = self._estimate_performance(freq, gain, antenna_type)
        
        # Create bar chart
        metrics = ['Gain', 'VSWR', 'Efficiency', 'Bandwidth']
        values = [
            perf['gain'] / 60 * 100,  # Normalize to 0-100
            (3 - perf['vswr']) / 2 * 100,  # Normalize (lower is better)
            perf['efficiency'] * 100,
            min(perf['bandwidth'] / 500 * 100, 100)  # Normalize
        ]
        
        fig = go.Figure(data=[
            go.Bar(x=metrics, y=values, marker_color=['#3498db', '#e74c3c', '#2ecc71', '#f39c12'])
        ])
        
        fig.update_layout(
            title="Performance Metrics (Normalized)",
            yaxis_title="Score (0-100)",
            height=500
        )
        
        return dcc.Graph(figure=fig)
    
    def _create_comparison_chart(self):
        """Create antenna type comparison chart."""
        types = ['Horn', 'Patch', 'Reflector', 'Array']
        gain_scores = [75, 60, 90, 85]
        bw_scores = [80, 40, 65, 70]
        cost_scores = [70, 90, 50, 40]
        complexity_scores = [80, 95, 60, 30]
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatterpolar(
            r=gain_scores, theta=types, fill='toself', name='Gain'
        ))
        fig.add_trace(go.Scatterpolar(
            r=bw_scores, theta=types, fill='toself', name='Bandwidth'
        ))
        fig.add_trace(go.Scatterpolar(
            r=cost_scores, theta=types, fill='toself', name='Cost-Effectiveness'
        ))
        fig.add_trace(go.Scatterpolar(
            r=complexity_scores, theta=types, fill='toself', name='Simplicity'
        ))
        
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            title="Antenna Type Comparison",
            height=600
        )
        
        return dcc.Graph(figure=fig)
    
    def _create_parametric_sweep_viz(self):
        """Create parametric sweep visualization."""
        # Generate sweep data
        freqs = np.linspace(5, 15, 20)
        gains = np.linspace(20, 40, 20)
        
        FREQ, GAIN = np.meshgrid(freqs, gains)
        
        # Calculate efficiency as a function of freq and gain
        # Higher gain at higher freq requires larger aperture = potential lower efficiency
        EFFICIENCY = 0.85 - 0.01 * (GAIN - 20) - 0.005 * (FREQ - 10)
        EFFICIENCY = np.clip(EFFICIENCY, 0.5, 0.9)
        
        fig = go.Figure(data=[go.Surface(
            x=FREQ, y=GAIN, z=EFFICIENCY,
            colorscale='RdYlGn',
            colorbar=dict(title="Efficiency")
        )])
        
        fig.update_layout(
            title="Design Space: Efficiency vs Frequency & Gain",
            scene=dict(
                xaxis_title="Frequency (GHz)",
                yaxis_title="Gain (dBi)",
                zaxis_title="Efficiency",
            ),
            height=600
        )
        
        return dcc.Graph(figure=fig)
    
    def load_simulation_results(self, results_file: str):
        """
        Load simulation results from file.
        
        Args:
            results_file: Path to results JSON file
        """
        with open(results_file, 'r') as f:
            self.simulation_results = json.load(f)
        
        logger.info(f"Loaded {len(self.simulation_results)} simulation results")
    
    def run(self, host: str = '127.0.0.1'):
        """
        Run the dashboard server.
        
        Args:
            host: Host address to run on
        """
        logger.info(f"Starting dashboard at http://{host}:{self.port}")
        print(f"\n{'='*70}")
        print(f"Astraeus Apertura Dashboard")
        print(f"{'='*70}")
        print(f"\nDashboard running at: http://{host}:{self.port}")
        print(f"Press Ctrl+C to stop\n")
        
        self.app.run_server(host=host, port=self.port, debug=self.debug)


def create_dashboard(
    title: str = "Antenna Design Dashboard",
    port: int = 8050,
    debug: bool = False
) -> AntennaDashboard:
    """
    Factory function to create dashboard.
    
    Args:
        title: Dashboard title
        port: Port number
        debug: Debug mode
    
    Returns:
        AntennaDashboard instance
    """
    return AntennaDashboard(title=title, port=port, debug=debug)
