"""Material Selector Agent - Selects optimal materials for antenna design."""

from typing import Any, Dict, List, Optional

from loguru import logger

from astraeus.core.agent_base import BaseAgent
from astraeus.core.message import Message, MessagePriority, MessageType
from astraeus.data.parameters import AntennaType, MissionRequirements
from astraeus.data.materials_database import MaterialsDatabase


class MaterialSelectorAgent(BaseAgent):
    """
    Agent responsible for selecting optimal materials for antenna design.

    Primary Responsibilities:
    - Select substrate materials for microstrip/patch antennas
    - Select conductor materials for radiating elements
    - Select structural materials for mechanical support
    - Consider electromagnetic, thermal, and mechanical properties
    - Evaluate material compatibility and manufacturing constraints
    - Assess space environment effects (radiation, outgassing, thermal cycling)
    """

    def _initialize(self) -> None:
        """Initialize the Material Selector Agent."""
        self.agent_type = "MaterialSelector"
        self.knowledge_domains = [
            "dielectric_materials",
            "conductor_materials",
            "substrate_materials",
            "space_materials",
            "material_properties",
            "thermal_management",
        ]
        self.capabilities = [
            "substrate_selection",
            "conductor_selection",
            "structural_material_selection",
            "material_property_analysis",
            "space_qualification_assessment",
        ]

        # Load materials database
        self.materials_db = MaterialsDatabase()

        # Selection criteria weights
        self.selection_weights = {
            "electromagnetic": 0.35,
            "thermal": 0.25,
            "mechanical": 0.20,
            "cost": 0.10,
            "availability": 0.10,
        }

        # Space environment requirements
        self.space_requirements = {
            "outgassing_tml_max": 1.0,  # Total Mass Loss %
            "outgassing_cvcm_max": 0.1,  # Collected Volatile Condensable Materials %
            "temperature_range_c": (-150, 150),
            "thermal_cycles_min": 1000,
        }

        logger.info("Material Selector Agent initialized")

    def process_message(self, message: Message) -> Optional[List[Message]]:
        """
        Process incoming messages.

        Args:
            message: Message to process

        Returns:
            List of response messages
        """
        if message.message_type == MessageType.REQUEST_TASK:
            return self._handle_task_request(message)
        elif message.message_type == MessageType.QUERY:
            return self._handle_query(message)
        else:
            logger.debug(f"Unhandled message type: {message.message_type}")
            return None

    def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute material selection task.

        Args:
            task: Task specification

        Returns:
            Material selection results
        """
        task_type = task.get("type")

        if task_type == "select_materials":
            return self._select_materials(
                task["architecture"],
                task["requirements"],
                task.get("environment", "space"),
            )
        elif task_type == "select_substrate":
            return self._select_substrate(
                task["frequency_ghz"], task.get("requirements")
            )
        elif task_type == "select_conductor":
            return self._select_conductor(
                task["frequency_ghz"], task.get("requirements")
            )
        elif task_type == "evaluate_material":
            return self._evaluate_material(
                task["material_name"], task.get("criteria")
            )
        else:
            raise ValueError(f"Unknown task type: {task_type}")

    def _select_materials(
        self,
        architecture: AntennaType,
        requirements: MissionRequirements,
        environment: str = "space",
    ) -> Dict[str, Any]:
        """
        Select all materials for antenna design.

        Args:
            architecture: Antenna architecture type
            requirements: Mission requirements
            environment: Operating environment (space, airborne, ground)

        Returns:
            Selected materials and rationale
        """
        logger.info(f"Selecting materials for {architecture.value} in {environment}")

        freq_ghz = requirements.frequency.center_frequency_ghz

        # Select materials based on architecture
        materials = {}

        # Substrate material (for planar antennas)
        if architecture in [
            AntennaType.PATCH,
            AntennaType.PATCH_ARRAY,
            AntennaType.PHASED_ARRAY,
            AntennaType.MICROSTRIP,
        ]:
            substrate_result = self._select_substrate(freq_ghz, requirements)
            materials["substrate"] = substrate_result["selected_material"]

        # Conductor material
        conductor_result = self._select_conductor(freq_ghz, requirements)
        materials["conductor"] = conductor_result["selected_material"]

        # Structural materials
        structural_result = self._select_structural_material(
            requirements, environment
        )
        materials["structure"] = structural_result["selected_material"]

        # For reflector antennas, select reflector surface material
        if architecture in [
            AntennaType.REFLECTOR_PARABOLIC,
            AntennaType.REFLECTOR_CASSEGRAIN,
            AntennaType.REFLECTOR_GREGORIAN,
        ]:
            reflector_result = self._select_reflector_material(requirements)
            materials["reflector_surface"] = reflector_result["selected_material"]

        # Validate material compatibility
        compatibility = self._check_material_compatibility(materials)

        # Estimate costs
        cost_estimate = self._estimate_material_costs(materials, architecture)

        # Log decision
        self.log_decision(
            decision=f"Selected materials for {architecture.value}",
            rationale=f"Optimized for {environment} environment at {freq_ghz} GHz",
            metadata={
                "materials": {k: v["name"] for k, v in materials.items()},
                "total_cost_estimate": cost_estimate["total"],
                "compatibility_score": compatibility["score"],
            },
        )

        return {
            "materials": materials,
            "compatibility": compatibility,
            "cost_estimate": cost_estimate,
            "environment": environment,
            "recommendations": self._generate_material_recommendations(
                materials, architecture
            ),
        }

    def _select_substrate(
        self, frequency_ghz: float, requirements: Optional[MissionRequirements] = None
    ) -> Dict[str, Any]:
        """
        Select optimal substrate material.

        Args:
            frequency_ghz: Operating frequency
            requirements: Mission requirements

        Returns:
            Selected substrate and rationale
        """
        logger.debug(f"Selecting substrate for {frequency_ghz} GHz")

        # Query materials database
        candidates = self.materials_db.query_substrates(
            frequency_range=(frequency_ghz * 0.9, frequency_ghz * 1.1),
            space_qualified=True,
        )

        # Score each candidate
        scored_materials = []
        for material in candidates:
            score = self._score_substrate(material, frequency_ghz)
            scored_materials.append({"material": material, "score": score})

        # Sort by score
        scored_materials.sort(key=lambda x: x["score"], reverse=True)

        # Select top material
        selected = scored_materials[0] if scored_materials else None

        if not selected:
            # Fallback to default
            selected = {
                "material": self.materials_db.get_material("Rogers RO4003C"),
                "score": 0.7,
            }

        return {
            "selected_material": selected["material"],
            "score": selected["score"],
            "alternatives": [m["material"] for m in scored_materials[1:4]],
            "rationale": self._generate_substrate_rationale(
                selected["material"], frequency_ghz
            ),
        }

    def _select_conductor(
        self, frequency_ghz: float, requirements: Optional[MissionRequirements] = None
    ) -> Dict[str, Any]:
        """
        Select optimal conductor material.

        Args:
            frequency_ghz: Operating frequency
            requirements: Mission requirements

        Returns:
            Selected conductor and rationale
        """
        logger.debug(f"Selecting conductor for {frequency_ghz} GHz")

        # Query materials database
        candidates = self.materials_db.query_conductors(space_qualified=True)

        # Score each candidate
        scored_materials = []
        for material in candidates:
            score = self._score_conductor(material, frequency_ghz)
            scored_materials.append({"material": material, "score": score})

        # Sort by score
        scored_materials.sort(key=lambda x: x["score"], reverse=True)

        selected = scored_materials[0] if scored_materials else None

        if not selected:
            # Fallback to default (copper)
            selected = {
                "material": self.materials_db.get_material("Copper"),
                "score": 0.8,
            }

        return {
            "selected_material": selected["material"],
            "score": selected["score"],
            "alternatives": [m["material"] for m in scored_materials[1:4]],
            "rationale": f"{selected['material']['name']} selected for excellent "
            f"conductivity ({selected['material']['properties']['conductivity_S_per_m']:.1e} S/m)",
        }

    def _select_structural_material(
        self, requirements: MissionRequirements, environment: str
    ) -> Dict[str, Any]:
        """
        Select structural support material.

        Args:
            requirements: Mission requirements
            environment: Operating environment

        Returns:
            Selected structural material
        """
        logger.debug(f"Selecting structural material for {environment}")

        # Query materials database
        candidates = self.materials_db.query_structural(
            space_qualified=(environment == "space")
        )

        # Score based on mechanical and thermal properties
        scored_materials = []
        for material in candidates:
            score = self._score_structural_material(material, requirements)
            scored_materials.append({"material": material, "score": score})

        scored_materials.sort(key=lambda x: x["score"], reverse=True)

        selected = scored_materials[0] if scored_materials else None

        if not selected:
            # Fallback to aluminum
            selected = {
                "material": self.materials_db.get_material("Aluminum 6061-T6"),
                "score": 0.75,
            }

        return {
            "selected_material": selected["material"],
            "score": selected["score"],
            "alternatives": [m["material"] for m in scored_materials[1:4]],
            "rationale": f"{selected['material']['name']} provides optimal "
            f"strength-to-weight ratio",
        }

    def _select_reflector_material(
        self, requirements: MissionRequirements
    ) -> Dict[str, Any]:
        """
        Select reflector surface material.

        Args:
            requirements: Mission requirements

        Returns:
            Selected reflector material
        """
        logger.debug("Selecting reflector surface material")

        # Common reflector materials
        candidates = [
            self.materials_db.get_material("Aluminum (polished)"),
            self.materials_db.get_material("Gold-plated aluminum"),
            self.materials_db.get_material("CFRP with metal coating"),
        ]

        # Score based on reflectivity and weight
        scored = []
        for material in candidates:
            if material:
                score = self._score_reflector_material(material, requirements)
                scored.append({"material": material, "score": score})

        scored.sort(key=lambda x: x["score"], reverse=True)

        selected = scored[0] if scored else None

        if not selected:
            # Fallback
            selected = {
                "material": {"name": "Aluminum (polished)", "properties": {}},
                "score": 0.8,
            }

        return {
            "selected_material": selected["material"],
            "score": selected["score"],
            "rationale": "High reflectivity and proven space heritage",
        }

    def _score_substrate(self, material: Dict[str, Any], frequency_ghz: float) -> float:
        """Score a substrate material."""
        score = 0.0
        props = material.get("properties", {})

        # Dielectric properties (40%)
        if "relative_permittivity" in props:
            # Prefer moderate permittivity (2-4) for most applications
            epsilon_r = props["relative_permittivity"]
            if 2.0 <= epsilon_r <= 4.0:
                score += 0.4
            else:
                score += 0.2

        # Loss tangent (30%)
        if "loss_tangent" in props:
            tan_delta = props["loss_tangent"]
            if tan_delta < 0.001:
                score += 0.3
            elif tan_delta < 0.005:
                score += 0.2
            else:
                score += 0.1

        # Thermal properties (20%)
        if "thermal_expansion_ppm_per_C" in props:
            cte = props["thermal_expansion_ppm_per_C"]
            if cte < 30:  # Low CTE is better
                score += 0.2
            else:
                score += 0.1

        # Space qualification (10%)
        if material.get("space_qualified", False):
            score += 0.1

        return score

    def _score_conductor(self, material: Dict[str, Any], frequency_ghz: float) -> float:
        """Score a conductor material."""
        score = 0.0
        props = material.get("properties", {})

        # Conductivity (50%)
        if "conductivity_S_per_m" in props:
            conductivity = props["conductivity_S_per_m"]
            # Copper is ~5.8e7 S/m
            if conductivity > 5.0e7:
                score += 0.5
            elif conductivity > 3.0e7:
                score += 0.3
            else:
                score += 0.1

        # Skin depth consideration (20%)
        # Lower resistivity = better at high frequency
        if "resistivity_ohm_m" in props:
            resistivity = props["resistivity_ohm_m"]
            if resistivity < 2e-8:
                score += 0.2
            else:
                score += 0.1

        # Space qualification (20%)
        if material.get("space_qualified", False):
            score += 0.2

        # Cost (10%)
        cost_level = material.get("cost_level", "medium")
        if cost_level == "low":
            score += 0.1
        elif cost_level == "medium":
            score += 0.05

        return score

    def _score_structural_material(
        self, material: Dict[str, Any], requirements: MissionRequirements
    ) -> float:
        """Score a structural material."""
        score = 0.0
        props = material.get("properties", {})

        # Strength-to-weight ratio (40%)
        if "density_kg_per_m3" in props and "yield_strength_MPa" in props:
            density = props["density_kg_per_m3"]
            strength = props["yield_strength_MPa"]
            specific_strength = strength / density

            if specific_strength > 0.2:  # High specific strength
                score += 0.4
            elif specific_strength > 0.1:
                score += 0.3
            else:
                score += 0.2

        # Thermal expansion (30%)
        if "thermal_expansion_ppm_per_C" in props:
            cte = props["thermal_expansion_ppm_per_C"]
            if cte < 15:
                score += 0.3
            elif cte < 25:
                score += 0.2
            else:
                score += 0.1

        # Space qualification (20%)
        if material.get("space_qualified", False):
            score += 0.2

        # Manufacturability (10%)
        if material.get("manufacturability", "medium") in ["easy", "medium"]:
            score += 0.1

        return score

    def _score_reflector_material(
        self, material: Dict[str, Any], requirements: MissionRequirements
    ) -> float:
        """Score a reflector material."""
        score = 0.0
        props = material.get("properties", {})

        # Reflectivity (50%)
        if "reflectivity" in props:
            reflectivity = props["reflectivity"]
            score += 0.5 * reflectivity

        # Density (30% - lighter is better)
        if "density_kg_per_m3" in props:
            density = props["density_kg_per_m3"]
            if density < 2000:
                score += 0.3
            elif density < 3000:
                score += 0.2
            else:
                score += 0.1

        # Space qualification (20%)
        if material.get("space_qualified", False):
            score += 0.2

        return score

    def _check_material_compatibility(
        self, materials: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Check compatibility between selected materials.

        Args:
            materials: Dictionary of selected materials

        Returns:
            Compatibility assessment
        """
        issues = []
        warnings = []
        score = 1.0

        # Check thermal expansion mismatch
        if "substrate" in materials and "conductor" in materials:
            substrate_cte = materials["substrate"].get("properties", {}).get(
                "thermal_expansion_ppm_per_C", 0
            )
            conductor_cte = materials["conductor"].get("properties", {}).get(
                "thermal_expansion_ppm_per_C", 0
            )

            cte_mismatch = abs(substrate_cte - conductor_cte)
            if cte_mismatch > 10:
                warnings.append(
                    f"CTE mismatch: {cte_mismatch:.1f} ppm/C between "
                    "substrate and conductor"
                )
                score -= 0.1

        # Check for galvanic corrosion potential
        # (simplified check)

        return {
            "score": max(0.0, score),
            "is_compatible": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
        }

    def _estimate_material_costs(
        self, materials: Dict[str, Dict[str, Any]], architecture: AntennaType
    ) -> Dict[str, Any]:
        """
        Estimate material costs.

        Args:
            materials: Selected materials
            architecture: Antenna architecture

        Returns:
            Cost estimate
        """
        # Simplified cost estimation
        costs = {}
        total = 0.0

        cost_map = {"low": 100, "medium": 500, "high": 2000}

        for component, material in materials.items():
            cost_level = material.get("cost_level", "medium")
            component_cost = cost_map[cost_level]
            costs[component] = component_cost
            total += component_cost

        return {
            "components": costs,
            "total": total,
            "currency": "USD",
            "basis": "material_only",
        }

    def _generate_material_recommendations(
        self, materials: Dict[str, Dict[str, Any]], architecture: AntennaType
    ) -> List[str]:
        """Generate recommendations for material selection."""
        recommendations = []

        recommendations.append(
            f"Materials selected are optimized for {architecture.value} architecture"
        )

        if "substrate" in materials:
            substrate = materials["substrate"]
            recommendations.append(
                f"Substrate: {substrate['name']} provides low loss and "
                "stable dielectric properties"
            )

        recommendations.append(
            "Verify thermal cycling compatibility before fabrication"
        )
        recommendations.append("Consider surface treatments for space environment")

        return recommendations

    def _generate_substrate_rationale(
        self, material: Dict[str, Any], frequency_ghz: float
    ) -> str:
        """Generate rationale for substrate selection."""
        props = material.get("properties", {})
        epsilon_r = props.get("relative_permittivity", "N/A")
        tan_delta = props.get("loss_tangent", "N/A")

        return (
            f"{material['name']} selected: εr={epsilon_r}, "
            f"tan(δ)={tan_delta}, optimal for {frequency_ghz} GHz"
        )

    def _handle_query(self, message: Message) -> List[Message]:
        """Handle query messages."""
        response = message.create_reply(
            sender=self.agent_id,
            message_type=MessageType.DATA_TRANSFER,
            payload={"status": "Material selection capability available"},
            rationale="Responding to query",
        )
        return [response]

    def _handle_task_request(self, message: Message) -> List[Message]:
        """Handle task request messages."""
        task_data = message.payload.get("task")
        if task_data:
            result = self.execute_task(task_data)
            response = message.create_reply(
                sender=self.agent_id,
                message_type=MessageType.DATA_TRANSFER,
                payload={"result": result},
                rationale="Material selection task completed",
            )
            return [response]
        return []
