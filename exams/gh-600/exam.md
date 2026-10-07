# GH-600 - Developing in Agentic AI Systems

Exam config for the GH-600 study agent. Read this first when GH-600 is active.

Credential: **GitHub Certified: Agentic AI Developer**.
Level: Intermediate. Passing score: 700. Duration: 120 minutes, proctored
(Pearson VUE), English only, may include interactive components.
GitHub certifications are valid for 2 years.

This is the closest credential to "harness engineering", "loop engineering", and
agent orchestration inside the software development lifecycle (SDLC), with
GitHub as the system of record and control plane.

## Domains (skills measured, GH-600 study guide)

1. **Prepare agent architecture and SDLC processes** (D1) - 15-20%
2. **Implement tool use and environment interaction** (D2) - 20-25%
3. **Manage memory, state, and execution** (D3) - 10-15%
4. **Perform evaluation, error analysis, and tuning** (D4) - 15-20%
5. **Orchestrate multi-agent coordination** (D5) - 15-20%
6. **Implement guardrails and accountability** (D6) - 10-15%

## Blueprint catalog

Use [blueprint.json](./blueprint.json) for the complete, source-mapped objective
and subskill inventory when building or following an approved study plan.
All 65 detailed official bullets and the domain weights above were reconciled
on October 4, 2026. The guide does not state an effective revision date;
its May 4 metadata date and July 9 update are not effective-date claims.
The certification page offers GH-600 scheduling. No future outline was found.
Check `revision`, `verified`, `verification_note`, and source dates before use.
`derived: true` marks teaching decomposition, not additional official bullets.
The guide's malformed approval-gate sentence is interpreted as requiring a
checked and approved plan before action; this interpretation is recorded in
the catalog rather than presented as corrected official wording.
Keep existing objective and subskill IDs stable when revising wording; do not
recycle removed IDs. Scope verification is not a product-behavior guarantee.

### D1 - Prepare agent architecture and SDLC processes (15-20%)

Integrate agents into the SDLC:

- Identify steps for agents to perform
- Identify and mitigate common agent anti-patterns
- Define inputs, outputs, and success criteria

Define boundaries between planning, reasoning, and action:

- Keep agent planning distinct from agent execution
- Configure an agent to output a structured plan
- Validate agent plans
- Prevent agent action until the plan is checked and approved

Observability and control for autonomous agents:

- Plan and implement the degree of autonomy, including guardrails
- Produce inspectable artifacts within standard development tooling
- Configure human intervention without slowing delivery

### D2 - Implement tool use and environment interaction (20-25%)

Select and configure agent tools:

- Identify required tools, configure tools, configure tool permissions

Configure Model Context Protocol (MCP) servers:

- Add an MCP server as a tool to an agent
- Configure a GitHub remote MCP server
- Configure MCP registries
- Configure MCP allow lists

Integrate agents within development environments:

- Evaluate the execution context for an agent
- Scope an agent to a specific repository
- Invoke an agent in a continuous integration (CI) workflow
- Configure branch-based scope
- Enable autonomous actions such as creating branches and pull requests
- Handle environment-specific constraints

Safe execution paths and robust error handling:

- Error handling, retries, rollbacks, escalation paths
- Traceability and accountability for agent actions

### D3 - Manage memory, state, and execution (10-15%)

- Choose between short-term, long-term, and external memory
- Scope memory to task-relevant information
- Define memory expiration, pruning, and reset rules
- Capture task progress and decisions as durable artifacts
- Resume agent work without repeating steps or diverging from prior decisions
- Detect and correct drift during extended execution
- Share agent state across tools and environments; prevent conflicting context
  and stale context

### D4 - Perform evaluation, error analysis, and tuning (15-20%)

- Specify expected outcomes and operational constraints for agent tasks
- Identify qualitative and quantitative evaluation signals
- Align evaluation criteria with development intent
- Generate evaluation signals using automated scanning tools
- Identify failures from logs, plans, traces, outputs, and workflow artifacts
- Classify root causes: reasoning errors, tool misuse, context or environment issues
- Tune behavior by revising instructions, workflows, constraints, memory usage,
  and tool usage or tool access

### D5 - Orchestrate multi-agent coordination (15-20%)

- Apply an orchestration pattern to coordinate multiple agents
- Configure agent isolation for parallel execution
- Detect and resolve agent conflicts: overlapping code changes, duplicated
  effort, contradictory outputs
- Produce artifacts suitable for review and audit; document key decisions,
  handoffs, and outcomes; perform post-hoc analysis
- Identify failed, partial, or stalled executions; respond to degraded behavior
- Multi-agent recovery patterns: rollback and human-in-the-loop
- Agent lifecycle: add, update, reconfigure, replace agents without disrupting
  active workflows; retire agents while preserving auditability

### D6 - Implement guardrails and accountability (10-15%)

- Classify agent actions by operational, security, and compliance risk to
  right-size human interventions
- Assign autonomy levels balancing delivery speed with security and
  Responsible AI standards
- Identify the subset of actions requiring human judgment
- Block actions that violate security, compliance, or Responsible AI policies
- Scope permissions and execution contexts for least-privilege access
- Require explicit authorization for irreversible or compliance-sensitive changes
- Preserve execution velocity by minimizing approvals that do not materially
  reduce risk

## Authoritative sources

- [Certification page](https://learn.microsoft.com/en-us/credentials/certifications/agentic-ai-developer/)
- [GH-600 study guide](https://learn.microsoft.com/en-us/credentials/certifications/resources/study-guides/gh-600)
- Learning modules:
  - [Foundations of Agentic AI in GitHub](https://learn.microsoft.com/en-us/training/modules/foundations-agentic-ai/)
  - [Designing Agent Architecture and SDLC Integration](https://learn.microsoft.com/en-us/training/modules/design-agent-architecture-integration/)
  - [Tooling, MCP, and Agent Execution Environments](https://learn.microsoft.com/en-us/training/modules/agent-tooling-mcp-execution-environments/)
- GitHub Docs (authoritative for product behavior):
  - [Prepare for custom agents](https://docs.github.com/copilot/how-tos/administer-copilot/manage-for-organization/prepare-for-custom-agents)
  - [Custom agents with the Copilot SDK](https://docs.github.com/copilot/how-tos/copilot-sdk/use-copilot-sdk/custom-agents)
  - [Copilot memory](https://docs.github.com/copilot/concepts/agents/copilot-memory)
  - [Implementation planner custom agent](https://docs.github.com/copilot/tutorials/customization-library/custom-agents/implementation-planner)
  - [Build guardrails](https://docs.github.com/copilot/tutorials/cloud-agent/build-guardrails)
  - [Cloud agent risks and mitigations](https://docs.github.com/en/copilot/concepts/agents/cloud-agent/risks-and-mitigations)
- [Exam sandbox](https://ghcertdemo.starttest.com/)

Microsoft Learn is authoritative for the exam outline. GitHub Docs is
authoritative for current product behavior, plans, policies, and feature
availability.

## Source hierarchy (lookup order)

1. `exams/gh-600/material/course/` - local notes mapped to D1-D6.
2. `exams/gh-600/material/github-docs/` - local summaries of GitHub Docs.
3. `exams/gh-600/material/test-exams/` - practice captures (none yet).
4. Microsoft Learn and GitHub Docs URLs above (authoritative).

## Relationship to GH-300

GH-300 (GitHub Copilot) covers Copilot features, responsible use, privacy, and
prompt engineering. GH-600 assumes that knowledge and moves to *operating*
agents: planning/execution separation, tools and MCP, memory and state,
evaluation, multi-agent orchestration, and guardrails. Do not reuse GH-300
questions or cite GH-300 material during a GH-600 session — each session stays
scoped to one exam.

## Question banks

No local question bank exists yet. Author original scenario questions from the
authoritative sources and cite the first-party page used to grade. Agent
features change fast: record the date each source was checked.
