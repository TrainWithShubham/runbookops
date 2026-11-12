variable "region" { default = "us-west-2" }
variable "image_uri" {
  type        = string
  default     = ""
  description = "Immutable ECR image digest. Empty provisions foundation resources only."
  validation {
    condition     = var.image_uri == "" || can(regex("^.+\\.dkr\\.ecr\\.[a-z0-9-]+\\.amazonaws\\.com/runbookops-presenter@sha256:[a-f0-9]{64}$", var.image_uri))
    error_message = "Use a runbookops-presenter ECR image pinned by sha256 digest."
  }
}
variable "public_key" {
  type        = string
  default     = ""
  description = "Public RS256 verification key only. Never pass a private signing key."
  validation {
    condition     = var.public_key == "" || (strcontains(var.public_key, "BEGIN PUBLIC KEY") && !strcontains(var.public_key, "PRIVATE"))
    error_message = "Provide a public PEM key, never a private key."
  }
}
variable "model_id" { default = "us.amazon.nova-lite-v1:0" }
variable "model_arns" {
  type        = list(string)
  description = "Inference profile ARN and its exact destination foundation-model ARNs."
}
variable "max_calls" {
  default = 8
  validation {
    condition     = var.max_calls >= 1 && var.max_calls <= 8
    error_message = "Model calls must be between 1 and 8."
  }
}
variable "log_retention_days" { default = 3 }
variable "cloudwatch_log_group" {
  type        = string
  default     = ""
  description = "Optional project sample log group managed by this stack for the read-only connector."
  validation {
    condition     = var.cloudwatch_log_group == "" || startswith(var.cloudwatch_log_group, "/runbookops/")
    error_message = "Only a project-owned /runbookops/ log group is permitted."
  }
}
