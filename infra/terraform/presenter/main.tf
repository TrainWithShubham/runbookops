data "aws_caller_identity" "current" {}
data "aws_partition" "current" {}
locals {
  prefix  = "arn:${data.aws_partition.current.partition}"
  account = data.aws_caller_identity.current.account_id
}
resource "aws_ecr_repository" "app" {
  name                 = "runbookops-presenter"
  image_tag_mutability = "IMMUTABLE"
  image_scanning_configuration { scan_on_push = true }
  encryption_configuration { encryption_type = "AES256" }
}
resource "aws_ecr_lifecycle_policy" "app" {
  repository = aws_ecr_repository.app.name
  policy = jsonencode({
    rules = [{
      rulePriority = 1,
      description  = "Keep the ten newest images for rollback",
      selection = {
        tagStatus   = "any",
        countType   = "imageCountMoreThan",
        countNumber = 10
      },
      action = {
        type = "expire"
      }
      }
    ]
  })
}
resource "aws_dynamodb_table" "operations" {
  name         = "runbookops-presenter-operations"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "pk"
  attribute {
    name = "pk"
    type = "S"
  }
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }
  server_side_encryption {
    enabled = true
  }
}
resource "aws_dynamodb_table" "checkpoints" {
  name         = "runbookops-presenter-checkpoints"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "PK"
  range_key    = "SK"
  attribute {
    name = "PK"
    type = "S"
  }
  attribute {
    name = "SK"
    type = "S"
  }
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }
  server_side_encryption {
    enabled = true
  }
}
resource "aws_iam_role" "runtime" {
  name = "runbookops-presenter-runtime"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Principal = {
        Service = "bedrock-agentcore.amazonaws.com"
      },
      Action = "sts:AssumeRole",
      Condition = {
        StringEquals = {
          "aws:SourceAccount" = local.account
        },
        ArnLike = {
          "aws:SourceArn" = "${local.prefix}:bedrock-agentcore:${var.region}:${local.account}:*"
        }
      }
      }
    ]
  })
}
resource "aws_iam_role_policy" "runtime" {
  role = aws_iam_role.runtime.id
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = concat([{
      Effect   = "Allow",
      Action   = "ecr:GetAuthorizationToken",
      Resource = "*"
      }, {
      Effect = "Allow",
      Action = [
        "ecr:BatchGetImage",
        "ecr:GetDownloadUrlForLayer"
      ],
      Resource = aws_ecr_repository.app.arn
      }, {
      Effect = "Allow",
      Action = [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      Resource = var.model_arns
      }, {
      Effect = "Allow",
      Action = [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem",
        "dynamodb:Query",
        "dynamodb:BatchWriteItem",
        "dynamodb:BatchGetItem",
        "dynamodb:DescribeTable"
      ],
      Resource = [
        aws_dynamodb_table.operations.arn,
        aws_dynamodb_table.checkpoints.arn
      ]
      }, {
      Effect = "Allow",
      Action = [
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      Resource = "${local.prefix}:logs:${var.region}:${local.account}:log-group:/aws/bedrock-agentcore/runtimes/runbookops_presenter*:log-stream:*"
      }, {
      Effect = "Allow",
      Action = [
        "logs:CreateLogGroup",
        "logs:DescribeLogStreams"
      ],
      Resource = "${local.prefix}:logs:${var.region}:${local.account}:log-group:/aws/bedrock-agentcore/runtimes/runbookops_presenter*"
      }
      ],
      var.cloudwatch_log_group == "" ? [
        ] : [{
          Effect = "Allow",
          Action = [
            "logs:FilterLogEvents"
          ],
          Resource = "${local.prefix}:logs:${var.region}:${local.account}:log-group:${var.cloudwatch_log_group}:*"
        }
    ])
  })
}
resource "aws_bedrockagentcore_agent_runtime" "app" {
  count              = var.image_uri == "" ? 0 : 1
  agent_runtime_name = "runbookops_presenter"
  description        = "Presenter-operated RunbookOps simulator with IAM admission"
  role_arn           = aws_iam_role.runtime.arn
  agent_runtime_artifact {
    container_configuration {
      container_uri = var.image_uri
    }
  }
  network_configuration { network_mode = "PUBLIC" }
  protocol_configuration { server_protocol = "HTTP" }
  request_header_configuration { request_header_allowlist = ["X-RunbookOps-Token"] }
  lifecycle_configuration {
    idle_runtime_session_timeout = 60
    max_lifetime                 = 900
  }
  environment_variables = {
    RUNBOOKOPS_CLOUD                = "true"
    RUNBOOKOPS_MODE                 = "bedrock"
    RUNBOOKOPS_EMBEDDING            = "semantic"
    RUNBOOKOPS_FREE_ONLY            = "false"
    RUNBOOKOPS_MAX_MODEL_CALLS      = tostring(var.max_calls)
    RUNBOOKOPS_MAX_OUTPUT_TOKENS    = "2048"
    BEDROCK_MODEL_ID                = var.model_id
    RUNBOOKOPS_DYNAMODB_TABLE       = aws_dynamodb_table.operations.name
    RUNBOOKOPS_CHECKPOINT_TABLE     = aws_dynamodb_table.checkpoints.name
    RUNBOOKOPS_OIDC_ISSUER          = "http://127.0.0.1:8000/oidc"
    RUNBOOKOPS_OIDC_AUDIENCE        = "runbookops"
    RUNBOOKOPS_OIDC_PUBLIC_KEY      = replace(var.public_key, "\n", "\\n")
    RUNBOOKOPS_CLOUDWATCH_LOG_GROUP = var.cloudwatch_log_group
  }
  lifecycle {
    precondition {
      condition     = var.public_key != ""
      error_message = "Generate and configure the presenter's public key before creating the runtime."
    }
  }
  depends_on = [aws_iam_role_policy.runtime]
}
resource "aws_bedrockagentcore_agent_runtime_endpoint" "presenter" {
  count                 = var.image_uri == "" ? 0 : 1
  name                  = "presenter"
  agent_runtime_id      = aws_bedrockagentcore_agent_runtime.app[0].agent_runtime_id
  agent_runtime_version = aws_bedrockagentcore_agent_runtime.app[0].agent_runtime_version
}

output "repository_url" { value = aws_ecr_repository.app.repository_url }
output "runtime_arn" { value = try(aws_bedrockagentcore_agent_runtime.app[0].agent_runtime_arn, "") }
output "runtime_version" { value = try(aws_bedrockagentcore_agent_runtime.app[0].agent_runtime_version, "") }
output "endpoint" { value = "presenter" }
output "region" { value = var.region }

resource "aws_cloudwatch_log_group" "sample" {
  count             = var.cloudwatch_log_group == "" ? 0 : 1
  name              = var.cloudwatch_log_group
  retention_in_days = 1
}

output "cloudwatch_log_group" { value = var.cloudwatch_log_group }
output "max_calls" { value = var.max_calls }
output "model_id" { value = var.model_id }
