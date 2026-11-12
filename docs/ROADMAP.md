# Roadmap

The first public release focuses on the local harness and presenter-operated AgentCore deployment. Its knowledge pack and operational target are synthetic.

Next work, each with separate design and tests:

- Private document uploads with strict size/type limits, access isolation, lifecycle management, and ingestion status.
- Additional read-only connectors for GitHub Actions and bounded Docker diagnostics.
- Shared-user hosting with real sign-in, managed roles, admission limits, and per-user data ownership.
- More browser/device and concurrency testing, measured provider reliability, and incremental type checking.
- More deployment profiles when there is a concrete use case and cost budget.

Real infrastructure changes require connector-specific authorization, approval, idempotency, and recovery design. A generic shell tool is not planned.
