## LLM-Powered Intelligent Agent Reasoning

This module provides Large Language Model (LLM) integration for Astraeus Apertura, enabling intelligent decision-making through:
- Natural language understanding of antenna requirements
- Chain-of-thought reasoning for complex design problems
- Few-shot learning from examples
- Structured prompts for each agent type

## Features

- **Multiple LLM Providers**: Anthropic Claude, OpenAI GPT, local models (Ollama)
- **Structured Prompts**: Pre-built templates for each agent type
- **Chain-of-Thought**: Step-by-step reasoning with transparency
- **Few-Shot Learning**: In-context learning from examples
- **Notion Integration**: Fetch design parameters from Notion databases

## Quick Start

### Basic LLM Usage

```python
from astraeus.llm import create_llm, LLMConfig, LLMProvider

# Using Anthropic Claude (recommended for reasoning tasks)
config = LLMConfig(
    provider=LLMProvider.ANTHROPIC,
    model="claude-3-5-sonnet-20241022",
    api_key="your-api-key"  # or set ANTHROPIC_API_KEY env var
)

llm = create_llm(config)

response = llm.generate(
    prompt="Analyze requirements for a 10 GHz satellite ground terminal antenna...",
    system_prompt="You are an expert antenna engineer."
)

print(response.content)
```

### Using OpenAI GPT

```python
config = LLMConfig(
    provider=LLMProvider.OPENAI,
    model="gpt-4",
    api_key="your-api-key"  # or set OPENAI_API_KEY env var
)

llm = create_llm(config)
```

### Chain-of-Thought Reasoning

```python
from astraeus.llm import ChainOfThoughtReasoning

cot = ChainOfThoughtReasoning(llm)

problem = "Select optimal antenna for weather radar at 5.6 GHz, 45 dBi gain, ±60° scan"
context = {
    "frequency": "5.6 GHz",
    "gain_requirement": "45 dBi",
    "scan_range": "±60°"
}

# Structured reasoning with predefined steps
reasoning_steps = [
    "Calculate required aperture size",
    "Evaluate scanning options (mechanical vs electronic)",
    "Compare candidate architectures",
    "Make recommendation with tradeoffs"
]

result = cot.reason_structured(problem, context, reasoning_steps)

# Display reasoning trace
print(result.get_reasoning_trace())
```

### Using Prompt Templates

```python
from astraeus.llm import PromptLibrary

library = PromptLibrary()

# Get requirements analysis template
template = library.get_template('requirements_analysis')

# Format with specific values
prompt = template.format(
    mission_type="Satellite Downlink",
    frequency_range="10.7-12.75 GHz",
    gain_requirement="> 35 dBi",
    beamwidth="< 3 degrees",
    polarization="Circular RHCP",
    environment="Outdoor, -20°C to +50°C",
    additional_requirements="Automatic tracking, low maintenance"
)

# Generate analysis
response = llm.generate(prompt, template.system_prompt)
```

### Few-Shot Learning

```python
from astraeus.llm import FewShotLibrary

few_shot = FewShotLibrary()

# Get examples for architecture selection
examples = few_shot.format_examples('architecture_selection', limit=3)

# Add examples to your prompt
full_prompt = examples + "\n\n" + your_prompt

response = llm.generate(full_prompt)
```

### Notion Database Integration

```python
from astraeus.integrations import NotionClient

# Initialize (uses NOTION_API_KEY environment variable)
notion = NotionClient()

# Fetch antenna parameters from database
database_id = "your-database-id"
parameters = notion.fetch_antenna_parameters(database_id)

# Use parameters with LLM
for params in parameters:
    print(f"Analyzing: {params['Name']}")

    # Feed to LLM for analysis
    prompt = f"Recommend antenna architecture for {params['Name']}, freq={params['Frequency (GHz)']} GHz, gain={params['Gain (dBi)']} dBi"

    response = llm.generate(prompt)
    print(response.content)
```

## Available Prompt Templates

The `PromptLibrary` includes templates for:

1. **requirements_analysis**: Analyze mission requirements and assess feasibility
2. **architecture_selection**: Select optimal antenna architecture
3. **geometry_generation**: Design antenna geometry with dimensions
4. **material_selection**: Choose materials for components
5. **performance_optimization**: Optimize design parameters
6. **validation**: Validate design against requirements
7. **supervisor_decision**: High-level decision-making

Access templates:
```python
library = PromptLibrary()
print(library.list_templates())

template = library.get_template('architecture_selection')
```

## Chain-of-Thought Reasoning

### Free-Form Reasoning

```python
result = cot.reason(
    problem="How to achieve 50 dBi gain at 24 GHz within 1m diameter constraint?",
    context={"wavelength": "12.5mm", "max_diameter": "1000mm"},
    num_steps=5
)

# Access reasoning steps
for step in result.steps:
    print(f"Step {step.step_number}: {step.description}")
    print(f"Reasoning: {step.reasoning}")
    print(f"Confidence: {step.confidence}")
```

### Structured Reasoning

```python
reasoning_template = [
    "Calculate wavelength and maximum aperture area",
    "Determine theoretical maximum gain from aperture",
    "Evaluate reflector vs phased array options",
    "Consider feed design and efficiency losses",
    "Recommend optimal solution"
]

result = cot.reason_structured(problem, context, reasoning_template)

print(f"Conclusion: {result.final_conclusion}")
print(f"Overall Confidence: {result.overall_confidence}")
```

## Notion Database Setup

### Create Antenna Requirements Database

1. Create a Notion page with a database
2. Add these properties:
   - **Name** (Title): Mission/design name
   - **Frequency (GHz)** (Number): Operating frequency
   - **Gain (dBi)** (Number): Required gain
   - **Beamwidth (deg)** (Number): Beamwidth
   - **Polarization** (Select): Linear/Circular/RHCP/LHCP
   - **Application** (Text): Description
   - **Status** (Select): Pending/In Progress/Complete

3. Create a Notion integration:
   - Go to https://www.notion.so/my-integrations
   - Create new integration
   - Copy the integration token
   - Share your database with the integration

4. Set environment variable:
```bash
export NOTION_API_KEY='your-integration-token'
export NOTION_DATABASE_ID='your-database-id'
```

### Add Parameters Programmatically

```python
notion = NotionClient()

# Create a requirements page
page = notion.create_antenna_requirements_page(
    database_id="your-database-id",
    mission_name="X-Band Satellite Terminal",
    frequency_ghz=10.5,
    gain_dbi=38.0,
    beamwidth_deg=2.5,
    polarization="Circular",
    application="LEO satellite downlink"
)
```

## LLM Configuration

### Anthropic Claude

```python
config = LLMConfig(
    provider=LLMProvider.ANTHROPIC,
    model="claude-3-5-sonnet-20241022",  # Latest Sonnet
    # model="claude-3-opus-20240229",  # Most capable
    # model="claude-3-haiku-20240307",  # Fastest, cheapest
    temperature=0.7,  # 0.0 = deterministic, 1.0 = creative
    max_tokens=4096
)
```

### OpenAI GPT

```python
config = LLMConfig(
    provider=LLMProvider.OPENAI,
    model="gpt-4",  # Most capable
    # model="gpt-4-turbo-preview",  # Faster, cheaper
    # model="gpt-3.5-turbo",  # Fastest, cheapest
    temperature=0.7,
    max_tokens=2000,
    top_p=0.9
)
```

### Local Models (Ollama)

```python
config = LLMConfig(
    provider=LLMProvider.LOCAL,
    model="llama2",  # or mistral, codellama, etc.
    base_url="http://localhost:11434",
    temperature=0.7
)
```

## Best Practices

### 1. Use Appropriate Models

- **Complex reasoning**: Claude 3.5 Sonnet or GPT-4
- **Fast iterations**: Claude Haiku or GPT-3.5 Turbo
- **Cost-sensitive**: Local models via Ollama
- **Privacy-sensitive**: Local models only

### 2. Optimize Temperature

```python
# For technical analysis (deterministic)
config.temperature = 0.3

# For creative brainstorming
config.temperature = 0.9

# Balanced (default)
config.temperature = 0.7
```

### 3. Use System Prompts

```python
system_prompt = """You are an expert RF engineer with 20 years of experience
in antenna design for aerospace applications. Always provide quantitative analysis
and cite relevant equations or standards."""

response = llm.generate(user_prompt, system_prompt)
```

### 4. Add Domain Context

```python
# Bad: Too vague
prompt = "Design an antenna"

# Good: Specific with context
prompt = """Design a patch antenna for 2.4 GHz ISM band.
Requirements:
- Frequency: 2.4 - 2.5 GHz
- Gain: > 6 dBi
- Substrate: FR4 (εr=4.4, h=1.6mm)
- Polarization: Linear
- Feed: 50Ω microstrip

Provide dimensions and expected performance."""
```

### 5. Leverage Few-Shot Examples

```python
few_shot = FewShotLibrary()
examples = few_shot.format_examples(task_type, limit=2)

prompt = examples + "\n\nNow analyze this new case:\n" + your_case
```

### 6. Parse Structured Responses

```python
schema = {
    "recommendation": "string",
    "dimensions": {
        "length_mm": "number",
        "width_mm": "number"
    },
    "expected_gain_dbi": "number",
    "confidence": "number (0.0-1.0)"
}

response = llm.generate_structured(prompt, response_schema)

if 'parsed_json' in response.metadata:
    data = response.metadata['parsed_json']
    print(f"Gain: {data['expected_gain_dbi']} dBi")
```

## Integration with Agents

### Enhance Existing Agents

```python
from astraeus.agents import RequirementsAnalyst
from astraeus.llm import create_llm, LLMConfig, PromptLibrary

# Create LLM-enhanced agent
class LLMRequirementsAnalyst(RequirementsAnalyst):
    def __init__(self, *args, llm_config=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.llm = create_llm(llm_config) if llm_config else None
        self.prompt_library = PromptLibrary()

    def _analyze_with_llm(self, requirements):
        template = self.prompt_library.get_template('requirements_analysis')

        prompt = template.format(
            mission_type=requirements.mission_type,
            frequency_range=f"{requirements.frequency_min}-{requirements.frequency_max} GHz",
            gain_requirement=f"> {requirements.min_gain_dbi} dBi",
            # ... other parameters
        )

        response = self.llm.generate(prompt, template.system_prompt)

        return self._parse_llm_analysis(response.content)
```

## Error Handling

```python
response = llm.generate(prompt)

if not response.is_success():
    print(f"LLM Error: {response.error}")

    # Fallback to rule-based approach
    result = fallback_analysis(requirements)
else:
    result = parse_llm_response(response.content)
```

## Cost Management

### Token Usage Tracking

```python
total_tokens = 0
total_cost = 0

response = llm.generate(prompt)

if 'input_tokens' in response.usage:
    input_tokens = response.usage['input_tokens']
    output_tokens = response.usage['output_tokens']

    # Claude pricing (example, check current rates)
    cost = (input_tokens * 0.000003) + (output_tokens * 0.000015)

    total_tokens += input_tokens + output_tokens
    total_cost += cost

print(f"Total tokens: {total_tokens}, Cost: ${total_cost:.4f}")
```

### Caching Prompts

```python
# Cache system prompts and examples to reduce input tokens
cache = {}

def get_cached_prompt(key, generator_func):
    if key not in cache:
        cache[key] = generator_func()
    return cache[key]

system_prompt = get_cached_prompt('requirements_system',
    lambda: template.system_prompt)
```

## Examples

See `examples/llm_agent_reasoning.py` for complete examples:
- Requirements analysis with GPT-4
- Chain-of-thought architecture selection
- Notion database integration
- Combined LLM + Notion workflow

Run:
```bash
# Set API keys
export ANTHROPIC_API_KEY='your-key'
export OPENAI_API_KEY='your-key'
export NOTION_API_KEY='your-key'

# Run examples
python examples/llm_agent_reasoning.py
```

## API Reference

### LLMInterface

- `generate(prompt, system_prompt, **kwargs)`: Generate text response
- `generate_structured(prompt, response_schema, system_prompt)`: Generate JSON response

### ChainOfThoughtReasoning

- `reason(problem, context, num_steps)`: Free-form reasoning
- `reason_structured(problem, context, reasoning_template)`: Structured reasoning

### PromptLibrary

- `get_template(name)`: Get prompt template
- `list_templates()`: List available templates
- `add_template(template)`: Add custom template

### FewShotLibrary

- `get_examples(task_type, tags, limit)`: Get examples
- `format_examples(task_type, tags, limit)`: Format as string
- `add_example(task_type, example)`: Add example

### NotionClient

- `get_database(database_id)`: Get database interface
- `query_database(database_id, filter, sorts, limit)`: Query database
- `fetch_antenna_parameters(database_id)`: Get all parameters
- `create_antenna_requirements_page(...)`: Create new page

## License

Part of the Astraeus Apertura project.
