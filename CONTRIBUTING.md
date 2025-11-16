# Contributing to Astraeus Apertura

Thank you for your interest in contributing to Astraeus Apertura! This document provides guidelines for contributing to the project.

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [Development Setup](#development-setup)
4. [How to Contribute](#how-to-contribute)
5. [Coding Standards](#coding-standards)
6. [Testing](#testing)
7. [Pull Request Process](#pull-request-process)
8. [Adding New Agents](#adding-new-agents)

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Prioritize the project's goals and user needs

## Getting Started

### Prerequisites

- Python 3.9 or higher
- Git
- Familiarity with antenna theory and electromagnetic simulation (helpful but not required)

### Fork and Clone

```bash
# Fork the repository on GitHub
# Then clone your fork
git clone https://github.com/YOUR_USERNAME/Astraeus_Apertura.git
cd Astraeus_Apertura
```

## Development Setup

### Create Development Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode with dev dependencies
pip install -e ".[dev]"

# Install pre-commit hooks (optional)
pre-commit install
```

### Verify Installation

```bash
# Run tests
pytest

# Check code style
black --check astraeus/
flake8 astraeus/

# Run example
python examples/run_simple_design.py
```

## How to Contribute

### Types of Contributions

We welcome many types of contributions:

- **Bug fixes**: Fix issues or improve error handling
- **New features**: Add new agents, algorithms, or capabilities
- **Documentation**: Improve docs, add examples, write tutorials
- **Tests**: Increase test coverage
- **Performance**: Optimize algorithms or reduce memory usage
- **Materials database**: Add new materials with properties
- **Design patterns**: Add proven antenna designs to knowledge base

### Reporting Bugs

**Before creating a bug report:**
- Check if the issue already exists
- Verify you're using the latest version
- Collect relevant information (logs, error messages, environment)

**Bug report should include:**
- Clear, descriptive title
- Steps to reproduce
- Expected vs. actual behavior
- System information (OS, Python version)
- Relevant code snippets or configuration

### Suggesting Enhancements

**Enhancement suggestions should include:**
- Clear description of the feature
- Rationale: why it's valuable
- Example use cases
- Potential implementation approach (if known)

## Coding Standards

### Python Style

We follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) with some modifications:

- **Line length**: 88 characters (Black default)
- **Imports**: Organize into standard library, third-party, local
- **Docstrings**: Google-style docstrings for all public functions/classes
- **Type hints**: Use type annotations where helpful

### Code Formatting

We use **Black** for code formatting:

```bash
# Format code
black astraeus/ tests/ examples/

# Check formatting
black --check astraeus/
```

### Linting

We use **flake8** for linting:

```bash
flake8 astraeus/ --max-line-length=88 --extend-ignore=E203,W503
```

### Import Organization

Use **isort** to organize imports:

```bash
isort astraeus/ tests/ examples/
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=astraeus --cov-report=html

# Run specific test file
pytest tests/test_agents.py

# Run specific test
pytest tests/test_agents.py::test_requirements_analyst_initialization
```

### Writing Tests

- Place tests in `tests/` directory
- Name test files `test_*.py`
- Name test functions `test_*`
- Use descriptive test names
- Include docstrings explaining what is being tested
- Test both success and failure cases

**Example test:**

```python
def test_requirements_analyst_validates_frequency():
    """Test that Requirements Analyst validates frequency ranges."""
    agent = RequirementsAnalystAgent()

    # Valid frequency should pass
    valid_req = MissionRequirements(...)
    result = agent.execute_task({"type": "validate_requirements", "requirements": valid_req})
    assert result["validation_results"]["is_valid"] == True

    # Invalid frequency should fail
    invalid_req = MissionRequirements(frequency=FrequencySpec(center_frequency_ghz=1000))
    result = agent.execute_task({"type": "validate_requirements", "requirements": invalid_req})
    assert result["validation_results"]["is_valid"] == False
```

## Pull Request Process

### Before Submitting

1. **Update from main**: Rebase your branch on latest main
2. **Run tests**: Ensure all tests pass
3. **Format code**: Run Black, isort, flake8
4. **Update docs**: Add/update docstrings and documentation
5. **Add tests**: Include tests for new functionality
6. **Update changelog**: Add entry to CHANGELOG.md (if applicable)

### Submitting PR

1. **Create feature branch**: `git checkout -b feature/my-feature`
2. **Commit changes**: Use clear, descriptive commit messages
3. **Push to fork**: `git push origin feature/my-feature`
4. **Open Pull Request** on GitHub

### PR Description

Include:
- **Summary**: What does this PR do?
- **Motivation**: Why is this change needed?
- **Changes**: List of modifications
- **Testing**: How was it tested?
- **Checklist**:
  - [ ] Tests added/updated
  - [ ] Documentation updated
  - [ ] Code formatted (Black, isort)
  - [ ] All tests pass
  - [ ] No new warnings

### Commit Messages

Use clear, imperative commit messages:

```
Add GeometryValidator class for mesh quality checking

- Implement aspect ratio checking
- Add volume closure validation
- Include comprehensive tests
```

**Good commit messages:**
- `Add support for dual-polarization antennas`
- `Fix VSWR calculation in simulation agent`
- `Update materials database with low-loss substrates`

**Avoid:**
- `Fixed stuff`
- `WIP`
- `asdfasdf`

## Adding New Agents

### Agent Structure

All agents inherit from `BaseAgent` and implement:

```python
from astraeus.core.agent_base import BaseAgent

class MyNewAgent(BaseAgent):
    def _initialize(self) -> None:
        """Agent-specific initialization."""
        self.agent_type = "MyNewAgent"
        self.knowledge_domains = ["domain1", "domain2"]
        self.capabilities = ["capability1", "capability2"]

        # Initialize resources
        # ...

    def process_message(self, message: Message) -> Optional[List[Message]]:
        """Process incoming messages."""
        # Handle different message types
        # ...

    def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute assigned tasks."""
        task_type = task.get("type")

        if task_type == "my_task":
            return self._do_my_task(task)
        else:
            raise ValueError(f"Unknown task type: {task_type}")
```

### Agent Checklist

When adding a new agent:

- [ ] Create agent file in `astraeus/agents/`
- [ ] Inherit from `BaseAgent`
- [ ] Implement required abstract methods
- [ ] Add comprehensive docstrings
- [ ] Define knowledge domains and capabilities
- [ ] Implement decision logging for major decisions
- [ ] Add unit tests in `tests/test_agents.py`
- [ ] Update `astraeus/agents/__init__.py`
- [ ] Add example demonstrating agent usage
- [ ] Update documentation

## Project Structure

```
astraeus/
├── core/           # Base framework
│   ├── agent_base.py
│   ├── communication.py
│   ├── message.py
│   └── workflow.py
├── agents/         # Specialized agents
│   ├── requirements_analyst.py
│   ├── architecture_agent.py
│   └── ...
├── data/           # Data structures and databases
│   ├── parameters.py
│   ├── materials_database.py
│   └── knowledge_base.py
├── optimization/   # Optimization algorithms
│   ├── genetic_algorithm.py
│   ├── particle_swarm.py
│   └── ...
├── simulation/     # Simulation abstraction
│   ├── base_simulator.py
│   └── workflow.py
└── visualization/  # Plotting and reporting
    ├── plotter.py
    └── report_generator.py
```

## Documentation

### Docstring Format

Use Google-style docstrings:

```python
def my_function(param1: str, param2: int) -> bool:
    """
    Brief description of function.

    Longer description explaining what the function does,
    any important details, or usage notes.

    Args:
        param1: Description of param1
        param2: Description of param2

    Returns:
        Description of return value

    Raises:
        ValueError: If param2 is negative

    Example:
        >>> result = my_function("test", 42)
        >>> print(result)
        True
    """
    # Implementation
```

### Updating Documentation

When adding features:
- Update relevant docs in `docs/`
- Add examples to `examples/`
- Update API reference if public interface changed
- Consider adding tutorial or how-to guide

## Questions?

If you have questions:
- Check existing documentation
- Search closed issues on GitHub
- Open a new issue with the "question" label
- Join discussions on GitHub Discussions

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (MIT License).

---

Thank you for contributing to Astraeus Apertura! 🚀
