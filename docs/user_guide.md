# Astraeus Apertura User Guide

## Table of Contents

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Quick Start](#quick-start)
4. [Defining Mission Requirements](#defining-mission-requirements)
5. [Running a Design Workflow](#running-a-design-workflow)
6. [Understanding Results](#understanding-results)
7. [Advanced Usage](#advanced-usage)
8. [Troubleshooting](#troubleshooting)

## Introduction

Astraeus Apertura is an autonomous multi-agent system for radar and antenna design. It combines specialized AI agents to automate the design process from requirements to validated antenna specifications.

### What Can It Do?

- Translate high-level mission requirements into antenna designs
- Select optimal architectures (reflectors, phased arrays, horns, etc.)
- Generate parametric 3D geometry
- Select appropriate materials
- Run electromagnetic simulations
- Optimize designs for multiple objectives
- Validate against requirements and standards
- Generate comprehensive documentation

## Installation

### Prerequisites

- Python 3.9 or higher
- pip package manager
- (Optional) ANSYS HFSS or other EM simulator

### Basic Installation

```bash
# Clone the repository
git clone https://github.com/Safatreza/Astraeus_Apertura.git
cd Astraeus_Apertura

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .
```

### Verify Installation

```bash
python -c "import astraeus; print(astraeus.__version__)"
```

## Quick Start

### Simple Example

```python
from astraeus.core.workflow import DesignWorkflow
from astraeus.data.parameters import (
    MissionRequirements,
    FrequencySpec,
    RadiationPattern,
    Polarization,
    RadarMode
)
from astraeus.agents import *

# Define requirements
requirements = MissionRequirements(
    mission_name="Simple SAR Mission",
    mission_type=RadarMode.SAR,
    frequency=FrequencySpec(
        center_frequency_ghz=10.0,
        bandwidth_mhz=200.0,
        frequency_band="X"
    ),
    radiation_pattern=RadiationPattern(
        gain_dbi=35.0,
        beamwidth_azimuth_deg=3.0,
        beamwidth_elevation_deg=3.0,
        sidelobe_level_db=-25.0
    ),
    polarization=Polarization.LINEAR_HORIZONTAL
)

# Create workflow
workflow = DesignWorkflow(
    max_iterations=20,
    convergence_threshold=0.001
)

# Register agents
workflow.register_agent(RequirementsAnalystAgent())
workflow.register_agent(ArchitectureAgent())
workflow.register_agent(GeometryGeneratorAgent())
workflow.register_agent(MaterialSelectorAgent())
workflow.register_agent(SimulationAgent())
workflow.register_agent(PerformanceOptimizerAgent())
workflow.register_agent(ValidationAgent())
workflow.register_agent(SupervisorAgent())

# Execute design workflow
result = workflow.execute(requirements)

# Generate report
from astraeus.visualization import ReportGenerator

report_gen = ReportGenerator(output_dir="output")
report_path = report_gen.generate_design_report(result, format="markdown")
print(f"Report generated: {report_path}")
```

## Defining Mission Requirements

### Frequency Specification

```python
from astraeus.data.parameters import FrequencySpec

freq_spec = FrequencySpec(
    center_frequency_ghz=10.0,     # Center frequency in GHz
    bandwidth_mhz=200.0,            # Bandwidth in MHz
    frequency_band="X",             # Standard band designation
    harmonic_suppression_dbc=40.0   # Harmonic suppression in dB
)
```

### Radiation Pattern Requirements

```python
from astraeus.data.parameters import RadiationPattern

rad_pattern = RadiationPattern(
    gain_dbi=35.0,                     # Boresight gain in dBi
    beamwidth_azimuth_deg=3.0,         # Azimuth 3-dB beamwidth
    beamwidth_elevation_deg=3.0,       # Elevation 3-dB beamwidth
    sidelobe_level_db=-25.0,           # Peak sidelobe level
    cross_pol_discrimination_db=25.0,  # Cross-pol isolation
    beam_steering_range_deg=(30, 30)  # Steering range (az, el)
)
```

### Physical Constraints

```python
from astraeus.data.parameters import PhysicalConstraints

physical = PhysicalConstraints(
    max_mass_kg=5.0,             # Mass budget
    max_length_m=1.0,            # Maximum dimension
    max_width_m=1.0,
    max_height_m=0.3,
    deployable=False             # Is antenna deployable?
)
```

### Complete Requirements

```python
requirements = MissionRequirements(
    mission_name="My Mission",
    mission_type=RadarMode.SAR,
    frequency=freq_spec,
    radiation_pattern=rad_pattern,
    polarization=Polarization.CIRCULAR_RIGHT,
    physical=physical
)
```

## Running a Design Workflow

### Workflow Configuration

```python
workflow = DesignWorkflow(
    max_iterations=50,              # Maximum optimization iterations
    convergence_threshold=0.001,    # Convergence criterion (1% improvement)
    enable_human_review=True        # Enable review checkpoints
)
```

### Monitoring Progress

```python
# Check workflow status
status = workflow.get_status()
print(f"Phase: {status['current_phase']}")
print(f"Iteration: {status['iteration_count']}/{status['max_iterations']}")
```

### Execution

```python
# Run workflow
result = workflow.execute(requirements)

# Check termination condition
print(f"Completed: {result['termination_condition']}")
print(f"Reason: {result['termination_reason']}")
print(f"Iterations: {result['iterations']}")
```

## Understanding Results

### Design Package Structure

```python
{
    'workflow_id': '...',
    'requirements': MissionRequirements(...),
    'final_design': {
        'architecture': {...},
        'geometry': {...},
        'materials': {...},
        'simulation_results': {...},
        'validation_results': {...}
    },
    'design_history': [...],
    'performance_history': [...],
    'communication_stats': {...}
}
```

### Accessing Performance Metrics

```python
final_design = result['final_design']
sim_results = final_design['simulation_results']

# Extract metrics
gain = sim_results.get('gain_dbi')
efficiency = sim_results.get('efficiency_percent')
vswr = sim_results.get('vswr')

print(f"Achieved Gain: {gain:.1f} dBi")
print(f"Efficiency: {efficiency:.1f}%")
print(f"VSWR: {vswr:.2f}")
```

### Validation Results

```python
validation = final_design['validation_results']

if validation.get('requirements_satisfied'):
    print("✓ All requirements met")
else:
    print("✗ Requirements not fully satisfied")
    print(f"Gaps: {validation.get('gaps', [])}")
```

## Advanced Usage

### Custom Agent Configuration

```python
# Configure specific agent
requirements_agent = RequirementsAnalystAgent()
requirements_agent.config = {
    'strict_validation': True,
    'custom_rules': [...]
}

workflow.register_agent(requirements_agent)
```

### Manual Agent Interaction

```python
from astraeus.core.message import Message, MessageType

# Create custom message
msg = Message(
    sender="user",
    recipients=["RequirementsAnalyst"],
    message_type=MessageType.QUERY,
    payload={"question": "What is the estimated aperture size?"},
    rationale="User query"
)

# Send through communication hub
workflow.comm_hub.route_message(msg)
```

### Parametric Studies

```python
# Run multiple designs with varying parameters
gains = [30, 35, 40]
frequencies = [8.0, 10.0, 12.0]

results = []
for gain in gains:
    for freq in frequencies:
        # Update requirements
        requirements.radiation_pattern.gain_dbi = gain
        requirements.frequency.center_frequency_ghz = freq

        # Run workflow
        result = workflow.execute(requirements)
        results.append(result)

# Analyze trade-offs
# ...
```

### Visualization

```python
from astraeus.visualization import PatternPlotter, PerformancePlotter

# Plot radiation pattern
angles = np.linspace(-90, 90, 181)
pattern = sim_results['radiation_pattern']

PatternPlotter.plot_2d_pattern(
    angles,
    pattern,
    title="Antenna Radiation Pattern",
    save_path="output/pattern.png"
)

# Plot convergence
iterations = list(range(len(result['performance_history'])))
gains = [p['performance'].get('gain_dbi', 0)
         for p in result['performance_history']]

PerformancePlotter.plot_convergence(
    iterations,
    gains,
    metric_name="Gain",
    save_path="output/convergence.png"
)
```

### Comparison with Baseline

```python
# Define baseline design
baseline = {...}

# Generate comparison report
from astraeus.visualization import ReportGenerator

report_gen = ReportGenerator()
comparison_path = report_gen.generate_comparison_report(
    ai_design=result['final_design'],
    baseline_design=baseline,
    format="markdown"
)
```

## Troubleshooting

### Common Issues

#### 1. Simulation Fails

**Problem**: Simulation agent reports errors

**Solutions**:
- Check geometry validity (no intersecting parts, closed volumes)
- Verify material properties are defined
- Reduce mesh density if out of memory
- Check simulation tool license/availability

#### 2. Optimization Not Converging

**Problem**: Iterations reach limit without convergence

**Solutions**:
- Increase `max_iterations`
- Relax `convergence_threshold`
- Check if requirements are feasible
- Review design space constraints

#### 3. Requirements Validation Fails

**Problem**: Requirements Analyst rejects specifications

**Solutions**:
- Check for conflicting requirements (e.g., high gain + wide beam)
- Verify physical constraints are reasonable
- Review frequency and gain ranges

#### 4. Agent Communication Errors

**Problem**: Agents not responding or messages not delivered

**Solutions**:
- Ensure all agents are registered with workflow
- Check agent initialization status
- Review communication hub logs
- Verify message format and recipients

### Debugging

Enable detailed logging:

```python
from loguru import logger

logger.add("debug.log", level="DEBUG")
```

Inspect message history:

```python
# Get all messages
messages = workflow.comm_hub.get_message_history()

# Filter by agent
analyst_messages = workflow.comm_hub.get_message_history(
    sender="RequirementsAnalyst"
)

# Print conversation
for msg in messages:
    print(f"{msg.sender} → {msg.recipients}: {msg.message_type.value}")
```

Check agent decisions:

```python
agent = workflow.comm_hub.get_agent("RequirementsAnalyst")
for decision in agent.decision_log:
    print(f"{decision['timestamp']}: {decision['decision']}")
    print(f"  Rationale: {decision['rationale']}")
```

### Getting Help

- **Documentation**: Check `docs/` directory
- **Examples**: Review `examples/` directory
- **Issues**: Report bugs on GitHub
- **Discussions**: Join community forum

## Best Practices

### 1. Start Simple

Begin with basic requirements and gradually add complexity.

### 2. Validate Early

Use Requirements Analyst to catch issues before optimization.

### 3. Monitor Progress

Check workflow status and iteration results regularly.

### 4. Save Intermediate Results

Archive design history for future reference.

### 5. Use Version Control

Track requirement changes and design evolution in git.

### 6. Document Assumptions

Log rationale for constraint choices and trade-offs.

## Next Steps

- Explore `examples/` directory for more scenarios
- Read `docs/architecture.md` for system internals
- Extend framework with custom agents
- Integrate with your simulation tools
- Contribute improvements on GitHub

---

**Need Help?** Check the FAQ or open an issue on GitHub.
