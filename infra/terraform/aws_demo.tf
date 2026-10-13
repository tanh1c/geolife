# Restricted internal demo only. No inbound security-group rules.
# Public subnet + public IP is used only for *outbound* SSM/ECR access
# without an expensive NAT gateway. This is NOT a public HTTP endpoint.

data "aws_ssm_parameter" "al2023_ami" {
  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
}

data "aws_caller_identity" "current" {}

resource "aws_ecr_repository" "api" {
  name                 = format("%s-%s-api", var.project_name, var.environment)
  image_tag_mutability = "IMMUTABLE"
  force_delete         = false

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }
}

resource "aws_ecr_lifecycle_policy" "api" {
  repository = aws_ecr_repository.api.name
  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep the 5 most recent images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 5
      }
      action = { type = "expire" }
    }]
  })
}

resource "aws_cloudwatch_log_group" "api" {
  name              = format("/geolife/%s/api", var.environment)
  retention_in_days = 7
}

resource "aws_security_group" "instance" {
  name_prefix = format("%s-%s-ssm-", var.project_name, var.environment)
  description = "No inbound: access only via AWS SSM session port forward"
  vpc_id      = var.vpc_id

  # There are intentionally ZERO ingress rules.
  egress {
    description = "Outbound HTTPS to SSM, ECR, package repositories and CW"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_iam_role" "instance" {
  name = format("%s-%s-ec2-role", var.project_name, var.environment)
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ssm" {
  role       = aws_iam_role.instance.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role_policy_attachment" "ecr" {
  role       = aws_iam_role.instance.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPullOnly"
}

resource "aws_iam_role_policy" "logs" {
  name = "geolife-api-cloudwatch-writer"
  role = aws_iam_role.instance.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "logs:CreateLogStream",
        "logs:DescribeLogStreams",
        "logs:PutLogEvents"
      ]
      Resource = format("%s:*", aws_cloudwatch_log_group.api.arn)
    }]
  })
}

resource "aws_iam_instance_profile" "api" {
  name = format("%s-%s-ec2-profile", var.project_name, var.environment)
  role = aws_iam_role.instance.name
}

resource "aws_instance" "api" {
  ami                         = data.aws_ssm_parameter.al2023_ami.value
  instance_type               = var.instance_type
  subnet_id                   = var.subnet_id
  vpc_security_group_ids      = [aws_security_group.instance.id]
  iam_instance_profile        = aws_iam_instance_profile.api.name
  associate_public_ip_address = true
  monitoring                  = false

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 2
  }

  root_block_device {
    volume_size           = 20
    volume_type           = "gp3"
    encrypted             = true
    delete_on_termination = true
  }

  # This installs Docker only. App image is deployed *after ECR push*, manually
  # through AWS Systems Manager. No credentials or GeoLife GPS data in user_data.
  user_data = <<-EOF
    #!/bin/bash
    set -euo pipefail
    dnf -y install docker
    systemctl enable --now docker
    systemctl enable --now amazon-ssm-agent
    mkdir -p /opt/geolife-private
    chmod 700 /opt/geolife-private
  EOF

  user_data_replace_on_change = false

  tags = {
    Name            = format("%s-%s-ssm-only", var.project_name, var.environment)
    DataSensitivity = "synthetic-only-in-aws"
    Access          = "ssm-no-inbound"
  }

  depends_on = [
    aws_iam_role_policy_attachment.ssm,
    aws_iam_role_policy_attachment.ecr,
    aws_iam_role_policy.logs
  ]
}
