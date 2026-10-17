# S2b recovery: Terraform refresh drift review without weakening apply guard

**Date:** 2026-10-17. **Status: NO-GO for apply until exact drift review.** This page responds to the operator's report after a successful S3 bucket untaint, state backup and private recovery plan generation. **No AWS or Terraform state operation is executed by this documentation.**

## Actual reported state

- Bucket exists with correct AWS account/region, synthetic tags, S3 Block Public Access and AES256. Object, version and multipart-upload checks were empty before the only bucket `untaint`.
- `terraform untaint aws_s3_bucket.payloads` succeeded after backup; private Terraform state now contains **six managed resources**, no taint. EC2 remains STOPPED, SG has 0 inbound.
- New private saved plan `s2b-after-untaint.tfplan`: **4 create / 6 no-op / 0 update / 0 delete** in `resource_changes`.
- The old guard REJECTED because Terraform reported **5 entries in `resource_drift`** with non-no-op refresh actions. This does NOT by itself imply Terraform plans to update five resources, but it MUST be reviewed. No apply was executed. The drift details were **not provided**, so we cannot assert they are harmless.

According to [HashiCorp Terraform JSON plan specification](https://developer.hashicorp.com/terraform/internals/json-format), `resource_drift` describes changes detected when comparing refreshed AWS objects with the previously saved state. `resource_changes` independently describes the operations Terraform would actually perform. See also [HashiCorp drift management](https://docs.hashicorp.com/terraform/tutorials/state/resource-drift).

## Guard patch (PR #78)

`scripts/s2b_plan_guard.py` now supports two **read-only** options:

- `--inspect-drift`: prints ONLY approved resource addresses, changed **attribute paths** and a SHA-256 fingerprint for the drift content, never raw before/after values, account IDs, private secrets or Terraform plan JSON. `resource_drift` with unexpected resource, duplicate, delete/replace or malformed values is rejected.
- `--reviewed-drift-digest <SHA256>`: after an operator has privately reviewed the precise paths for this saved plan, binds acceptance to exactly those `resource_drift` objects. It **does not bypass** the strict allowlist: all 10 planned resources must still be 4 `create` / 6 `no-op` in this instance, no managed prior resource may be recreated or updated, and each drifted resource must be in the tracked six with a true planned `no-op`. Each drift's observed post-refresh `after` must equal the planned no-op `after`. Drift in security-sensitive fields (encryption, policies, public access, ACL, TTL, billing mode, redrive, SQS SSE/visibility/retention, lifecycle, permission/principal) is **never automatically approvable**, even with the matching digest.

These flags do **not** edit the plan, state or AWS. The default behavior remains NO-GO on unreviewed drift. The resulting `decision` is `GO_FOR_MANUAL_REVIEW_ONLY_NOT_APPLY`; this is **NOT** a command or authorization to apply.

## Run on local with the EXISTING saved plan JSON — no new plan necessary

From repository root in PowerShell:

```powershell
git fetch origin
git switch feature/track-b1-s2b-aws-sqs-serving
git pull --ff-only
python -m pytest -q tests/test_s2b_plan_guard.py

$tfDir = Join-Path $HOME "geolife-private/s2b-plan-3y9c3j"
$plan = Join-Path $tfDir "s2b-after-untaint.tfplan"
$planJson = Join-Path $tfDir "s2b-after-untaint.json"

# Existing saved plan and its ORIGINAL JSON are private and remain unchanged.
if (-not (Test-Path $plan) -or -not (Test-Path $planJson)) {
    throw "STOP: expected saved plan/JSON not found; inspect operator's filenames"
}

# Display only field paths and an exact digest, not AWS attribute values:
$reportFile = Join-Path $tfDir "s2b-refresh-drift-review.json"
python scripts/s2b_plan_guard.py $planJson --expected-account 939169265033 --allow-partial-state --inspect-drift > $reportFile
if ($LASTEXITCODE -ne 0) { throw "STOP: invalid or external Terraform drift" }
$report = Get-Content $reportFile -Raw | ConvertFrom-Json
$report.drift | Format-List

# Manually read every changed_attribute_paths for the five drifted resources.
# STOP if any unknown/unapproved path or security-sensitive configuration.
# Ensure the original saved plan itself still lists 4 create / 6 no-op / 0 changes/deletes.
terraform "-chdir=$tfDir" show $plan

# Only after review of the exact report: use its fingerprint, not a synthetic one.
$digest = $report.fingerprint_sha256
python scripts/s2b_plan_guard.py $planJson --expected-account 939169265033 --allow-partial-state --reviewed-drift-digest $digest
if ($LASTEXITCODE -ne 0) { throw "NO-GO: strict drift-aware plan guard rejected" }
```

The drift fingerprint is **not a secret**; the field paths and counts are safe to share for review, but NEVER upload the Terraform plan/JSON/state or `before`/`after` raw values. If any changed path looks sensitive, stop before the second guard command and report only the **resource address and attribute-path name**. If the guard says `after-state differs from no-op plan`, an untracked resource, or unexpected action, **do not use `-refresh=false`, `terraform apply -target`, `terraform state rm`, or alter plan JSON** as a workaround.

## Acceptance before an AWS mutation

1. `--inspect-drift` reports only expected S2b resources/attribute paths and stable fingerprint.
2. Human reviews the drift field names and the saved plan, no security-sensitive changes or unknown scope.
3. Strict `--reviewed-drift-digest` guard PASS with **4 create / 6 no-op / 0 update / 0 delete**, unchanged state, correct account and region. No state edits or new plan in this step.
4. USD 10 experimental limit and existing charges/remaining USD 2 cushion confirmed; provisioned DynamoDB/SQS/S3/CloudWatch resources already incur costs.
5. Separate **explicit approval for applying that exact saved plan**. The current user has asked for diagnosis/recovery, not an unreviewed production change.

If all gates pass, the only planned AWS changes should be four remaining S3 configuration resources (public access block, default encryption, lifecycle rule and bucket policy). The actual `resource_changes` allowlist and state must confirm that; do not infer the exact four solely from counts.

**Worklog:** update after operator runs the amended guard. Until then, S2b is partially provisioned and the drift gate remains NO-GO.
