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
