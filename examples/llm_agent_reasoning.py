"""
LLM-Powered Agent Reasoning Example.

Demonstrates using LLMs (OpenAI GPT or Anthropic Claude) for intelligent
antenna design decision-making with:
- Structured prompts
- Chain-of-thought reasoning
- Few-shot learning
- Notion database integration for parameters
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from astraeus.llm import (
    LLMInterface,
    LLMConfig,
    LLMProvider,
    PromptLibrary,
    ChainOfThoughtReasoning,
    FewShotLibrary,
    create_llm
)
from astraeus.integrations import NotionClient


def example_requirements_analysis_openai():
    """Example: Use OpenAI GPT for requirements analysis."""
    print("="*70)
    print("REQUIREMENTS ANALYSIS WITH OPENAI GPT")
    print("="*70)
    print()

    # Check for API key
    if not os.getenv('OPENAI_API_KEY'):
        print("ERROR: OPENAI_API_KEY environment variable not set")
        print("Set it with: export OPENAI_API_KEY='your-key-here'")
        return

    # Initialize OpenAI LLM
    config = LLMConfig(
        provider=LLMProvider.OPENAI,
        model="gpt-4",
        temperature=0.7,
        max_tokens=2000
    )

    llm = create_llm(config)
    print(f"Initialized {config.provider.value} with model {config.model}")
    print()

    # Get prompt template
    prompt_library = PromptLibrary()
    template = prompt_library.get_template('requirements_analysis')

    # Get few-shot examples
    few_shot = FewShotLibrary()
    examples_text = few_shot.format_examples('requirements_analysis', limit=2)

    # Create prompt with mission requirements
    user_prompt = template.format(
        mission_type="Satellite Communication Ground Station",
        frequency_range="10.7 - 12.75 GHz (Ku-band downlink)",
        gain_requirement="> 35 dBi",
        beamwidth="< 3 degrees",
        polarization="Circular (RHCP or LHCP selectable)",
        environment="Outdoor, -20°C to +50°C, wind loading up to 150 km/h",
        additional_requirements="Automatic tracking, low maintenance, budget < $100K"
    )

    # Add few-shot examples
    full_prompt = examples_text + "\n\n" + user_prompt

    print("Analyzing requirements with GPT-4...")
    print()

    # Generate response
    response = llm.generate(
        prompt=full_prompt,
        system_prompt=template.system_prompt
    )

    if response.is_success():
        print("ANALYSIS RESULT:")
        print("-" * 70)
        print(response.content)
        print()
        print(f"Tokens used: {response.usage.get('total_tokens', 'N/A')}")
    else:
        print(f"ERROR: {response.error}")

    print()


def example_chain_of_thought_reasoning():
    """Example: Chain-of-thought reasoning for architecture selection."""
    print("="*70)
    print("CHAIN-OF-THOUGHT REASONING FOR ARCHITECTURE SELECTION")
    print("="*70)
    print()

    # Check for API key (trying Anthropic first, OpenAI as fallback)
    if os.getenv('ANTHROPIC_API_KEY'):
        config = LLMConfig(
            provider=LLMProvider.ANTHROPIC,
            model="claude-3-5-sonnet-20241022",
            temperature=0.7
        )
        print("Using Anthropic Claude")
    elif os.getenv('OPENAI_API_KEY'):
        config = LLMConfig(
            provider=LLMProvider.OPENAI,
            model="gpt-4",
            temperature=0.7
        )
        print("Using OpenAI GPT-4")
    else:
        print("ERROR: No API key found. Set ANTHROPIC_API_KEY or OPENAI_API_KEY")
        return

    llm = create_llm(config)
    print()

    # Initialize chain-of-thought reasoning
    cot = ChainOfThoughtReasoning(llm)

    # Define the problem
    problem = """Select the optimal antenna architecture for a weather radar system
operating at 5.6 GHz with requirements: 45 dBi gain, scanning coverage of ±60°,
update rate of 2 Hz, and operating in harsh outdoor conditions."""

    context = {
        "frequency": "5.6 GHz (C-band)",
        "wavelength": "53.6 mm",
        "gain_requirement": "45 dBi",
        "scan_range": "±60° (120° total)",
        "update_rate": "2 Hz (0.5 second per scan)",
        "environment": "Outdoor, rain, wind, temperature extremes",
        "budget_constraint": "Moderate ($200K - $500K range)",
    }

    # Define structured reasoning steps
    reasoning_template = [
        "Calculate the required aperture size based on gain requirement",
        "Evaluate mechanical scanning vs electronic scanning for the update rate",
        "Assess candidate architectures (reflector, phased array, hybrid)",
        "Analyze cost-performance tradeoffs for each option",
        "Consider environmental robustness and maintenance requirements",
        "Make final recommendation with justification"
    ]

    print("Performing structured chain-of-thought reasoning...")
    print()

    # Execute reasoning
    result = cot.reason_structured(
        problem=problem,
        context=context,
        reasoning_template=reasoning_template
    )

    # Display results
    print(result.get_reasoning_trace())
    print()

    # Show confidence scores
    print("STEP CONFIDENCE SCORES:")
    for step in result.steps:
        print(f"  Step {step.step_number}: {step.confidence:.2f} - {step.description[:50]}...")

    print()


def example_notion_integration():
    """Example: Fetch antenna parameters from Notion database."""
    print("="*70)
    print("NOTION DATABASE INTEGRATION")
    print("="*70)
    print()

    # Check for Notion API key
    if not os.getenv('NOTION_API_KEY'):
        print("ERROR: NOTION_API_KEY environment variable not set")
        print()
        print("To use Notion integration:")
        print("1. Create a Notion integration at https://www.notion.so/my-integrations")
        print("2. Get your integration token")
        print("3. Share your database with the integration")
        print("4. Set environment variable: export NOTION_API_KEY='your-token'")
        print()
        print("Creating demo data instead...")
        print()

        # Show what the integration would do
        demo_parameters = [
            {
                'mission_name': 'LEO Satcom Ground Terminal',
                'frequency_ghz': 11.5,
                'gain_dbi': 38.0,
                'beamwidth_deg': 2.5,
                'polarization': 'Circular',
                'application': 'Satellite downlink reception'
            },
            {
                'mission_name': 'Weather Radar',
                'frequency_ghz': 5.6,
                'gain_dbi': 45.0,
                'beamwidth_deg': 1.5,
                'polarization': 'Horizontal',
                'application': 'Precipitation detection'
            }
        ]

        print("DEMO: Example antenna parameters from Notion:")
        print()
        for i, params in enumerate(demo_parameters, 1):
            print(f"Design {i}: {params['mission_name']}")
            print(f"  Frequency: {params['frequency_ghz']} GHz")
            print(f"  Gain: {params['gain_dbi']} dBi")
            print(f"  Beamwidth: {params['beamwidth_deg']}°")
            print(f"  Polarization: {params['polarization']}")
            print(f"  Application: {params['application']}")
            print()

        return demo_parameters

    # Initialize Notion client
    try:
        notion = NotionClient()
        print("✓ Connected to Notion")
        print()

        # You would need to replace this with your actual database ID
        database_id = os.getenv('NOTION_DATABASE_ID', 'your-database-id-here')

        if database_id == 'your-database-id-here':
            print("NOTE: Set NOTION_DATABASE_ID environment variable to your database ID")
            print()
            return []

        # Fetch antenna parameters
        print(f"Fetching parameters from database: {database_id}")
        parameters = notion.fetch_antenna_parameters(database_id)

        print(f"Retrieved {len(parameters)} parameter sets:")
        print()

        for i, params in enumerate(parameters, 1):
            print(f"Parameter Set {i}:")
            for key, value in params.items():
                if key not in ['notion_page_id', 'created_time', 'last_edited_time']:
                    print(f"  {key}: {value}")
            print()

        return parameters

    except Exception as e:
        print(f"ERROR: {e}")
        return []


def example_llm_with_notion():
    """Example: Combine LLM reasoning with Notion parameters."""
    print("="*70)
    print("COMBINED: LLM REASONING + NOTION PARAMETERS")
    print("="*70)
    print()

    # Get parameters (from Notion or demo)
    parameters = example_notion_integration()

    if not parameters:
        print("No parameters available, skipping LLM analysis")
        return

    # Check for LLM API key
    if not os.getenv('ANTHROPIC_API_KEY') and not os.getenv('OPENAI_API_KEY'):
        print("No LLM API key found, skipping analysis")
        return

    # Initialize LLM
    if os.getenv('ANTHROPIC_API_KEY'):
        config = LLMConfig(provider=LLMProvider.ANTHROPIC)
    else:
        config = LLMConfig(provider=LLMProvider.OPENAI, model="gpt-4")

    llm = create_llm(config)

    # Get architecture selection template
    prompt_library = PromptLibrary()
    template = prompt_library.get_template('architecture_selection')

    # Analyze first parameter set
    params = parameters[0]

    print(f"Analyzing: {params.get('mission_name', 'Unknown Mission')}")
    print()

    freq = params.get('frequency_ghz') or params.get('Frequency (GHz)', 10.0)
    gain = params.get('gain_dbi') or params.get('Gain (dBi)', 30.0)
    beamwidth = params.get('beamwidth_deg') or params.get('Beamwidth (deg)', 5.0)

    prompt = template.format(
        frequency_ghz=freq,
        gain_dbi=gain,
        beamwidth_deg=beamwidth,
        size_constraint="< 3 meters diameter",
        application=params.get('application', 'General purpose'),
        cost_target="Moderate ($100K-$500K)",
        manufacturing="Standard RF manufacturing",
        available_architectures="Parabolic reflector, Cassegrain, Phased array, Horn array"
    )

    print("Requesting LLM analysis...")
    print()

    response = llm.generate(prompt, template.system_prompt)

    if response.is_success():
        print("RECOMMENDATION:")
        print("-" * 70)
        print(response.content)
        print()
    else:
        print(f"ERROR: {response.error}")


if __name__ == '__main__':
    print()
    print("="*70)
    print("LLM-POWERED ANTENNA DESIGN AGENT")
    print("="*70)
    print()
    print("This example demonstrates AI-powered antenna design decision-making")
    print()

    # Check what's available
    has_anthropic = bool(os.getenv('ANTHROPIC_API_KEY'))
    has_openai = bool(os.getenv('OPENAI_API_KEY'))
    has_notion = bool(os.getenv('NOTION_API_KEY'))

    print("API Keys Status:")
    print(f"  Anthropic Claude: {'✓' if has_anthropic else '✗'}")
    print(f"  OpenAI GPT:       {'✓' if has_openai else '✗'}")
    print(f"  Notion:           {'✓' if has_notion else '✗'}")
    print()

    if not has_anthropic and not has_openai:
        print("WARNING: No LLM API keys found. Set ANTHROPIC_API_KEY or OPENAI_API_KEY")
        print("Some examples will be skipped.")
        print()

    # Run examples
    try:
        # Example 1: Requirements analysis with OpenAI
        if has_openai:
            example_requirements_analysis_openai()

        # Example 2: Chain-of-thought reasoning
        if has_anthropic or has_openai:
            example_chain_of_thought_reasoning()

        # Example 3: Notion integration
        example_notion_integration()

        # Example 4: Combined LLM + Notion
        if (has_anthropic or has_openai):
            print()
            example_llm_with_notion()

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()

    print()
    print("="*70)
    print("Example complete!")
    print()
    print("Next steps:")
    print("  1. Set up API keys for Claude/GPT and Notion")
    print("  2. Create a Notion database with antenna requirements")
    print("  3. Run parametric sweeps with LLM-guided optimization")
    print("  4. Use chain-of-thought for complex design decisions")
    print()
