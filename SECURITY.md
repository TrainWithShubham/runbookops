# Security policy

RunbookOps is a reference application with synthetic operational tools. Its local demo identities let the laptop owner exercise viewer and approver roles. They are not a shared-user authentication service.

The presenter UI is loopback-only. AWS IAM authenticates runtime invocations; signed application tokens enforce the demonstrated roles inside the agent. Do not publish the local presenter server or distribute its signing key.

## Reporting a vulnerability

Use GitHub's **Security → Report a vulnerability** in this repository when private vulnerability reporting is available. If it is unavailable, contact the maintainer through the contact method listed on their GitHub profile. Do not include an exploit, credentials, company documents, or sensitive traces in a public issue.

Include the affected commit/version, a minimal reproduction using synthetic data, and the expected security boundary. We will acknowledge and investigate reports as maintainer availability permits; there is no promised response-time SLA.

## Scope

Report authentication bypass, cross-user/source access, approval tampering, unsafe tool execution, credential disclosure, and dependency/container vulnerabilities. Prompt injection should be reported with the unauthorized effect it causes, using the supplied synthetic corpus where possible.

Security fixes are maintained on the current release line. Older course versions are historical examples. See [application boundaries](docs/SECURITY.md) and [AWS operations](docs/AWS.md) before deploying.
