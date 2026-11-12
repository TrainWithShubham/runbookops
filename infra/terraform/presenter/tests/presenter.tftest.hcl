mock_provider "aws" {
  mock_resource "aws_iam_role" {
    defaults = { arn = "arn:aws:iam::123456789012:role/runbookops-presenter-runtime" }
  }
  mock_resource "aws_ecr_repository" {
    defaults = { arn = "arn:aws:ecr:us-west-2:123456789012:repository/runbookops-presenter" }
  }
  mock_resource "aws_dynamodb_table" {
    defaults = { arn = "arn:aws:dynamodb:us-west-2:123456789012:table/runbookops-presenter-test" }
  }
  mock_resource "aws_bedrockagentcore_agent_runtime" {
    defaults = {
      agent_runtime_arn     = "arn:aws:bedrock-agentcore:us-west-2:123456789012:runtime/runbookops_presenter-ABCDEFGHIJ"
      agent_runtime_id      = "runbookops_presenter-ABCDEFGHIJ"
      agent_runtime_version = "1"
    }
  }

  mock_data "aws_caller_identity" {
    defaults = { account_id = "123456789012" }
  }
  mock_data "aws_partition" {
    defaults = { partition = "aws" }
  }
}
variables {
  model_arns = ["arn:aws:bedrock:us-west-2:123456789012:inference-profile/example"]
}
run "foundation_has_no_runtime_before_image" {
  command = plan
  variables { image_uri = "" }
  assert {
    condition     = length(aws_bedrockagentcore_agent_runtime.app) == 0
    error_message = "Bootstrap must not create a runtime with an absent image."
  }
  assert {
    condition     = aws_dynamodb_table.operations.billing_mode == "PAY_PER_REQUEST" && aws_dynamodb_table.checkpoints.ttl[0].enabled
    error_message = "Demo state must use on-demand capacity and TTL."
  }
}
run "presenter_is_bounded_and_uses_durable_state" {
  command = apply
  variables {
    image_uri  = "123456789012.dkr.ecr.us-west-2.amazonaws.com/runbookops-presenter@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    public_key = "-----BEGIN PUBLIC KEY-----\nexample-public-fixture\n-----END PUBLIC KEY-----"
  }
  assert {
    condition     = aws_bedrockagentcore_agent_runtime.app[0].lifecycle_configuration[0].idle_runtime_session_timeout == 60
    error_message = "Idle microVMs must be released after 60 seconds."
  }
  assert {
    condition     = aws_bedrockagentcore_agent_runtime.app[0].environment_variables["RUNBOOKOPS_CLOUD"] == "true" && aws_bedrockagentcore_agent_runtime.app[0].environment_variables["RUNBOOKOPS_MAX_MODEL_CALLS"] == "8"
    error_message = "Cloud mode and bounded model calls are required."
  }
  assert {
    condition     = toset(jsondecode(aws_iam_role_policy.runtime.policy).Statement[2].Resource) == toset(var.model_arns)
    error_message = "Model permissions must use the selected inference profile and models."
  }
}
run "mutable_image_is_rejected" {
  command = plan
  variables { image_uri = "123456789012.dkr.ecr.us-west-2.amazonaws.com/runbookops-presenter:latest" }
  expect_failures = [var.image_uri]
}
run "private_signing_key_is_rejected" {
  command = plan
  variables { public_key = "-----BEGIN PRIVATE KEY-----\nfixture\n-----END PRIVATE KEY-----" }
  expect_failures = [var.public_key]
}
