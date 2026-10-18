
terraform {
  required_version = ">= 1.9.0, < 2.0.0"
  required_providers {
    aws = {
      source = "hashicorp/aws"
      version = ">= 6.35.0, < 7.0"
    }
  }
}
provider "aws" {
  region = "ap-southeast-1"
}
data "aws_caller_identity" "current" {}
variable "account_id" {
  type = string
  default = "939169265033"
}
variable "user_pool_id" { type = string }
variable "public_client_id" { type = string }
variable "vpc_id" { type = string }
variable "vpc_link_subnet_ids" {
  type = list(string)
  validation {
    condition = length(distinct(var.vpc_link_subnet_ids)) >= 2
    error_message = "Two distinct reviewed private subnets are required."
  }
}
variable "private_alb_arn" {
  description = "Existing internal ALB ARN only. None exists in the current SSM-only stack."
  type = string
}
variable "private_alb_listener_arn" {
  description = "Existing PRIVATE ALB listener ARN, not a public listener."
  type = string
}
variable "private_alb_security_group_id" { type = string }
variable "private_alb_listener_port" {
  type = number
  default = 80
  validation {
    condition = contains([80, 8000, 8080], var.private_alb_listener_port)
    error_message = "Only reviewed internal HTTP ports may be used."
  }
}

data "aws_vpc" "selected" { id = var.vpc_id }
data "aws_subnet" "link" {
  for_each = toset(var.vpc_link_subnet_ids)
  id = each.value
}
data "aws_lb" "private" { arn = var.private_alb_arn }
data "aws_lb_listener" "backend" { arn = var.private_alb_listener_arn }

check "hard_preflight" {
  assert {
    condition = data.aws_caller_identity.current.account_id == var.account_id
    error_message = "STOP: wrong AWS account."
  }
  assert {
    condition = data.aws_lb.private.load_balancer_type == "application" && data.aws_lb.private.internal
    error_message = "STOP: target ALB must be internal application load balancer."
  }
  assert {
    condition = data.aws_lb.private.vpc_id == var.vpc_id
    error_message = "STOP: private ALB must be in reviewed VPC."
  }
  assert {
    condition = alltrue([for s in data.aws_subnet.link : s.vpc_id == var.vpc_id])
    error_message = "STOP: VPC Link subnets must be in reviewed VPC."
  }
  assert {
    condition = length(distinct([for s in data.aws_subnet.link : s.availability_zone])) >= 2
    error_message = "STOP: VPC Link needs distinct availability zones."
  }
  assert {
    condition = data.aws_lb_listener.backend.load_balancer_arn == var.private_alb_arn
    error_message = "STOP: listener ARN does not belong to private ALB."
  }
  assert {
    condition = data.aws_lb_listener.backend.port == var.private_alb_listener_port
    error_message = "STOP: private ALB listener port mismatch."
  }
}

# VPC Link SECURITY GROUP has NO inbound and EGRESS to reviewed ALB SG only.
# The ALB SG must separately allow this source; this root never changes
# any existing EC2 or ALB security group.
resource "aws_security_group" "vpc_link" {
  name_prefix = "geolife-beta-vpclink-"
  description = "VPC Link egress only to reviewed private ALB SG"
  vpc_id = var.vpc_id
  ingress = []
  egress {
    description = "Private ALB listener"
    from_port = var.private_alb_listener_port
    to_port = var.private_alb_listener_port
    protocol = "tcp"
    security_groups = [var.private_alb_security_group_id]
  }
  tags = { Project = "geolife-mle", DataClass = "synthetic-only" }
}
resource "aws_apigatewayv2_vpc_link" "beta" {
  name = "geolife-mentor-beta-vpclink"
  subnet_ids = var.vpc_link_subnet_ids
  security_group_ids = [aws_security_group.vpc_link.id]
}

# Bridge ALB SG has NO inline ingress rules; this API root owns precisely the
# rule admitting VPC Link SG -> internal ALB listener. Neither root edits the
# legacy EC2 SSM-only SG.
resource "aws_vpc_security_group_ingress_rule" "alb_from_vpc_link" {
  security_group_id            = var.private_alb_security_group_id
  referenced_security_group_id = aws_security_group.vpc_link.id
  ip_protocol                  = "tcp"
  from_port                    = var.private_alb_listener_port
  to_port                      = var.private_alb_listener_port
  description                  = "Only beta HTTP API VPC Link can reach internal ALB"
}

resource "aws_apigatewayv2_api" "beta" {
  name = "geolife-mentor-beta-http-api"
  protocol_type = "HTTP"
  lifecycle {
    precondition {
      condition     = data.aws_caller_identity.current.account_id == var.account_id
      error_message = "Hard stop: wrong AWS account."
    }
    precondition {
      condition     = data.aws_lb.private.load_balancer_type == "application" && data.aws_lb.private.internal
      error_message = "Hard stop: ALB must be internal and application type."
    }
    precondition {
      condition     = data.aws_lb.private.vpc_id == var.vpc_id
      error_message = "Hard stop: ALB must be in selected VPC."
    }
    precondition {
      condition     = contains(data.aws_lb.private.security_groups, var.private_alb_security_group_id)
      error_message = "Hard stop: selected SG not attached to the private ALB."
    }
    precondition {
      condition     = alltrue([for s in data.aws_subnet.link : s.vpc_id == var.vpc_id])
      error_message = "Hard stop: VPC Link subnets outside selected VPC."
    }
    precondition {
      condition     = length(distinct([for s in data.aws_subnet.link : s.availability_zone])) >= 2
      error_message = "Hard stop: VPC Link requires two AZs."
    }
    precondition {
      condition     = data.aws_lb_listener.backend.load_balancer_arn == var.private_alb_arn
      error_message = "Hard stop: ALB listener belongs to another ALB."
    }
    precondition {
      condition     = data.aws_lb_listener.backend.port == var.private_alb_listener_port
      error_message = "Hard stop: ALB listener port mismatch."
    }
  }
}
resource "aws_apigatewayv2_authorizer" "cognito" {
  api_id = aws_apigatewayv2_api.beta.id
  name = "mentor-cognito-jwt"
  authorizer_type = "JWT"
  identity_sources = ["$request.header.Authorization"]
  jwt_configuration {
    audience = [var.public_client_id]
    issuer = "https://cognito-idp.ap-southeast-1.amazonaws.com/${var.user_pool_id}"
  }
}
resource "aws_apigatewayv2_integration" "private" {
  api_id = aws_apigatewayv2_api.beta.id
  integration_type = "HTTP_PROXY"
  integration_method = "ANY"
  connection_type = "VPC_LINK"
  connection_id = aws_apigatewayv2_vpc_link.beta.id
  integration_uri = var.private_alb_listener_arn
  payload_format_version = "1.0"
  request_parameters = {
    "overwrite:path" = "$request.path"
  }
}
resource "aws_apigatewayv2_route" "me" {
  api_id = aws_apigatewayv2_api.beta.id
  route_key = "GET /v3/beta/me"
  target = "integrations/${aws_apigatewayv2_integration.private.id}"
  authorization_type = "JWT"
  authorizer_id = aws_apigatewayv2_authorizer.cognito.id
  authorization_scopes = ["geolife-demo/read"]
}
resource "aws_apigatewayv2_route" "suggestions" {
  api_id = aws_apigatewayv2_api.beta.id
  route_key = "GET /v3/beta/destination-suggestions"
  target = "integrations/${aws_apigatewayv2_integration.private.id}"
  authorization_type = "JWT"
  authorizer_id = aws_apigatewayv2_authorizer.cognito.id
  authorization_scopes = ["geolife-demo/read"]
}
resource "aws_apigatewayv2_stage" "default" {
  api_id = aws_apigatewayv2_api.beta.id
  name = "$default"
  auto_deploy = true
  default_route_settings {
    throttling_burst_limit = 10
    throttling_rate_limit = 5
  }
}
output "api_origin_dns" {
  description = "Phase A needs a separately approved CloudFront update to route beta API."
  value = replace(aws_apigatewayv2_api.beta.api_endpoint, "https://", "")
}
output "vpc_link_security_group_id" { value = aws_security_group.vpc_link.id }
output "api_gateway_id" { value = aws_apigatewayv2_api.beta.id }
