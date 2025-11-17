"""
Chain-of-thought reasoning for complex antenna design decisions.

Implements structured reasoning processes that break down complex problems
into steps, enabling transparent and verifiable decision-making.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from loguru import logger

from .llm_interface import LLMInterface, LLMResponse


@dataclass
class ReasoningStep:
    """
    A single step in chain-of-thought reasoning.

    Attributes:
        step_number: Sequential step number
        description: What this step does
        input: Input data for this step
        reasoning: The reasoning process
        output: Output/conclusion from this step
        confidence: Confidence level (0.0 to 1.0)
        timestamp: When this step was executed
    """
    step_number: int
    description: str
    input: Any
    reasoning: str
    output: Any
    confidence: float = 1.0
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'step_number': self.step_number,
            'description': self.description,
            'input': str(self.input),
            'reasoning': self.reasoning,
            'output': str(self.output),
            'confidence': self.confidence,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class ReasoningResult:
    """
    Result of chain-of-thought reasoning process.

    Attributes:
        steps: List of reasoning steps
        final_conclusion: Final decision/output
        overall_confidence: Overall confidence in conclusion
        metadata: Additional metadata
    """
    steps: List[ReasoningStep] = field(default_factory=list)
    final_conclusion: Any = None
    overall_confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_step(self, step: ReasoningStep):
        """Add a reasoning step."""
        self.steps.append(step)

        # Update overall confidence (minimum of all steps)
        if self.steps:
            self.overall_confidence = min(s.confidence for s in self.steps)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'steps': [s.to_dict() for s in self.steps],
            'final_conclusion': str(self.final_conclusion),
            'overall_confidence': self.overall_confidence,
            'num_steps': len(self.steps),
            'metadata': self.metadata
        }

    def get_reasoning_trace(self) -> str:
        """Get formatted reasoning trace."""
        lines = ["Chain-of-Thought Reasoning Trace:", "=" * 60]

        for step in self.steps:
            lines.append(f"\nStep {step.step_number}: {step.description}")
            lines.append(f"Input: {step.input}")
            lines.append(f"Reasoning: {step.reasoning}")
            lines.append(f"Output: {step.output}")
            lines.append(f"Confidence: {step.confidence:.2f}")

        lines.append("\n" + "=" * 60)
        lines.append(f"Final Conclusion: {self.final_conclusion}")
        lines.append(f"Overall Confidence: {self.overall_confidence:.2f}")

        return "\n".join(lines)


class ChainOfThoughtReasoning:
    """
    Implements chain-of-thought reasoning using LLMs.

    Breaks down complex antenna design decisions into step-by-step
    reasoning processes, improving transparency and accuracy.
    """

    def __init__(self, llm: LLMInterface):
        """
        Initialize chain-of-thought reasoning.

        Args:
            llm: LLM interface for generating reasoning steps
        """
        self.llm = llm
        logger.info("Initialized chain-of-thought reasoning")

    def reason(
        self,
        problem: str,
        context: Dict[str, Any],
        num_steps: Optional[int] = None,
        system_prompt: Optional[str] = None
    ) -> ReasoningResult:
        """
        Perform chain-of-thought reasoning on a problem.

        Args:
            problem: Problem statement
            context: Context information
            num_steps: Suggested number of reasoning steps
            system_prompt: Optional system prompt

        Returns:
            ReasoningResult with step-by-step reasoning
        """
        result = ReasoningResult(metadata={'problem': problem, 'context': context})

        # Build initial prompt for structured reasoning
        prompt = self._build_reasoning_prompt(problem, context, num_steps)

        # Get LLM response with chain-of-thought
        response = self.llm.generate(prompt, system_prompt or self._default_system_prompt())

        if not response.is_success():
            logger.error(f"LLM reasoning failed: {response.error}")
            return result

        # Parse reasoning steps from response
        steps = self._parse_reasoning_steps(response.content)

        for step in steps:
            result.add_step(step)

        # Extract final conclusion
        result.final_conclusion = self._extract_conclusion(response.content, steps)

        logger.info(f"Completed reasoning with {len(steps)} steps, confidence: {result.overall_confidence:.2f}")

        return result

    def reason_structured(
        self,
        problem: str,
        context: Dict[str, Any],
        reasoning_template: List[str],
        system_prompt: Optional[str] = None
    ) -> ReasoningResult:
        """
        Perform structured reasoning following a template.

        Args:
            problem: Problem statement
            context: Context information
            reasoning_template: List of reasoning step descriptions
            system_prompt: Optional system prompt

        Returns:
            ReasoningResult following template
        """
        result = ReasoningResult(
            metadata={
                'problem': problem,
                'context': context,
                'template': reasoning_template
            }
        )

        # Execute each step in the template
        for i, step_desc in enumerate(reasoning_template, 1):
            step = self._execute_reasoning_step(
                step_number=i,
                description=step_desc,
                problem=problem,
                context=context,
                previous_steps=result.steps,
                system_prompt=system_prompt
            )

            result.add_step(step)

            # Update context with step output
            context[f'step_{i}_output'] = step.output

        # Generate final conclusion
        result.final_conclusion = self._synthesize_conclusion(
            problem, context, result.steps, system_prompt
        )

        logger.info(f"Completed structured reasoning: {len(result.steps)} steps")

        return result

    def _build_reasoning_prompt(
        self,
        problem: str,
        context: Dict[str, Any],
        num_steps: Optional[int]
    ) -> str:
        """Build prompt for chain-of-thought reasoning."""
        context_str = "\n".join(f"- {k}: {v}" for k, v in context.items())

        step_guidance = ""
        if num_steps:
            step_guidance = f"\nBreak down your reasoning into approximately {num_steps} clear steps."

        prompt = f"""Problem: {problem}

Context:
{context_str}
{step_guidance}

Please solve this problem using step-by-step reasoning:
1. Break down the problem into logical steps
2. For each step:
   - State what you're analyzing
   - Explain your reasoning
   - Draw a conclusion
3. Provide a final recommendation

Use the format:
Step 1: [Description]
Reasoning: [Your reasoning process]
Conclusion: [What you concluded]

Step 2: ...

Final Recommendation: [Your final answer]"""

        return prompt

    def _default_system_prompt(self) -> str:
        """Get default system prompt for reasoning."""
        return """You are an expert antenna engineer using systematic step-by-step reasoning.
For each problem, break down your analysis into clear, logical steps.
Explain your reasoning at each step and state your confidence level.
Be quantitative where possible and cite relevant equations or principles."""

    def _execute_reasoning_step(
        self,
        step_number: int,
        description: str,
        problem: str,
        context: Dict[str, Any],
        previous_steps: List[ReasoningStep],
        system_prompt: Optional[str]
    ) -> ReasoningStep:
        """Execute a single reasoning step."""

        # Build prompt for this step
        prev_outputs = {f"step_{s.step_number}": s.output for s in previous_steps}

        prompt = f"""Problem: {problem}

Step {step_number}: {description}

Context: {context}

Previous Steps: {prev_outputs}

Analyze this step:
1. What input do you need?
2. What is your reasoning process?
3. What is your conclusion?
4. How confident are you (0.0 to 1.0)?

Respond in JSON format:
{{
    "input": "what inputs you're considering",
    "reasoning": "your detailed reasoning",
    "output": "your conclusion",
    "confidence": 0.95
}}"""

        response = self.llm.generate_structured(
            prompt,
            response_schema={
                "input": "string",
                "reasoning": "string",
                "output": "string",
                "confidence": "number"
            },
            system_prompt=system_prompt or self._default_system_prompt()
        )

        if response.is_success() and 'parsed_json' in response.metadata:
            data = response.metadata['parsed_json']
            return ReasoningStep(
                step_number=step_number,
                description=description,
                input=data.get('input', ''),
                reasoning=data.get('reasoning', ''),
                output=data.get('output', ''),
                confidence=float(data.get('confidence', 0.5))
            )
        else:
            # Fallback if structured generation fails
            return ReasoningStep(
                step_number=step_number,
                description=description,
                input=context,
                reasoning=response.content,
                output="Unable to complete step",
                confidence=0.3
            )

    def _parse_reasoning_steps(self, content: str) -> List[ReasoningStep]:
        """Parse reasoning steps from LLM response."""
        steps = []

        # Simple parsing - look for "Step N:" patterns
        lines = content.split('\n')
        current_step = None
        current_content = []

        for line in lines:
            # Check for step header
            if line.strip().startswith('Step '):
                # Save previous step
                if current_step is not None:
                    steps.append(self._create_step_from_content(
                        current_step,
                        '\n'.join(current_content)
                    ))

                # Start new step
                try:
                    step_num = int(line.split(':')[0].replace('Step', '').strip())
                    current_step = step_num
                    current_content = [line.split(':', 1)[1].strip() if ':' in line else '']
                except (ValueError, IndexError):
                    current_content.append(line)
            else:
                if current_step is not None:
                    current_content.append(line)

        # Add last step
        if current_step is not None:
            steps.append(self._create_step_from_content(
                current_step,
                '\n'.join(current_content)
            ))

        return steps

    def _create_step_from_content(self, step_num: int, content: str) -> ReasoningStep:
        """Create ReasoningStep from parsed content."""
        # Extract reasoning and conclusion
        reasoning = ""
        output = ""
        confidence = 0.8

        if 'Reasoning:' in content:
            parts = content.split('Reasoning:', 1)
            if len(parts) > 1:
                reasoning_part = parts[1]

                if 'Conclusion:' in reasoning_part:
                    reasoning, output = reasoning_part.split('Conclusion:', 1)
                    reasoning = reasoning.strip()
                    output = output.strip()
                else:
                    reasoning = reasoning_part.strip()

        return ReasoningStep(
            step_number=step_num,
            description=content.split('\n')[0][:100],
            input="",
            reasoning=reasoning or content,
            output=output or "See reasoning",
            confidence=confidence
        )

    def _extract_conclusion(self, content: str, steps: List[ReasoningStep]) -> str:
        """Extract final conclusion from content."""
        # Look for final recommendation/conclusion
        if 'Final Recommendation:' in content:
            return content.split('Final Recommendation:')[1].strip()
        elif 'Conclusion:' in content:
            # Get last conclusion
            conclusions = content.split('Conclusion:')
            return conclusions[-1].strip()
        elif steps:
            # Use last step output
            return steps[-1].output
        else:
            return content[:200]  # First 200 chars as fallback

    def _synthesize_conclusion(
        self,
        problem: str,
        context: Dict[str, Any],
        steps: List[ReasoningStep],
        system_prompt: Optional[str]
    ) -> str:
        """Synthesize final conclusion from all steps."""
        step_summaries = "\n".join(
            f"Step {s.step_number}: {s.output} (confidence: {s.confidence:.2f})"
            for s in steps
        )

        prompt = f"""Problem: {problem}

Reasoning Steps:
{step_summaries}

Based on the step-by-step analysis above, provide a concise final recommendation
that addresses the original problem. Be specific and actionable."""

        response = self.llm.generate(prompt, system_prompt or self._default_system_prompt())

        return response.content if response.is_success() else "Unable to synthesize conclusion"
