"""Offline verification for post-failed-apply inventory, zero AWS access."""
from __future__ import annotations

import importlib.util
from pathlib import Path


FILE = Path(__file__).resolve().parents[1] / "scripts" / "s2b_failed_apply_inventory_readonly.py"
spec = importlib.util.spec_from_file_location("s2b_inventory", FILE)
assert spec is not None and spec.loader is not None
inv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inv)


class AwsError(Exception):
    def __init__(self, code: str):
        self.response = {"Error": {"Code": code}}


class Stub:
    def __init__(self, resource: str = "absent"):
        self.resource = resource

    def head_bucket(self, **kwargs):
        return self._resolve("404")

    def describe_table(self, **kwargs):
        return self._resolve("ResourceNotFoundException")

    def get_queue_url(self, **kwargs):
        return self._resolve("AWS.SimpleQueueService.NonExistentQueue")

    def describe_alarms(self, **kwargs):
        if self.resource == "present":
            return {"MetricAlarms": [{"AlarmName": "synthetic"}]}
        if self.resource == "unknown":
            raise AwsError("AccessDeniedException")
        return {"MetricAlarms": []}

    def get_caller_identity(self):
        return {"Account": "123456789012"}

    def _resolve(self, missing: str):
        if self.resource == "absent":
            raise AwsError(missing)
        if self.resource == "unknown":
            raise AwsError("AccessDenied")
        return {"Resource": "some-value"}


def inspect(*, s3="absent", ddb="absent", sqs="absent", cw="absent"):
    return inv.inspect(
        s3=Stub(s3), ddb=Stub(ddb), sqs=Stub(sqs),
        cloudwatch=Stub(cw), sts=Stub(), account="123456789012",
    )


def test_empty_aws_resources_are_only_plan_review_ready():
    report = inspect()
    assert report["all_five_resources_confirmed_absent"] is True
    assert report["decision"] == "READY_FOR_NEW_PLAN_REVIEW_ONLY"
    assert report["terraform_apply_authorized"] is False
    assert set(report["checks"].values()) == {"ABSENT"}
    assert "123456789012" not in str(report)


def test_any_partial_existing_resource_fails_closed():
    for key in ("s3", "ddb", "sqs", "cw"):
        report = inspect(**{key: "present"})
        assert report["decision"] == "NO_GO"
        assert report["all_five_resources_confirmed_absent"] is False


def test_access_denied_is_unknown_not_absent():
    for key in ("s3", "ddb", "sqs", "cw"):
        report = inspect(**{key: "unknown"})
        assert report["decision"] == "NO_GO"
        assert "UNKNOWN" in report["checks"].values()


def test_wrong_aws_account_is_no_go():
    report = inv.inspect(
        s3=Stub(), ddb=Stub(), sqs=Stub(),
        cloudwatch=Stub(), sts=Stub(), account="999999999999",
    )
    assert report == {"decision": "NO_GO", "reason": "wrong_account"}
