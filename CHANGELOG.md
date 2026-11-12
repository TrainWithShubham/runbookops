# Changelog

## 2.1.0 — presenter release

- Added a localhost-only UI bridge to AgentCore with IAM-signed calls and scoped demo identities.
- Streamed the runtime's actual investigation events into the existing harness.
- Added persistent presenter run allowances, single-investigation admission, and a live-run disable switch.
- Added an optional read-only CloudWatch sample-log connector.
- Added non-root Docker/Compose support, persistent state, and a restart/approval smoke test.
- Added Terraform bootstrap/presenter stacks, immutable images, CI federation, deployment tests, and cloud verification tooling.
- Added release/security workflows, Apache-2.0 licensing, contributor documents, and a public application README.

See the release's verification record for executed checks and remaining limits.

## 2.0.0 — standalone extraction

Extracted RunbookOps from the Agentic AI for DevOps course into its own repository. Original source: course commit `9e251fb2517d7d5158c9da93f7e23948c3498329`.
