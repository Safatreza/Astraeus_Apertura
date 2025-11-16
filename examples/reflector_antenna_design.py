#!/usr/bin/env python
"""
Reflector Antenna Design Example

This example demonstrates designing a large reflector antenna
for deep space communication with high gain and efficiency.
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
    EnvironmentalSpec,
)
from astraeus.agents import *
from astraeus.visualization import ReportGenerator


def main():
    """Design a reflector antenna for deep space communication."""

    logger.info("=" * 80)
    logger.info("REFLECTOR ANTENNA DESIGN FOR DEEP SPACE COMMUNICATION")
    logger.info("=" * 80)

    # Define requirements for X/Ka dual-band reflector
    requirements = MissionRequirements(
        mission_name="Dual-Band Deep Space Reflector",
        mission_type=RadarMode.COMMUNICATION,

        # Primary frequency at X-band (Ka-band secondary)
        frequency=FrequencySpec(
            center_frequency_ghz=8.4,
            bandwidth_mhz=150.0,
            frequency_band="X",
        ),

        # Very high gain for long-range communication
        radiation_pattern=RadiationPattern(
            gain_dbi=45.0,  # High gain for deep space
            beamwidth_azimuth_deg=1.5,
            beamwidth_elevation_deg=1.5,
            sidelobe_level_db=-30.0,  # Strict sidelobe requirement
            cross_pol_discrimination_db=35.0,
            front_to_back_ratio_db=50.0,
        ),

        # Circular polarization to handle Faraday rotation
        polarization=Polarization.CIRCULAR_RIGHT,

        # Ground-based, size not critical but quality is
        physical=PhysicalConstraints(
            max_mass_kg=50.0,  # Can be heavier for ground station
            max_length_m=3.0,  # ~3m diameter reflector
            deployable=False
        ),

        # Ground environment
        environmental=EnvironmentalSpec(
            operating_temp_min_c=-20.0,
            operating_temp_max_c=50.0,
            survival_temp_min_c=-40.0,
            survival_temp_max_c=70.0,
            vacuum_exposure=False,
        ),

        metadata={
            "reflector_type": "cassegrain",  # Dual-reflector for low noise
            "surface_accuracy_rms_mm": 0.5,  # Very tight surface tolerance
            "feed_type": "corrugated_horn",
            "application": "deep_space_network",
        }
    )

    logger.info(f"\nMission: {requirements.mission_name}")
    logger.info(f"Frequency: {requirements.frequency.center_frequency_ghz} GHz")
    logger.info(f"Target Gain: {requirements.radiation_pattern.gain_dbi} dBi")
    logger.info(f"Beamwidth: {requirements.radiation_pattern.beamwidth_azimuth_deg}°")
    logger.info(f"Sidelobe Level: {requirements.radiation_pattern.sidelobe_level_db} dB")
    logger.info("")

    # Create workflow
    workflow = DesignWorkflow(
        max_iterations=25,
        convergence_threshold=0.002,
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
    logger.info("Starting reflector antenna design workflow...")
    logger.info("-" * 80)

    result = workflow.execute(requirements)

    # Display results
    logger.info("\n" + "=" * 80)
    logger.info("DESIGN RESULTS")
    logger.info("=" * 80)

    final_design = result['final_design']

    logger.info(f"\nArchitecture: {final_design.get('architecture', {}).get('antenna_type', 'N/A')}")
    logger.info(f"Reflector Configuration:")

    geometry = final_design.get('geometry', {})
    logger.info(f"  Main Reflector Diameter: {geometry.get('main_diameter_m', 'N/A')} m")
    logger.info(f"  Focal Length: {geometry.get('focal_length_m', 'N/A')} m")
    logger.info(f"  F/D Ratio: {geometry.get('f_over_d', 'N/A')}")
    logger.info(f"  Subreflector Diameter: {geometry.get('sub_diameter_m', 'N/A')} m")
    logger.info(f"  Feed Type: {geometry.get('feed_type', 'N/A')}")

    logger.info(f"\nMaterials:")
    for component, material in final_design.get('materials', {}).items():
        logger.info(f"  {component}: {material}")

    logger.info(f"\nPerformance:")
    perf = final_design.get('simulation_results', {}).get('performance_metrics', {})
    logger.info(f"  Realized Gain: {perf.get('gain_dbi', 'N/A')} dBi")
    logger.info(f"  Aperture Efficiency: {perf.get('aperture_efficiency_percent', 'N/A')}%")
    logger.info(f"  VSWR: {perf.get('vswr', 'N/A')}")
    logger.info(f"  Beamwidth: {perf.get('beamwidth_deg', 'N/A')}°")
    logger.info(f"  Sidelobe Level: {perf.get('sidelobe_level_db', 'N/A')} dB")

    logger.info(f"\nWorkflow Statistics:")
    logger.info(f"  Iterations: {result['iterations']}")
    logger.info(f"  Duration: {result.get('duration_seconds', 0):.1f}s")
    logger.info(f"  Termination: {result['termination_condition']}")

    # Generate report
    output_dir = Path("output/reflector")
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
