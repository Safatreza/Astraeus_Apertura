#!/usr/bin/env python
"""
Phased Array Antenna Design Example

This example demonstrates designing a phased array antenna for
communication satellite applications with beam steering capability.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from astraeus.core.workflow import DesignWorkflow
from astraeus.data.parameters import (
    MissionRequirements,
    FrequencySpec,
    RadiationPattern,
    Polarization,
    RadarMode,
    PhysicalConstraints,
)
from astraeus.agents import *
from astraeus.visualization import ReportGenerator


def main():
    """Design a phased array antenna for communication satellite."""

    logger.info("=" * 80)
    logger.info("PHASED ARRAY ANTENNA DESIGN FOR COMMUNICATION SATELLITE")
    logger.info("=" * 80)

    # Define requirements for Ka-band communication array
    requirements = MissionRequirements(
        mission_name="Ka-Band Phased Array for LEO Comms",
        mission_type=RadarMode.COMMUNICATION,

        # Ka-band downlink
        frequency=FrequencySpec(
            center_frequency_ghz=20.0,
            bandwidth_mhz=500.0,
            frequency_band="Ka",
            harmonic_suppression_dbc=50.0
        ),

        # High gain with beam steering
        radiation_pattern=RadiationPattern(
            gain_dbi=32.0,
            beamwidth_azimuth_deg=5.0,
            beamwidth_elevation_deg=5.0,
            sidelobe_level_db=-20.0,
            cross_pol_discrimination_db=30.0,
            beam_steering_range_deg=(45, 45)  # ±45° steering
        ),

        # Circular polarization for satellite link
        polarization=Polarization.CIRCULAR_RIGHT,

        # Lightweight for space application
        physical=PhysicalConstraints(
            max_mass_kg=3.0,
            max_length_m=0.5,
            max_width_m=0.5,
            max_height_m=0.1,
            deployable=False
        ),

        metadata={
            "array_type": "phased_array",
            "beamforming": "digital",
            "num_beams": 4,
            "data_rate_mbps": 1000,
        }
    )

    logger.info(f"\nMission: {requirements.mission_name}")
    logger.info(f"Frequency: {requirements.frequency.center_frequency_ghz} GHz ({requirements.frequency.frequency_band}-band)")
    logger.info(f"Gain: {requirements.radiation_pattern.gain_dbi} dBi")
    logger.info(f"Beam Steering: ±{requirements.radiation_pattern.beam_steering_range_deg[0]}°")
    logger.info(f"Polarization: {requirements.polarization.value}")
    logger.info("")

    # Create and configure workflow
    workflow = DesignWorkflow(
        max_iterations=30,
        convergence_threshold=0.005,
        enable_human_review=False
    )

    # Register agents
    agents = [
        RequirementsAnalystAgent(),
        ArchitectureAgent(),
        GeometryGeneratorAgent(),
        MaterialSelectorAgent(),
        SimulationAgent(),
        PerformanceOptimizerAgent(),
        ValidationAgent(),
        SupervisorAgent(),
    ]

    for agent in agents:
        workflow.register_agent(agent)

    logger.info(f"Registered {len(agents)} agents\n")

    # Execute workflow
    logger.info("Starting phased array design workflow...")
    logger.info("-" * 80)

    result = workflow.execute(requirements)

    # Display results
    logger.info("\n" + "=" * 80)
    logger.info("DESIGN RESULTS")
    logger.info("=" * 80)

    final_design = result['final_design']

    logger.info(f"\nArchitecture: {final_design.get('architecture', {}).get('antenna_type', 'N/A')}")
    logger.info(f"Array Configuration:")

    geometry = final_design.get('geometry', {})
    logger.info(f"  Elements: {geometry.get('num_elements', 'N/A')}")
    logger.info(f"  Array Size: {geometry.get('array_size', 'N/A')}")
    logger.info(f"  Element Spacing: {geometry.get('element_spacing', 'N/A')} λ")

    logger.info(f"\nMaterials:")
    for component, material in final_design.get('materials', {}).items():
        logger.info(f"  {component}: {material}")

    logger.info(f"\nPerformance:")
    perf = final_design.get('simulation_results', {}).get('performance_metrics', {})
    logger.info(f"  Realized Gain: {perf.get('gain_dbi', 'N/A')} dBi")
    logger.info(f"  Efficiency: {perf.get('efficiency_percent', 'N/A')}%")
    logger.info(f"  VSWR: {perf.get('vswr', 'N/A')}")
    logger.info(f"  Scan Range: {perf.get('scan_range_deg', 'N/A')}°")

    logger.info(f"\nWorkflow Statistics:")
    logger.info(f"  Iterations: {result['iterations']}")
    logger.info(f"  Duration: {result.get('duration_seconds', 0):.1f}s")
    logger.info(f"  Termination: {result['termination_condition']}")

    # Generate report
    output_dir = Path("output/phased_array")
    output_dir.mkdir(parents=True, exist_ok=True)

    report_gen = ReportGenerator(output_dir=str(output_dir))
    md_report = report_gen.generate_design_report(result, format="markdown")

    logger.info(f"\n✓ Report saved: {md_report}")
    logger.info("=" * 80)

    return 0


if __name__ == "__main__":
    logger.remove()
    logger.add(sys.stderr, format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>", level="INFO")
    sys.exit(main())
