terraform {
  required_version = ">= 1.11, < 2"
  required_providers {
    aws = { source = "hashicorp/aws", version = "= 6.49.0" }
  }
}
provider "aws" { region = var.region }
variable "region" { default = "us-west-2" }
variable "github_repository" {
  type        = string
  default     = ""
  description = "Explicit owner/repo to trust for deployment. Empty creates no GitHub deployment access."
  validation {
    condition     = var.github_repository == "" || can(regex("^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", var.github_repository))
    error_message = "Name your own GitHub owner/repo explicitly, or leave federation disabled."
  }
}
variable "github_oidc_provider_arn" {
  type    = string
  default = ""
}
data "aws_caller_identity" "current" {}
data "aws_partition" "current" {}
locals {
  account      = data.aws_caller_identity.current.account_id
  state_bucket = "runbookops-state-${local.account}-${var.region}"
  oidc_arn     = var.github_oidc_provider_arn != "" ? var.github_oidc_provider_arn : try(aws_iam_openid_connect_provider.github[0].arn, null)
  prefix       = "arn:${data.aws_partition.current.partition}"
}
resource "aws_s3_bucket" "state" {
  bucket = local.state_bucket
  tags   = { Project = "runbookops", Purpose = "terraform-state" }
  lifecycle { prevent_destroy = true }
}
resource "aws_s3_bucket_versioning" "state" {
  bucket = aws_s3_bucket.state.id
  versioning_configuration { status = "Enabled" }
}
resource "aws_s3_bucket_server_side_encryption_configuration" "state" {
  bucket = aws_s3_bucket.state.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}
resource "aws_s3_bucket_public_access_block" "state" {
  bucket                  = aws_s3_bucket.state.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
resource "aws_s3_bucket_policy" "tls" {
  bucket = aws_s3_bucket.state.id
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect    = "Deny",
      Principal = "*",
      Action    = "s3:*",
      Resource = [
        aws_s3_bucket.state.arn,
        "${aws_s3_bucket.state.arn}/*"
      ],
      Condition = {
        Bool = {
          "aws:SecureTransport" = "false"
        }
      }
      }
    ]
  })
}
resource "aws_iam_openid_connect_provider" "github" {
  count          = var.github_oidc_provider_arn == "" ? 1 : 0
  url            = "https://token.actions.githubusercontent.com"
  client_id_list = ["sts.amazonaws.com"]
  tags           = { Project = "runbookops" }
}
resource "aws_iam_role" "deploy" {
  count = var.github_repository == "" ? 0 : 1
  name  = "runbookops-github-deploy"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Principal = {
        Federated = local.oidc_arn
      },
      Action = "sts:AssumeRoleWithWebIdentity",
      Condition = {
        StringEquals = {
          "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com",
          "token.actions.githubusercontent.com:sub" = "repo:${var.github_repository}:environment:presenter"
        }
      }
      }
    ]
  })
  tags = { Project = "runbookops" }
}
resource "aws_iam_role_policy" "deploy" {
  count = var.github_repository == "" ? 0 : 1
  role  = aws_iam_role.deploy[0].id
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Action = [
        "kms:CreateKey"
      ],
      Resource = "*",
      Condition = {
        StringEquals = {
          "aws:RequestTag/Project" = "runbookops"
        }
      }
      }, {
      Effect = "Allow",
      Action = [
        "kms:DescribeKey",
        "kms:GetKeyPolicy",
        "kms:PutKeyPolicy",
        "kms:EnableKeyRotation",
        "kms:GetKeyRotationStatus",
        "kms:ListResourceTags",
        "kms:TagResource",
        "kms:UntagResource"
      ],
      Resource = "${local.prefix}:kms:${var.region}:${local.account}:key/*",
      Condition = {
        StringEquals = {
          "aws:ResourceTag/Project" = "runbookops"
        }
      }
      }, {
      Effect = "Allow",
      Action = [
        "logs:DescribeLogGroups"
      ],
      Resource = "*"
      }, {
      Effect = "Allow",
      Action = [
        "s3:ListBucket"
      ],
      Resource = aws_s3_bucket.state.arn
      }, {
      Effect = "Allow",
      Action = [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject"
      ],
      Resource = "${aws_s3_bucket.state.arn}/presenter/*"
      }, {
      Effect = "Allow",
      Action = [
        "ecr:GetAuthorizationToken",
        "sts:GetCallerIdentity",
        "bedrock:GetInferenceProfile"
      ],
      Resource = "*"
      }, {
      Effect = "Allow",
      Action = [
        "ecr:CreateRepository",
        "ecr:DescribeRepositories",
        "ecr:DescribeImages",
        "ecr:BatchCheckLayerAvailability",
        "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload",
        "ecr:PutImage",
        "ecr:BatchGetImage",
        "ecr:GetDownloadUrlForLayer",
        "ecr:GetRepositoryPolicy",
        "ecr:GetLifecyclePolicy",
        "ecr:PutLifecyclePolicy",
        "ecr:DeleteLifecyclePolicy",
        "ecr:ListTagsForResource",
        "ecr:TagResource",
        "ecr:UntagResource"
      ],
      Resource = "${local.prefix}:ecr:${var.region}:${local.account}:repository/runbookops-presenter"
      }, {
      Effect = "Allow",
      Action = [
        "dynamodb:CreateTable",
        "dynamodb:DescribeTable",
        "dynamodb:UpdateTable",
        "dynamodb:UpdateTimeToLive",
        "dynamodb:DescribeTimeToLive",
        "dynamodb:DescribeContinuousBackups",
        "dynamodb:UpdateContinuousBackups",
        "dynamodb:ListTagsOfResource",
        "dynamodb:TagResource",
        "dynamodb:UntagResource"
      ],
      Resource = "${local.prefix}:dynamodb:${var.region}:${local.account}:table/runbookops-presenter-*"
      }, {
      Effect = "Allow",
      Action = [
        "iam:CreateRole",
        "iam:GetRole",
        "iam:TagRole",
        "iam:UntagRole",
        "iam:UpdateAssumeRolePolicy",
        "iam:PutRolePolicy",
        "iam:GetRolePolicy",
        "iam:ListRolePolicies",
        "iam:ListAttachedRolePolicies",
        "iam:DeleteRolePolicy"
      ],
      Resource = "${local.prefix}:iam::${local.account}:role/runbookops-presenter-runtime"
      }, {
      Effect   = "Allow",
      Action   = "iam:PassRole",
      Resource = "${local.prefix}:iam::${local.account}:role/runbookops-presenter-runtime",
      Condition = {
        StringEquals = {
          "iam:PassedToService" = "bedrock-agentcore.amazonaws.com"
        }
      }
      }, {
      Effect = "Allow",
      Action = [
        "bedrock-agentcore:CreateAgentRuntime",
        "bedrock-agentcore:CreateWorkloadIdentity"
      ],
      Resource = "*"
      }, {
      Effect = "Allow",
      Action = [
        "bedrock-agentcore:GetAgentRuntime",
        "bedrock-agentcore:UpdateAgentRuntime",
        "bedrock-agentcore:CreateAgentRuntimeEndpoint",
        "bedrock-agentcore:GetAgentRuntimeEndpoint",
        "bedrock-agentcore:UpdateAgentRuntimeEndpoint",
        "bedrock-agentcore:ListTagsForResource",
        "bedrock-agentcore:TagResource",
        "bedrock-agentcore:UntagResource",
        "bedrock-agentcore:InvokeAgentRuntime"
      ],
      Resource = "${local.prefix}:bedrock-agentcore:${var.region}:${local.account}:runtime/runbookops_presenter*"
      }, {
      Effect = "Allow",
      Action = [
        "logs:CreateLogGroup",
        "logs:PutRetentionPolicy",
        "logs:AssociateKmsKey",
        "logs:ListTagsForResource",
        "logs:TagResource",
        "logs:UntagResource"
      ],
      Resource = [
        "${local.prefix}:logs:${var.region}:${local.account}:log-group:/aws/bedrock-agentcore/runtimes/runbookops_presenter*",
        "${local.prefix}:logs:${var.region}:${local.account}:log-group:/runbookops/presenter-sample*"
      ]
      }
    ]
  })
}
output "state_bucket" { value = aws_s3_bucket.state.id }
output "deploy_role_arn" { value = try(aws_iam_role.deploy[0].arn, "") }

moved {
  from = aws_iam_role.deploy
  to   = aws_iam_role.deploy[0]
}
moved {
  from = aws_iam_role_policy.deploy
  to   = aws_iam_role_policy.deploy[0]
}
