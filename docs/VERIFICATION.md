# Presenter release verification — November 12, 2026

These results cover the standalone RunbookOps 2.1.0 presenter release. The [machine-readable record](verification/presenter-release.json) captures counts and live observations. Earlier course results remain in [verification history](VERIFICATION_HISTORY.md); their deleted AWS deployment is separate from this release's dedicated resources.

| Check | Observed result |
|---|---|
| Python application tests | 156 passed; 100% statements and branches, no source exclusions |
| JavaScript application tests | 32 passed; 100% statements, branches, functions and lines across four modules |
| Offline evaluations | 13/13 passed; no live-model quality claim |
| Terraform | Four presenter mock tests and two bootstrap trust tests passed |
| Docker Compose | Actual HTTP auth, denied viewer, restart while awaiting approval, recovery to HTTP 200, denied replay |
| AgentCore and Bedrock | Real streamed investigation, denied viewer approval, authorized approval in another runtime session, HTTP 200 recovery, six discovered MCP tools |
| Semantic RAG | Actual cloud sources inspected in Safari; repeated query changed from Fresh to Cache hit |
| CloudWatch connector | Actual bounded AWS read; separate demo-source marker preserved; no simulator change authorized by AWS sample logs |
| Browser | Safari desktop: recovered incident, AgentCore/DynamoDB details, both themes; README screenshots captured from the running app |
| Dependencies | FastMCP upgraded to 3.4.11; vulnerable DiskCache path removed; four unresolved Chroma findings have exact expiring exceptions |
| Packaging and source checks | Locked install, wheel/source build, Ruff, workflow lint, local documentation links, and secret scan passed |

Python coverage covers 1,661 statements and 436 branches across every application module. UI tests run actual JavaScript in JSDOM. AWS adapter tests use Moto and botocore Stubber; live AWS/browser results are separate checks. See [testing](TESTING.md) for reproducible commands and [dependency exceptions](../security/dependency-exceptions.json) for the remaining findings.

## Deployment and evidence

The presenter deployment uses us-west-2, a digest-pinned ARM64 image, IAM admission, the owner-selected Bedrock profile, DynamoDB state, and managed log retention/encryption. The browser/API bridge stays on localhost. The private demo signing key remains on the presenter laptop.

[Application checks](https://github.com/TrainWithShubham/runbookops/actions/workflows/checks.yml), [security](https://github.com/TrainWithShubham/runbookops/actions/workflows/security.yml), and [deployment records](https://github.com/TrainWithShubham/runbookops/actions/workflows/deploy.yml) expose their actual status. The deployment probe checks IAM admission and durable configuration without inference. The separate paid smoke command verifies model behavior and approval from the laptop.

The [main-branch application run](https://github.com/TrainWithShubham/runbookops/actions/runs/43225088696) passed all seven jobs, including Python 3.11/3.12/3.13. Its [secret scan](https://github.com/TrainWithShubham/runbookops/actions/runs/43225088714) also passed.

Repeat the full capstone with `uv run --extra aws python deploy/manage.py smoke`. It writes sanitized evidence to `artifacts/presenter-cloud-smoke.json`. That is a new live run, not a replay of the saved release record. The optional CloudWatch read uses a 15-minute window; reseed before presenting if needed.

The [GitHub deployment](https://github.com/TrainWithShubham/runbookops/actions/runs/43225980070) passed, including its image scan (zero fixable HIGH/CRITICAL findings) and IAM health probe. The final paid smoke used runtime version 5 and three model calls; viewer denial, fresh-session approval, HTTP 200 and six MCP tools passed. Subsequent plans for all three Terraform stacks showed no changes. A separate fresh installation without the AWS extra completed the offline approval/recovery demo.

## Limits

Live model checks are samples. Earlier attempts failed to prepare a valid proposal; they stayed failures, and the model instructions received bounded corrective guidance. The application never fabricates a proposal or substitutes offline results for a failed live model.

This release does not establish a production SLO, a full mobile/accessibility audit, load-test results, or deterministic model reliability. Full teardown and recreation of the Terraform stacks were not rehearsed; cleanup and retained-resource behavior are documented in the [AWS guide](AWS.md). Windows and other native browsers were not rechecked.

The owner requested AWS teardown after release verification. On November 12, the runtime/endpoints, workload identity, ECR images/repository, DynamoDB tables, all project logs, state bucket (including object versions), and project IAM roles were deleted. Direct AWS checks confirmed their absence. The dedicated disabled KMS key is PendingDeletion until November 19; [AWS does not charge for keys scheduled for deletion](https://aws.amazon.com/kms/pricing/). See the [cleanup record](verification/presenter-cleanup.json).

The GitHub deployment workflow is disabled and its environment variables were removed. AWS-connected local servers were stopped; local offline/Docker apps and source code remain available. The shared GitHub OIDC provider and unrelated AWS workloads were preserved. Recreate the AWS deployment and explicitly re-enable its workflow before another cloud demo. Earlier live results above are historical evidence, not a claim that an endpoint remains running.
