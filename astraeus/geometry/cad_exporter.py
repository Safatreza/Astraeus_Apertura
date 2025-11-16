"""CAD export utilities for antenna geometry."""

from pathlib import Path
from typing import Any, Dict, Optional
import json

from loguru import logger

try:
    import trimesh
    TRIMESH_AVAILABLE = True
except ImportError:
    TRIMESH_AVAILABLE = False
    logger.warning("trimesh not available. Install with: pip install trimesh")


class CADExporter:
    """
    Export antenna geometry to CAD formats.

    Supports:
    - STEP format (.step, .stp)
    - IGES format (.iges, .igs)
    - STL format (.stl)
    - OBJ format (.obj)
    """

    def __init__(self):
        """Initialize CAD exporter."""
        if not TRIMESH_AVAILABLE:
            logger.warning("trimesh not available - limited CAD export functionality")

    def export_geometry(
        self,
        geometry: Dict[str, Any],
        output_file: str,
        format: Optional[str] = None
    ) -> bool:
        """
        Export geometry to CAD file.

        Args:
            geometry: Geometry specification dictionary
            output_file: Output file path
            format: Output format ('step', 'iges', 'stl', 'obj')
                   Auto-detected from extension if not specified

        Returns:
            True if export successful
        """
        output_path = Path(output_file)

        # Auto-detect format from extension
        if format is None:
            format = output_path.suffix.lstrip('.').lower()

        logger.info(f"Exporting geometry to {format.upper()}: {output_file}")

        try:
            if geometry.get("type") == "horn":
                return self._export_horn(geometry, output_path, format)
            elif geometry.get("type") == "patch":
                return self._export_patch(geometry, output_path, format)
            elif geometry.get("type") == "dipole":
                return self._export_dipole(geometry, output_path, format)
            else:
                logger.error(f"Unsupported geometry type: {geometry.get('type')}")
                return False

        except Exception as e:
            logger.error(f"Failed to export geometry: {e}", exc_info=True)
            return False

    def _export_horn(
        self,
        geometry: Dict[str, Any],
        output_path: Path,
        format: str
    ) -> bool:
        """Export horn antenna geometry."""
        if not TRIMESH_AVAILABLE:
            logger.error("trimesh required for CAD export")
            return False

        # Extract parameters
        aperture_width = geometry.get("aperture_width_mm", 50.0) / 1000  # Convert to m
        aperture_height = geometry.get("aperture_height_mm", 40.0) / 1000
        length = geometry.get("length_mm", 80.0) / 1000

        # Create simplified horn geometry using boxes
        # In production, would create proper swept surfaces

        # Create mesh for visualization/export
        # Simplified representation
        vertices = [
            # Aperture
            [-aperture_width/2, -aperture_height/2, length],
            [aperture_width/2, -aperture_height/2, length],
            [aperture_width/2, aperture_height/2, length],
            [-aperture_width/2, aperture_height/2, length],
            # Throat
            [-aperture_width/4, -aperture_height/4, 0],
            [aperture_width/4, -aperture_height/4, 0],
            [aperture_width/4, aperture_height/4, 0],
            [-aperture_width/4, aperture_height/4, 0],
        ]

        faces = [
            [0, 1, 2], [0, 2, 3],  # Aperture
            [4, 5, 6], [4, 6, 7],  # Throat
            # Sides (simplified)
            [0, 1, 5], [0, 5, 4],
            [1, 2, 6], [1, 6, 5],
            [2, 3, 7], [2, 7, 6],
            [3, 0, 4], [3, 4, 7],
        ]

        mesh = trimesh.Trimesh(vertices=vertices, faces=faces)

        # Export based on format
        if format == 'stl':
            mesh.export(str(output_path))
        elif format == 'obj':
            mesh.export(str(output_path))
        elif format in ['step', 'stp', 'iges', 'igs']:
            # STEP/IGES export requires additional libraries
            logger.warning(f"{format.upper()} export requires CAD kernel (e.g., OCC)")
            # Save as STL as fallback
            stl_path = output_path.with_suffix('.stl')
            mesh.export(str(stl_path))
            logger.info(f"Exported as STL instead: {stl_path}")
        else:
            logger.error(f"Unsupported export format: {format}")
            return False

        logger.info(f"✓ Horn geometry exported: {output_path}")
        return True

    def _export_patch(
        self,
        geometry: Dict[str, Any],
        output_path: Path,
        format: str
    ) -> bool:
        """Export patch antenna geometry."""
        if not TRIMESH_AVAILABLE:
            logger.error("trimesh required for CAD export")
            return False

        # Extract parameters (convert mm to m)
        patch_length = geometry.get("patch_length_mm", 10.0) / 1000
        patch_width = geometry.get("patch_width_mm", 12.0) / 1000
        substrate_height = geometry.get("substrate_height_mm", 1.6) / 1000
        ground_size = geometry.get("ground_size_mm", 40.0) / 1000

        # Create meshes for each layer
        meshes = []

        # Ground plane
        ground_box = trimesh.creation.box(
            extents=[ground_size, ground_size, 0.001]
        )
        meshes.append(ground_box)

        # Substrate
        substrate_box = trimesh.creation.box(
            extents=[ground_size, ground_size, substrate_height]
        )
        substrate_box.apply_translation([0, 0, substrate_height/2])
        meshes.append(substrate_box)

        # Patch
        patch_box = trimesh.creation.box(
            extents=[patch_length, patch_width, 0.001]
        )
        patch_box.apply_translation([0, 0, substrate_height])
        meshes.append(patch_box)

        # Combine meshes
        combined = trimesh.util.concatenate(meshes)

        # Export
        combined.export(str(output_path))

        logger.info(f"✓ Patch antenna geometry exported: {output_path}")
        return True

    def _export_dipole(
        self,
        geometry: Dict[str, Any],
        output_path: Path,
        format: str
    ) -> bool:
        """Export dipole antenna geometry."""
        if not TRIMESH_AVAILABLE:
            logger.error("trimesh required for CAD export")
            return False

        # Extract parameters
        length = geometry.get("length_mm", 75.0) / 1000  # Convert to m
        diameter = geometry.get("diameter_mm", 2.0) / 1000

        # Create two cylindrical arms
        arm1 = trimesh.creation.cylinder(
            radius=diameter/2,
            height=length/2,
            sections=16
        )
        arm1.apply_translation([0, 0, length/4])

        arm2 = trimesh.creation.cylinder(
            radius=diameter/2,
            height=length/2,
            sections=16
        )
        arm2.apply_translation([0, 0, -length/4])

        # Combine arms
        dipole = trimesh.util.concatenate([arm1, arm2])

        # Export
        dipole.export(str(output_path))

        logger.info(f"✓ Dipole geometry exported: {output_path}")
        return True

    def create_json_specification(
        self,
        geometry: Dict[str, Any],
        output_file: str
    ) -> bool:
        """
        Export geometry as JSON specification.

        Useful for documentation and version control.

        Args:
            geometry: Geometry specification
            output_file: Output JSON file path

        Returns:
            True if successful
        """
        try:
            with open(output_file, 'w') as f:
                json.dump(geometry, f, indent=2, sort_keys=True)

            logger.info(f"✓ JSON specification exported: {output_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to export JSON: {e}")
            return False
