# RunbookOps

An agent workspace for investigating incidents, searching runbooks, and reviewing proposed fixes. Built with LangGraph, MCP, FastAPI, and a small browser UI.

The included Gada Electronics scenario starts with a broken checkout. The agent checks health, logs, recent changes, and company documents, then prepares a correction for human approval. A viewer can investigate; an approver must review the exact change before execution.

Operations run against a local simulator. Connecting production infrastructure requires replacing those tools and configuring your own identity provider and operational policies.

## Quick start

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then:

```bash
git clone https://github.com/TrainWithShubham/runbookops.git
cd runbookops
uv sync --frozen
uv run runbookops preflight
uv run runbookops demo
uv run runbookops --mode offline serve --demo-auth --port 8002
```

Open **http://127.0.0.1:8002/**. No API key or AWS account is needed for offline practice. The browser shows tool calls, retrieved sources, saved agent state, approval, and execution. Dark and light themes are included.

`--demo-auth` enables local sample identities. It is intended for loopback development; configure trusted OIDC/JWT admission before any shared deployment. Model keys stay on the server.

## Use a live model

Copy `.env.example` to `.env` and add your own OpenRouter key. Keep `RUNBOOKOPS_FREE_ONLY=true` to reject paid OpenRouter models. Availability and quotas depend on the provider; a failed request never silently switches to paid inference.

```bash
cp .env.example .env
uv run runbookops models
uv run runbookops --embedding semantic index
uv run runbookops --mode openrouter --embedding semantic serve --demo-auth --port 8002
```

Semantic indexing downloads a local embedding model once. Use hash embeddings for offline practice. For Amazon Bedrock, follow [Bedrock setup](docs/BEDROCK_DEMO.md); inference is billed to your AWS account. Hosting on [AgentCore Runtime](deploy/agentcore/README.md) is a separate deployment step.

## What you can inspect

- **Agent:** system instructions, model limits, tool requests, and LangGraph checkpoints.
- **RAG:** PDF, DOCX, PPTX, Markdown, and text ingestion, citations, access filtering, and cache hits.
- **MCP:** actual tool discovery, schemas, inputs, outputs, and transport settings.
- **Approval:** identity checks, exact-change review, expiry, restart/resume, and idempotent execution.
- **Evidence:** event timelines, trace export, evaluations, and regression reports.

Start with [the short walkthrough](docs/BEGINNER_DEMO.md), then explore [harness examples](docs/HARNESS_DEMOS.md). The [run guide](RUNBOOK.md) covers CLI commands, configuration, shutdown, and troubleshooting.

## Development

```bash
uv sync --frozen --extra aws
uv run ruff check src examples scripts tests deploy/agentcore
uv run python scripts/verify_docs.py
uv run --extra aws pytest --cov=runbookops --cov-branch --cov-report=term-missing -q
npm ci
npm run test:coverage
uv run runbookops evaluate
```

Node.js 26 or newer is needed for JavaScript tests, not for running the app. Both application coverage gates require 100%; see [testing scope and limits](docs/TESTING.md). CI uses offline simulations and mocked providers. Live Bedrock checks require explicit opt-in and AWS access.

| Path | Purpose |
|---|---|
| `src/runbookops` | Agent, providers, retrieval, MCP, permissions, stores, API, CLI, and UI |
| `resources` | Synthetic knowledge pack, incident fixture, and editable document sources |
| `examples` | Small runnable model, tool, RAG, and MCP examples |
| `tests` | Python integration and JavaScript UI tests |
| `deploy/agentcore` | Optional AWS deployment and cleanup tools |
| `docs` | Architecture, API, security, demos, and verification |

Read [architecture](docs/ARCHITECTURE.md) and [security boundaries](docs/SECURITY.md) before extending the tools. Use `.env` for local secrets; never commit credentials or `.state`.

## Course and provenance

RunbookOps is maintained as a standalone application. The [Agentic AI for DevOps course](https://github.com/TrainWithShubham/agentic-ai-for-devops/tree/v2) links to it from module 6. Lessons, exercises, and instructor delivery plans remain in the course repository.

The initial application was extracted from course commit `9e251fb2517d7d5158c9da93f7e23948c3498329`. Existing verification reports record the environment and limitations of those earlier runs. [DECISIONS.md](DECISIONS.md) records changes made after extraction.
