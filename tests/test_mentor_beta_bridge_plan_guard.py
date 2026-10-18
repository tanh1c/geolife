"""No AWS credentials: synthetic Terraform plans with only safe in-memory data."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.mentor_beta_bridge_plan_guard import (
    BRIDGE_RESOURCES, bridge_guard, ec2_attach_guard,
)


def bridge_plan():
    return {
        "resource_changes": [
            {"mode": "managed", "address": a, "change": {"actions": ["create"]}}
            for a in sorted(BRIDGE_RESOURCES)
        ],
        "variables": {
            "account_id": {"value": "939169265033"},
            "existing_ec2_instance_id": {"value": "i-0dfcfa110c0fd8af1"},
            "beta_backend_port": {"value": 18080},
        },
    }


def ec2_plan():
    before = {
        "id": "i-0dfcfa110c0fd8af1", "ami": "ami-test", "instance_type": "c7i-flex.large",
        "subnet_id": "subnet-00000000", "iam_instance_profile": "reviewed",
        "associate_public_ip_address": True, "user_data": "unchanged",
        "private_ip": "10.0.1.20", "vpc_security_group_ids": ["sg-00000000000000001"],
    }
    after = dict(before, vpc_security_group_ids=[
        "sg-00000000000000001", "sg-00000000000000002"
    ])
    return {"resource_changes": [{
        "mode": "managed", "address": "aws_instance.api",
        "change": {"actions": ["update"], "before": before, "after": after},
    }]}


def test_bridge_accepts_only_eight_creates():
    assert bridge_guard(bridge_plan())["create"] == 8


@pytest.mark.parametrize("mutation", [
    lambda p: p["resource_changes"].pop(),
    lambda p: p["resource_changes"][0]["change"].update(actions=["update"]),
    lambda p: p["resource_changes"].append({
        "mode": "managed", "address": "aws_security_group_rule.open_internet",
        "change": {"actions": ["create"]},
    }),
    lambda p: p["variables"]["beta_backend_port"].update(value=8000),
    lambda p: p["variables"]["account_id"].update(value="000000000000"),
])
def test_bridge_rejects_unknown_changes(mutation):
    p = bridge_plan()
    mutation(p)
    with pytest.raises(ValueError):
        bridge_guard(p)


def test_ec2_only_adds_second_sg_without_recreation():
    assert ec2_attach_guard(ec2_plan(), "sg-00000000000000002")["update"] == 1


@pytest.mark.parametrize("mutation", [
    lambda p: p["resource_changes"][0]["change"].update(actions=["delete", "create"]),
    lambda p: p["resource_changes"][0]["change"]["after"].update(
        instance_type="t2.micro"
    ),
    lambda p: p["resource_changes"][0]["change"]["after"].update(
        tags={"PublicExposure": "true"}
    ),
    lambda p: p["resource_changes"][0]["change"]["after"].update(
        vpc_security_group_ids=["sg-00000000000000002"]
    ),
    lambda p: p["resource_changes"].append({
        "mode": "managed", "address": "aws_s3_bucket.anything",
        "change": {"actions": ["create"]},
    }),
])
def test_ec2_rejects_replacement_drift_or_broad_changes(mutation):
    p = ec2_plan()
    mutation(p)
    with pytest.raises(ValueError):
        ec2_attach_guard(p, "sg-00000000000000002")
