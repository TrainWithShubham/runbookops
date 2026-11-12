terraform {
  required_version = ">= 1.11, < 2"
  backend "s3" {
    key          = "presenter/logs.tfstate"
    use_lockfile = true
  }
  required_providers {
    aws = { source = "hashicorp/aws", version = "= 6.49.0" }
  }
}
variable "region" { default = "us-west-2" }
variable "runtime_id" {
  type = string
  validation {
    condition     = can(regex("^runbookops_presenter-[A-Za-z0-9]+$", var.runtime_id))
    error_message = "Only the dedicated RunbookOps presenter runtime can be managed here."
  }
}
variable "retention_days" { default = 3 }
provider "aws" { region = var.region }
import {
  to = aws_cloudwatch_log_group.runtime
  id = "/aws/bedrock-agentcore/runtimes/${var.runtime_id}-DEFAULT"
}
resource "aws_cloudwatch_log_group" "runtime" {
  kms_key_id        = aws_kms_key.logs.arn
  name              = "/aws/bedrock-agentcore/runtimes/${var.runtime_id}-DEFAULT"
  retention_in_days = var.retention_days
  tags              = { Project = "runbookops", Environment = "presenter", ManagedBy = "terraform" }
}
data "aws_caller_identity" "current" {}
resource "aws_kms_key" "logs" {
  description             = "RunbookOps presenter runtime logs"
  enable_key_rotation     = true
  deletion_window_in_days = 7
  tags                    = { Project = "runbookops", Environment = "presenter" }
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Sid    = "AccountAdministration",
      Effect = "Allow",
      Principal = {
        AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
      },
      Action   = "kms:*",
      Resource = "*"
      }, {
      Sid    = "RuntimeLogEncryption",
      Effect = "Allow",
      Principal = {
        Service = "logs.${var.region}.amazonaws.com"
      },
      Action = [
        "kms:Encrypt",
        "kms:Decrypt",
        "kms:ReEncrypt*",
        "kms:GenerateDataKey*",
        "kms:DescribeKey"
      ],
      Resource = "*",
      Condition = {
        ArnEquals = {
          "kms:EncryptionContext:aws:logs:arn" = "arn:aws:logs:${var.region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/bedrock-agentcore/runtimes/${var.runtime_id}-DEFAULT"
        }
      }
      }
    ]
  })
}
