variable "aws_region" {
  description = "AWS region for the GeoLife service. Singapore is the default development region."
  type        = string
  default     = "ap-southeast-1"
}

variable "project_name" {
  description = "Project tag/name used by future AWS resources."
  type        = string
  default     = "geolife-mle"
}

variable "environment" {
  description = "Deployment environment name."
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be one of: dev, staging, prod."
  }
}

# Explicit VPC and public subnet selection avoids implicit/default VPC assumptions.
variable "vpc_id" {
  description = "Existing AWS VPC ID. Must contain the selected subnet."
  type        = string
  validation {
    condition     = can(regex("^vpc-[0-9a-f]+$", var.vpc_id))
    error_message = "Provide a valid vpc-... ID."
  }
}

variable "subnet_id" {
  description = "Existing public subnet with a 0.0.0.0/0 route to an Internet Gateway. No inbound SG rules are created."
  type        = string
  validation {
    condition     = can(regex("^subnet-[0-9a-f]+$", var.subnet_id))
    error_message = "Provide a valid subnet-... ID."
  }
}

variable "instance_type" {
  description = "Non-production single instance; t3.medium is safer for Python scientific packages than 1-2 GiB sizes."
  type        = string
  default     = "t3.medium"

  validation {
    condition     = contains(["t3.medium", "t3.large", "t3a.medium", "t3a.large"], var.instance_type)
    error_message = "Only t3/t3a medium or large are permitted for this demo."
  }
}

# One-time IAM console bootstrap by account admin; this role/profile is NOT
# created or mutated by Terraform. Only iam:PassRole on this exact IAM role
# is needed by the project SSO provisioning identity.
variable "instance_profile_name" {
  description = "Exact pre-created EC2 IAM role/instance profile name"
  type        = string
  default     = "geolife-mle-dev-ec2-role"
  validation {
    condition     = can(regex("^geolife-mle-[a-z0-9-]+-ec2-role$", var.instance_profile_name))
    error_message = "Expected a scoped geolife-mle-ENV-ec2-role instance profile name."
  }
}
