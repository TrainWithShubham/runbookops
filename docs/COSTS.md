# Costs and usage limits

Offline local practice makes no generative-model API calls. Local semantic retrieval downloads a model once and uses laptop CPU/memory. Live OpenRouter capacity depends on each user's provider account; the application never silently falls back to paid inference.

The presenter AWS deployment has a **$10/month hosting design target, excluding Bedrock inference**. It is not guaranteed free and is not an AWS billing cap. Usage, image/storage size, region, account allowances, logs, and runtime session lifetime determine the bill.

## What is billed

| Component | Usage driver |
|---|---|
| AgentCore Runtime | CPU and memory consumption across active/idle session lifetime |
| Bedrock | Model input/output tokens and selected inference profile/model |
| DynamoDB | Reads/writes, checkpoint/event volume, stored rows |
| ECR | Retained image storage and applicable transfer/scanning charges |
| CloudWatch | Log ingestion/storage; optional sample-log reads |
| S3 | Versioned Terraform state/locks and requests |
| KMS | Dedicated runtime-log encryption key and requests |

The baseline does not provision always-on compute, a load balancer, NAT gateway, managed vector cluster, or purchased domain. It retains ten ECR images for rollback, runtime logs for three days, optional sample logs for one day, and application rows for their configured seven-day TTL. Checkpoint retention is managed by its adapter. TTL is asynchronous and does not remove the infrastructure itself.

## Admission controls

The local presenter defaults to one active investigation and 20 admitted starts per UTC day per runtime. Counts persist in `.state/presenter-usage.sqlite`, including across bridge restarts and failed attempts. API and streamed starts share that allowance. Inspectors and saved-state reads do not call a model but still invoke the runtime.

Set limits in the presenter's environment before starting it:

```bash
export RUNBOOKOPS_PRESENTER_DAILY_RUNS=20
export RUNBOOKOPS_LIVE_ENABLED=true
```

Set `RUNBOOKOPS_LIVE_ENABLED=false` and restart the presenter to disable new investigations while retaining read access. The runtime independently enforces its model-call, token, tool-step, and investigation-time budgets. The demo Terraform profile permits at most eight model calls and releases idle microVMs after 60 seconds.

These are application limits. An AWS administrator invoking the runtime directly can bypass the local presenter's allowance. They are not a global account spending control. Billing alerts can be delayed and in-flight work can continue to incur charges.

## Estimate from evidence

Use the public [AgentCore pricing](https://aws.amazon.com/bedrock/agentcore/pricing/), [Bedrock pricing](https://aws.amazon.com/bedrock/pricing/), and each regional service's rates. Measure CPU time, peak/billed memory, total session lifetime including initialization and idle time, retained image size, API/read volume, and log bytes. Include retries and a margin. Check eligibility before counting free allowances or promotional credits.

The built-in development budgets are conservative starting values, not a measured monthly quote. Record an actual rehearsal workload and model usage in the release verification record. Short tests cannot establish a monthly cost guarantee. Review billing and set AWS Budget notifications through your account's existing alert channel before keeping a deployment running unattended.

Stopping the laptop UI does not delete AWS resources. Follow [AWS cleanup](AWS.md). Retained ECR images, state, tables, and logs may still incur storage costs after runtime sessions expire.
