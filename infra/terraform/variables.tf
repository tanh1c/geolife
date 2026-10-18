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
  description = "AWS Free plan eligible x86_64 (post-2025) instance with >=4 GiB RAM for scientific Python container. Verify actual account and AZ eligibility with AWS CLI before apply."
  type        = string
  default     = "c7i-flex.large"

  validation {
    condition     = contains(["c7i-flex.large", "m7i-flex.large"], var.instance_type)
    error_message = "Use only c7i-flex.large (4 GiB) or m7i-flex.large (8 GiB). Verify FreeTierEligible and AZ availability first."
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

# Intentionally OFF in every existing SSM-only run and default terraform plan.
# Set only to the separately approved mentor-beta backend SG in a scoped EC2
# state plan. The old SSM-only SG itself retains NO inbound rules.
variable "mentor_beta_backend_security_group_id" {
  type        = string
  default     = ""
  description = "Optional dedicated ALB-only inbound SG ID; PLAN/approval required before EC2 attachment."
  validation {
    condition     = var.mentor_beta_backend_security_group_id == "" || can(regex("^sg-[0-9a-f]{8,17}$", var.mentor_beta_backend_security_group_id))
    error_message = "Expected empty value or explicit reviewed sg-... backend SG ID."
  }
}
