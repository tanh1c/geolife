# Independent mentor-beta ALB bridge. Existing EC2/SG/IAM/SSM Terraform untouched.
terraform {
  required_version = ">= 1.9.0, < 2.0.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 6.35.0, < 7.0"
    }
  }
}
provider "aws" {
  region = "ap-southeast-1"
  default_tags {
    tags = {
      Project     = "geolife-mle"
      Environment = "mentor-beta"
      DataClass   = "synthetic-only"
      ManagedBy   = "terraform"
    }
  }
}
data "aws_caller_identity" "current" {}
variable "account_id" {
  type    = string
  default = "939169265033"
}
variable "vpc_id" {
  type = string
  validation {
    condition     = can(regex("^vpc-[0-9a-f]{8,17}$", var.vpc_id))
    error_message = "Must identify existing EC2 VPC by exact ID."
  }
}
variable "alb_subnet_ids" {
  description = "Two reviewed ALB subnets in separate AZs; never invent IDs."
  type        = list(string)
  validation {
    condition     = length(var.alb_subnet_ids) == 2 && length(distinct(var.alb_subnet_ids)) == 2
    error_message = "Supply exactly two distinct reviewed subnet IDs."
  }
}
variable "existing_ec2_instance_id" {
  type    = string
  default = "i-0dfcfa110c0fd8af1"
  validation {
    condition     = var.existing_ec2_instance_id == "i-0dfcfa110c0fd8af1"
    error_message = "Bridge fenced to the previously reviewed EC2 instance."
  }
}
variable "beta_backend_port" {
  type    = number
  default = 18080
  validation {
    condition     = var.beta_backend_port == 18080
    error_message = "Only dedicated beta port 18080 is reviewed."
  }
}
variable "attach_existing_target" {
  description = "Second-stage only: do not register STOPPED EC2 in the initial bridge plan."
  type        = bool
  default     = false
}
data "aws_vpc" "target" { id = var.vpc_id }
data "aws_subnet" "alb" {
  for_each = toset(var.alb_subnet_ids)
  id       = each.value
}
data "aws_instance" "existing" {
  instance_id = var.existing_ec2_instance_id
}
data "aws_subnet" "instance" {
  id = data.aws_instance.existing.subnet_id
}

locals {
  tag = "geolife-mentor-beta"
}
# Standalone SG rules: API root will own ALB ingress FROM VPC Link SG.
# Neither new SG contains public ingress or an inline rule to conflict with
# rules owned in another Terraform state.
resource "aws_security_group" "alb" {
  name_prefix            = "${local.tag}-alb-"
  description            = "Internal ALB: only VPC Link ingress in API Terraform root"
  vpc_id                 = var.vpc_id
  revoke_rules_on_delete = true
}
resource "aws_security_group" "backend" {
  name_prefix            = "${local.tag}-ec2-"
  description            = "Second EC2 SG: ALB-only ingress to dedicated beta port"
  vpc_id                 = var.vpc_id
  revoke_rules_on_delete = true
}
resource "aws_vpc_security_group_egress_rule" "alb_to_backend" {
  security_group_id            = aws_security_group.alb.id
  referenced_security_group_id = aws_security_group.backend.id
  ip_protocol                  = "tcp"
  from_port                    = var.beta_backend_port
  to_port                      = var.beta_backend_port
  description                  = "ALB -> dedicated beta container private IP port"
}
resource "aws_vpc_security_group_ingress_rule" "backend_from_alb" {
  security_group_id            = aws_security_group.backend.id
  referenced_security_group_id = aws_security_group.alb.id
  ip_protocol                  = "tcp"
  from_port                    = var.beta_backend_port
  to_port                      = var.beta_backend_port
  description                  = "Only internal ALB SG may reach backend port"
}
resource "aws_lb" "private" {
  name                       = "geolife-mentor-beta-alb"
  internal                   = true
  load_balancer_type         = "application"
  security_groups            = [aws_security_group.alb.id]
  subnets                    = var.alb_subnet_ids
  enable_deletion_protection = false
  drop_invalid_header_fields = true
  lifecycle {
    precondition {
      condition     = data.aws_caller_identity.current.account_id == var.account_id
      error_message = "STOP: wrong AWS account."
    }
    precondition {
      condition     = data.aws_subnet.instance.vpc_id == var.vpc_id
      error_message = "STOP: EC2 and ALB must use the same VPC."
    }
    precondition {
      condition     = alltrue([for s in data.aws_subnet.alb : s.vpc_id == var.vpc_id])
      error_message = "STOP: ALB subnets must use existing EC2 VPC."
    }
    precondition {
      condition     = length(distinct([for s in data.aws_subnet.alb : s.availability_zone])) == 2
      error_message = "STOP: ALB requires two AZs."
    }
    precondition {
      condition     = contains([for s in data.aws_subnet.alb : s.availability_zone], data.aws_subnet.instance.availability_zone)
      error_message = "STOP: EC2 target AZ MUST be enabled on the internal ALB (include the EC2's 1a subnet)."
    }
    precondition {
      condition     = !contains(["terminated", "shutting-down"], data.aws_instance.existing.instance_state)
      error_message = "STOP: existing EC2 is terminated."
    }
  }
}
resource "aws_lb_target_group" "beta" {
  name                 = "geolife-mentor-beta-tg"
  port                 = var.beta_backend_port
  protocol             = "HTTP"
  target_type          = "instance"
  vpc_id               = var.vpc_id
  deregistration_delay = 15
  health_check {
    path                = "/health"
    protocol            = "HTTP"
    matcher             = "200"
    port                = "traffic-port"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 2
  }
}
resource "aws_lb_target_group_attachment" "current_ec2" {
  count            = var.attach_existing_target ? 1 : 0
  target_group_arn = aws_lb_target_group.beta.arn
  target_id        = data.aws_instance.existing.id
  port             = var.beta_backend_port
  lifecycle {
    precondition {
      condition     = data.aws_instance.existing.instance_state == "running"
      error_message = "STOP: do not register the EC2 target until the instance is running (separate owner approval)."
    }
  }
}
resource "aws_lb_listener" "http_internal" {
  load_balancer_arn = aws_lb.private.arn
  port              = 80
  protocol          = "HTTP"
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.beta.arn
  }
}
output "alb_arn" {
  value = aws_lb.private.arn
}
output "alb_listener_arn" {
  value = aws_lb_listener.http_internal.arn
}
output "alb_security_group_id" {
  value = aws_security_group.alb.id
}
output "backend_security_group_id" {
  description = "Attach to existing EC2 only after separately approved in-place EC2 Terraform plan."
  value       = aws_security_group.backend.id
}
output "backend_private_ip" {
  value = data.aws_instance.existing.private_ip
}
output "backend_port" {
  value = var.beta_backend_port
}

output "target_registration_enabled" {
  value       = var.attach_existing_target
  description = "False during initial bridge plan; separate target-registration step after EC2 starts."
}
