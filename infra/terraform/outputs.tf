output "aws_region" {
  description = "Configured AWS region."
  value       = var.aws_region
}

output "project_name" {
  description = "Configured project name."
  value       = var.project_name
}

output "environment" {
  description = "Configured deployment environment."
  value       = var.environment
}

output "ecr_repository_url" {
  description = "Push only synthetic/demo image; no GeoLife raw/cache data"
  value       = aws_ecr_repository.api.repository_url
}

output "ec2_instance_id" {
  description = "SSM session target (there is deliberately no public HTTP address)"
  value       = aws_instance.api.id
}

output "cloudwatch_log_group" {
  description = "Restricted demo container log group"
  value       = aws_cloudwatch_log_group.api.name
}

output "aws_account_id" {
  description = "Verify target AWS account before applying resources"
  value       = data.aws_caller_identity.current.account_id
}

output "instance_role_name" {
  value = aws_iam_role.instance.name
}

output "instance_security_group_id" {
  value = aws_security_group.instance.id
}
