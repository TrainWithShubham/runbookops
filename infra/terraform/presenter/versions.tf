terraform {
  required_version = ">= 1.11, < 2"
  backend "s3" {
    key          = "presenter/terraform.tfstate"
    use_lockfile = true
  }
  required_providers {
    aws = { source = "hashicorp/aws", version = "= 6.49.0" }
  }
}
provider "aws" {
  region = var.region
  default_tags { tags = { Project = "runbookops", Environment = "presenter", ManagedBy = "terraform" } }
}
