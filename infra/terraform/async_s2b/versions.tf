terraform {
  required_version = ">= 1.9.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "geolife-mle"
      Environment = "synthetic-research"
      Track       = "b1-s2b"
      DataClass   = "synthetic-only"
    }
  }
}

variable "aws_region" {
  type        = string
  description = "AWS operator-approved region."
  default     = "ap-southeast-1"
}

variable "prefix" {
  description = "Unique lowercase test namespace, no actual user/project secrets."
  type        = string
  default     = "geolife-mle-s2b-dev"
  validation {
    condition     = can(regex("^[a-z0-9-]{10,36}$", var.prefix))
    error_message = "Prefix must be a lowercase alphanumeric/hyphen identifier."
  }
}

data "aws_caller_identity" "current" {}
