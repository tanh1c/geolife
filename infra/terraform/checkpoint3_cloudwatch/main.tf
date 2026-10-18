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
  region = "ap-southeast-1"
}

resource "aws_cloudwatch_log_group" "s2b_telemetry" {
  name              = "/geolife/dev/s2b-telemetry"
  retention_in_days = 7
  log_group_class   = "STANDARD"
}

resource "aws_cloudwatch_dashboard" "s2b_telemetry" {
  dashboard_name = "geolife-dev-s2b-synthetic-review"
  dashboard_body = file("${path.module}/../../../docs/design/checkpoint3_s2b_dashboard_review.json")
}
