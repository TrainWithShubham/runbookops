# Test RunbookOps

Run these commands from the repository directory. Coverage is a measure of executed code, not a promise that an AI provider will always answer correctly.

## Offline regression tests and coverage

```bash
uv sync --frozen --extra aws
uv run --extra aws pytest --cov=runbookops --cov-branch \
  --cov-report=term-missing \
  --cov-report=json:artifacts/coverage/python.json \
  --cov-report=html -q
npm ci
npm run test:coverage
uv run --extra aws runbookops evaluate
uv run python scripts/verify_docs.py
```

The JavaScript test tooling needs Node.js 26 or newer. Node.js is not required to run the Python web app or attend the learner labs.

The gates require:

- **Python:** 100% statement and branch coverage of every module under `src/runbookops`, including the CLI, providers, auth, API, RAG, MCP, and optional storage adapters.
- **JavaScript:** 100% statement, branch, function, and line coverage of every `.js` file under `src/runbookops/web`.

No application files or lines are omitted from those scopes. Templates, CSS, fonts, binary assets, instructor deployment scripts, dependencies, and test code are not executable application coverage. Reports stay in the ignored `artifacts/coverage` folder; the recorded verification summary is in [the presenter release record](verification/presenter-release.json).

The Python tests exercise real SQLite transactions, graph checkpoints, mixed-format extraction, Chroma retrieval, stdio MCP, a separate HTTP MCP process with JWT admission, and the HTTP/NDJSON API. DynamoDB uses Moto. PostgreSQL connection and query paths use a local adapter contract test; the PostgreSQL checkpoint path uses a saver contract test. HTTP model providers and Bedrock response conversion use mock transports and SDK Stubber. Semantic embedding vectors use a test double in the deterministic coverage suite.

The JavaScript suite runs the actual application modules in JSDOM with a controlled HTTP boundary. It checks rendering, errors, partial NDJSON chunks, token refresh, stale identities, approval controls, source inspection, keyboard navigation, theme startup, storage failure, and trace export. JSDOM tests do not establish real CSS layout or screen-reader behaviour. Native Safari visual checks and live Bedrock results are separate evidence.

To run a focused Python test while developing, use `uv run --extra aws pytest tests/NAME.py --no-cov -q`. A partial suite is not expected to meet the full-application coverage gate.

## Explicit live Bedrock checks

These make billed inference requests using the local AWS SDK credential configuration or a configured Bedrock bearer token. They never create cloud hosting resources. The simulator stays local.

```bash
RUNBOOKOPS_ENABLE_PAID_TESTS=true uv run --extra aws pytest -q tests/live_bedrock.py
```

The file is deliberately outside normal `test_*.py` discovery, so CI does not need AWS credentials or spend inference credits. There are four live scenarios: approved recovery, rejection, permission claim, and an unsupported destructive request. The full recovery checks approval denial, process restart/resume, HTTP 200, and idempotent replay. Live tests use a bounded eight-call budget for the instructor model; the learner default remains six calls.

A model may refuse an unsafe request or offer a valid, pending alternative suggestion. The enforced safety requirement is that it cannot execute arbitrary commands, change permissions, or apply an unapproved fix. A valid alternative proposal must still satisfy the same evidence and approval checks.

Successful scenario summaries are saved to `artifacts/live-bedrock`. Test failures remain failures: do not turn them into offline fallbacks or count a rerun as a reliability benchmark. Model output, quotas, and service availability vary. The application now gives one bounded completion reminder after partial checks, and tool-validation errors provide a safe next action for retrieving the required runbook.

## Browser end-to-end check

Open the instructor Bedrock app on port 8004. Use the four starter examples, then inspect the technical System prompt, Model, MCP tools, RAG, Approval, and Execute components. Verify a viewer's denial and an authorized approval or rejection. Check RAG retrieval/cache, saved work, theme switching, keyboard tabs, and the original diagnostic disclosure on errors. Follow [the beginner walkthrough](BEGINNER_DEMO.md).

The GitHub workflow runs the deterministic coverage gates and offline evaluations on `main` and pull requests. It uploads reports even when a check fails. Live inference is opt-in and is not part of CI.

## Presenter release checks

Use `make check` for the locked AWS-extra Python suite, all four JavaScript modules, lint/format/link checks, and offline evaluations. The first presenter release was checked locally with 156 Python tests, 32 JavaScript tests, 100% application coverage, and 13/13 offline outcomes. See [the release verification record](verification/presenter-release.json) for scope and final evidence.

`python3 scripts/container_smoke.py` requires the Compose app running. It checks real HTTP auth/approval, restarts the container while approval is pending, and verifies recovery and denied replay. Terraform tests use `mock_provider`; they do not create AWS resources. Run `make terraform-check` for all three stacks.

CI also audits the locked runtime dependency set with [exact expiring exceptions](../security/dependency-exceptions.json), scans the built image for fixable HIGH/CRITICAL findings, produces an SBOM, and scans Git history for secrets. Unresolved embedded-only Chroma findings are documented in [security boundaries](SECURITY.md); there is no zero-vulnerabilities claim.

The deployment workflow uses an IAM-authenticated health/durable-configuration probe, with no model inference and no private signing key in GitHub. Run `uv run --extra aws python deploy/manage.py smoke` from the presenter laptop for the separate billed Bedrock role/approval check. Native Safari checks observed actual cloud recovery, semantic RAG Fresh → Cache hit, AgentCore/DynamoDB metadata, and both themes. Browser logic coverage does not replace those checks or establish a device/accessibility audit.
