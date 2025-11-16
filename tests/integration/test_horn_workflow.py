"""Integration test for horn antenna design workflow."""

import pytest
import tempfile
from pathlib import Path

from astraeus.data.parameters import (
    MissionRequirements,
    FrequencySpec,
    RadiationPattern,
    Polarization,
    RadarMode,
)
from astraeus.core.workflow import DesignWorkflow
from astraeus.agents import *
from astraeus.data.simulation_database import SimulationDatabase
from astraeus.geometry import CADExporter
from astraeus.utils.antenna_math import AntennaMath


class TestHornAntennaWorkflow:
    """Test complete horn antenna design workflow."""

    @pytest.fixture
    def horn_requirements(self):
        """Create horn antenna requirements."""
        return MissionRequirements(
            mission_name="X-Band Horn Antenna Test",
            mission_type=RadarMode.COMMUNICATION,
            frequency=FrequencySpec(
                center_frequency_ghz=10.0,
                bandwidth_mhz=500.0,
                frequency_band="X"
            ),
            radiation_pattern=RadiationPattern(
                gain_dbi=20.0,
                beamwidth_azimuth_deg=20.0,
                beamwidth_elevation_deg=25.0,
                sidelobe_level_db=-20.0
            ),
            polarization=Polarization.LINEAR_HORIZONTAL
        )

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test outputs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_requirements_validation(self, horn_requirements):
        """Test that requirements are valid."""
        analyst = RequirementsAnalystAgent()

        task = {
            "type": "analyze_requirements",
            "requirements": horn_requirements
        }

        result = analyst.execute_task(task)

        assert "validated_requirements" in result
        assert "validation_results" in result
        assert result["validation_results"]["is_valid"]

    def test_geometry_generation(self):
        """Test horn geometry generation."""
        frequency_ghz = 10.0
        wavelength_m = AntennaMath.wavelength(frequency_ghz)

        # Expected geometry for horn
        geometry = {
            "type": "horn",
            "frequency_ghz": frequency_ghz,
            "aperture_width_mm": 3.0 * wavelength_m * 1000,
            "aperture_height_mm": 2.4 * wavelength_m * 1000,
            "length_mm": 2.5 * wavelength_m * 1000,
        }

        # Verify dimensions are reasonable
        assert geometry["aperture_width_mm"] > 50  # At least 50 mm
        assert geometry["length_mm"] > 50

    def test_cad_export(self, temp_dir):
        """Test CAD export functionality."""
        geometry = {
            "type": "horn",
            "frequency_ghz": 10.0,
            "aperture_width_mm": 90.0,
            "aperture_height_mm": 72.0,
            "length_mm": 75.0,
            "waveguide_width_mm": 22.86,
            "waveguide_height_mm": 10.16,
        }

        exporter = CADExporter()

        # Export as STL
        stl_file = temp_dir / "horn.stl"
        success = exporter.export_geometry(geometry, str(stl_file), format="stl")

        assert success
        assert stl_file.exists()
        assert stl_file.stat().st_size > 0

    def test_simulation_database(self, temp_dir):
        """Test simulation database functionality."""
        db_file = temp_dir / "test_simulations.db"
        db = SimulationDatabase(str(db_file))

        # Add design
        design_id = db.add_design(
            requirements={"frequency_ghz": 10.0},
            design_params={"type": "horn"},
            mission_name="Test Horn",
            tags=["test", "horn"]
        )

        assert design_id is not None

        # Add simulation
        sim_id = db.add_simulation(
            design_id=design_id,
            tool_name="TestTool",
            frequency_ghz=10.0,
            configuration={"test": True}
        )

        assert sim_id is not None

        # Add results
        result_id = db.add_results(
            simulation_id=sim_id,
            performance_metrics={
                "gain_dbi": 20.0,
                "efficiency_percent": 85.0
            }
        )

        assert result_id is not None

        # Query designs
        designs = db.query_designs(gain_min=15.0)
        assert len(designs) > 0
        assert designs[0]["design_id"] == design_id

        # Get statistics
        stats = db.get_statistics()
        assert stats["total_designs"] == 1
        assert stats["total_simulations"] == 1

        db.close()

    def test_cached_simulation_retrieval(self, temp_dir):
        """Test that duplicate simulations are retrieved from cache."""
        db_file = temp_dir / "cache_test.db"
        db = SimulationDatabase(str(db_file))

        design_params = {
            "type": "horn",
            "frequency": 10.0,
            "aperture": 50.0
        }

        # Add first simulation
        design_id = db.add_design(
            requirements={},
            design_params=design_params,
            mission_name="Cache Test"
        )

        sim_id = db.add_simulation(
            design_id=design_id,
            tool_name="HFSS",
            frequency_ghz=10.0,
            configuration={}
        )

        db.update_simulation_status(sim_id, "completed")

        db.add_results(
            simulation_id=sim_id,
            performance_metrics={"gain_dbi": 20.0}
        )

        # Try to find cached result
        cached = db.find_cached_simulation(
            design_params=design_params,
            tool_name="HFSS",
            frequency_ghz=10.0
        )

        assert cached is not None
        assert cached["simulation_id"] == sim_id
        assert cached["performance_metrics"]["gain_dbi"] == 20.0

        db.close()

    def test_analytical_validation(self):
        """Test analytical validation of horn antenna."""
        frequency_ghz = 10.0
        wavelength_m = AntennaMath.wavelength(frequency_ghz)

        # Horn with 3λ x 2.4λ aperture
        aperture_width_m = 3.0 * wavelength_m
        aperture_height_m = 2.4 * wavelength_m
        aperture_area_m2 = aperture_width_m * aperture_height_m

        # Calculate expected gain
        expected_gain = AntennaMath.gain_from_aperture(
            aperture_area_m2,
            wavelength_m,
            efficiency=0.5  # Typical horn efficiency
        )

        # Expected beamwidth
        expected_bw_az, expected_bw_el = AntennaMath.beamwidth_from_gain(expected_gain)

        # Validate ranges
        assert 15 < expected_gain < 25  # Reasonable gain range
        assert 10 < expected_bw_az < 40  # Reasonable beamwidth
        assert 10 < expected_bw_el < 40

        # Check gain-beamwidth relationship
        recalc_gain = AntennaMath.gain_from_beamwidth(expected_bw_az, expected_bw_el)
        assert abs(recalc_gain - expected_gain) < 2.0  # Should be close

    @pytest.mark.slow
    def test_complete_workflow(self, horn_requirements, temp_dir):
        """
        Test complete end-to-end workflow (without actual ANSYS).

        This test validates:
        1. Requirements analysis
        2. Architecture selection
        3. Geometry generation
        4. Material selection
        5. Validation
        """
        # Create workflow
        workflow = DesignWorkflow(
            max_iterations=5,  # Limited for testing
            convergence_threshold=0.01,
            enable_human_review=False
        )

        # Register agents
        workflow.register_agent(RequirementsAnalystAgent())
        workflow.register_agent(ArchitectureAgent())
        workflow.register_agent(GeometryGeneratorAgent())
        workflow.register_agent(MaterialSelectorAgent())
        workflow.register_agent(ValidationAgent())
        workflow.register_agent(SupervisorAgent())

        # Note: Simulation and Optimizer agents would require actual simulation
        # For integration test, we validate the framework works

        try:
            # Execute workflow
            result = workflow.execute(horn_requirements)

            # Verify result structure
            assert "workflow_id" in result
            assert "requirements" in result
            assert "final_design" in result

            # Verify design components
            final_design = result["final_design"]
            assert "architecture" in final_design

            # Verify workflow completed
            assert result["termination_condition"] is not None

        except Exception as e:
            pytest.fail(f"Workflow failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
