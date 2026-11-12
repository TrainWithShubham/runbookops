# AWS presenter deployment

This deployment runs LangGraph on AgentCore Runtime and keeps the browser/API bridge on your laptop. It uses IAM admission and short-lived signed demo identities. No shared website, Cognito pool, API Gateway, Lambda, ALB, NAT gateway, or purchased domain is required.

Default region: `us-west-2`. The Nova Lite US inference profile can route inference to other US regions; its exact destination ARNs are included in the runtime policy. Runtime, tables, image repository, and logs are regional. This is a billed AWS deployment; see [costs](COSTS.md).

## Requirements

- uv, Terraform 1.11 or newer, and Docker with Buildx; the verified Terraform version is 1.15.8.
- AWS SDK credentials/profile for the intended account. Verify the account before applying Terraform. Temporary AWS login/profile credentials are preferred.
- Operator permission to create this project's state bucket, roles, ECR repository, two DynamoDB tables, runtime/endpoint, and log groups, plus access to the selected Bedrock model/profile.

Run commands from the repository root. The following steps create only the dedicated RunbookOps resource set. Do not use legacy Python cleanup scripts against Terraform-managed resources.

## 1. Prepare local configuration

```bash
uv sync --frozen --extra aws
uv run --extra aws python deploy/manage.py configure
```

The helper discovers the account and inference profile, reuses the local demo issuer key, and writes ignored Terraform variable files. It prints the account and region for review. The public key is saved to `.state/presenter-public.pem`; the private key remains in `.state/dev-issuer.pem`. Keep it to continue issuing the demo identities trusted by this deployment.

A pre-existing GitHub OIDC provider is reused through its ARN; this stack does not alter it. When CI federation is explicitly enabled and no provider exists, bootstrap creates one. CI federation is disabled on a new setup unless you explicitly name your own repository. Cloning this public project does not grant its authors access to your AWS account.

## 2. Bootstrap state and CI federation

```bash
terraform -chdir=infra/terraform/bootstrap init
terraform -chdir=infra/terraform/bootstrap plan -out=bootstrap.tfplan
terraform -chdir=infra/terraform/bootstrap apply bootstrap.tfplan
```

Record the `state_bucket` and `deploy_role_arn` outputs. The bucket is private, versioned, encrypted, TLS-only, and protected against accidental Terraform destruction. Bootstrap state remains local and ignored; back it up securely. The application stack uses remote state and S3 lock files.

## 3. Create the image repository and durable tables

Replace `YOUR_STATE_BUCKET` with the bootstrap output:

```bash
terraform -chdir=infra/terraform/presenter init \
  -backend-config=bucket=YOUR_STATE_BUCKET \
  -backend-config=region=us-west-2
terraform -chdir=infra/terraform/presenter plan -out=foundation.tfplan
terraform -chdir=infra/terraform/presenter apply foundation.tfplan
```

An empty image URI creates the foundation without an unusable runtime. Do not apply this empty-image configuration to an existing deployment: keep its `image_uri` in the ignored variable file. The configuration helper preserves it when rerun.

## 4. Build, publish, and deploy

Choose a new immutable tag for each build; the repository rejects overwriting tags:

```bash
uv run --extra aws python deploy/manage.py publish --tag YOUR_COMMIT_OR_UNIQUE_TAG
terraform -chdir=infra/terraform/presenter plan -out=runtime.tfplan
terraform -chdir=infra/terraform/presenter apply runtime.tfplan
uv run --extra aws python deploy/manage.py logs
terraform -chdir=infra/terraform/presenter output runtime_arn
```

Publishing builds an ARM64 image, uses temporary ECR login material, pushes it, and pins `image_uri` to the registry digest. The runtime uses the packaged embedding model, DynamoDB state/checkpoints, the configured public verification key, eight model calls maximum, a 150-second investigation budget, and a 60-second idle timeout. `PUBLIC` is the runtime networking mode; invocation still requires IAM permission and operational requests still require the application JWT.

AgentCore creates its log group during provisioning. The separate logs stack declaratively imports that existing group, applies retention, and configures a dedicated KMS key. This avoids racing the service with a second CreateLogGroup request.

The `presenter` endpoint is pinned to a runtime version. Image/configuration updates produce a new version and Terraform moves that endpoint. New sessions see the selected version; already-running sessions may continue on the previous one until released.

## 5. Verify and present

```bash
uv run --extra aws python deploy/manage.py probe
uv run --extra aws python deploy/manage.py smoke
uv run runbookops present --runtime-arn YOUR_RUNTIME_ARN
```

The probe checks the actual IAM-authenticated runtime's health and durable configuration without requesting model inference. The smoke command makes **billed Bedrock calls**: it reads the actual event stream, requires a valid pending proposal, verifies viewer denial, approves in a fresh runtime session, checks HTTP 200, and discovers MCP tools. It writes a sanitized report to `artifacts/presenter-cloud-smoke.json` and fails rather than silently substituting offline results.

Open **http://127.0.0.1:8005/**. Choose Bagha for investigation and Jethalal for approval. Model, RAG, MCP, knowledge, incident, and approval requests go through AgentCore. The bridge does not run a duplicate local agent or local retrieval index. Inspect **Model & limits → Agent backend** to confirm the selected path.

AWS credentials are used only by the local server. Tokens remain in browser memory. The presenter server rejects non-loopback clients/hosts and cross-origin requests. Do not expose it through a tunnel or shared listener.

## Optional CloudWatch example

Set `cloudwatch_log_group` to `/runbookops/presenter-sample` in the ignored presenter variable file and apply the plan. Terraform creates that group with one-day retention and grants the agent only `logs:FilterLogEvents` for it.

```bash
uv run --extra aws python deploy/manage.py seed-logs
```

Ask the live agent to read the sample CloudWatch logs, or inspect/call `read_cloudwatch_logs` through MCP. The tool reads at most 20 entries over the last 15 minutes, truncates long messages, and redacts secrets. It reports that the data is a separate AWS demo source; it cannot replace the required simulator evidence for an approved correction. Reseed before presenting if the sample falls outside the time window.

Seeding is an explicit operator command with AWS write access; those permissions are not given to the agent. Leave the variable empty to omit the sixth tool.

## GitHub Actions deployment

First fork the repository if you are deploying it under another owner. Explicitly opt into federation, then review/apply the bootstrap plan again:

```bash
gh api repos/YOUR_OWNER/YOUR_REPO/actions/oidc/customization/sub --jq .sub_claim_prefix
uv run --extra aws python deploy/manage.py configure \
  --github-repository YOUR_OWNER/YOUR_REPO \
  --github-subject-prefix EXACT_PREFIX_FROM_GITHUB
terraform -chdir=infra/terraform/bootstrap plan -out=ci.tfplan
terraform -chdir=infra/terraform/bootstrap apply ci.tfplan
```

Copy the exact prefix returned by GitHub. New repositories use immutable owner/repository IDs in their subject; a name-only trust will fail. See [GitHub OIDC subject formats](https://docs.github.com/en/actions/reference/security/oidc). The policy requires that exact prefix and the `presenter` environment, with no wildcard.

After local bootstrap/foundation, configure your repository's `presenter` environment to allow deployments only from `main`. Set these environment variables:

| Variable | Value |
|---|---|
| `AWS_DEPLOY_ROLE_ARN` | Bootstrap deployment role ARN |
| `TF_STATE_BUCKET` | Bootstrap state bucket name |
| `AWS_ACCOUNT_ID` | Intended account ID |
| `RUNBOOKOPS_PUBLIC_KEY` | Contents of `.state/presenter-public.pem` |

These are configuration/public values. No AWS access key, model key, or demo private signing key is stored in GitHub. Run **Deploy presenter** manually from `main`. It obtains temporary credentials through OIDC, discovers model/profile metadata, builds and scans an immutable image, applies Terraform, and probes the real endpoint.

The CI probe does not exercise approver credentials or call a model. Run the full `smoke` command from your presenter laptop after a release to verify the paid capstone. This separation keeps the private signing key local. See [IAM](IAM.md) for role scope and policy generation.

CI intentionally does not bootstrap an empty AWS account or delete tables. Keep deployment concurrency at one. A failed deploy remains failed; inspect its Terraform/runtime status before trying another change.

## Update and rollback

Before deploying, record the current image digest and runtime version from the local configuration/Terraform outputs. Build a new unique tag and repeat the plan/apply/probe sequence. Terraform preserves the role, tables, and signing-key configuration.

To roll back, restore the previous `image_uri` digest in the ignored variable file, review the plan, apply it, and run the probe/smoke. Rollback is only supported across compatible state schemas. Existing sessions may retain older code until their idle/lifetime boundary; start a fresh presenter process when verifying a version change.

## Cleanup

Stop the local presenter with Ctrl+C, export any wanted evidence, then review the resource-removal plan:

```bash
terraform -chdir=infra/terraform/presenter plan -destroy -out=destroy.tfplan
terraform -chdir=infra/terraform/presenter apply destroy.tfplan
```

ECR must be empty before Terraform can delete it. Review the dedicated `runbookops-presenter` repository and remove its image tags/digests in AWS before applying the destroy plan; do not delete another project's repository. DynamoDB deletion removes saved incidents and approvals. A resource TTL deletes rows, not tables, runtimes, images, or log groups.

After the runtime stack is removed, destroy the logs stack with `terraform -chdir=infra/terraform/logs destroy`. Its dedicated KMS key enters a seven-day pending-deletion window. Never delete a log key while retaining logs that still need it.

Bootstrap is retained separately: its state bucket, CI role/policy, and an OIDC provider only if it created one. The bucket's `prevent_destroy` deliberately requires an explicit lifecycle change and removal of versioned objects before deletion. Keep it while using remote state. Remove only this project's CI role and any provider that bootstrap created; never remove a reused account-wide OIDC provider. Revoke the repository's environment variables when retiring the deployment.
