#!/usr/bin/env python
"""
Simple Antenna Design Example using Astraeus Apertura

This example demonstrates a complete end-to-end antenna design workflow
for a SAR (Synthetic Aperture Radar) mission.

The multi-agent system will:
1. Analyze requirements
2. Select optimal architecture
3. Generate geometry
4. Select materials
5. Run simulations
6. Optimize design
7. Validate results
8. Generate report
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger

# Import Astraeus components
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
from astraeus.agents import (
    RequirementsAnalystAgent,
    ArchitectureAgent,
    GeometryGeneratorAgent,
    MaterialSelectorAgent,
    SimulationAgent,
    PerformanceOptimizerAgent,
    ValidationAgent,
    SupervisorAgent,
)
from astraeus.visualization import ReportGenerator


def main():
    """Run simple antenna design workflow."""

    logger.info("=" * 80)
    logger.info("ASTRAEUS APERTURA - AUTONOMOUS ANTENNA DESIGN SYSTEM")
    logger.info("=" * 80)
    logger.info("")

    # ========================================================================
    # STEP 1: Define Mission Requirements
    # ========================================================================
    logger.info("Step 1: Defining Mission Requirements")
    logger.info("-" * 80)

    requirements = MissionRequirements(
        mission_name="X-Band SAR Antenna for Earth Observation",
        mission_type=RadarMode.SAR,

        # Frequency specification
        frequency=FrequencySpec(
            center_frequency_ghz=10.0,
            bandwidth_mhz=200.0,
            frequency_band="X",
            harmonic_suppression_dbc=40.0
        ),

        # Radiation pattern requirements
        radiation_pattern=RadiationPattern(
            gain_dbi=35.0,
            beamwidth_azimuth_deg=3.0,
            beamwidth_elevation_deg=3.0,
            sidelobe_level_db=-25.0,
            cross_pol_discrimination_db=25.0,
            beam_steering_range_deg=(0, 0)  # Broadside, no steering
        ),

        # Polarization
        polarization=Polarization.LINEAR_HORIZONTAL,

        # Physical constraints
        physical=PhysicalConstraints(
            max_mass_kg=5.0,
            max_length_m=1.0,
            max_width_m=1.0,
            max_height_m=0.3,
            deployable=False
        ),

        # Environmental specification (space mission)
        environmental=EnvironmentalSpec(
            operating_temp_min_c=-40.0,
            operating_temp_max_c=85.0,
            survival_temp_min_c=-55.0,
            survival_temp_max_c=125.0,
            vacuum_exposure=True,
            atomic_oxygen_exposure=True
        ),

        # Performance requirements
        radar_range_km=100.0,
        angular_resolution_deg=0.5,

        # Metadata
        metadata={
            "mission_altitude_km": 600.0,
            "mission_lifetime_years": 5.0,
            "launch_vehicle": "Falcon 9",
        }
    )

    logger.info(f"Mission: {requirements.mission_name}")
    logger.info(f"Frequency: {requirements.frequency.center_frequency_ghz} GHz")
    logger.info(f"Target Gain: {requirements.radiation_pattern.gain_dbi} dBi")
    logger.info(f"Beamwidth: {requirements.radiation_pattern.beamwidth_azimuth_deg}°")
    logger.info(f"Max Mass: {requirements.physical.max_mass_kg} kg")
    logger.info("")

    # ========================================================================
    # STEP 2: Initialize Workflow and Register Agents
    # ========================================================================
    logger.info("Step 2: Initializing Multi-Agent System")
    logger.info("-" * 80)

    # Create workflow with configuration
    workflow = DesignWorkflow(
        max_iterations=20,
        convergence_threshold=0.01,  # 1% improvement threshold
        enable_human_review=False     # Automated run (set True for interactive)
    )

    # Register all specialized agents
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
        logger.info(f"✓ Registered: {agent.agent_type}")

    logger.info(f"\nTotal agents registered: {len(agents)}")
    logger.info("")

    # ========================================================================
    # STEP 3: Execute Design Workflow
    # ========================================================================
    logger.info("Step 3: Executing Autonomous Design Workflow")
    logger.info("-" * 80)
    logger.info("The multi-agent system will now autonomously:")
    logger.info("  1. Analyze and validate requirements")
    logger.info("  2. Select optimal antenna architecture")
    logger.info("  3. Generate parametric geometry")
    logger.info("  4. Select appropriate materials")
    logger.info("  5. Run electromagnetic simulations")
    logger.info("  6. Optimize design iteratively")
    logger.info("  7. Validate against requirements")
    logger.info("  8. Generate final design package")
    logger.info("")

    try:
        # Execute the workflow
        result = workflow.execute(requirements)

        logger.info("=" * 80)
        logger.info("WORKFLOW COMPLETED SUCCESSFULLY!")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"Workflow failed: {e}", exc_info=True)
        logger.error("=" * 80)
        logger.error("WORKFLOW FAILED")
        logger.error("=" * 80)
        return 1

    # ========================================================================
    # STEP 4: Review Results
    # ========================================================================
    logger.info("")
    logger.info("Step 4: Reviewing Results")
    logger.info("-" * 80)

    logger.info(f"Workflow ID: {result['workflow_id']}")
    logger.info(f"Termination: {result['termination_condition']}")
    logger.info(f"Reason: {result['termination_reason']}")
    logger.info(f"Iterations: {result['iterations']}")
    logger.info(f"Duration: {result['duration_seconds']:.1f} seconds")
    logger.info("")

    # Extract final design
    final_design = result.get('final_design', {})

    logger.info("Architecture Selected:")
    architecture = final_design.get('architecture', {})
    logger.info(f"  Type: {architecture.get('antenna_type', 'N/A')}")
    logger.info(f"  Configuration: {architecture.get('configuration', 'N/A')}")
    logger.info("")

    logger.info("Geometry Generated:")
    geometry = final_design.get('geometry', {})
    logger.info(f"  Dimensions: {geometry.get('dimensions', 'N/A')}")
    logger.info(f"  Elements: {geometry.get('num_elements', 'N/A')}")
    logger.info("")

    logger.info("Materials Selected:")
    materials = final_design.get('materials', {})
    for component, material in materials.items():
        logger.info(f"  {component}: {material}")
    logger.info("")

    logger.info("Performance Achieved:")
    sim_results = final_design.get('simulation_results', {})
    perf_metrics = sim_results.get('performance_metrics', {})
    logger.info(f"  Gain: {perf_metrics.get('gain_dbi', 'N/A')} dBi")
    logger.info(f"  Efficiency: {perf_metrics.get('efficiency_percent', 'N/A')}%")
    logger.info(f"  VSWR: {perf_metrics.get('vswr', 'N/A')}")
    logger.info(f"  Beamwidth: {perf_metrics.get('beamwidth_deg', 'N/A')}°")
    logger.info("")

    logger.info("Validation Results:")
    validation = final_design.get('validation_results', {})
    if validation.get('requirements_satisfied'):
        logger.info("  ✓ All requirements satisfied")
    else:
        logger.info("  ✗ Some requirements not met")
        gaps = validation.get('gaps', [])
        for gap in gaps:
            logger.info(f"    - {gap}")
    logger.info("")

    # Communication statistics
    logger.info("Communication Statistics:")
    comm_stats = result.get('communication_stats', {})
    logger.info(f"  Total Messages: {comm_stats.get('total_messages', 0)}")
    logger.info(f"  Active Agents: {comm_stats.get('active_agents', 0)}")
    logger.info(f"  Conversations: {comm_stats.get('active_conversations', 0)}")
    logger.info("")

    # ========================================================================
    # STEP 5: Generate Reports
    # ========================================================================
    logger.info("Step 5: Generating Reports")
    logger.info("-" * 80)

    # Create output directory
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    # Generate reports in different formats
    report_gen = ReportGenerator(output_dir=str(output_dir))

    # Markdown report
    md_report = report_gen.generate_design_report(result, format="markdown")
    logger.info(f"✓ Markdown report: {md_report}")

    # HTML report
    html_report = report_gen.generate_design_report(result, format="html")
    logger.info(f"✓ HTML report: {html_report}")

    logger.info("")

    # ========================================================================
    # STEP 6: Summary
    # ========================================================================
    logger.info("=" * 80)
    logger.info("DESIGN SUMMARY")
    logger.info("=" * 80)
    logger.info("")
    logger.info(f"Mission: {requirements.mission_name}")
    logger.info(f"Status: {result['termination_condition']}")
    logger.info(f"Iterations: {result['iterations']}")
    logger.info(f"Reports: {output_dir.absolute()}")
    logger.info("")
    logger.info("Next Steps:")
    logger.info("  1. Review detailed reports in output/ directory")
    logger.info("  2. Validate design with detailed EM simulation")
    logger.info("  3. Fabricate prototype for testing")
    logger.info("  4. Integrate with spacecraft platform")
    logger.info("")
    logger.info("=" * 80)
    logger.info("Thank you for using Astraeus Apertura!")
    logger.info("=" * 80)

    return 0


if __name__ == "__main__":
    # Configure logging
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )

    # Run example
    exit_code = main()
    sys.exit(exit_code)
