Systems Engineering Automator
Overview

The Systems Engineering Automator is a structured, agent-based framework designed to support end-to-end systems engineering workflows for complex technical systems. Its primary goal is to reduce manual effort and improve consistency when generating and maintaining core systems engineering artifacts such as requirements structures, product and work breakdowns, dependency maps, and execution timelines.

The framework focuses on engineering logic and traceability, rather than autonomous design or optimization, and is intended to support iterative projects where system definitions evolve over time.

Motivation

In many engineering projects, systems engineering activities are still performed manually using document-centric workflows. As system complexity increases, this often leads to:

high coordination overhead,

inconsistent artifacts across iterations,

loss of traceability between requirements, system structure, and planning.

The Systems Engineering Automator was developed to address these challenges by formalizing systems engineering artifacts and applying agentic workflows to generate, transform, and update them in a consistent and repeatable manner.

Core Idea

The central idea of the framework is that systems engineering artifacts can be treated as structured data objects rather than static documents. By representing requirements, breakdown structures, dependencies, and timelines explicitly, it becomes possible to:

propagate changes across artifacts,

regenerate planning views automatically,

maintain traceability across iterations.

Agentic workflows are used to orchestrate these transformations in a step-by-step, auditable process.

Scope

The Systems Engineering Automator is intended to support:

Mission and system requirements structuring

Product Breakdown Structure (PBS) generation

Work Breakdown Structure (WBS) generation with defined work packages

Dependency modeling between work packages

Execution timeline synthesis based on dependencies

The framework does not aim to:

perform detailed subsystem design,

replace engineering judgment,

autonomously optimize hardware designs.

Architecture Concept

At a high level, the framework follows a sequential but iterative workflow:

Input ingestion
Mission objectives, constraints, and source documents are ingested and converted into structured representations.

Requirements structuring
Requirements are extracted, classified, and organized into a consistent requirements baseline.

System decomposition
A Product Breakdown Structure (PBS) is generated to represent the system architecture.

Work decomposition
A Work Breakdown Structure (WBS) is derived from the PBS, with clearly defined work packages.

Dependency modeling
Technical, programmatic, and external dependencies between work packages are identified and represented explicitly.

Planning synthesis
A feasible execution timeline is generated based on the dependency relationships.

Each step produces an artifact that becomes the input to the next, enabling traceability and iteration.

Agentic Workflow

The framework uses agentic workflows in a task-oriented sense:

each agent is responsible for a well-defined transformation (e.g. requirements → PBS),

agents operate on structured inputs and produce structured outputs,

human review and correction are supported at each stage.

This approach allows partial automation while keeping engineering decisions transparent and reviewable.

Intended Use

The Systems Engineering Automator is designed for:

early and mid-stage systems engineering,

radar-centric satellite missions and similar complex systems,

iterative project environments with recurring system updates.

The framework is particularly useful when the same systems engineering workflow must be repeated across multiple project iterations.

Relation to Other Work

This project focuses on systems engineering automation and artifact generation. It complements, but is distinct from, ongoing work on multi-agent autonomous design frameworks (e.g. antenna and radar design automation), which address detailed design and optimization problems.

Status

The Systems Engineering Automator is a working research and engineering prototype. Core systems engineering functionality (requirements structuring, PBS/WBS generation, dependency modeling, and planning) is operational and has been applied in a real project context. Further extensions are under active development.

Disclaimer

This framework is intended to support systems engineering activities, not to replace engineering judgment. All generated artifacts are expected to be reviewed and validated by engineers.
