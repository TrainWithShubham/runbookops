# Decisions

## Standalone application — November 12, 2026

RunbookOps now has its own repository and release history. The source was extracted from TrainWithShubham/agentic-ai-for-devops at commit 9e251fb2517d7d5158c9da93f7e23948c3498329. A new Git history starts here; the original implementation history remains in the course repository.

Application code, UI, tests, locked dependencies, runnable examples, synthetic resources, development container, operational documentation, and optional AgentCore deployment tools move together. Lessons, exercises, solutions, curriculum, and instructor delivery plans stay in the course. Module 6 links to this repository.

No credentials, local databases, environments, caches, or generated artifacts are included. Historic sanitized verification reports are retained under docs/verification and identified as earlier results. No cloud resources are provisioned by the split.

The app remains a local simulator with optional live inference. Repository independence does not turn the synthetic tools or local demo identities into production integrations. AgentCore Runtime hosts LangGraph; managed AgentCore Harness remains a separate architecture.

CI runs on main and pull requests, with locked dependencies, documentation checks, 100% Python/JavaScript application coverage gates, and offline outcome evaluation. Paid live inference stays explicitly opt-in.

### Extraction checks

The standalone checkout passed 144 deterministic Python tests and 32 JavaScript tests. Both coverage gates remain at 100% across the original application scope (1,432 Python statements and 382 branches; all four UI JavaScript modules). The offline evaluator passed 13/13 outcomes, the complete CLI approval/recovery demo passed, Ruff passed, local Markdown links passed, and source/wheel builds succeeded. No paid inference was needed for these checks. Historic live results remain explicitly labeled; they were not rerun during extraction.

## Presenter release — November 12, 2026

### Scope and ownership

The owner selected a presenter-only cloud demo before November 14. The UI and bridge run on the laptop; AgentCore Runtime hosts LangGraph. Learners use their own local copies. Shared hosting, invitations, Cognito, API Gateway, Lambda, an ALB/NAT gateway, private uploads, and real operational writes are outside this release. Keep TWS branding, the fictional Gada Electronics example, and the existing local path. The owner selected Apache-2.0.

The cloud target is us-west-2, with a $10/month hosting design budget excluding inference. Nova Lite uses a US cross-region profile, so permitted model destinations are discovered rather than guessed. No monthly cost guarantee is made. The deployer found an unrelated agent_prod runtime in the account; it was not modified. This release uses its own runbookops-presenter resources.

### Transport, identity, and cache

The bridge uses IAM-signed SDK calls and an allowlisted HTTP envelope, retaining the original scoped application identity inside the runtime. Per-call context variables isolate headers across threads. The runtime reuses normal route/schema/ownership checks. No AWS credential or signing key is sent to the browser. Only localhost clients/hosts and matching browser origins can use the presenter.

The shared local event generator produces NDJSON. Runtime invocations wrap events in SSE, the standard AgentCore streaming boundary, and the bridge translates them back to NDJSON. Small read chunks preserve visible progress. Read-only metadata and RAG requests reuse a serialized session per user/scopes, preserving warm retrieval/cache behavior. Investigation and decision calls use fresh sessions to exercise durable DynamoDB state. Session memory is not the approval source of truth.

A live smoke initially failed when forwarding viewer approval. Investigations had already produced valid proposals; the failure was not a missing model result. DynamoDB IDs use proposal:gada-…:… while SQLite IDs use proposal-…. The route allowlist supported only the SQLite form. Added a narrow DynamoDB form and a Moto-backed regression. A subsequent real stream, viewer denial, fresh-session approval, HTTP 200, and MCP discovery passed.

A short live browser prompt also exposed a model claiming a proposal existed after a failed prepare call. The application correctly displayed that no fix was prepared. The bounded completion reminder now states that no saved proposal exists and that a source ID is not a proposal ID. The system instruction reinforces successful tool-result grounding. The short starter prompt explicitly asks for logs/runbook checks and preparing a fix. Failed model attempts remain failed evidence; no automatic proposal or paid/offline fallback is introduced.

### Containers and provisioning

The local image runs as UID 1000 with a read-only root filesystem, dropped capabilities, localhost port mapping, and a named state volume. Container-network clients do not pass the local persona issuer's loopback requirement; the Docker guide uses explicit short-lived tokens. The uv path retains the easy persona picker. A real Compose smoke verified viewer denial, restart while approval was pending, authorized recovery, and replay rejection.

Docker's temporary ECR login configuration initially hid the locally installed Buildx plugin. Builds now use the normal Docker context; only login/push use temporary credentials, which are deleted afterward. Publishing before the repository foundation existed also failed; the helper now gives an explicit ordering error. Immutable tags are reused by digest on a retry rather than overwritten. The base image is digest-pinned, dependencies use uv.lock, and AgentCore builds ARM64 with the embedding model included.

Terraform is split into bootstrap, presenter, and logs stacks. Bootstrap owns versioned encrypted private state storage and GitHub federation; it keeps an ignored local bootstrap state. The presenter stack uses S3 locking and owns ECR, roles, two on-demand tables, runtime, endpoint, and optional sample logs. Bootstrap reuses an existing GitHub OIDC provider without changing it.

AgentCore creates its log group during runtime provisioning. Attempting to create it again failed with ResourceAlreadyExistsException. A separate logs stack declaratively imports the service-created group after the runtime exists, then applies retention and a dedicated rotating KMS key. This avoids repeated imperative mutations or Terraform targeting. Cleanup handles runtime, logs/key, and bootstrap separately. The KMS key has a seven-day deletion window; retained infrastructure/storage is not free.

### Admission and CI

The presenter admits one investigation at a time and 20 starts per UTC day per runtime, persisted transactionally in a local SQLite quota file. Failed attempts consume admission. A disable switch blocks new investigations while leaving read access. These limits cover this bridge, not direct calls by an AWS administrator. The cloud engine remains bounded to eight model calls, 16 tool steps, and a 150-second investigation.

GitHub deployment is manual from main, restricted by the presenter environment and an OIDC subject/audience trust. No AWS key, model key, or demo private signing key is stored in GitHub. CI verifies an IAM-authenticated health/durable-configuration probe without model inference. Full paid approval/model checks run from the laptop. Workflow actions and scanner versions are pinned; untrusted PR checks receive no AWS credentials. Deployment is serialized and images are pinned by digest. Package releases include provenance attestations.

IAM Policy Autopilot generated source and Terraform-plan baselines. Its source baseline included conditional guardrail/tool/bearer-token, replication, KMS-decryption, and log-unmasking actions that this application does not require. Those are not granted merely because they appeared in generated output. Checkpoint-adapter access and exact resource scope are reviewed separately. GitHub can manage this project's runtime policies; deployment access is a trusted-maintainer capability, not an untrusted agent capability.

### Dependency review and test limits

The audit found two fixable FastMCP advisories and an affected DiskCache dependency. Upgrading to FastMCP 3.4 removed those findings and retained protocol behavior in tests. Four unresolved Chroma advisories concern server collection/model injection and its built-in tenant/RBAC paths. RunbookOps uses embedded PersistentClient, fixed embedding configuration, no Chroma HTTP server, and its own retrieval authorization. Exact package/version/advisory exceptions have references, rationale, and a 30-day review date. New, version-mismatched, or expired findings fail the gate; this is not a vulnerability-free claim.

A live check caught treating boto3 clients as context managers. Replaced that with explicit closing and strengthened the CloudWatch test to use a real botocore client/Stubber, not a fake context-manager contract. The optional connector reads only a configured /runbookops/ sample group, at most 20 events over 15 minutes; seeding is a separate operator action. Agent IAM permissions remain read-only for logs.

Application coverage remains a separate scope from Terraform, container, native browser, and model reliability. Full-suite, cloud, browser, and CI results are recorded in the release verification record after their final runs. No source exclusions are added to satisfy the 100% gates.

### Public bootstrap safety

CI federation is opt-in for new installations. A public clone must not silently create an AWS deployment role trusting the original authors' GitHub repository. Bootstrap defaults to no GitHub role/provider, and the configure helper accepts an explicit --github-repository OWNER/REPO while preserving a previous explicit choice. The owner's existing TrainWithShubham/runbookops trust is retained through Terraform moved blocks, without recreating its role.

A transient Docker push failed with a broken network pipe during a large layer upload. Dependency and embedding layers are now separated from frequently changing application files. This also reduces repeat upload/storage work. The build backend, Python base image, runtime dependencies, workflow actions, and scanner executable are pinned. NOTICE is included in both the package and image.

### GitHub immutable OIDC identities

The first GitHub deployment could not assume its role. The repository OIDC API showed GitHub's newer immutable subject prefix, including numeric owner/repository IDs; the original name-only trust correctly denied it. Added explicit subject-prefix configuration and exact repository validation instead of weakening the trust or opting out of immutable identities. The owner deployment uses the observed immutable prefix. Bootstrap tests verify no default CI role/provider and the exact environment-bound immutable subject. ARM64 image builds on the x86 GitHub runner explicitly enable QEMU.

The next deployment built/pushed the ARM64 image and reached scanning, but Trivy could not write its report because the fresh deployment workspace had no artifacts directory. The workflow now creates it explicitly before scanning. The failure did not update the runtime. Local package verification also initially selected a stale 2.0 wheel from dist; checking the exact 2.1 wheel confirmed LICENSE, NOTICE, presenter code and UI assets are included. Release runners build in a fresh workspace.

### Final delivery checks

The GitHub deployment completed with temporary OIDC credentials, a passing image scan, Terraform update/log adoption and an IAM-authenticated health probe. The subsequent paid smoke on runtime version 5 passed streamed events, viewer denial, fresh-session approval, HTTP 200 and six MCP tools. Native GitHub secret scanning, push protection and vulnerability alerts are enabled; private vulnerability reporting is available. No static AWS keys or private demo key were added to GitHub.

The post-deployment no-change check exposed one formatting difference: GitHub's environment public key lacked the PEM file's trailing newline. Terraform now trims surrounding PEM whitespace before escaping newlines, avoiding a redundant runtime version update when switching between local and CI configuration. The local variable file was synchronized to the deployed digest before checking drift. The optional CloudWatch read returned a real seeded sample event; that inspection run did not prepare a fix, and the simulator remained at HTTP 503. The separate final recovery smoke passed.

Terraform mock scenarios now declare their empty-image/no-CI inputs explicitly. A local rerun after deployment exposed that an ignored operator variable file could override a test's intended default; fresh GitHub runners did not have that file. The corrected scenarios pass both locally with deployed configuration present and in a clean runner.
