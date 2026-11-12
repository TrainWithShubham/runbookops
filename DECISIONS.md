# Decisions

## Standalone application — November 12, 2026

RunbookOps now has its own repository and release history. The source was extracted from TrainWithShubham/agentic-ai-for-devops at commit 9e251fb2517d7d5158c9da93f7e23948c3498329. A new Git history starts here; the original implementation history remains in the course repository.

Application code, UI, tests, locked dependencies, runnable examples, synthetic resources, development container, operational documentation, and optional AgentCore deployment tools move together. Lessons, exercises, solutions, curriculum, and instructor delivery plans stay in the course. Module 6 links to this repository.

No credentials, local databases, environments, caches, or generated artifacts are included. Historic sanitized verification reports are retained under docs/verification and identified as earlier results. No cloud resources are provisioned by the split.

The app remains a local simulator with optional live inference. Repository independence does not turn the synthetic tools or local demo identities into production integrations. AgentCore Runtime hosts LangGraph; managed AgentCore Harness remains a separate architecture.

CI runs on main and pull requests, with locked dependencies, documentation checks, 100% Python/JavaScript application coverage gates, and offline outcome evaluation. Paid live inference stays explicitly opt-in.

### Extraction checks

The standalone checkout passed 144 deterministic Python tests and 32 JavaScript tests. Both coverage gates remain at 100% across the original application scope (1,432 Python statements and 382 branches; all four UI JavaScript modules). The offline evaluator passed 13/13 outcomes, the complete CLI approval/recovery demo passed, Ruff passed, local Markdown links passed, and source/wheel builds succeeded. No paid inference was needed for these checks. Historic live results remain explicitly labeled; they were not rerun during extraction.
