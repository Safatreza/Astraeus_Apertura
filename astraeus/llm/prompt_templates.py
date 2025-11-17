"""
Structured prompt templates for antenna design agents.

Provides reusable prompt templates with variable substitution for
consistent agent interactions with LLMs.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from string import Template
from loguru import logger


@dataclass
class PromptTemplate:
    """
    A reusable prompt template with variable substitution.

    Attributes:
        name: Template identifier
        system_prompt: System-level instructions
        user_template: User prompt template with ${variables}
        response_schema: Optional JSON schema for structured output
        examples: Optional few-shot examples
    """
    name: str
    system_prompt: str
    user_template: str
    response_schema: Optional[Dict[str, Any]] = None
    examples: Optional[List[str]] = None

    def format(self, **kwargs) -> str:
        """
        Format the template with provided variables.

        Args:
            **kwargs: Variables to substitute

        Returns:
            Formatted prompt string
        """
        template = Template(self.user_template)

        try:
            return template.substitute(**kwargs)
        except KeyError as e:
            logger.error(f"Missing template variable: {e}")
            raise

    def format_with_examples(self, **kwargs) -> str:
        """
        Format template including few-shot examples.

        Args:
            **kwargs: Variables to substitute

        Returns:
            Formatted prompt with examples
        """
        prompt_parts = []

        # Add examples if available
        if self.examples:
            prompt_parts.append("Here are some examples:\n")
            for i, example in enumerate(self.examples, 1):
                prompt_parts.append(f"Example {i}:\n{example}\n")
            prompt_parts.append("\n")

        # Add main prompt
        prompt_parts.append(self.format(**kwargs))

        return "\n".join(prompt_parts)


class PromptLibrary:
    """
    Library of prompt templates for antenna design agents.

    Provides structured prompts for each agent type with domain-specific
    knowledge and reasoning patterns.
    """

    def __init__(self):
        """Initialize prompt library with pre-defined templates."""
        self.templates: Dict[str, PromptTemplate] = {}
        self._initialize_templates()

    def _initialize_templates(self):
        """Create all prompt templates."""

        # Requirements Analysis Agent
        self.templates['requirements_analysis'] = PromptTemplate(
            name='requirements_analysis',
            system_prompt="""You are an expert antenna requirements analyst with deep knowledge of:
- Radar system design and link budgets
- Electromagnetic propagation and antenna theory
- RF/microwave engineering principles
- Aerospace and defense requirements standards

Your role is to analyze mission requirements, identify constraints, assess feasibility,
and provide clear recommendations with technical justification.""",
            user_template="""Analyze the following antenna system requirements:

Mission Type: ${mission_type}
Frequency Range: ${frequency_range}
Required Gain: ${gain_requirement}
Beamwidth: ${beamwidth}
Polarization: ${polarization}
Environmental Constraints: ${environment}
Additional Requirements: ${additional_requirements}

Please provide:
1. Feasibility assessment (feasible, challenging, or infeasible)
2. Key technical challenges
3. Recommended antenna architectures (ranked by suitability)
4. Critical constraints and tradeoffs
5. Risk assessment

Be specific and quantitative where possible.""",
            response_schema={
                "feasibility": "string (feasible/challenging/infeasible)",
                "challenges": "list of strings",
                "recommended_architectures": "list of {name, suitability_score, rationale}",
                "constraints": "list of {type, description, severity}",
                "risks": "list of {risk, probability, mitigation}"
            }
        )

        # Architecture Selection Agent
        self.templates['architecture_selection'] = PromptTemplate(
            name='architecture_selection',
            system_prompt="""You are an expert antenna architect with extensive experience in:
- Reflector antennas (parabolic, Cassegrain, Gregorian)
- Phased array systems
- Horn antennas and feeds
- Printed antennas (patch, dipole, slot)
- Lens antennas

You select optimal antenna architectures based on requirements, considering
performance, complexity, cost, and manufacturability.""",
            user_template="""Select the optimal antenna architecture for these requirements:

Frequency: ${frequency_ghz} GHz
Gain: ${gain_dbi} dBi
Beamwidth: ${beamwidth_deg} degrees
Size Constraint: ${size_constraint}
Application: ${application}
Cost Target: ${cost_target}
Manufacturing Constraints: ${manufacturing}

Available architectures:
${available_architectures}

Provide:
1. Recommended architecture with detailed justification
2. Alternative options with pros/cons
3. Expected performance estimates
4. Implementation complexity assessment
5. Cost and schedule implications""",
            response_schema={
                "primary_recommendation": {
                    "architecture": "string",
                    "justification": "string",
                    "estimated_performance": "object",
                    "complexity": "string (low/medium/high)",
                    "cost_estimate": "string"
                },
                "alternatives": "list of architecture options",
                "tradeoffs": "string"
            }
        )

        # Geometry Generation Agent
        self.templates['geometry_generation'] = PromptTemplate(
            name='geometry_generation',
            system_prompt="""You are an expert in antenna geometry design with knowledge of:
- Electromagnetic field theory and radiation patterns
- Aperture theory and diffraction
- Feed design and illumination
- Structural mechanics and thermal considerations

You generate optimized antenna geometries based on electromagnetic principles
and practical manufacturing constraints.""",
            user_template="""Design the geometry for a ${antenna_type} antenna:

Operating Frequency: ${frequency_ghz} GHz (wavelength: ${wavelength_mm} mm)
Target Gain: ${gain_dbi} dBi
Polarization: ${polarization}
Beamwidth: ${beamwidth_deg} degrees
Physical Constraints: ${constraints}

Provide:
1. Complete geometry specification with dimensions
2. Design rationale based on EM theory
3. Expected electrical performance
4. Manufacturing considerations
5. Tolerance analysis

Use standard design equations and cite them in your response.""",
            response_schema={
                "geometry": {
                    "type": "string",
                    "dimensions": "object with all measurements in mm",
                    "materials": "list"
                },
                "design_equations": "list of equations used",
                "expected_performance": "object",
                "tolerances": "object",
                "notes": "string"
            }
        )

        # Material Selection Agent
        self.templates['material_selection'] = PromptTemplate(
            name='material_selection',
            system_prompt="""You are a materials expert specializing in RF/microwave materials with knowledge of:
- Dielectric materials and their properties (εr, tan δ)
- Conductor materials (copper, aluminum, silver)
- Substrate materials for printed antennas
- Environmental resistance (temperature, radiation, moisture)
- Space-qualified materials

You select materials optimized for electrical performance, environmental
requirements, and manufacturing constraints.""",
            user_template="""Select materials for a ${antenna_type} antenna:

Frequency: ${frequency_ghz} GHz
Environment: ${environment}
Temperature Range: ${temperature_range}
Substrate Required: ${requires_substrate}
Special Requirements: ${special_requirements}

Available materials database:
${materials_available}

Provide:
1. Recommended materials for each component
2. Material properties relevant to this application
3. Environmental compatibility assessment
4. Cost and availability considerations
5. Alternative materials if primary unavailable""",
            response_schema={
                "conductor": {
                    "material": "string",
                    "properties": "object",
                    "rationale": "string"
                },
                "substrate": {
                    "material": "string",
                    "properties": "object",
                    "rationale": "string"
                },
                "alternatives": "list",
                "environmental_rating": "string"
            }
        )

        # Performance Optimization Agent
        self.templates['performance_optimization'] = PromptTemplate(
            name='performance_optimization',
            system_prompt="""You are an antenna optimization expert with expertise in:
- Multi-objective optimization techniques
- Antenna parameter tuning
- Tradeoff analysis (gain vs bandwidth vs size)
- Numerical optimization methods

You analyze simulation results, identify improvement opportunities, and
recommend parameter adjustments to optimize antenna performance.""",
            user_template="""Optimize this antenna design:

Current Design:
${current_design}

Current Performance:
Gain: ${current_gain_dbi} dBi (target: ${target_gain_dbi} dBi)
VSWR: ${current_vswr} (target: < ${target_vswr})
Bandwidth: ${current_bandwidth_mhz} MHz (target: ${target_bandwidth_mhz} MHz)
Efficiency: ${current_efficiency}% (target: > ${target_efficiency}%)

Simulation Results:
${simulation_results}

Constraints:
${constraints}

Provide:
1. Analysis of current performance gaps
2. Recommended parameter adjustments
3. Expected performance improvements
4. Optimization strategy (sequential vs multi-objective)
5. Sensitivity analysis of key parameters""",
            response_schema={
                "performance_gaps": "list of {metric, current, target, gap}",
                "recommended_adjustments": "list of {parameter, current_value, new_value, rationale}",
                "expected_improvements": "object",
                "optimization_strategy": "string",
                "sensitivity": "object"
            }
        )

        # Validation Agent
        self.templates['validation'] = PromptTemplate(
            name='validation',
            system_prompt="""You are a validation expert ensuring antenna designs meet all requirements and constraints.
You have deep knowledge of:
- RF/antenna measurement techniques
- Standards (MIL-STD, NASA, ESA)
- Physics-based sanity checks
- Requirements traceability

You verify designs against requirements, check for physical inconsistencies,
and identify potential issues before fabrication.""",
            user_template="""Validate this antenna design:

Requirements:
${requirements}

Design Parameters:
${design_parameters}

Simulated Performance:
${performance_metrics}

Please check:
1. Requirements compliance (each requirement)
2. Physics-based sanity checks (Chu-Harrington limit, aperture-gain relationship, etc.)
3. Manufacturing feasibility
4. Environmental compliance
5. Standards conformance

For each check, provide: PASS/FAIL/WARNING with detailed explanation.""",
            response_schema={
                "overall_status": "string (PASS/FAIL/WARNING)",
                "requirements_compliance": "list of {requirement, status, details}",
                "physics_checks": "list of {check_name, status, details}",
                "manufacturing_checks": "list",
                "recommendations": "list of strings",
                "showstoppers": "list of critical issues"
            }
        )

        # Supervisor Agent
        self.templates['supervisor_decision'] = PromptTemplate(
            name='supervisor_decision',
            system_prompt="""You are a senior technical lead overseeing antenna design projects.
You coordinate multiple specialist agents, resolve conflicts, make strategic
decisions, and ensure efficient progress toward design goals.

You have a broad understanding of antenna engineering and project management.""",
            user_template="""Make a strategic decision for this antenna design project:

Current Status:
${current_status}

Agent Recommendations:
${agent_recommendations}

Conflicts/Issues:
${conflicts}

Project Constraints:
- Budget: ${budget}
- Schedule: ${schedule}
- Risk Tolerance: ${risk_tolerance}

Provide:
1. Decision on how to proceed
2. Rationale considering all inputs
3. Task assignments for agents
4. Risk mitigation steps
5. Success criteria for next iteration""",
            response_schema={
                "decision": "string",
                "rationale": "string",
                "task_assignments": "list of {agent, task, priority, deadline}",
                "risks": "list of {risk, mitigation}",
                "success_criteria": "list of strings"
            }
        )

        logger.info(f"Initialized {len(self.templates)} prompt templates")

    def get_template(self, name: str) -> Optional[PromptTemplate]:
        """
        Get prompt template by name.

        Args:
            name: Template identifier

        Returns:
            PromptTemplate or None if not found
        """
        return self.templates.get(name)

    def list_templates(self) -> List[str]:
        """Get list of available template names."""
        return list(self.templates.keys())

    def add_template(self, template: PromptTemplate):
        """
        Add a custom template to the library.

        Args:
            template: PromptTemplate to add
        """
        self.templates[template.name] = template
        logger.info(f"Added custom template: {template.name}")
