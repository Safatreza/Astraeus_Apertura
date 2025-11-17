# Astraeus Apertura

**Production-Ready Multi-Agent System for Autonomous Radar and Antenna Design**

A comprehensive AI-powered framework for collaborative antenna and radar system design, integrating multi-agent intelligence, electromagnetic simulation, optimization algorithms, and standards compliance.

## 🌟 Features

### Core Capabilities
- **Multi-Agent Orchestration** with OpenAI GPT and Anthropic Claude
  - 16 agent variants (8 capabilities × 2 LLM providers)
  - Intelligent routing, consensus mechanisms, and load balancing
  - Automatic failover and cost optimization
- **8 Specialized AI Agents** working collaboratively on antenna design
- **LLM Integration** (OpenAI GPT-4, Anthropic Claude 3.5 Sonnet) for intelligent reasoning
- **Parallel Job Scheduling** for local and HPC cluster execution
- **ANSYS HFSS Integration** for electromagnetic simulation
- **Interactive Dashboard** for real-time design exploration
- **Standards Compliance** checking (NASA, ESA, MIL-STD)
- **Complete Workflow Automation** from requirements to manufacturing

### Technical Highlights
- 🤖 **Multi-Agent Architecture**: Hierarchical orchestration with supervisor mechanisms
- 🧠 **AI-Powered Reasoning**: Chain-of-thought, few-shot learning, structured prompts
- ⚡ **Parallel Execution**: 100s of simulations locally, 1000s on HPC clusters
- 📊 **Interactive Visualization**: Web-based dashboards, 3D radiation patterns
- ✅ **Standards Validation**: Automated compliance checking against aerospace/defense standards
- 🔄 **Complete Traceability**: Full decision logging and design history

## 🚀 Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/Safatreza/Astraeus_Apertura.git
cd Astraeus_Apertura

# Install dependencies
pip install -r requirements.txt

# Optional: Set up API keys for LLM features
export ANTHROPIC_API_KEY='your-claude-key'
export OPENAI_API_KEY='your-gpt-key'
export NOTION_API_KEY='your-notion-key'
```

### Run Examples

```bash
# Multi-agent orchestration (NEW!)
python examples/multi_agent_orchestration.py

# Agent benchmarking and comparison (NEW!)
python examples/agent_benchmarking.py

# Complete end-to-end workflow
python examples/complete_workflow_demo.py

# Standards compliance checking
python examples/standards_compliance_demo.py

# LLM-powered agent reasoning
python examples/llm_agent_reasoning.py

# Parallel parametric sweep
python examples/parametric_sweep_parallel.py

# ANSYS HFSS simulation
python examples/horn_antenna_ansys.py

# Interactive dashboard
python -c "from astraeus.visualization import create_dashboard; create_dashboard().run()"
```

## 📚 System Architecture

### Multi-Agent System

```
┌─────────────────────────────────────────────────────────────┐
│                     Supervisor Agent                         │
│              (High-level decision-making)                    │
└───────────┬────────────────────────────────────┬────────────┘
            │                                    │
   ┌────────▼────────┐                  ┌───────▼──────────┐
   │  Requirements   │                  │   Architecture   │
   │    Analyst      │                  │   Selection      │
   └────────┬────────┘                  └────────┬─────────┘
            │                                    │
            └───────┬──────────┬──────────┬─────┘
                    │          │          │
         ┌──────────▼───┐ ┌───▼──────┐ ┌▼───────────┐
         │   Geometry   │ │ Material │ │ Simulation │
         │  Generation  │ │ Selector │ │   Agent    │
         └──────────────┘ └──────────┘ └────────────┘
                    │          │          │
                    └──────────┼──────────┘
                               │
                    ┌──────────▼──────────┐
                    │  Performance        │
                    │  Optimization       │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │  Validation         │
                    │  Agent              │
                    └─────────────────────┘
```

### Data Flow

```
Requirements → Analysis → Architecture → Design → Simulation
                                                      ↓
Manufacturing ← Export ← Validation ← Optimization ← Results
```

## 🎯 Key Components

### 1. Multi-Agent Collaborative Design
**Location**: `astraeus/agents/`

Eight specialized agents collaborate on antenna design:
- **Requirements Analyst**: Analyzes requirements, assesses feasibility
- **Architecture Selector**: Selects optimal antenna architecture
- **Geometry Generator**: Designs antenna geometry with dimensions
- **Material Selector**: Chooses appropriate materials
- **Simulation Agent**: Runs electromagnetic simulations
- **Performance Optimizer**: Optimizes design parameters
- **Validation Agent**: Validates against requirements
- **Supervisor**: Coordinates agents, makes strategic decisions

### 2. LLM Integration
**Location**: `astraeus/llm/`

AI-powered reasoning using large language models:
- **OpenAI GPT-4** support for intelligent analysis
- **Anthropic Claude** for complex reasoning tasks
- **Structured Prompts** for each agent type
- **Chain-of-Thought** reasoning for transparency
- **Few-Shot Learning** from examples
- **Notion Database** integration for parameters

Example:
```python
from astraeus.llm import create_llm, LLMConfig, LLMProvider

llm = create_llm(LLMConfig(provider=LLMProvider.OPENAI, model="gpt-4"))
response = llm.generate("Analyze antenna requirements for LEO satellite...")
```

### 3. Multi-Agent Orchestration (NEW!)
**Location**: `astraeus/orchestration/`

Advanced orchestration system for hosting multiple agents from different LLM providers:

**Key Features:**
- **Agent Registry**: Discover and manage agents from OpenAI, Claude, and local models
- **Agent Pools**: Execute tasks using various strategies (parallel, race, consensus)
- **Consensus Engine**: Combine outputs using voting mechanisms (majority, weighted, unanimous)
- **Intelligent Routing**: Route tasks based on cost, latency, quality, or task characteristics
- **Agent Comparison**: Benchmark and compare agents across providers
- **Automatic Failover**: Fallback to alternative agents on failure

**Pool Strategies:**
- `SINGLE_BEST`: Use best performing agent
- `ALL_PARALLEL`: Execute on all agents in parallel
- `RACE`: Use first successful response
- `MAJORITY_VOTE`: Consensus from multiple agents

**Voting Strategies:**
- `MAJORITY`: Simple majority vote
- `WEIGHTED`: Weighted by reliability/confidence
- `UNANIMOUS`: Require all agents to agree
- `MEDIAN/AVERAGE`: For numerical results

Example:
```python
from astraeus.orchestration import MultiAgentExecutor, MultiAgentConfig
from astraeus.orchestration.agent_factory import register_all_agents
from astraeus.orchestration.agent_pool import PoolStrategy
from astraeus.orchestration.consensus import VotingStrategy

# Register all agents (OpenAI + Claude variants)
register_all_agents()

# Create executor with consensus
config = MultiAgentConfig(
    pool_strategy=PoolStrategy.ALL_PARALLEL,
    voting_strategy=VotingStrategy.WEIGHTED,
)
executor = MultiAgentExecutor(config=config)

# Execute with consensus from multiple agents
result = executor.execute(
    capability=AgentCapability.REQUIREMENTS_ANALYSIS,
    message=message,
    use_consensus=True,
)

print(f"Confidence: {result.consensus_result.confidence:.2f}")
print(f"Agreement: {result.consensus_result.agreement_level:.1%}")
```

See `MULTI_AGENT_ARCHITECTURE.md` for complete documentation.

### 4. Parallel Job Scheduling
**Location**: `astraeus/scheduling/`

Production-ready job scheduling system:
- **Priority-Based Queue**: CRITICAL, HIGH, NORMAL, LOW priorities
- **Worker Pool**: Multi-threaded local execution
- **HPC Integration**: SLURM and PBS cluster support
- **Job Monitoring**: Real-time statistics and progress tracking
- **Automatic Retry**: Exponential backoff for failures
- **Persistent State**: SQLite job database

Example:
```python
from astraeus.scheduling import JobQueue, WorkerPool, SimulationJob

queue = JobQueue()
pool = WorkerPool(queue, num_workers=8)
pool.register_executor('simulation', my_simulator)
pool.start()
```

### 5. ANSYS HFSS Simulation
**Location**: `astraeus/simulation/backends/`

Full electromagnetic simulation integration:
- **PyAEDT Interface**: Python automation of ANSYS HFSS
- **Geometry Creation**: Horn, patch, dipole antennas
- **Material Assignment**: Automated material configuration
- **S-Parameter Extraction**: Full network parameter extraction
- **Radiation Patterns**: Far-field pattern calculation
- **Simulation Database**: Results caching and retrieval

Example:
```python
from astraeus.simulation.backends import AnsysHFSSSimulator

sim = AnsysHFSSSimulator()
results = sim.run_simulation(frequency_ghz=10.0, geometry={...})
```

### 6. Interactive Visualization
**Location**: `astraeus/visualization/`

Web-based interactive dashboards:
- **Plotly Dash Dashboard**: Real-time parameter exploration
- **3D Radiation Patterns**: Interactive pattern visualization
- **Performance Comparison**: Multi-design comparison charts
- **Parametric Sweeps**: Design space exploration
- **Cut Plane Plots**: E-plane and H-plane patterns

Run dashboard:
```python
from astraeus.visualization import create_dashboard
dashboard = create_dashboard()
dashboard.run()  # Open http://localhost:8050
```

### 6. Standards Compliance
**Location**: `astraeus/standards/`

Automated compliance checking:
- **NASA Standards**: Outgassing (ASTM E595), thermal, EMC, reliability
- **ESA/ECSS**: RF performance, space-qualified materials, thermal cycling
- **MIL-STD**: EMI/EMC (461), environmental (810), shock/vibration

Example:
```python
from astraeus.standards import ComplianceChecker, StandardType, NASAStandardsChecker

checker = ComplianceChecker()
checker.register_checker(StandardType.NASA, NASAStandardsChecker())
result = checker.check_nasa(design, performance, requirements)
result.print_report()
```

### 7. Optimization Algorithms
**Location**: `astraeus/optimization/`

Multiple optimization methods:
- **Genetic Algorithm**: SBX crossover, polynomial mutation
- **Particle Swarm**: Global best tracking, inertia weight
- **NSGA-II**: Multi-objective optimization
- **Sensitivity Analysis**: Local and global methods

## 📊 Example Workflows

### Complete Antenna Design

```python
from astraeus.core.workflow import DesignWorkflow
from astraeus.data.parameters import MissionRequirements

# Define requirements
requirements = MissionRequirements(
    frequency_min_ghz=10.0,
    frequency_max_ghz=12.0,
    min_gain_dbi=35.0,
    max_beamwidth_deg=3.0,
    environment="LEO space"
)

# Run workflow
workflow = DesignWorkflow(max_iterations=10)
results = workflow.execute(requirements)

# Check compliance
from astraeus.standards import ComplianceChecker, StandardType
checker = ComplianceChecker()
compliance = checker.check_all(results.design, results.performance, requirements)
```

### Parametric Sweep with HPC

```python
from astraeus.scheduling import JobQueue, SLURMBackend, HPCJobConfig

# Initialize HPC backend
slurm = SLURMBackend()
queue = JobQueue()

# Configure HPC resources
config = HPCJobConfig(
    nodes=10,
    cpus_per_task=8,
    memory_mb=32768,
    time_limit="04:00:00"
)

# Submit sweep jobs
for freq in np.linspace(8, 12, 100):
    job = SimulationJob(job_type='ansys_hfss', parameters={'frequency': freq})
    queue.submit_job(job)
    slurm.submit_job(job, config, script_content)
```

### LLM-Powered Design Reasoning

```python
from astraeus.llm import ChainOfThoughtReasoning, create_llm

llm = create_llm()
cot = ChainOfThoughtReasoning(llm)

result = cot.reason_structured(
    problem="Select antenna for weather radar at 5.6 GHz, 45 dBi gain, ±60° scan",
    context={'frequency': '5.6 GHz', 'gain': '45 dBi'},
    reasoning_template=[
        "Calculate required aperture size",
        "Evaluate scanning options",
        "Compare architectures",
        "Make recommendation"
    ]
)

print(result.get_reasoning_trace())
```

## 📁 Project Structure

```
Astraeus_Apertura/
├── astraeus/                 # Main package
│   ├── agents/              # Multi-agent system (8 agents)
│   ├── core/                # Core framework (workflow, communication)
│   ├── data/                # Data structures and databases
│   ├── geometry/            # CAD export and geometry
│   ├── integrations/        # External integrations (Notion)
│   ├── llm/                 # LLM integration (OpenAI, Claude)
│   ├── optimization/        # Optimization algorithms
│   ├── scheduling/          # Parallel job scheduling
│   ├── simulation/          # Simulation backends (ANSYS HFSS)
│   ├── standards/           # Standards compliance (NASA, ESA, MIL-STD)
│   ├── utils/               # Utilities and helpers
│   ├── validation/          # Physics-based validation
│   └── visualization/       # Interactive dashboards
├── examples/                # Complete examples
│   ├── complete_workflow_demo.py
│   ├── standards_compliance_demo.py
│   ├── llm_agent_reasoning.py
│   ├── parametric_sweep_parallel.py
│   ├── hpc_cluster_submission.py
│   └── horn_antenna_ansys.py
├── tests/                   # Test suite
└── docs/                    # Documentation

Total: 94+ files, 26,700+ lines of production code
```

## 🛠️ Dependencies

### Core
- Python ≥ 3.9
- NumPy, SciPy, Matplotlib
- Pandas, PyYAML

### Simulation
- PyAEDT ≥ 0.7.0 (ANSYS HFSS)
- Trimesh, PyVista (CAD/geometry)

### AI/ML
- Anthropic ≥ 0.25.0 (Claude API)
- OpenAI ≥ 1.0.0 (GPT API)
- Notion-client ≥ 2.2.0

### Visualization
- Plotly ≥ 5.14.0
- Dash ≥ 2.14.0
- Seaborn

### Scheduling
- psutil ≥ 5.9.0

### Optimization
- scikit-optimize, pygmo, optuna

See `requirements.txt` for complete list.

## 📖 Documentation

Comprehensive documentation available in each module:
- **LLM Integration**: `astraeus/llm/README.md`
- **Job Scheduling**: `astraeus/scheduling/README.md`
- **Agent Architecture**: `docs/architecture.md`
- **User Guide**: `docs/user_guide.md`

## 🔬 Examples

### 1. Simple Patch Antenna Design
```bash
python examples/run_simple_design.py
```

### 2. Phased Array Design
```bash
python examples/phased_array_design.py
```

### 3. Parametric Sweep (125 designs in parallel)
```bash
python examples/parametric_sweep_parallel.py
```

### 4. Complete Workflow with Standards Checking
```bash
python examples/complete_workflow_demo.py
```

### 5. Interactive Dashboard
```bash
python -m astraeus.visualization.dashboard
```

## 🧪 Testing

```bash
# Run all tests
pytest

# Run specific test suite
pytest tests/test_scheduling.py
pytest tests/integration/

# With coverage
pytest --cov=astraeus --cov-report=html
```

## 🎓 Use Cases

### Space Applications
- Satellite communication antennas
- Deep space mission antennas
- CubeSat antenna systems
- Ground station terminals

### Defense & Military
- Tactical communication systems
- Radar systems (weather, surveillance)
- Electronic warfare antennas
- UAV/drone communication

### Commercial
- 5G/6G base station antennas
- IoT device antennas
- Automotive radar
- Wireless power transfer

## 🏗️ Development Phases

### ✅ Phase 1: Core Framework
- Multi-agent system with 8 agents
- Message protocol and communication hub
- Design workflow orchestration
- Knowledge base and materials database

### ✅ Phase 2: Enhancements
- CLI interface
- Optimization algorithms (GA, PSO, NSGA-II)
- Utility modules
- Testing framework

### ✅ Phase 3: ANSYS Integration
- PyAEDT ANSYS HFSS interface
- Simulation results database
- CAD geometry export
- Physics-based validation

### ✅ Phase 4: Parallel Scheduling
- Priority-based job queue
- Multi-threaded worker pool
- HPC cluster integration (SLURM, PBS)
- Job monitoring and analytics

### ✅ Phase 5: LLM Integration
- OpenAI GPT and Anthropic Claude support
- Structured prompt templates
- Chain-of-thought reasoning
- Notion database integration

### ✅ Phase 6: Visualization & Standards
- Interactive Plotly Dash dashboard
- 3D radiation pattern visualization
- NASA, ESA, MIL-STD compliance checking
- Complete workflow examples

## 📄 License

[Add your license here]

## 👥 Contributors

Developed as part of the Astraeus Apertura project for autonomous antenna and radar design.

## 📧 Contact

[Add contact information]

## 🙏 Acknowledgments

This project builds on established antenna theory, multi-agent systems research, and modern AI/ML techniques for engineering design automation.

## 🔗 References

- ANSYS HFSS Documentation
- NASA Standards (NASA-STD-8739, ASTM E595)
- ESA/ECSS Standards (ECSS-E-ST-20, ECSS-Q-ST-70)
- MIL-STD-461, MIL-STD-810
- Multi-agent system architectures
- Large language models for engineering

---

**Astraeus Apertura** - Bringing AI-powered intelligence to antenna design 🚀
