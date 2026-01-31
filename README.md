# Astraeus Apertura

**Agentic Systems Engineering Framework for Satellite Mission Planning**

Astraeus Apertura is a Python framework that applies the ReAct (Reason + Act) paradigm to automate systems engineering artifact generation for space missions. Originally developed for the ATLAS-III radar payload mission, it provides a structured approach to requirements management, product decomposition, and schedule generation.

## Features

- **ReAct-Based Agents**: Transparent reasoning with auditable decision traces
- **Automated Artifact Generation**: Requirements → PBS → WBS → Dependencies → Timeline
- **Cross-Artifact Validation**: Consistency checking and traceability verification
- **Extensible Architecture**: Easy to add new agents, tools, and artifact types

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/astraeus-apertura.git
cd astraeus-apertura

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .
```

### Run the Full Pipeline

```bash
# Run with ATLAS-III mission data
python examples/run_full_pipeline.py

# With verbose output
python examples/run_full_pipeline.py --verbose --details
```

### Run Individual Examples

```bash
# Generate PBS from requirements with reasoning trace
python examples/generate_pbs_from_requirements.py --show-trace

# Validate artifact consistency
python examples/validate_artifact_consistency.py
```

### Run Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_artifacts.py -v
```

## Project Structure

```
Astraeus_Apertura/
├── config/                 # Configuration
│   └── settings.py        # Application settings
├── src/
│   ├── agents/            # ReAct agents
│   │   ├── base_agent.py  # Base agent class
│   │   ├── requirements_agent.py
│   │   ├── decomposition_agent.py
│   │   └── scheduling_agent.py
│   ├── artifacts/         # Data models
│   │   ├── requirements.py
│   │   ├── pbs.py
│   │   ├── wbs.py
│   │   ├── dependencies.py
│   │   └── timeline.py
│   ├── orchestration/     # Workflow management
│   │   ├── react_loop.py
│   │   └── workflow.py
│   └── tools/             # Artifact operations
│       ├── artifact_crud.py
│       ├── validation.py
│       └── consistency_checker.py
├── data/
│   └── atlas_iii/         # ATLAS-III mission data
│       ├── mission_inputs.json
│       ├── requirements_baseline.json
│       ├── pbs_baseline.json
│       └── wbs_baseline.json
├── examples/              # Example scripts
├── tests/                 # Test suite
└── docs/                  # Documentation
```

## Theoretical Foundation

### Core Model: ReAct (Reason + Act)

The framework implements the ReAct paradigm (Yao et al., 2022):

```
Thought → Action → Observation → Thought → Action → ...
```

Each agent generates explicit reasoning traces, selects actions from its toolkit, and incorporates observations to make progress on tasks.

### Multi-Agent Architecture

Based on Masterman et al. (2024) taxonomy:

| Dimension | Our Approach |
|-----------|--------------|
| Single vs. Multi-Agent | Multi-agent with specialized roles |
| Planning Strategy | Hierarchical decomposition |
| Tool Calling | Schema-defined tools for artifact CRUD |
| Memory | Persistent artifact store |

## Pipeline Stages

### 1. Requirements Extraction
- Parse mission inputs
- Classify requirements by category
- Generate derived requirements from constraints
- Validate completeness

### 2. Decomposition
- Generate Product Breakdown Structure (PBS)
- Allocate requirements to PBS elements
- Derive Work Breakdown Structure (WBS)
- Create work packages with estimates

### 3. Scheduling
- Build dependency graph
- Identify critical path
- Generate execution timeline
- Validate schedule consistency

## Artifacts

### Requirements Set
- Categorized requirements (functional, performance, interface, etc.)
- Verification method specification
- PBS allocation tracking

### Product Breakdown Structure (PBS)
- Hierarchical system decomposition
- Mission-critical element identification
- Mass and power budgets

### Work Breakdown Structure (WBS)
- Work packages derived from PBS
- Effort and duration estimates
- Dependency relationships

### Dependency Graph
- NetworkX-based directed graph
- Cycle detection
- Critical path analysis

### Timeline
- Scheduled tasks with dates
- Resource tracking
- Gantt chart export

## Configuration

Environment variables (prefix `ASTRAEUS_`):

```bash
ASTRAEUS_MAX_REACT_ITERATIONS=10
ASTRAEUS_LOG_LEVEL=INFO
ASTRAEUS_STRICT_VALIDATION=true
```

Or create a `.env` file in the project root.

## API Usage

```python
from orchestration.workflow import SEWorkflow
import json

# Load mission inputs
with open("data/atlas_iii/mission_inputs.json") as f:
    mission_inputs = json.load(f)

# Run the pipeline
workflow = SEWorkflow(output_dir="./outputs")
result = workflow.run_pipeline(mission_inputs)

# Check results
print(f"Success: {result.success}")
print(f"Requirements: {result.summary['total_requirements']}")
print(f"PBS Nodes: {result.summary['total_pbs_nodes']}")
print(f"Work Packages: {result.summary['total_work_packages']}")
```

## AWS Deployment (Future)

The architecture maps to AWS services:

```
Amazon Bedrock (LLM + Agents)
      ↓
AWS Lambda (Tools / Custom Orchestration)
      ↓
AWS Step Functions (Workflow Orchestration)
      ↓
Amazon S3 / RDS (Artifact Storage)
      ↓
Amazon CloudWatch (Logging)
```

## Documentation

- [Architecture Overview](docs/architecture.md)
- [ATLAS-III Case Study](docs/atlas_iii_case_study.md)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Submit a pull request

## References

- Yao, S., et al. (2022). *ReAct: Synergizing Reasoning and Acting in Language Models.* arXiv:2210.03629
- Masterman, T., et al. (2024). *The Landscape of Emerging AI Agent Architectures.* arXiv:2404.11584

## License

MIT License - see LICENSE file for details.
