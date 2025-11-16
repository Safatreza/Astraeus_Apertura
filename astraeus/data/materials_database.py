"""Materials database for antenna design."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class DielectricProperties:
    """Dielectric material properties."""

    relative_permittivity: float  # εr
    loss_tangent: float  # tan(δ)
    frequency_ghz: float  # Frequency at which properties are specified
    temperature_coefficient_ppm_per_c: Optional[float] = None


@dataclass
class ThermalProperties:
    """Thermal material properties."""

    thermal_conductivity_w_per_mk: float
    specific_heat_j_per_kgk: float
    coefficient_of_thermal_expansion_per_k: float
    max_operating_temperature_c: float
    min_operating_temperature_c: float


@dataclass
class MechanicalProperties:
    """Mechanical material properties."""

    density_kg_per_m3: float
    youngs_modulus_gpa: float
    poissons_ratio: float
    tensile_strength_mpa: float
    yield_strength_mpa: Optional[float] = None


@dataclass
class SpaceEnvironmentProperties:
    """Space environment compatibility properties."""

    total_mass_loss_percent: float  # Vacuum outgassing
    collected_volatile_condensable_material_percent: float  # CVCM
    radiation_hardness_rad: Optional[float] = None  # Total ionizing dose tolerance
    atomic_oxygen_resistance: str = "unknown"  # low, medium, high, unknown


@dataclass
class Material:
    """
    Complete material specification.

    Comprehensive material properties for antenna design selection.
    """

    name: str
    category: str  # dielectric, conductor, composite, radome, etc.
    manufacturer: Optional[str] = None
    material_id: Optional[str] = None

    # Properties
    dielectric: Optional[DielectricProperties] = None
    thermal: Optional[ThermalProperties] = None
    mechanical: Optional[MechanicalProperties] = None
    space_environment: Optional[SpaceEnvironmentProperties] = None

    # Electrical properties (for conductors)
    electrical_conductivity_s_per_m: Optional[float] = None
    surface_resistivity_ohm_per_sq: Optional[float] = None

    # Manufacturing
    fabrication_methods: List[str] = field(default_factory=list)
    minimum_thickness_mm: Optional[float] = None
    maximum_thickness_mm: Optional[float] = None
    available_forms: List[str] = field(default_factory=list)  # sheet, rod, liquid, etc.

    # Cost and availability
    cost_per_kg_usd: Optional[float] = None
    lead_time_weeks: Optional[int] = None
    availability: str = "common"  # common, limited, rare, custom

    # Application notes
    recommended_applications: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)
    notes: str = ""

    def is_suitable_for_frequency(self, frequency_ghz: float) -> bool:
        """
        Check if material is suitable for a given frequency.

        Args:
            frequency_ghz: Operating frequency in GHz

        Returns:
            True if suitable, False otherwise
        """
        if not self.dielectric:
            return True  # Conductors are generally frequency-agnostic

        # Check if loss tangent is acceptable (< 0.01 is good)
        return self.dielectric.loss_tangent < 0.01

    def is_space_qualified(self) -> bool:
        """
        Check if material is qualified for space use.

        Returns:
            True if space-qualified, False otherwise
        """
        if not self.space_environment:
            return False

        # Check outgassing requirements (NASA ASTM E595)
        tml_ok = self.space_environment.total_mass_loss_percent < 1.0
        cvcm_ok = (
            self.space_environment.collected_volatile_condensable_material_percent
            < 0.1
        )

        return tml_ok and cvcm_ok


class MaterialDatabase:
    """
    Database of materials for antenna design.

    Provides search and selection capabilities.
    """

    def __init__(self):
        """Initialize materials database."""
        self.materials: Dict[str, Material] = {}
        self._initialize_database()

    def _initialize_database(self) -> None:
        """Initialize database with common antenna materials."""

        # Dielectric substrates
        self.add_material(
            Material(
                name="Rogers RO4003C",
                category="dielectric_substrate",
                manufacturer="Rogers Corporation",
                dielectric=DielectricProperties(
                    relative_permittivity=3.38,
                    loss_tangent=0.0027,
                    frequency_ghz=10.0,
                    temperature_coefficient_ppm_per_c=-3.0,
                ),
                thermal=ThermalProperties(
                    thermal_conductivity_w_per_mk=0.64,
                    specific_heat_j_per_kgk=1150,
                    coefficient_of_thermal_expansion_per_k=11e-6,
                    max_operating_temperature_c=280,
                    min_operating_temperature_c=-55,
                ),
                mechanical=MechanicalProperties(
                    density_kg_per_m3=1790,
                    youngs_modulus_gpa=11,
                    poissons_ratio=0.3,
                    tensile_strength_mpa=140,
                ),
                fabrication_methods=["pcb_etching", "laser_cutting"],
                available_forms=["laminate"],
                recommended_applications=["microstrip", "patch_array"],
                availability="common",
            )
        )

        self.add_material(
            Material(
                name="PTFE (Teflon)",
                category="dielectric_substrate",
                dielectric=DielectricProperties(
                    relative_permittivity=2.1,
                    loss_tangent=0.0002,
                    frequency_ghz=10.0,
                ),
                thermal=ThermalProperties(
                    thermal_conductivity_w_per_mk=0.25,
                    specific_heat_j_per_kgk=1000,
                    coefficient_of_thermal_expansion_per_k=135e-6,
                    max_operating_temperature_c=260,
                    min_operating_temperature_c=-200,
                ),
                mechanical=MechanicalProperties(
                    density_kg_per_m3=2200,
                    youngs_modulus_gpa=0.5,
                    poissons_ratio=0.46,
                    tensile_strength_mpa=20,
                ),
                space_environment=SpaceEnvironmentProperties(
                    total_mass_loss_percent=0.5,
                    collected_volatile_condensable_material_percent=0.05,
                    atomic_oxygen_resistance="high",
                ),
                fabrication_methods=["machining", "molding"],
                available_forms=["sheet", "rod", "tube"],
                recommended_applications=["radome", "dielectric_lens", "spacer"],
                availability="common",
            )
        )

        # Conductors
        self.add_material(
            Material(
                name="Copper",
                category="conductor",
                electrical_conductivity_s_per_m=5.96e7,
                thermal=ThermalProperties(
                    thermal_conductivity_w_per_mk=401,
                    specific_heat_j_per_kgk=385,
                    coefficient_of_thermal_expansion_per_k=16.5e-6,
                    max_operating_temperature_c=1000,
                    min_operating_temperature_c=-200,
                ),
                mechanical=MechanicalProperties(
                    density_kg_per_m3=8960,
                    youngs_modulus_gpa=130,
                    poissons_ratio=0.34,
                    tensile_strength_mpa=220,
                ),
                fabrication_methods=["machining", "etching", "electroplating"],
                available_forms=["sheet", "foil", "wire", "plating"],
                recommended_applications=[
                    "patch_conductor",
                    "feed_network",
                    "waveguide",
                ],
                availability="common",
                limitations=["oxidation in atmosphere", "space tarnishing"],
            )
        )

        self.add_material(
            Material(
                name="Aluminum 6061",
                category="conductor_structural",
                electrical_conductivity_s_per_m=2.5e7,
                thermal=ThermalProperties(
                    thermal_conductivity_w_per_mk=167,
                    specific_heat_j_per_kgk=896,
                    coefficient_of_thermal_expansion_per_k=23.6e-6,
                    max_operating_temperature_c=300,
                    min_operating_temperature_c=-200,
                ),
                mechanical=MechanicalProperties(
                    density_kg_per_m3=2700,
                    youngs_modulus_gpa=69,
                    poissons_ratio=0.33,
                    tensile_strength_mpa=310,
                    yield_strength_mpa=276,
                ),
                space_environment=SpaceEnvironmentProperties(
                    total_mass_loss_percent=0.0,
                    collected_volatile_condensable_material_percent=0.0,
                    atomic_oxygen_resistance="high",
                    radiation_hardness_rad=1e8,
                ),
                fabrication_methods=["machining", "casting", "extrusion"],
                available_forms=["sheet", "plate", "rod", "tube", "extrusion"],
                recommended_applications=[
                    "reflector_surface",
                    "horn_antenna",
                    "structural_support",
                    "waveguide",
                ],
                availability="common",
            )
        )

        # Honeycomb cores
        self.add_material(
            Material(
                name="Aluminum Honeycomb 5052",
                category="core_material",
                mechanical=MechanicalProperties(
                    density_kg_per_m3=80,  # Low density
                    youngs_modulus_gpa=0.5,
                    poissons_ratio=0.0,
                    tensile_strength_mpa=1.2,
                ),
                thermal=ThermalProperties(
                    thermal_conductivity_w_per_mk=1.5,
                    specific_heat_j_per_kgk=896,
                    coefficient_of_thermal_expansion_per_k=23e-6,
                    max_operating_temperature_c=150,
                    min_operating_temperature_c=-200,
                ),
                space_environment=SpaceEnvironmentProperties(
                    total_mass_loss_percent=0.0,
                    collected_volatile_condensable_material_percent=0.0,
                    atomic_oxygen_resistance="high",
                ),
                fabrication_methods=["expansion", "bonding"],
                available_forms=["panel"],
                recommended_applications=["reflector_backing", "radome_core"],
                availability="common",
            )
        )

        # Radome materials
        self.add_material(
            Material(
                name="Quartz",
                category="radome",
                dielectric=DielectricProperties(
                    relative_permittivity=3.78,
                    loss_tangent=0.0001,
                    frequency_ghz=10.0,
                ),
                thermal=ThermalProperties(
                    thermal_conductivity_w_per_mk=1.4,
                    specific_heat_j_per_kgk=730,
                    coefficient_of_thermal_expansion_per_k=0.5e-6,
                    max_operating_temperature_c=1200,
                    min_operating_temperature_c=-200,
                ),
                mechanical=MechanicalProperties(
                    density_kg_per_m3=2200,
                    youngs_modulus_gpa=71,
                    poissons_ratio=0.17,
                    tensile_strength_mpa=50,
                ),
                space_environment=SpaceEnvironmentProperties(
                    total_mass_loss_percent=0.0,
                    collected_volatile_condensable_material_percent=0.0,
                    atomic_oxygen_resistance="high",
                    radiation_hardness_rad=1e9,
                ),
                fabrication_methods=["molding", "machining"],
                recommended_applications=["radome", "high_temp_window"],
                availability="common",
                limitations=["brittle", "expensive"],
            )
        )

    def add_material(self, material: Material) -> None:
        """
        Add a material to the database.

        Args:
            material: Material to add
        """
        self.materials[material.name] = material

    def get_material(self, name: str) -> Optional[Material]:
        """
        Get a material by name.

        Args:
            name: Material name

        Returns:
            Material if found, None otherwise
        """
        return self.materials.get(name)

    def search_by_category(self, category: str) -> List[Material]:
        """
        Search materials by category.

        Args:
            category: Material category

        Returns:
            List of materials in category
        """
        return [
            mat for mat in self.materials.values() if mat.category == category
        ]

    def search_by_application(self, application: str) -> List[Material]:
        """
        Search materials suitable for an application.

        Args:
            application: Application name

        Returns:
            List of suitable materials
        """
        return [
            mat
            for mat in self.materials.values()
            if application in mat.recommended_applications
        ]

    def search_dielectrics(
        self,
        min_permittivity: Optional[float] = None,
        max_permittivity: Optional[float] = None,
        max_loss_tangent: float = 0.01,
        space_qualified: bool = False,
    ) -> List[Material]:
        """
        Search for dielectric materials with specific properties.

        Args:
            min_permittivity: Minimum relative permittivity
            max_permittivity: Maximum relative permittivity
            max_loss_tangent: Maximum loss tangent
            space_qualified: Require space qualification

        Returns:
            List of matching materials
        """
        results = []

        for mat in self.materials.values():
            if mat.dielectric is None:
                continue

            # Check permittivity range
            if min_permittivity and mat.dielectric.relative_permittivity < min_permittivity:
                continue
            if max_permittivity and mat.dielectric.relative_permittivity > max_permittivity:
                continue

            # Check loss tangent
            if mat.dielectric.loss_tangent > max_loss_tangent:
                continue

            # Check space qualification if required
            if space_qualified and not mat.is_space_qualified():
                continue

            results.append(mat)

        return results

    def get_all_materials(self) -> List[Material]:
        """
        Get all materials in database.

        Returns:
            List of all materials
        """
        return list(self.materials.values())

    def get_material_summary(self) -> Dict[str, int]:
        """
        Get summary statistics of materials database.

        Returns:
            Dictionary with counts by category
        """
        summary = {}
        for mat in self.materials.values():
            summary[mat.category] = summary.get(mat.category, 0) + 1
        return summary
