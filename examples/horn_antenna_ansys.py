#!/usr/bin/env python
"""
Horn Antenna Design with ANSYS HFSS Integration

This example demonstrates:
1. Parametric horn antenna design
2. ANSYS HFSS simulation integration
3. Result extraction and validation
4. Database storage of results

Requirements:
- ANSYS Electronics Desktop installed
- PyAEDT: pip install pyaedt
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
import numpy as np

from astraeus.simulation.backends import AnsysHFSSSimulator
from astraeus.data.simulation_database import SimulationDatabase
from astraeus.geometry import CADExporter
from astraeus.utils.antenna_math import AntennaMath


def design_horn_antenna(frequency_ghz: float = 10.0) -> dict:
    """
    Design pyramidal horn antenna for given frequency.

    Args:
        frequency_ghz: Operating frequency in GHz

    Returns:
        Horn geometry parameters
    """
    logger.info(f"Designing horn antenna for {frequency_ghz} GHz")

    # Calculate wavelength
    wavelength_m = AntennaMath.wavelength(frequency_ghz)
    wavelength_mm = wavelength_m * 1000

    logger.info(f"Wavelength: {wavelength_mm:.2f} mm")

    # Design parameters (optimized for ~20 dBi gain)
    # Aperture dimensions: ~3λ x 2.4λ
    aperture_width_mm = 3.0 * wavelength_mm
    aperture_height_mm = 2.4 * wavelength_mm

    # Waveguide dimensions (WR-90 for X-band)
    waveguide_width_mm = 0.9 * wavelength_mm  # ~22.86 mm for X-band
    waveguide_height_mm = 0.4 * wavelength_mm  # ~10.16 mm

    # Horn length (for optimal phase taper)
    length_mm = 2.5 * wavelength_mm

    geometry = {
        "type": "horn",
        "frequency_ghz": frequency_ghz,
        "aperture_width_mm": aperture_width_mm,
        "aperture_height_mm": aperture_height_mm,
        "waveguide_width_mm": waveguide_width_mm,
        "waveguide_height_mm": waveguide_height_mm,
        "length_mm": length_mm,
    }

    logger.info(f"Horn dimensions:")
    logger.info(f"  Aperture: {aperture_width_mm:.1f} x {aperture_height_mm:.1f} mm")
    logger.info(f"  Length: {length_mm:.1f} mm")

    # Estimate expected gain
    aperture_area_m2 = (aperture_width_mm / 1000) * (aperture_height_mm / 1000)
    estimated_gain = AntennaMath.gain_from_aperture(
        aperture_area_m2,
        wavelength_m,
        efficiency=0.5  # Typical for horn
    )

    logger.info(f"Estimated gain: {estimated_gain:.1f} dBi")

    return geometry


def run_ansys_simulation(geometry: dict, use_ansys: bool = False):
    """
    Run ANSYS HFSS simulation.

    Args:
        geometry: Horn geometry parameters
        use_ansys: Whether to actually run ANSYS (requires license)
    """
    logger.info("=" * 80)
    logger.info("ANSYS HFSS SIMULATION")
    logger.info("=" * 80)

    if not use_ansys:
        logger.warning("ANSYS simulation disabled (use_ansys=False)")
        logger.info("To enable: Set use_ansys=True and ensure ANSYS is installed")
        logger.info("\nSimulation would perform:")
        logger.info("  1. Launch ANSYS Electronics Desktop")
        logger.info("  2. Create 3D horn geometry")
        logger.info("  3. Assign materials (PEC conductor, vacuum)")
        logger.info("  4. Create radiation boundary")
        logger.info("  5. Define wave port excitation")
        logger.info("  6. Run adaptive meshing and solver")
        logger.info("  7. Extract S-parameters and radiation pattern")
        logger.info("  8. Calculate gain, beamwidth, efficiency")
        logger.info("\nReturning estimated results instead...")

        # Return estimated results
        frequency_ghz = geometry["frequency_ghz"]
        wavelength_m = AntennaMath.wavelength(frequency_ghz)
        aperture_area = (geometry["aperture_width_mm"] / 1000) * (geometry["aperture_height_mm"] / 1000)

        estimated_gain = AntennaMath.gain_from_aperture(aperture_area, wavelength_m, 0.5)
        estimated_bw_az, estimated_bw_el = AntennaMath.beamwidth_from_gain(estimated_gain)

        return {
            "gain_dbi": estimated_gain,
            "beamwidth_az_deg": estimated_bw_az,
            "beamwidth_el_deg": estimated_bw_el,
            "efficiency_percent": 50.0,
            "vswr": 1.5,
            "simulated": False
        }

    # Actual ANSYS simulation
    try:
        # Initialize ANSYS HFSS
        simulator = AnsysHFSSSimulator(
            version="2024.1",
            non_graphical=True,
            new_desktop_session=True
        )

        # Initialize
        if not simulator.initialize():
            logger.error("Failed to initialize ANSYS HFSS")
            return None

        # Create geometry
        if not simulator.setup_geometry(geometry):
            logger.error("Failed to create geometry")
            return None

        # Set materials (already set in geometry creation)

        # Set boundary conditions
        simulator.set_boundary_conditions({
            "radiation_box": True,
            "frequency_ghz": geometry["frequency_ghz"]
        })

        # Set excitation
        simulator.set_excitation({
            "type": "wave_port",
            "location": [0, 0, 0]
        })

        # Run simulation
        result = simulator.run_simulation(
            frequency_ghz=geometry["frequency_ghz"],
            max_passes=15,
            max_delta_s=0.01
        )

        # Cleanup
        simulator.cleanup()

        if result.success:
            logger.info("✓ Simulation completed successfully")
            return {
                "gain_dbi": result.gain_dbi,
                "beamwidth_az_deg": result.beamwidth_3db_deg[0] if result.beamwidth_3db_deg else None,
                "beamwidth_el_deg": result.beamwidth_3db_deg[1] if result.beamwidth_3db_deg else None,
                "efficiency_percent": result.efficiency_percent,
                "vswr": result.vswr,
                "simulated": True
            }
        else:
            logger.error("Simulation failed")
            return None

    except Exception as e:
        logger.error(f"ANSYS simulation error: {e}", exc_info=True)
        return None


def main():
    """Main execution function."""
    logger.info("=" * 80)
    logger.info("HORN ANTENNA DESIGN WITH ANSYS HFSS")
    logger.info("=" * 80)
    logger.info("")

    # Design frequency
    frequency_ghz = 10.0

    # Step 1: Design horn antenna
    logger.info("Step 1: Designing Horn Antenna")
    logger.info("-" * 80)
    geometry = design_horn_antenna(frequency_ghz)
    logger.info("")

    # Step 2: Export geometry to CAD
    logger.info("Step 2: Exporting Geometry")
    logger.info("-" * 80)

    output_dir = Path("output/horn_antenna")
    output_dir.mkdir(parents=True, exist_ok=True)

    cad_exporter = CADExporter()

    # Export as STL for visualization
    stl_file = output_dir / "horn_antenna.stl"
    if cad_exporter.export_geometry(geometry, str(stl_file), format="stl"):
        logger.info(f"✓ STL exported: {stl_file}")

    # Export JSON specification
    json_file = output_dir / "horn_antenna.json"
    if cad_exporter.create_json_specification(geometry, str(json_file)):
        logger.info(f"✓ JSON specification: {json_file}")

    logger.info("")

    # Step 3: Run ANSYS simulation (or use estimates)
    logger.info("Step 3: Simulation")
    logger.info("-" * 80)

    # Set use_ansys=True to actually run ANSYS (requires license and installation)
    results = run_ansys_simulation(geometry, use_ansys=False)

    if results:
        logger.info("")
        logger.info("=" * 80)
        logger.info("SIMULATION RESULTS")
        logger.info("=" * 80)
        logger.info(f"Gain: {results['gain_dbi']:.2f} dBi")
        logger.info(f"Beamwidth (Az): {results['beamwidth_az_deg']:.2f}°")
        logger.info(f"Beamwidth (El): {results['beamwidth_el_deg']:.2f}°")
        logger.info(f"Efficiency: {results['efficiency_percent']:.1f}%")
        logger.info(f"VSWR: {results['vswr']:.2f}")
        logger.info(f"Simulated: {'Yes (ANSYS)' if results['simulated'] else 'No (Estimated)'}")
        logger.info("")

        # Step 4: Store in database
        logger.info("Step 4: Storing Results in Database")
        logger.info("-" * 80)

        db_file = output_dir / "simulations.db"
        db = SimulationDatabase(str(db_file))

        # Add design
        design_id = db.add_design(
            requirements={"frequency_ghz": frequency_ghz, "antenna_type": "horn"},
            design_params=geometry,
            mission_name="X-band Horn Antenna",
            tags=["horn", "x-band", "example"]
        )
        logger.info(f"Design ID: {design_id}")

        # Add simulation
        sim_id = db.add_simulation(
            design_id=design_id,
            tool_name="ANSYS_HFSS" if results['simulated'] else "Analytical",
            frequency_ghz=frequency_ghz,
            configuration=geometry,
            status="completed"
        )
        logger.info(f"Simulation ID: {sim_id}")

        # Add results
        result_id = db.add_results(
            simulation_id=sim_id,
            performance_metrics=results
        )
        logger.info(f"Result ID: {result_id}")

        # Get statistics
        stats = db.get_statistics()
        logger.info(f"\nDatabase Statistics:")
        logger.info(f"  Total designs: {stats['total_designs']}")
        logger.info(f"  Total simulations: {stats['total_simulations']}")

        db.close()
        logger.info(f"✓ Results stored: {db_file}")

    logger.info("")
    logger.info("=" * 80)
    logger.info("COMPLETE")
    logger.info("=" * 80)
    logger.info(f"Output directory: {output_dir.absolute()}")
    logger.info("\nGenerated files:")
    logger.info(f"  - {stl_file.name}: 3D geometry for visualization")
    logger.info(f"  - {json_file.name}: Design specification")
    logger.info(f"  - simulations.db: Results database")
    logger.info("\nNext steps:")
    logger.info("  1. Visualize STL in CAD viewer or MeshLab")
    logger.info("  2. Review JSON specification")
    logger.info("  3. Query database for design history")
    logger.info("  4. Run with use_ansys=True for actual HFSS simulation")
    logger.info("")

    return 0


if __name__ == "__main__":
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )

    sys.exit(main())
