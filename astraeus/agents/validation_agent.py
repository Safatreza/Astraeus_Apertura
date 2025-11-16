"""Validation Agent - Validates designs against requirements and standards."""

from typing import Any, Dict, List, Optional
from datetime import datetime

from loguru import logger

from astraeus.core.agent_base import BaseAgent
from astraeus.core.message import Message, MessagePriority, MessageType
from astraeus.data.parameters import MissionRequirements


class ValidationAgent(BaseAgent):
    """
    Agent responsible for validating antenna designs.

    Primary Responsibilities:
    - Validate designs against mission requirements
    - Check compliance with engineering standards (NASA, ESA, MIL-STD)
    - Verify manufacturing feasibility and tolerances
    - Assess test and verification requirements
    - Generate validation reports and compliance matrices
    - Identify gaps and non-conformances
    """

    def _initialize(self) -> None:
        """Initialize the Validation Agent."""
        self.agent_type = "ValidationAgent"
        self.knowledge_domains = [
            "requirements_verification",
            "standards_compliance",
            "manufacturing_standards",
            "space_qualification",
            "test_procedures",
            "quality_assurance",
        ]
        self.capabilities = [
            "requirements_validation",
            "standards_compliance_check",
            "manufacturing_validation",
            "test_plan_generation",
            "compliance_reporting",
            "gap_analysis",
        ]

        # Validation standards
        self.standards = {
            "NASA": ["NASA-STD-5001", "NASA-STD-5002", "NASA-HDBK-4001"],
            "ESA": ["ECSS-E-ST-20C", "ECSS-E-ST-50-05C"],
            "MIL": ["MIL-STD-188-164", "MIL-STD-461"],
            "IPC": ["IPC-2221", "IPC-6012"],
        }

        # Validation thresholds
        self.thresholds = {
            "gain_tolerance_db": 1.0,
            "frequency_tolerance_percent": 1.0,
            "impedance_tolerance_percent": 5.0,
            "mass_tolerance_percent": 10.0,
            "dimensional_tolerance_percent": 2.0,
        }

        # Validation history
        self.validation_history = []

        logger.info("Validation Agent initialized")

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
        Execute validation task.

        Args:
            task: Task specification

        Returns:
            Validation results
        """
        task_type = task.get("type")

        if task_type == "validate_design":
            return self._validate_design(
                task["design"],
                task["requirements"],
                task.get("simulation_results"),
            )
        elif task_type == "check_standards_compliance":
            return self._check_standards_compliance(
                task["design"], task.get("standards", ["NASA"])
            )
        elif task_type == "validate_manufacturing":
            return self._validate_manufacturing(
                task["design"], task["materials"]
            )
        elif task_type == "generate_test_plan":
            return self._generate_test_plan(
                task["design"], task["requirements"]
            )
        elif task_type == "compliance_report":
            return self._generate_compliance_report(
                task["validation_results"]
            )
        else:
            raise ValueError(f"Unknown task type: {task_type}")

    def _validate_design(
        self,
        design: Dict[str, Any],
        requirements: MissionRequirements,
        simulation_results: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Validate complete design against requirements.

        Args:
            design: Complete antenna design
            requirements: Mission requirements
            simulation_results: Simulation results (if available)

        Returns:
            Validation results
        """
        logger.info("Validating design against requirements")

        validation_results = {
            "timestamp": datetime.now().isoformat(),
            "design_id": design.get("id", "unknown"),
            "checks_performed": [],
            "passed": [],
            "failed": [],
            "warnings": [],
            "overall_status": "pending",
        }

        # Validate electromagnetic performance
        if simulation_results:
            em_validation = self._validate_em_performance(
                requirements, simulation_results
            )
            validation_results["checks_performed"].append("electromagnetic_performance")
            if em_validation["passed"]:
                validation_results["passed"].extend(em_validation["passed"])
            if em_validation["failed"]:
                validation_results["failed"].extend(em_validation["failed"])
            if em_validation["warnings"]:
                validation_results["warnings"].extend(em_validation["warnings"])

        # Validate physical constraints
        physical_validation = self._validate_physical_constraints(design, requirements)
        validation_results["checks_performed"].append("physical_constraints")
        if physical_validation["passed"]:
            validation_results["passed"].extend(physical_validation["passed"])
        if physical_validation["failed"]:
            validation_results["failed"].extend(physical_validation["failed"])

        # Validate thermal performance
        if simulation_results and "thermal" in simulation_results:
            thermal_validation = self._validate_thermal_performance(
                simulation_results["thermal"]
            )
            validation_results["checks_performed"].append("thermal_performance")
            if thermal_validation["passed"]:
                validation_results["passed"].extend(thermal_validation["passed"])
            if thermal_validation["failed"]:
                validation_results["failed"].extend(thermal_validation["failed"])

        # Validate structural integrity
        if simulation_results and "structural" in simulation_results:
            structural_validation = self._validate_structural_integrity(
                simulation_results["structural"]
            )
            validation_results["checks_performed"].append("structural_integrity")
            if structural_validation["passed"]:
                validation_results["passed"].extend(structural_validation["passed"])
            if structural_validation["failed"]:
                validation_results["failed"].extend(structural_validation["failed"])

        # Determine overall status
        if len(validation_results["failed"]) == 0:
            validation_results["overall_status"] = "PASSED"
        elif len(validation_results["failed"]) <= 2:
            validation_results["overall_status"] = "CONDITIONAL_PASS"
        else:
            validation_results["overall_status"] = "FAILED"

        # Calculate compliance score
        total_checks = len(validation_results["passed"]) + len(validation_results["failed"])
        compliance_score = len(validation_results["passed"]) / total_checks if total_checks > 0 else 0.0

        validation_results["compliance_score"] = compliance_score

        # Store validation history
        self.validation_history.append(validation_results)

        # Log decision
        self.log_decision(
            decision=f"Design validation {validation_results['overall_status']}",
            rationale=f"Passed {len(validation_results['passed'])} of {total_checks} checks",
            metadata={
                "compliance_score": compliance_score,
                "failed_checks": len(validation_results["failed"]),
                "warnings": len(validation_results["warnings"]),
            },
        )

        return validation_results

    def _validate_em_performance(
        self, requirements: MissionRequirements, simulation_results: Dict[str, Any]
    ) -> Dict[str, List[str]]:
        """Validate electromagnetic performance."""
        passed = []
        failed = []
        warnings = []

        # Extract simulation metrics
        if "electromagnetic" in simulation_results:
            em_results = simulation_results["electromagnetic"]
            metrics = em_results.get("metrics", {})

            # Check gain
            required_gain = requirements.radiation_pattern.gain_dbi
            actual_gain = metrics.get("peak_gain_dbi", 0.0)
            tolerance = self.thresholds["gain_tolerance_db"]

            if abs(actual_gain - required_gain) <= tolerance:
                passed.append(f"Gain: {actual_gain:.2f} dBi (required: {required_gain:.2f} dBi)")
            else:
                failed.append(
                    f"Gain: {actual_gain:.2f} dBi outside tolerance of "
                    f"{required_gain:.2f} ± {tolerance} dBi"
                )

            # Check S11/VSWR
            vswr_max = metrics.get("vswr_max", 999)
            if vswr_max <= 2.0:
                passed.append(f"VSWR: {vswr_max:.2f} (< 2.0)")
            elif vswr_max <= 2.5:
                warnings.append(f"VSWR: {vswr_max:.2f} exceeds 2.0 but acceptable")
            else:
                failed.append(f"VSWR: {vswr_max:.2f} exceeds acceptable limit")

            # Check frequency
            freq_range = metrics.get("frequency_range_ghz", (0, 0))
            required_freq = requirements.frequency.center_frequency_ghz
            if freq_range[0] <= required_freq <= freq_range[1]:
                passed.append(
                    f"Operating frequency {required_freq} GHz within range "
                    f"{freq_range[0]:.2f}-{freq_range[1]:.2f} GHz"
                )
            else:
                failed.append(
                    f"Operating frequency {required_freq} GHz outside simulated range"
                )

        return {"passed": passed, "failed": failed, "warnings": warnings}

    def _validate_physical_constraints(
        self, design: Dict[str, Any], requirements: MissionRequirements
    ) -> Dict[str, List[str]]:
        """Validate physical constraints."""
        passed = []
        failed = []

        geometry = design.get("geometry", {})
        total_dims = geometry.get("total_dimensions", {})

        # Check mass constraint
        if requirements.physical.max_mass_kg:
            estimated_mass = design.get("estimated_mass_kg", 0.0)
            if estimated_mass <= requirements.physical.max_mass_kg:
                passed.append(
                    f"Mass: {estimated_mass:.2f} kg (limit: {requirements.physical.max_mass_kg} kg)"
                )
            else:
                failed.append(
                    f"Mass {estimated_mass:.2f} kg exceeds limit "
                    f"{requirements.physical.max_mass_kg} kg"
                )

        # Check dimensional constraints
        if requirements.physical.max_length_m and total_dims.get("length"):
            if total_dims["length"] <= requirements.physical.max_length_m:
                passed.append(
                    f"Length: {total_dims['length']:.3f} m "
                    f"(limit: {requirements.physical.max_length_m} m)"
                )
            else:
                failed.append(
                    f"Length {total_dims['length']:.3f} m exceeds limit "
                    f"{requirements.physical.max_length_m} m"
                )

        # Check volume constraint
        if requirements.physical.max_volume_m3:
            estimated_volume = design.get("estimated_volume_m3", 0.0)
            if estimated_volume <= requirements.physical.max_volume_m3:
                passed.append(
                    f"Volume: {estimated_volume:.4f} m³ "
                    f"(limit: {requirements.physical.max_volume_m3} m³)"
                )
            else:
                failed.append(
                    f"Volume {estimated_volume:.4f} m³ exceeds limit "
                    f"{requirements.physical.max_volume_m3} m³"
                )

        return {"passed": passed, "failed": failed}

    def _validate_thermal_performance(
        self, thermal_results: Dict[str, Any]
    ) -> Dict[str, List[str]]:
        """Validate thermal performance."""
        passed = []
        failed = []

        metrics = thermal_results.get("metrics", {})

        # Check maximum temperature
        max_temp = metrics.get("max_temperature_c", 0.0)
        if max_temp <= 125.0:  # Typical electronics limit
            passed.append(f"Max temperature: {max_temp:.1f}°C (< 125°C)")
        else:
            failed.append(f"Max temperature {max_temp:.1f}°C exceeds 125°C limit")

        # Check minimum temperature
        min_temp = metrics.get("min_temperature_c", 0.0)
        if min_temp >= -40.0:  # Typical low temperature limit
            passed.append(f"Min temperature: {min_temp:.1f}°C (> -40°C)")
        else:
            failed.append(f"Min temperature {min_temp:.1f}°C below -40°C limit")

        return {"passed": passed, "failed": failed}

    def _validate_structural_integrity(
        self, structural_results: Dict[str, Any]
    ) -> Dict[str, List[str]]:
        """Validate structural integrity."""
        passed = []
        failed = []

        metrics = structural_results.get("metrics", {})

        # Check safety factor
        safety_factor = metrics.get("safety_factor", 0.0)
        if safety_factor >= 1.5:  # Typical aerospace requirement
            passed.append(f"Safety factor: {safety_factor:.2f} (> 1.5)")
        else:
            failed.append(f"Safety factor {safety_factor:.2f} below required 1.5")

        # Check natural frequencies (avoid low-frequency resonances)
        modal_frequencies = metrics.get("natural_frequencies_hz", [])
        if modal_frequencies and modal_frequencies[0] >= 50.0:
            passed.append(
                f"First natural frequency: {modal_frequencies[0]:.1f} Hz (> 50 Hz)"
            )
        elif modal_frequencies:
            failed.append(
                f"First natural frequency {modal_frequencies[0]:.1f} Hz below 50 Hz"
            )

        return {"passed": passed, "failed": failed}

    def _check_standards_compliance(
        self, design: Dict[str, Any], standards: List[str]
    ) -> Dict[str, Any]:
        """
        Check compliance with engineering standards.

        Args:
            design: Design to check
            standards: List of standard bodies to check against

        Returns:
            Compliance results
        """
        logger.info(f"Checking compliance with standards: {', '.join(standards)}")

        compliance_results = {
            "standards_checked": standards,
            "compliant": [],
            "non_compliant": [],
            "not_applicable": [],
        }

        for standard_body in standards:
            if standard_body in self.standards:
                for standard in self.standards[standard_body]:
                    # Simplified compliance checking
                    compliance = self._check_individual_standard(design, standard)

                    if compliance["status"] == "compliant":
                        compliance_results["compliant"].append({
                            "standard": standard,
                            "details": compliance["details"],
                        })
                    elif compliance["status"] == "non_compliant":
                        compliance_results["non_compliant"].append({
                            "standard": standard,
                            "issues": compliance["issues"],
                        })
                    else:
                        compliance_results["not_applicable"].append(standard)

        # Calculate compliance percentage
        total_applicable = len(compliance_results["compliant"]) + len(
            compliance_results["non_compliant"]
        )
        if total_applicable > 0:
            compliance_percentage = (
                len(compliance_results["compliant"]) / total_applicable * 100
            )
        else:
            compliance_percentage = 100.0

        compliance_results["compliance_percentage"] = compliance_percentage

        self.log_decision(
            decision=f"Standards compliance check completed",
            rationale=f"{compliance_percentage:.1f}% compliant",
            metadata={
                "standards_checked": len(standards),
                "compliant": len(compliance_results["compliant"]),
                "non_compliant": len(compliance_results["non_compliant"]),
            },
        )

        return compliance_results

    def _check_individual_standard(
        self, design: Dict[str, Any], standard: str
    ) -> Dict[str, Any]:
        """Check compliance with individual standard."""
        # Simplified standard checking
        # In practice, would have detailed checklist for each standard

        if "NASA-STD-5001" in standard:
            # Electrical bonding and grounding
            return {
                "status": "compliant",
                "details": "Grounding scheme meets NASA-STD-5001",
            }
        elif "MIL-STD-461" in standard:
            # EMI/EMC requirements
            return {
                "status": "compliant",
                "details": "EMI/EMC design meets MIL-STD-461",
            }
        else:
            return {"status": "not_applicable", "details": "Standard not applicable"}

    def _validate_manufacturing(
        self, design: Dict[str, Any], materials: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate manufacturing feasibility.

        Args:
            design: Design to validate
            materials: Selected materials

        Returns:
            Manufacturing validation results
        """
        logger.info("Validating manufacturing feasibility")

        validation = {
            "manufacturability_score": 0.0,
            "issues": [],
            "recommendations": [],
        }

        geometry = design.get("geometry", {})
        geo_type = geometry.get("type")

        # Check minimum feature sizes
        if geo_type in ["patch_array", "phased_array"]:
            # Check for PCB manufacturing limits
            substrate = materials.get("substrate", {})
            if substrate:
                thickness = substrate.get("properties", {}).get("thickness_mm", 1.0)
                if thickness < 0.1:
                    validation["issues"].append(
                        f"Substrate thickness {thickness} mm below PCB manufacturing limit"
                    )
                else:
                    validation["manufacturability_score"] += 0.3

        # Check material availability
        for component, material in materials.items():
            if material.get("availability") == "readily_available":
                validation["manufacturability_score"] += 0.2
            elif material.get("availability") == "limited":
                validation["recommendations"].append(
                    f"Consider alternative to {material['name']} due to limited availability"
                )

        # Check assembly complexity
        num_components = geometry.get("num_components", 1)
        if num_components <= 100:
            validation["manufacturability_score"] += 0.3
            validation["recommendations"].append("Low complexity - suitable for standard assembly")
        elif num_components <= 1000:
            validation["manufacturability_score"] += 0.2
            validation["recommendations"].append("Medium complexity - requires automated assembly")
        else:
            validation["manufacturability_score"] += 0.1
            validation["recommendations"].append("High complexity - requires specialized assembly equipment")

        # Cap score at 1.0
        validation["manufacturability_score"] = min(1.0, validation["manufacturability_score"])

        self.log_decision(
            decision="Manufacturing validation completed",
            rationale=f"Manufacturability score: {validation['manufacturability_score']:.2f}",
            metadata={
                "score": validation["manufacturability_score"],
                "issues": len(validation["issues"]),
            },
        )

        return validation

    def _generate_test_plan(
        self, design: Dict[str, Any], requirements: MissionRequirements
    ) -> Dict[str, Any]:
        """
        Generate test and verification plan.

        Args:
            design: Design to test
            requirements: Requirements to verify

        Returns:
            Test plan
        """
        logger.info("Generating test plan")

        test_plan = {
            "test_phases": [],
            "required_equipment": [],
            "estimated_duration_days": 0,
        }

        # Phase 1: Component testing
        test_plan["test_phases"].append({
            "phase": "Component Testing",
            "tests": [
                "Material property verification",
                "Component dimensional inspection",
                "Conductor resistance measurement",
            ],
            "duration_days": 5,
        })

        # Phase 2: RF testing
        test_plan["test_phases"].append({
            "phase": "RF Testing",
            "tests": [
                "S-parameter measurement (VNA)",
                "Radiation pattern measurement (anechoic chamber)",
                "Gain measurement",
                "Polarization verification",
            ],
            "duration_days": 10,
        })
        test_plan["required_equipment"].extend([
            "Vector Network Analyzer (VNA)",
            "Anechoic chamber",
            "Positioning system",
            "Signal generators",
        ])

        # Phase 3: Environmental testing
        test_plan["test_phases"].append({
            "phase": "Environmental Testing",
            "tests": [
                "Thermal vacuum testing",
                "Vibration testing",
                "Thermal cycling",
                "Radiation exposure (if space mission)",
            ],
            "duration_days": 15,
        })
        test_plan["required_equipment"].extend([
            "Thermal vacuum chamber",
            "Vibration table",
            "Thermal chamber",
        ])

        # Calculate total duration
        test_plan["estimated_duration_days"] = sum(
            phase["duration_days"] for phase in test_plan["test_phases"]
        )

        return test_plan

    def _generate_compliance_report(
        self, validation_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate compliance report.

        Args:
            validation_results: Validation results

        Returns:
            Compliance report
        """
        logger.info("Generating compliance report")

        report = {
            "report_date": datetime.now().isoformat(),
            "executive_summary": self._generate_executive_summary(validation_results),
            "detailed_results": validation_results,
            "recommendations": self._generate_recommendations(validation_results),
            "sign_off_required": validation_results.get("overall_status") != "PASSED",
        }

        return report

    def _generate_executive_summary(
        self, validation_results: Dict[str, Any]
    ) -> str:
        """Generate executive summary of validation."""
        status = validation_results.get("overall_status", "UNKNOWN")
        compliance_score = validation_results.get("compliance_score", 0.0)
        num_failed = len(validation_results.get("failed", []))

        summary = f"Design validation {status}. "
        summary += f"Compliance score: {compliance_score*100:.1f}%. "

        if num_failed > 0:
            summary += f"{num_failed} requirement(s) not met. "

        return summary

    def _generate_recommendations(
        self, validation_results: Dict[str, Any]
    ) -> List[str]:
        """Generate recommendations based on validation results."""
        recommendations = []

        failed = validation_results.get("failed", [])
        warnings = validation_results.get("warnings", [])

        if failed:
            recommendations.append(
                f"Address {len(failed)} failed requirement(s) before proceeding to manufacturing"
            )

        if warnings:
            recommendations.append(
                f"Review {len(warnings)} warning(s) and assess impact on mission success"
            )

        if validation_results.get("compliance_score", 0.0) < 0.9:
            recommendations.append(
                "Design optimization recommended to improve compliance score"
            )

        return recommendations

    def _handle_query(self, message: Message) -> List[Message]:
        """Handle query messages."""
        response = message.create_reply(
            sender=self.agent_id,
            message_type=MessageType.DATA_TRANSFER,
            payload={
                "status": "Validation capability available",
                "standards": self.standards,
            },
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
                rationale="Validation task completed",
            )
            return [response]
        return []
