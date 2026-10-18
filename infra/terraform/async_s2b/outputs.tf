output "s2b_bucket" {
  value       = aws_s3_bucket.payloads.id
  description = "S3 encrypted synthetic-only payload bucket."
}

output "s2b_table" {
  value = aws_dynamodb_table.jobs.name
}

output "s2b_queue_url" {
  value = aws_sqs_queue.jobs.id
}

output "s2b_dlq_url" {
  value = aws_sqs_queue.dead_letter.id
}

# IAM policy JSON for independent, explicit operator review/attachment.
# Terraform deliberately does NOT modify the existing EC2 instance role.
data "aws_iam_policy_document" "api_permissions" {
  statement {
    actions = ["s3:PutObject"]
    resources = ["${aws_s3_bucket.payloads.arn}/synthetic/*"]
  }
  statement {
    actions = ["dynamodb:GetItem", "dynamodb:PutItem"]
    resources = [aws_dynamodb_table.jobs.arn]
  }
  statement {
    actions = ["sqs:SendMessage"]
    resources = [aws_sqs_queue.jobs.arn]
  }
}

data "aws_iam_policy_document" "worker_permissions" {
  statement {
    actions = ["s3:GetObject", "s3:DeleteObject"]
    resources = ["${aws_s3_bucket.payloads.arn}/synthetic/*"]
  }
  statement {
    actions = ["dynamodb:GetItem", "dynamodb:UpdateItem"]
    resources = [aws_dynamodb_table.jobs.arn]
  }
  statement {
    actions = ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"]
    resources = [aws_sqs_queue.jobs.arn]
  }
}

# Existing SSM-only EC2 can run both API and a bounded CLI worker in the
# operator-approved demo. A joined policy is only for manual review.
data "aws_iam_policy_document" "combined_permissions" {
  source_policy_documents = [
    data.aws_iam_policy_document.api_permissions.json,
    data.aws_iam_policy_document.worker_permissions.json,
  ]
}

output "manual_ec2_iam_policy_json" {
  description = "REVIEW ONLY: no role attachment or new IAM privilege is automatically granted"
  value       = data.aws_iam_policy_document.combined_permissions.json
}
