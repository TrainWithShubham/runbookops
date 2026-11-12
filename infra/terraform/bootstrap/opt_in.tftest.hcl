mock_provider "aws" {}

run "local_bootstrap_has_no_ci_trust" {
  command = plan
  variables {
    github_repository        = ""
    github_subject_prefix    = ""
    github_oidc_provider_arn = ""
  }
  assert {
    condition     = length(aws_iam_role.deploy) == 0 && length(aws_iam_role_policy.deploy) == 0 && length(aws_iam_openid_connect_provider.github) == 0
    error_message = "A public clone must not grant CI deployment access by default."
  }
}

run "explicit_ci_trust_reuses_provider" {
  command = plan
  variables {
    github_repository        = "example/runbookops"
    github_subject_prefix    = "repo:example@123/runbookops@456"
    github_oidc_provider_arn = "arn:aws:iam::123456789012:oidc-provider/token.actions.githubusercontent.com"
  }
  assert {
    condition     = length(aws_iam_role.deploy) == 1 && length(aws_iam_openid_connect_provider.github) == 0
    error_message = "Explicit federation must create one role and reuse the supplied provider."
  }
  assert {
    condition     = jsondecode(aws_iam_role.deploy[0].assume_role_policy).Statement[0].Condition.StringEquals["token.actions.githubusercontent.com:sub"] == "repo:example@123/runbookops@456:environment:presenter"
    error_message = "The trust must name the selected repository and presenter environment."
  }
}
