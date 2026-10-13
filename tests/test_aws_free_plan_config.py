"""Guardrails against reintroducing Free-plan-ineligible EC2 into AWS IaC.

These are source-contract tests, not proof of AWS account eligibility or actual
IAM assignment. AWS CLI still must verify account, region and AZ and Console
must update the *live* IAM Group policy.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOWED = {"c7i-flex.large", "m7i-flex.large"}


def test_free_plan_instance_types_and_iam_deny_are_aligned():
    text = (ROOT / "infra/terraform/variables.tf").read_text()
    match = re.search(r'variable "instance_type"\s*\{(?P<body>.*?)\n\}', text, re.S)
    assert match is not None
    block = match.group("body")
    assert re.search(r'default\s*=\s*"c7i-flex.large"', block)
    assert re.search(r'contains\(\["c7i-flex.large",\s*"m7i-flex.large"\]', block)
    assert "t3.medium" not in block
    policy = json.loads(
        (ROOT / "infra/iam/geolife-deployer-permission-set.template.json").read_text()
    )
    guards = [s for s in policy["Statement"] if s["Sid"] == "DenyUnapprovedEC2Sizes"]
    assert len(guards) == 1
    deny = guards[0]
    assert deny["Effect"] == "Deny"
    assert deny["Action"] == "ec2:RunInstances"
    assert set(deny["Condition"]["StringNotEqualsIfExists"]["ec2:InstanceType"]) == ALLOWED
    assert "t3.medium" not in str(deny)
    example = (ROOT / "infra/terraform/terraform.tfvars.example").read_text()
    assert re.search(r'instance_type\s*=\s*"c7i-flex.large"', example)


def test_ssm_only_and_no_terraform_iam_role_creation():
    tf = (ROOT / "infra/terraform/aws_demo.tf").read_text()
    assert "ingress = []" in tf
    assert "iam_instance_profile        = var.instance_profile_name" in tf
    assert 'resource "aws_iam_role"' not in tf
    assert 'resource "aws_iam_instance_profile"' not in tf
    assert "http_tokens                 = \"required\"" in tf
