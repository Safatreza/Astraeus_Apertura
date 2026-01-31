# Astraeus Apertura — Agentic Methods Definition

## Theoretical Foundation

### Core Model: ReAct (Reason + Act)

Our agentic methodology is grounded in the **ReAct paradigm** (Yao et al., 2022), which interleaves reasoning traces with task-specific actions in a synergistic loop:

```
Thought → Action → Observation → Thought → Action → ...
```

ReAct agents generate verbal reasoning to track progress, handle exceptions, and decide what action to take next—then observe the result and continue. This contrasts with one-shot generation where a model produces a final answer without intermediate steps.

**Why ReAct for systems engineering:**
- Explicit reasoning traces make design decisions auditable
- Action-observation loops enable iterative refinement as requirements evolve
- Tool use (actions) maps naturally to artifact transformations (requirements → PBS → WBS)

### Architecture Taxonomy: Masterman et al. (2024)

We adopt the broader agent architecture taxonomy from Masterman et al. (2024), which categorizes agentic systems along key dimensions:

| Dimension | Our Approach |
|-----------|--------------|
| **Single vs. Multi-Agent** | Multi-agent with specialized roles (requirements analyst, decomposition agent, scheduling agent) |
| **Planning Strategy** | Hierarchical decomposition with iterative re-planning |
| **Tool Calling** | Schema-defined tools for artifact CRUD operations |
| **Memory** | Persistent artifact store as external memory |

---

## What Our Agentic Methods Achieve

### 1. Structured Artifact Generation
Turn mission inputs into structured SE artifacts in a repeatable way:
```
Requirements → PBS → WBS → Dependencies → Timeline
```

### 2. Cross-Artifact Consistency
Maintain consistency across artifacts when assumptions or requirements change. No "PBS says X but WBS says Y" drift.

### 3. Auditable Reasoning
Make reasoning auditable by keeping intermediate states/artifacts. Outputs are reviewable, not magic black-box results.

### 4. Rapid Iteration Support
Support iteration: regenerate updated artifacts quickly as Project-S evolves (ATLAS-III → ATLAS-IV/V).

> Conceptually, this aligns with tool-using, iterative Reason–Act loops rather than one-shot generation.

---

## AWS Deployment Feasibility

**Yes** — the "agentic" part (orchestration + tool calls + state) maps cleanly to AWS patterns:

- **Amazon Bedrock Agents** supports a default ReAct-style orchestration strategy and allows custom orchestration configuration

- **Custom Orchestration via Lambda** — for tighter control, Bedrock supports custom orchestration through AWS Lambda functions where you decide how the agent plans steps, calls tools/actions, and terminates

- **AWS Step Functions** — for multi-step workflows and multi-agent routing, Step Functions orchestrate sequence/parallelism around Bedrock calls and tool invocations

- **Tool-Based Agent Pattern** — AWS documents the general pattern of agents invoking functions/tools with schemas and guardrails, matching our "artifact transformation pipeline" style

- **State & Logging** — S3/RDS for artifact persistence, CloudWatch for reasoning trace logging and observability

### Deployment Architecture (Summary)

```
┌─────────────────────────────────────────────────────────────────┐
│                        AWS Deployment                           │
├─────────────────────────────────────────────────────────────────┤
│  Bedrock (model + agent)                                        │
│       ↓                                                         │
│  Lambda (tools / actions / custom orchestrator)                 │
│       ↓                                                         │
│  Step Functions (workflow orchestration)                        │
│       ↓                                                         │
│  S3 / RDS (artifact storage)                                    │
│       ↓                                                         │
│  CloudWatch (logging + observability)                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## References

- Yao, S., Zhao, J., Yu, D., Du, N., Shafran, I., Narasimhan, K., & Cao, Y. (2022). *ReAct: Synergizing Reasoning and Acting in Language Models.* arXiv:2210.03629

- Masterman, T., Besen, S., Sawtell, M., & Chao, A. (2024). *The Landscape of Emerging AI Agent Architectures for Reasoning, Planning, and Tool Calling: A Survey.* arXiv:2404.11584
