"""
Few-shot learning examples for antenna design agents.

Provides curated examples for few-shot prompting to improve LLM performance
on antenna design tasks.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from loguru import logger


@dataclass
class FewShotExample:
    """
    A few-shot learning example.

    Attributes:
        input: Example input
        output: Expected output
        explanation: Optional explanation of the reasoning
        tags: Optional tags for filtering examples
    """
    input: str
    output: str
    explanation: Optional[str] = None
    tags: List[str] = None

    def format(self) -> str:
        """Format as a prompt example."""
        parts = [f"Input: {self.input}", f"Output: {self.output}"]

        if self.explanation:
            parts.append(f"Explanation: {self.explanation}")

        return "\n".join(parts)


class FewShotLibrary:
    """
    Library of few-shot examples for antenna design tasks.

    Provides domain-specific examples to improve LLM performance through
    in-context learning.
    """

    def __init__(self):
        """Initialize few-shot library."""
        self.examples: Dict[str, List[FewShotExample]] = {}
        self._initialize_examples()

    def _initialize_examples(self):
        """Create few-shot examples for each task type."""

        # Requirements Analysis Examples
        self.examples['requirements_analysis'] = [
            FewShotExample(
                input="Mission: Satellite communication downlink, Frequency: 12 GHz, Gain: > 30 dBi, Beamwidth: 2°",
                output="FEASIBLE - Recommend parabolic reflector (1.5m diameter) or 64-element phased array. Key challenge: precise pointing for narrow beam. Cost estimate: $50K-$200K depending on approach.",
                explanation="High gain + narrow beam suggests reflector or large array. 12 GHz is Ku-band, well-established technology.",
                tags=["satellite", "downlink", "high-gain"]
            ),
            FewShotExample(
                input="Mission: Weather radar, Frequency: 5.6 GHz, Gain: 45 dBi, Scan: ±60°, Update rate: 1 Hz",
                output="CHALLENGING - Recommend mechanically scanned parabolic reflector (3m) or expensive phased array. Electronic scanning at this gain level requires 1000+ elements. Mechanical scanning achievable but limits update rate.",
                explanation="45 dBi requires very large aperture. Wide scan + fast update favors electronic, but cost is prohibitive.",
                tags=["radar", "scanning", "high-gain"]
            ),
        ]

        # Architecture Selection Examples
        self.examples['architecture_selection'] = [
            FewShotExample(
                input="10 GHz, 15 dBi gain, hemispheric coverage, airborne platform",
                output="Primary: Horn antenna array (4×4). Rationale: Wide coverage, lightweight, simple. Estimated gain per element: 10 dBi, array gain: 16 dBi. Alternative: Microstrip patch array (lighter but narrower bandwidth).",
                explanation="Hemispheric coverage rules out reflector. Horn array provides robustness for airborne environment.",
                tags=["airborne", "wide-coverage", "x-band"]
            ),
        ]

        # Geometry Design Examples
        self.examples['geometry_generation'] = [
            FewShotExample(
                input="Patch antenna, 2.4 GHz, FR4 substrate (εr=4.4, h=1.6mm), 50Ω feed",
                output="""Dimensions:
- Width (W): 38.0 mm (using W = c/(2×f₀×√((εr+1)/2)))
- Length (L): 29.3 mm (accounting for fringe effects)
- Feed point: 10.8 mm from edge for 50Ω match
- Ground plane: minimum 60mm × 60mm

Expected: Gain ~6-7 dBi, VSWR < 2, Bandwidth ~80 MHz""",
                explanation="Used standard microstrip patch equations with fringe field corrections.",
                tags=["patch", "microstrip", "2.4ghz"]
            ),
        ]

        # Material Selection Examples
        self.examples['material_selection'] = [
            FewShotExample(
                input="Space-qualified, X-band (8-12 GHz), LEO environment, -100°C to +100°C",
                output="""Recommendations:
- Substrate: Rogers RO4003C (εr=3.38, low outgassing, space-qualified)
- Conductor: Electrodeposited copper (35μm) with gold plating
- Adhesive: Vacuum-compatible epoxy
- Radome: Quartz or alumina (low loss at X-band, radiation hard)

All materials meet NASA outgassing requirements (TML <1%, CVCM <0.1%)""",
                explanation="Space environment requires low outgassing, radiation resistance, wide temperature range.",
                tags=["space", "x-band", "leo"]
            ),
        ]

        # Optimization Examples
        self.examples['performance_optimization'] = [
            FewShotExample(
                input="Current: Gain=7.2 dBi (target: 8 dBi), VSWR=2.5 (target: <2.0), patch antenna",
                output="""Analysis:
- Gain is 0.8 dB below target (small gap, likely efficiency issue)
- VSWR indicates impedance mismatch

Recommendations:
1. Adjust feed point position: move 2mm toward center (improves matching)
2. Increase patch length by 0.5mm (improves gain via better resonance)
3. Add impedance matching network if feed adjustment insufficient

Expected improvement: Gain → 8.1 dBi, VSWR → 1.6""",
                explanation="VSWR problem suggests feed mismatch. Small gain gap suggests minor geometry tuning needed.",
                tags=["patch", "impedance-matching", "optimization"]
            ),
        ]

        logger.info(f"Initialized {sum(len(exs) for exs in self.examples.values())} few-shot examples")

    def get_examples(
        self,
        task_type: str,
        tags: Optional[List[str]] = None,
        limit: Optional[int] = None
    ) -> List[FewShotExample]:
        """
        Get few-shot examples for a task type.

        Args:
            task_type: Type of task (e.g., 'requirements_analysis')
            tags: Optional tags to filter examples
            limit: Maximum number of examples to return

        Returns:
            List of FewShotExample objects
        """
        examples = self.examples.get(task_type, [])

        # Filter by tags if provided
        if tags:
            examples = [ex for ex in examples if ex.tags and any(tag in ex.tags for tag in tags)]

        # Limit if requested
        if limit:
            examples = examples[:limit]

        return examples

    def format_examples(
        self,
        task_type: str,
        tags: Optional[List[str]] = None,
        limit: Optional[int] = 3
    ) -> str:
        """
        Get formatted few-shot examples as a string.

        Args:
            task_type: Type of task
            tags: Optional tags to filter
            limit: Maximum number of examples

        Returns:
            Formatted string with examples
        """
        examples = self.get_examples(task_type, tags, limit)

        if not examples:
            return ""

        formatted = ["Here are some examples:\n"]

        for i, example in enumerate(examples, 1):
            formatted.append(f"Example {i}:")
            formatted.append(example.format())
            formatted.append("")  # Blank line

        return "\n".join(formatted)

    def add_example(self, task_type: str, example: FewShotExample):
        """
        Add a new example to the library.

        Args:
            task_type: Task type to add example to
            example: FewShotExample to add
        """
        if task_type not in self.examples:
            self.examples[task_type] = []

        self.examples[task_type].append(example)
        logger.info(f"Added example to {task_type}")

    def list_task_types(self) -> List[str]:
        """Get list of available task types."""
        return list(self.examples.keys())
