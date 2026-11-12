# IAM boundaries

The presenter laptop uses the AWS SDK credential chain. Its IAM identity needs permission to invoke the selected runtime/endpoint. It signs each cloud request and adds a short-lived, scoped application JWT. AWS credentials never reach the browser. The JWT demonstrates viewer/approver roles; it does not grant AWS permissions.

Terraform creates a dedicated runtime role scoped to the selected inference profile and its actual destination models, the two project tables, the project image, and runtime logs. ECR authorization-token retrieval requires `Resource: "*"`; image operations are scoped to the repository. Runtime trust includes source-account and region-scoped source-ARN restrictions using the verified AgentCore pattern.

The optional CloudWatch connector receives `logs:FilterLogEvents` only for its configured project sample log group. No agent permission allows changing workloads or deleting AWS resources.

CI federation is opt-in. When you explicitly name your own repository, its deployment role trusts only that GitHub `repo:OWNER/REPO:environment:presenter` subject and the STS audience. New clones create no deployment role by default. Configure that environment to accept `main` only. The role can publish/update this project; its `iam:PassRole` permission names only the runtime role and the AgentCore service. It cannot delete tables/runtimes through the automated deployment workflow. Account-wide discovery/create actions that cannot be expressed as an existing resource ARN are enumerated rather than granted as service wildcards.

## Reproduce the baseline analysis

Policy Autopilot provides a deterministic baseline. Run from the repository root, substituting the account ID printed by configuration:

```bash
DISABLE_IAM_POLICY_AUTOPILOT_TELEMETRY=true uvx iam-policy-autopilot@latest generate-policies \
  src/runbookops/aws_store.py src/runbookops/models.py src/runbookops/cloudwatch.py \
  --region us-west-2 --account YOUR_ACCOUNT_ID \
  --service-hints dynamodb bedrock logs \
  --tf-dir infra/terraform/presenter \
  --tfvars infra/terraform/presenter/terraform.tfvars.json --pretty
```

For deployment permissions, render a saved Terraform plan to an ignored owner-readable JSON file and analyze that file separately. Do not upload or commit plans; they can contain sensitive values. Source analysis cannot discover every permission used inside a checkpoint library. Plan analysis may include broader provider lifecycle capabilities than the deploy workflow needs.

Review conditional actions in generated output. The baseline for this source included optional Guardrail/tool/bearer-token actions, DynamoDB replication actions, KMS decryption, and Logs Unmask. The supplied workload does not use those features and does not grant them. The maintained checkpoint adapter needs scoped query/batch/update/delete actions in addition to the direct store's get/put calls. Validate any change against the actual configured API path and a live deployment.

Generated output is a baseline, not authorization to attach it blindly. The Terraform policies are the deployed contracts. Changes to tools, storage encryption, identity, or providers require reviewing those contracts and recording new verification evidence.
