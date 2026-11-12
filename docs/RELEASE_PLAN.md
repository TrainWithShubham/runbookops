# Presenter release plan

Updated November 12, 2026 after the owner selected a presenter-only deployment.

## Scope

RunbookOps remains a public standalone Apache-2.0 application with TWS branding and the fictional Gada Electronics demo. Learners run their own local copy. Only the presenter operates the AWS-backed UI during screen sharing.

The browser and API bridge stay on the laptop. AgentCore Runtime hosts LangGraph, Bedrock supplies inference, and DynamoDB preserves incidents, approvals, and graph checkpoints. IAM signs invocations; scoped local demo JWTs retain the viewer/approver checks inside the application. There is no public shared UI, invitation flow, Cognito pool, API Gateway, Lambda bridge, ALB, NAT gateway, or purchased domain in this release.

Use regional services in us-west-2 and target $10/month hosting excluding inference, measured against actual usage. Default local practice needs no API key. Keep the included knowledge pack; private uploads and real infrastructure writes remain outside this release.

## Deliverables

1. Preserve the existing local harness and offline capstone, with the current permission and exact-change approval checks.
2. Add a loopback-only AgentCore bridge that shows actual cloud tools, sources, events, and durable state. Reuse read-only sessions per identity/scopes for cache visibility; use fresh investigation/decision sessions to verify persisted state.
3. Add a root Dockerfile and Compose configuration with a non-root user, persistent state, health checks, and a real restart/approval smoke test.
4. Add Terraform bootstrap, presenter, and service-log adoption stacks. Use digest-pinned ARM64 images, dedicated roles, scoped model/table/image/log permissions, short idle lifetimes, retained state, and documented cleanup.
5. Add CI gates, secret/dependency/container checks, trusted GitHub OIDC deployment, a no-inference runtime probe, package provenance, and release artifacts. Keep the private demo signing key out of CI.
6. Retain 100% Python and JavaScript application coverage. Add regressions for cloud-specific IDs, stream conversion, concurrency, quota persistence, and connector boundaries. Verify paid model/browser/infrastructure behavior separately.
7. Add a persistent 20-run/day presenter allowance, one active investigation, and a disable switch. Publish the cost drivers and limits without claiming an AWS billing cap.
8. Add the optional read-only CloudWatch sample-log connector. Keep it disabled without a configured project log group; never grant it AWS write access.
9. Publish a README with working badges, index, actual screenshots, local/cloud quick starts, architecture, developer paths, and linked operational guides. Add licensing, contributor/security documents, templates, and a roadmap.

## Verification before release

- Fresh uv and Compose runs, including saved approval across a container restart.
- Complete application coverage gates, offline evaluations, lint/format/link checks, package builds, workflow lint, and Terraform mock tests.
- Dependency review: upgrade fixable findings; document only exact, expiring exceptions with the affected boundary and references. Fail new or expired findings.
- Real AgentCore event stream, viewer denial, authorized approval in a fresh session, HTTP 200, actual MCP discovery, and bounded CloudWatch reads.
- Native browser checks for the presenter harness, RAG cache visibility, saved work, approval, and both themes.
- Terraform deployment/update/log adoption and no-change plans. Verify trusted CI deployment and package release. Record cleanup instructions and retained resources.

Implementation was developed on release/presenter-mode and fast-forwarded to main after the first checks passed. The original main commit remains in history. Record decisions, failures, fixes, and evidence limits in DECISIONS.md and the verification record. No PR is required for this delivery.

## Later

Private uploads, shared-user hosting, additional connectors, broader load/device testing, and deeper type checking require separate scope and acceptance criteria. Keep workshop setup stable before November 14.
