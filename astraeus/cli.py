"""Command-line interface for Astraeus Apertura."""

import argparse
import sys
from pathlib import Path
import json
import yaml

from loguru import logger

from astraeus.core.workflow import DesignWorkflow
from astraeus.data.parameters import MissionRequirements, FrequencySpec, RadiationPattern, Polarization, RadarMode
from astraeus.agents import *
from astraeus.visualization import ReportGenerator


def load_requirements_from_file(file_path: str) -> MissionRequirements:
    """
    Load requirements from YAML or JSON file.

    Args:
        file_path: Path to requirements file

    Returns:
        MissionRequirements object
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Requirements file not found: {file_path}")

    # Load file
    if path.suffix in ['.yaml', '.yml']:
        with open(path) as f:
            data = yaml.safe_load(f)
    elif path.suffix == '.json':
        with open(path) as f:
            data = json.load(f)
    else:
        raise ValueError(f"Unsupported file format: {path.suffix}. Use .yaml, .yml, or .json")

    # Parse requirements
    freq_spec = FrequencySpec(
        center_frequency_ghz=data['frequency']['center_frequency_ghz'],
        bandwidth_mhz=data['frequency'].get('bandwidth_mhz'),
        frequency_band=data['frequency'].get('frequency_band'),
    )

    rad_pattern = RadiationPattern(
        gain_dbi=data['radiation_pattern']['gain_dbi'],
        beamwidth_azimuth_deg=data['radiation_pattern'].get('beamwidth_azimuth_deg'),
        beamwidth_elevation_deg=data['radiation_pattern'].get('beamwidth_elevation_deg'),
        sidelobe_level_db=data['radiation_pattern'].get('sidelobe_level_db', -20.0),
    )

    polarization = Polarization[data['polarization'].upper()]
    mission_type = RadarMode[data['mission_type'].upper()]

    requirements = MissionRequirements(
        mission_name=data['mission_name'],
        mission_type=mission_type,
        frequency=freq_spec,
        radiation_pattern=rad_pattern,
        polarization=polarization,
    )

    return requirements


def cmd_design(args):
    """Execute design workflow."""
    logger.info("Astraeus Apertura - Autonomous Antenna Design")
    logger.info("=" * 80)

    # Load requirements
    if args.requirements:
        logger.info(f"Loading requirements from: {args.requirements}")
        requirements = load_requirements_from_file(args.requirements)
    else:
        logger.error("Requirements file is required. Use --requirements <file.yaml>")
        return 1

    # Create workflow
    workflow = DesignWorkflow(
        max_iterations=args.max_iterations,
        convergence_threshold=args.convergence_threshold,
        enable_human_review=args.human_review,
    )

    # Register agents
    logger.info("Registering agents...")
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

    logger.info(f"Registered {len(agents)} agents")

    # Execute workflow
    logger.info("Starting design workflow...")
    try:
        result = workflow.execute(requirements)
        logger.info("✓ Workflow completed successfully")
    except Exception as e:
        logger.error(f"✗ Workflow failed: {e}")
        return 1

    # Generate reports
    logger.info(f"Generating reports in: {args.output}")
    report_gen = ReportGenerator(output_dir=args.output)

    if 'markdown' in args.formats:
        md_path = report_gen.generate_design_report(result, format='markdown')
        logger.info(f"✓ Markdown report: {md_path}")

    if 'html' in args.formats:
        html_path = report_gen.generate_design_report(result, format='html')
        logger.info(f"✓ HTML report: {html_path}")

    logger.info("=" * 80)
    logger.info(f"Design completed: {result['termination_condition']}")
    logger.info(f"Iterations: {result['iterations']}")
    logger.info(f"Reports saved to: {args.output}")

    return 0


def cmd_validate(args):
    """Validate requirements file."""
    logger.info("Validating requirements file...")

    try:
        requirements = load_requirements_from_file(args.requirements)
        logger.info("✓ Requirements file is valid")
        logger.info(f"  Mission: {requirements.mission_name}")
        logger.info(f"  Frequency: {requirements.frequency.center_frequency_ghz} GHz")
        logger.info(f"  Gain: {requirements.radiation_pattern.gain_dbi} dBi")
        return 0
    except Exception as e:
        logger.error(f"✗ Validation failed: {e}")
        return 1


def cmd_materials(args):
    """List available materials."""
    from astraeus.data.materials_database import MaterialDatabase

    db = MaterialDatabase()
    materials = db.get_all_materials()

    logger.info(f"Materials Database: {len(materials)} materials")
    logger.info("=" * 80)

    if args.category:
        materials = [m for m in materials if m.category == args.category]
        logger.info(f"Filtering by category: {args.category}")

    for mat in materials:
        logger.info(f"\n{mat.name}")
        logger.info(f"  Category: {mat.category}")
        if mat.dielectric:
            logger.info(f"  εr: {mat.dielectric.relative_permittivity}, tan δ: {mat.dielectric.loss_tangent}")
        if mat.manufacturer:
            logger.info(f"  Manufacturer: {mat.manufacturer}")
        logger.info(f"  Availability: {mat.availability}")

    return 0


def cmd_patterns(args):
    """List design patterns."""
    from astraeus.data.knowledge_base import KnowledgeBase

    kb = KnowledgeBase()
    patterns = kb.get_all_patterns()

    logger.info(f"Design Patterns: {len(patterns)} patterns")
    logger.info("=" * 80)

    for pattern in patterns:
        logger.info(f"\n{pattern.name}")
        logger.info(f"  Type: {pattern.antenna_type.value}")
        logger.info(f"  Frequency: {pattern.applicable_frequencies_ghz[0]}-{pattern.applicable_frequencies_ghz[1]} GHz")
        logger.info(f"  Typical Gain: {pattern.typical_gain_dbi} dBi")
        logger.info(f"  Confidence: {pattern.confidence_score * 100:.0f}%")
        logger.info(f"  Heritage: {', '.join(pattern.heritage_missions[:3])}")

    return 0


def cmd_template(args):
    """Generate requirements template."""
    template = {
        'mission_name': 'My Antenna Mission',
        'mission_type': 'sar',  # sar, isar, weather, altimeter, communication
        'frequency': {
            'center_frequency_ghz': 10.0,
            'bandwidth_mhz': 200.0,
            'frequency_band': 'X'
        },
        'radiation_pattern': {
            'gain_dbi': 35.0,
            'beamwidth_azimuth_deg': 3.0,
            'beamwidth_elevation_deg': 3.0,
            'sidelobe_level_db': -25.0
        },
        'polarization': 'linear_horizontal',  # linear_horizontal, circular_right, etc.
        'physical_constraints': {
            'max_mass_kg': 5.0,
            'max_length_m': 1.0,
            'max_width_m': 1.0,
            'max_height_m': 0.3
        }
    }

    output_file = args.output or 'requirements_template.yaml'

    with open(output_file, 'w') as f:
        yaml.dump(template, f, default_flow_style=False, sort_keys=False)

    logger.info(f"✓ Template saved to: {output_file}")
    logger.info("Edit this file with your requirements and use with: astraeus design --requirements <file>")

    return 0


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Astraeus Apertura - Multi-Agent Autonomous Antenna Design System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate requirements template
  astraeus template -o my_requirements.yaml

  # Validate requirements
  astraeus validate --requirements my_requirements.yaml

  # Run design workflow
  astraeus design --requirements my_requirements.yaml --output results/

  # List available materials
  astraeus materials --category dielectric_substrate

  # List design patterns
  astraeus patterns
        """
    )

    parser.add_argument('--version', action='version', version='Astraeus Apertura v0.1.0')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose logging')

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Design command
    design_parser = subparsers.add_parser('design', help='Run antenna design workflow')
    design_parser.add_argument('--requirements', '-r', required=True, help='Requirements file (YAML/JSON)')
    design_parser.add_argument('--output', '-o', default='output', help='Output directory')
    design_parser.add_argument('--max-iterations', type=int, default=20, help='Maximum optimization iterations')
    design_parser.add_argument('--convergence-threshold', type=float, default=0.01, help='Convergence threshold')
    design_parser.add_argument('--human-review', action='store_true', help='Enable human review checkpoints')
    design_parser.add_argument('--formats', nargs='+', default=['markdown', 'html'],
                               choices=['markdown', 'html'], help='Report formats')
    design_parser.set_defaults(func=cmd_design)

    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate requirements file')
    validate_parser.add_argument('--requirements', '-r', required=True, help='Requirements file to validate')
    validate_parser.set_defaults(func=cmd_validate)

    # Materials command
    materials_parser = subparsers.add_parser('materials', help='List available materials')
    materials_parser.add_argument('--category', '-c', help='Filter by category')
    materials_parser.set_defaults(func=cmd_materials)

    # Patterns command
    patterns_parser = subparsers.add_parser('patterns', help='List design patterns')
    patterns_parser.set_defaults(func=cmd_patterns)

    # Template command
    template_parser = subparsers.add_parser('template', help='Generate requirements template')
    template_parser.add_argument('--output', '-o', help='Output file path')
    template_parser.set_defaults(func=cmd_template)

    # Parse arguments
    args = parser.parse_args()

    # Configure logging
    logger.remove()
    log_level = "DEBUG" if args.verbose else "INFO"
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level=log_level
    )

    # Execute command
    if args.command:
        return args.func(args)
    else:
        parser.print_help()
        return 0


if __name__ == '__main__':
    sys.exit(main())
