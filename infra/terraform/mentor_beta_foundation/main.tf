
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
  region = var.aws_region
  default_tags {
    tags = {
      Project     = "geolife-mle"
      Environment = "mentor-beta"
      DataClass   = "synthetic-only"
      ManagedBy   = "terraform"
    }
  }
}
variable "aws_region" {
  type = string
  default = "ap-southeast-1"
  validation {
    condition = var.aws_region == "ap-southeast-1"
    error_message = "STOP wrong region."
  }
}
variable "account_id" {
  type = string
  default = "939169265033"
}
variable "api_gateway_origin" {
  type = string
  default = ""
  description = "Phase-B hostname only. Must have separately approved UPDATE plan."
  validation {
    condition = var.api_gateway_origin == "" || can(regex("^[a-z0-9]+[.]execute-api[.]ap-southeast-1[.]amazonaws[.]com$",var.api_gateway_origin))
    error_message = "Only ap-southeast-1 execute-api hostnames are permitted."
  }
}
data "aws_caller_identity" "current" {}
check "account_gate" {
  assert {
    condition = data.aws_caller_identity.current.account_id == var.account_id
    error_message = "STOP wrong AWS account."
  }
}
locals {
  prefix = "geolife-mentor-beta-${data.aws_caller_identity.current.account_id}"
  hosted = "${local.prefix}.auth.${var.aws_region}.amazoncognito.com"
}
resource "aws_s3_bucket" "site" {
  bucket        = "${local.prefix}-site"
  force_destroy = false
}
resource "aws_s3_bucket_public_access_block" "site" {
  bucket                  = aws_s3_bucket.site.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
resource "aws_s3_bucket_server_side_encryption_configuration" "site" {
  bucket = aws_s3_bucket.site.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}
resource "aws_s3_bucket_versioning" "site" {
  bucket = aws_s3_bucket.site.id
  versioning_configuration {
    status = "Enabled"
  }
}
resource "aws_cloudfront_origin_access_control" "site" {
  name                              = "${local.prefix}-oac"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}
resource "aws_cloudfront_response_headers_policy" "spa" {
  name = "${local.prefix}-headers"
  security_headers_config {
    content_type_options {
      override = true
    }
    frame_options {
      frame_option = "DENY"
      override     = true
    }
    referrer_policy {
      referrer_policy = "no-referrer"
      override        = true
    }
    strict_transport_security {
      access_control_max_age_sec = 31536000
      include_subdomains         = false
      override                   = true
    }
    content_security_policy {
      content_security_policy = "default-src 'self'; base-uri 'none'; object-src 'none'; frame-ancestors 'none'; connect-src 'self' https://${local.hosted}; form-action 'self' https://${local.hosted}; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self' data:"
      override                = true
    }
  }
}
resource "aws_cloudfront_distribution" "site" {
  enabled             = true
  is_ipv6_enabled     = true
  comment             = "Invite-only synthetic mentor beta"
  default_root_object = "index.html"
  price_class         = "PriceClass_100"
  origin {
    domain_name              = aws_s3_bucket.site.bucket_regional_domain_name
    origin_id                = "website-s3"
    origin_access_control_id = aws_cloudfront_origin_access_control.site.id
  }
  dynamic "origin" {
    for_each = var.api_gateway_origin == "" ? [] : [var.api_gateway_origin]
    content {
      domain_name = origin.value
      origin_id   = "jwt-http-api"
      custom_origin_config {
        http_port              = 80
        https_port             = 443
        origin_protocol_policy = "https-only"
        origin_ssl_protocols   = ["TLSv1.2"]
      }
    }
  }
  default_cache_behavior {
    target_origin_id           = "website-s3"
    viewer_protocol_policy     = "redirect-to-https"
    allowed_methods            = ["GET", "HEAD"]
    cached_methods             = ["GET", "HEAD"]
    cache_policy_id            = "658327ea-f89d-4fab-a63d-7e88639e58f6"
    response_headers_policy_id = aws_cloudfront_response_headers_policy.spa.id
    compress                   = true
  }
  dynamic "ordered_cache_behavior" {
    for_each = var.api_gateway_origin == "" ? [] : [1]
    content {
      path_pattern               = "/v3/beta/*"
      target_origin_id           = "jwt-http-api"
      viewer_protocol_policy     = "https-only"
      allowed_methods            = ["GET", "HEAD", "OPTIONS"]
      cached_methods             = ["GET", "HEAD"]
      cache_policy_id            = "4135ea2d-6df8-44a3-9df3-4b5a84be39ad"
      origin_request_policy_id   = "b689b0a8-53d0-40ab-baf2-68738e2966ac"
      response_headers_policy_id = aws_cloudfront_response_headers_policy.spa.id
      compress                   = true
    }
  }
  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }
  viewer_certificate {
    cloudfront_default_certificate = true
    minimum_protocol_version       = "TLSv1.2_2021"
  }
}
data "aws_iam_policy_document" "site" {
  statement {
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.site.arn}/*"]
    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [aws_cloudfront_distribution.site.arn]
    }
  }
  statement {
    effect    = "Deny"
    actions   = ["s3:*"]
    resources = [aws_s3_bucket.site.arn, "${aws_s3_bucket.site.arn}/*"]
    principals {
      type        = "*"
      identifiers = ["*"]
    }
    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }
}
resource "aws_s3_bucket_policy" "site" {
  bucket     = aws_s3_bucket.site.id
  policy     = data.aws_iam_policy_document.site.json
  depends_on = [aws_s3_bucket_public_access_block.site]
}
resource "aws_cognito_user_pool" "invite" {
  name                     = "${local.prefix}-users"
  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]
  deletion_protection      = "ACTIVE"
  user_pool_tier           = "ESSENTIALS"
  admin_create_user_config {
    allow_admin_create_user_only = true
  }
  password_policy {
    minimum_length    = 12
    require_lowercase = true
    require_uppercase = true
    require_numbers   = true
    require_symbols   = true
  }
  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }
}
resource "aws_cognito_user_group" "testers" {
  name         = "geolife-demo-testers"
  user_pool_id = aws_cognito_user_pool.invite.id
  description  = "Manually invited mentors and testers"
}
resource "aws_cognito_resource_server" "demo" {
  name         = "GeoLife synthetic beta"
  identifier   = "geolife-demo"
  user_pool_id = aws_cognito_user_pool.invite.id
  scope {
    scope_name        = "read"
    scope_description = "Read fictional destination suggestions only"
  }
}
resource "aws_cognito_user_pool_domain" "login" {
  domain                = local.prefix
  user_pool_id          = aws_cognito_user_pool.invite.id
  managed_login_version = 2
}
resource "aws_cognito_user_pool_client" "spa" {
  name                                 = "${local.prefix}-spa"
  user_pool_id                         = aws_cognito_user_pool.invite.id
  generate_secret                      = false
  prevent_user_existence_errors        = "ENABLED"
  enable_token_revocation              = true
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = ["openid", "geolife-demo/read"]
  supported_identity_providers         = ["COGNITO"]
  callback_urls                        = ["https://${aws_cloudfront_distribution.site.domain_name}/"]
  logout_urls                          = ["https://${aws_cloudfront_distribution.site.domain_name}/"]
  access_token_validity                = 15
  id_token_validity                    = 15
  refresh_token_validity               = 1
  token_validity_units {
    access_token  = "minutes"
    id_token      = "minutes"
    refresh_token = "days"
  }
  depends_on = [aws_cognito_resource_server.demo]
}
resource "aws_cognito_managed_login_branding" "spa" {
  client_id                   = aws_cognito_user_pool_client.spa.id
  user_pool_id                = aws_cognito_user_pool.invite.id
  use_cognito_provided_values = true
}

output "frontend_url" {
  value = "https://${aws_cloudfront_distribution.site.domain_name}/"
}
output "s3_bucket" {
  value = aws_s3_bucket.site.bucket
}
output "user_pool_id" {
  value = aws_cognito_user_pool.invite.id
}
output "public_client_id" {
  value = aws_cognito_user_pool_client.spa.id
}
output "issuer" {
  value = "https://cognito-idp.${var.aws_region}.amazonaws.com/${aws_cognito_user_pool.invite.id}"
}
output "hosted_login" {
  value = "https://${local.hosted}"
}
output "api_origin_enabled" {
  value = var.api_gateway_origin != ""
}
