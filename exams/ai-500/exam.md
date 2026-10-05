# AI-500 - Designing and Implementing Multi-Agent AI Solutions

Exam config for the AI-500 study agent. Read this first when AI-500 is active.

Credential: **Microsoft Certified: Multi-Agent AI Solutions Expert (beta)**.
Level: Expert. Passing score: 700. Exam is in **beta** — scores are not released
immediately and the outline can change; re-check the study guide before every
sprint.

**Prerequisite:** the certification requires completing one prerequisite
associate-level credential (Azure AI Apps and Agents Developer path). Confirm
the current prerequisite on the certification page before scheduling.

## Domains (skills measured as of the 2026-06-30 study guide)

1. **Architect multi-agent solutions** (D1) - 15-20%
2. **Develop multi-agent solutions in Azure** (D2) - 30-35%
3. **Evaluate, optimize, and monitor multi-agent solutions** (D3) - 20-25%
4. **Secure, govern, and deploy multi-agent solutions** (D4) - 20-25%

### D1 - Architect multi-agent solutions (15-20%)

Design logical architecture for multi-agent solutions:

- Decompose goals into workflows, agents, and tools
- Design workflows: agents, subagents, control loops, human-in-the-loop
- Specify agent personas, scopes, boundaries, autonomy levels, behavioral guidelines
- Specify tool scopes, permission boundaries, authentication methods
- Specify communication protocols (agent-to-agent, agent-to-component)
- Design human-AI experience (HAX) controls and responsible AI adherence
- Design short-term and long-term memory architectures, including context sharing
- Match task demands to model family capacities

Specify technology components:

- Integration components for agent-to-agent, agent-to-tool, agent-to-knowledge routing
- Zero Trust components: per-agent identity scoping, lateral movement prevention,
  compliance control mapping
- Multi-tier state persistence: session state, shared team state, long-term
  semantic memory, lifecycle and tenant-isolation policies
- Compute components for scalability, reliability, efficiency, security, cost
- Observability: cross-service trace correlation, structured logging of reasoning
  paths, agent replay capture
- Monitoring: cross-agent coordination tracking, behavioral drift and quality
  regression detection, automated remediation
- Developer tools and SDLC environment: dev containers, Visual Studio Code
  extensions, command-line interface (CLI), dependency management, AI instructions

### D2 - Develop multi-agent solutions in Azure (30-35%)

Advanced prompt engineering:

- Examples, dynamic context injection, defensive guidelines, prompt lifecycle
- Context-aware multi-agent behaviors
- Fine-tuning strategy for agents and models (data and frequency)

Memory, context management, knowledge integration:

- Context accumulation, retrieval, injection, compaction (single and multi-agent)
- Memory strategies: security, compliance, lifecycle, storage, session management
- Multi-agent retrieval-augmented generation (RAG): chunking, embedding quality,
  retrieval precision
- Knowledge integration: search, RAG, Model Context Protocol (MCP) sources,
  semantic search

Tool ecosystems:

- Function calling, specified tool use, dynamic tool use
- Build MCP servers and clients with Azure Functions, Azure Logic Apps,
  Azure API Management
- Tool error handling, fallback, result validation and quality checks

Multi-agent orchestration:

- Patterns: hub-and-spoke, sequential, parallel, peer-to-peer, orchestrator-subagent
- Human-in-the-loop: approvals, overrides, edge cases
- Caching: prompt, semantic, response
- Scaling and control of agent spawning, batching, concurrent execution
- Integrate existing agents securely via Agent2Agent (A2A) and/or MCP
- Frameworks: Microsoft Agent Framework, LangChain, LangGraph
- Advanced capabilities with Hugging Face Transformers
- Middleware for reusable capabilities: logging, authorization, exception handling

### D3 - Evaluate, optimize, and monitor (20-25%)

- Human review process in Microsoft Foundry; evaluations for memory, knowledge,
  tools, prompts
- Optimize task duration: parallelism, rate limits
- Context window failure modes: sliding-window amnesia, summary drift,
  vector-only recall, entity continuity
- Continuous improvement: large language model-as-a-judge (LLM-as-a-judge),
  synthetic data generation, semantic optimization loops, user feedback loops
- Reliability monitoring: agent health, workflow failures, trace correlation,
  drift detection, quality regression, remediation
- Availability, performance, reliability, service-level agreement (SLA) adherence
- Token optimization: token limits, loop controls, tool calls
- Cost monitoring: usage, quotas, allocations, chargebacks
- Tracing in Foundry: tokens, prompts, correlation IDs, alerting, execution tracking

### D4 - Secure, govern, and deploy (20-25%)

- Resource access: identity-based access, network boundaries, access control
  policies, role-based access control (RBAC)
- Authentication flows: user impersonation, on-behalf-of (OBO), API keys, OAuth 2.0
- Secrets management with Azure Key Vault: secrets, certificates, key rotation,
  role-based access to secrets, encryption
- Shift-left security, including the AI Red Teaming Agent in Foundry
- Multi-intervention guardrails across user inputs, tool calls, tool responses,
  outputs; custom domain guardrails; guardrail testing with synthetic data
- Release methodology: Development-Test-Acceptance-Production (DTAP), blue/green,
  canary; multi-environment releases, rollback, release management, rollout
- Testing: unit, regression, integration, automated evaluations
- Continuous integration and continuous deployment (CI/CD), including
  infrastructure-as-code deployments and testing

## Authoritative sources

- [Certification page](https://learn.microsoft.com/en-us/credentials/certifications/multi-agent-ai-solutions-expert/)
- [AI-500 study guide](https://learn.microsoft.com/en-us/credentials/certifications/resources/study-guides/ai-500)
- [Microsoft Foundry documentation](https://learn.microsoft.com/en-us/azure/foundry/)
- [Multiple-agent workflow automation with Microsoft Agent Framework](https://learn.microsoft.com/en-us/azure/architecture/ai-ml/idea/multiple-agent-workflow-automation)
- [Azure developer documentation](https://learn.microsoft.com/en-us/azure/developer/)
- [Model Context Protocol specification](https://modelcontextprotocol.io/)

Microsoft Learn is authoritative for the exam outline and Azure behavior. For
open-source frameworks (LangGraph, LangChain, Hugging Face Transformers, MCP),
the project's own official documentation is authoritative for product behavior;
Microsoft Learn remains authoritative for what the exam measures.

## Source hierarchy (lookup order)

1. `exams/ai-500/material/course/` - local notes mapped to D1-D4.
2. `exams/ai-500/material/test-exams/` - practice captures (none yet).
3. Microsoft Learn URLs above (authoritative).
4. Official framework documentation for non-Microsoft components, flagged as
   such in the citation.

## Question banks

No local question bank exists yet. Author original scenario questions from the
authoritative sources, cite each graded answer, and never borrow questions or
evidence from another exam (AZ-305, AZ-104, GH-300, GH-600).

Because the exam is in beta, flag any answer that depends on a preview feature
and state the date the source was checked.
