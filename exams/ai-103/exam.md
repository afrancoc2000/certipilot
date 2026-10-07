# AI-103 - Developing AI Apps and Agents on Azure

Exam config for the AI-103 study agent. Read this first when AI-103 is active.

Credential: **Microsoft Certified: Azure AI Apps and Agents Developer
Associate**. Level: Associate. Passing score: 700 (per the study guide's
scoring link, checked October 7, 2026). The candidate profile is an Azure AI
engineer who builds generative AI apps, agents, and multimodal solutions with
Python and Microsoft Foundry. The Practice Assessment is hosted on AI Skills
Navigator (sign-in required). Re-check official status before every sprint.

**Why this exam:** this credential is the required prerequisite for
**AI-500** (Multi-Agent AI Solutions Expert). Path: **AI-103 → AI-500**.

## Domains (skills measured as of April 16, 2026, checked 2026-10-07)

1. **Plan and manage an Azure AI solution** (D1) - 25-30%
2. **Implement generative AI and agentic solutions** (D2) - 30-35%
3. **Implement computer vision solutions** (D3) - 10-15%
4. **Implement text analysis solutions** (D4) - 10-15%
5. **Implement information extraction solutions** (D5) - 10-15%

## Blueprint catalog

Use [blueprint.json](./blueprint.json) for the complete, source-mapped objective
and subskill inventory when building or following an approved study plan.
All 64 detailed official bullets (64 objectives, 168 subskills) and the weights
above were reconciled on October 7, 2026 against the only published outline,
"Skills measured as of April 16, 2026". No future effective outline was found.
Check `revision`, `verified`, `verification_note`, and source dates before use.
`derived: true` marks teaching decomposition, not additional official bullets.
Keep existing objective and subskill IDs stable when revising wording; do not
recycle removed IDs. Scope verification does not guarantee service behavior,
preview availability, or unpublished exam content.

### D1 - Plan and manage an Azure AI solution (25-30%)

Choose the appropriate Foundry services for generative AI and agents:

- Choose a model per task: large language models (LLMs), small language
  models, multimodal models, or Foundry Tools
- Choose Foundry services for generation, grounding, vector search, agent
  workflows, and multimodal processing
- Choose retrieval and indexing methods
- Choose memory, tool, and knowledge integration services

Set up AI solutions in Foundry:

- Design Azure infrastructure for AI apps and agent-based solutions
- Choose deployment options; configure model and agent deployments
- Integrate Foundry projects with continuous integration and continuous
  deployment (CI/CD)

Manage, monitor, and secure AI systems:

- Quotas, scaling, rate limits, and cost footprint
- Monitor performance, drift, safety events, grounding quality
- Monitor ingestion quality, index health, relevance
- Security: managed identity, private networking, keyless credentials, role
  policies

Implement responsible AI across generative AI and agentic systems:

- Safety filters, guardrails, risk detection, content moderation
- Evaluators, safety evaluations, explanation tooling
- Auditing via trace logging, provenance metadata, approval workflows
- Agent oversight modes, behavior constraints, tool-access controls

### D2 - Implement generative AI and agentic solutions (30-35%)

Build generative applications by using Foundry:

- Deploy and consume LLMs, small, code, and multimodal models
- Retrieval-augmented generation (RAG) in an application
- Workflows, tool-augmented flows, multistep reasoning pipelines
- Evaluate for fabrications, relevance, quality, safety
- Integrate via Foundry SDKs and connectors; connect an app to a Foundry project

Build agents by using Foundry:

- Roles, goals, conversation tracking, tool schemas
- Retrieval, function calling, conversation memory
- Tools: APIs, knowledge stores, search, content understanding, custom functions
- Orchestrated multi-agent solutions
- Autonomous/semiautonomous workflows with safeguards and approval flows
- Monitoring, behavior evaluation, error analysis

Optimize and operationalize generative AI systems:

- Prompt engineering and model parameters
- Reflection, chain-of-thought evaluations, self-critique loops
- Observability: tracing, token analytics, safety signals, latency breakdowns
- Orchestrate multiple models, flows, and hybrid LLM + rules engines

### D3 - Implement computer vision solutions (10-15%)

- Image and video generation from text prompts or reference media; inpainting,
  mask-based and prompt-driven edits; video editing; generation controls
- Multimodal understanding: visual context, captions, visual question
  answering, alt-text, Azure Content Understanding (single-task vs pro-mode),
  video segment analysis, object/region identification
- Responsible AI for multimodal content: unsafe-content filters, indirect
  prompt injection via image text, watermarks, prohibited symbols, brand rules

### D4 - Implement text analysis solutions (10-15%)

- Language model text analysis: entities, topics, summaries, structured JSON;
  sentiment, tone, safety, sensitive content; Azure Translator vs LLM
  translation; domain-customized outputs
- Speech: speech to text and text to speech for agents, speech as an agent
  modality, custom speech models, audio reasoning, speech translation

### D5 - Implement information extraction solutions (10-15%)

- Retrieval and grounding pipelines: ingest/index documents, images, audio,
  video; semantic, hybrid, vector search; built-in and custom enrichment skills;
  RAG ingestion with optical character recognition (OCR); connect retrieval to
  workflows and agent tools
- Document extraction: OCR + layout + field extraction pipelines; grounded
  Content Understanding representations; analyzers producing structured or
  markdown output

## Authoritative sources

- [Certification page](https://learn.microsoft.com/en-us/credentials/certifications/azure-ai-apps-and-agents-developer-associate/)
- [AI-103 study guide](https://learn.microsoft.com/en-us/credentials/certifications/resources/study-guides/ai-103)
- [Microsoft Foundry documentation](https://learn.microsoft.com/en-us/azure/foundry/)
- [Azure AI services documentation](https://learn.microsoft.com/en-us/azure/ai-services/)
- [Azure AI Search documentation](https://learn.microsoft.com/en-us/azure/search/)
- [Azure OpenAI documentation](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/)
- [Speech documentation](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/)
- [Azure Content Understanding documentation](https://learn.microsoft.com/en-us/azure/ai-services/content-understanding/)

Microsoft Learn is authoritative for the exam outline and Azure behavior.

## Source hierarchy (lookup order)

1. `exams/ai-103/material/course/` - local notes mapped to D1-D5.
2. `exams/ai-103/material/test-exams/` - practice captures (none yet).
3. Microsoft Learn URLs above (authoritative).

## Question banks

No local question bank exists yet. Author original scenario questions from the
authoritative sources, cite each graded answer, and never borrow questions or
evidence from another exam (AZ-305, AZ-104, GH-300, GH-600, AI-500).

Flag any answer that depends on a preview feature and state the date the
source was checked.
