<#
S2b AWS preflight — READ-ONLY AWS CLI calls. Does NOT start EC2, attach IAM,
create budgets, create AWS resources, run terraform apply, or store credentials.
Execution:
  .\scripts\s2b_preflight_readonly.ps1 -Profile geolife -ExpectedAccountId <12 digits> -InstanceId i-...
Results are only an identity/network summary. All returned AWS account details
must be reviewed locally. Never post credentials, private data, or raw AWS plans.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$Profile,
    [Parameter(Mandatory=$true)][ValidatePattern('^\d{12}$')][string]$ExpectedAccountId,
    [Parameter(Mandatory=$true)][ValidatePattern('^i-[0-9a-f]{8,17}$')][string]$InstanceId,
    [ValidateSet('ap-southeast-1')][string]$Region = 'ap-southeast-1'
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function ReadAwsJson([string[]]$AwsArgs) {
    $lines = & aws @AwsArgs --profile $Profile --region $Region --output json --no-cli-pager 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Read-only AWS command failed (inspect locally): $($AwsArgs[0]) $($AwsArgs[1])"
    }
    return ($lines | Out-String | ConvertFrom-Json)
}

if (-not (Get-Command aws -ErrorAction SilentlyContinue)) {
    throw 'AWS CLI v2 required; use aws sso login --profile <name> before the preflight.'
}
Write-Host 'S2b PRECHECK — read-only API calls only, no Terraform apply or resources created.'
$identity = ReadAwsJson @('sts', 'get-caller-identity')
if ($identity.Account -ne $ExpectedAccountId) {
    throw "NO-GO: AWS caller account does not match the expected ID."
}
Write-Host ("PASS: expected AWS account matched; region {0} (read-only)." -f $Region)

$raw = ReadAwsJson @('ec2', 'describe-instances', '--instance-ids', $InstanceId)
$instances = @($raw.Reservations | ForEach-Object { $_.Instances } | Where-Object { $null -ne $_ })
if ($instances.Count -ne 1) {
    throw 'NO-GO: expected exactly one existing EC2 instance.'
}
$instance = $instances[0]
if ($instance.State.Name -notin @('running', 'stopped')) {
    throw "NO-GO: instance is not in running or stopped state."
}
if (-not $instance.IamInstanceProfile -or -not $instance.IamInstanceProfile.Arn) {
    throw 'NO-GO: existing SSM instance profile is missing.'
}
Write-Host ("PASS: existing EC2 state {0}; instance type {1}." -f $instance.State.Name, $instance.InstanceType)

$groupIds = @($instance.SecurityGroups | ForEach-Object { $_.GroupId })
if ($groupIds.Count -lt 1) {
    throw 'NO-GO: no EC2 Security Group could be resolved.'
}
$groups = ReadAwsJson (@('ec2', 'describe-security-groups', '--group-ids') + $groupIds)
foreach ($group in $groups.SecurityGroups) {
    if (@($group.IpPermissions).Count -gt 0) {
        throw 'NO-GO: existing EC2 Security Group has inbound rules. Do not expose FastAPI.'
    }
}
Write-Host 'PASS: all attached EC2 Security Groups have zero inbound rules.'

$profileName = ($instance.IamInstanceProfile.Arn -split '/')[-1]
$profileResult = ReadAwsJson @('iam', 'get-instance-profile', '--instance-profile-name', $profileName)
$roles = @($profileResult.InstanceProfile.Roles)
if ($roles.Count -ne 1) {
    throw 'NO-GO: exactly one role must be attached to the existing instance profile.'
}
$roleName = $roles[0].RoleName
$attached = ReadAwsJson @('iam', 'list-attached-role-policies', '--role-name', $roleName)
$inline = ReadAwsJson @('iam', 'list-role-policies', '--role-name', $roleName)
Write-Host ("PASS: EC2 instance role resolved; {0} managed and {1} inline policies. Review these locally before adding S2b permissions." -f @($attached.AttachedPolicies).Count, @($inline.PolicyNames).Count)

if ($instance.State.Name -eq 'running') {
    $node = ReadAwsJson @('ssm', 'describe-instance-information', '--filters', ("Key=InstanceIds,Values={0}" -f $InstanceId))
    $online = @($node.InstanceInformationList | Where-Object { $_.PingStatus -eq 'Online' })
    if ($online.Count -ne 1) {
        throw 'NO-GO: EC2 running but SSM node is not ONLINE.'
    }
    Write-Host 'PASS: SSM agent is ONLINE.'
} else {
    Write-Host 'HOLD: EC2 is STOPPED. SSM online cannot be validated until separately approved start.'
}

# Budget inspection is read-only. If AWS account has no suitable budget,
# the operator must configure alerts in Billing separately before applying.
$budgets = ReadAwsJson @('budgets', 'describe-budgets', '--account-id', $ExpectedAccountId)
$budget10 = @($budgets.Budgets | Where-Object {
    $_.BudgetType -eq 'COST' -and $_.BudgetLimit.Unit -eq 'USD' -and
    [decimal]$_.BudgetLimit.Amount -le [decimal]10
})
if ($budget10.Count -lt 1) {
    Write-Warning 'HOLD: no account budget at or below 10 USD was confirmed. Set a cost budget with 5/8 USD alerts and verify Cost Explorer before apply.'
} else {
    Write-Host ("OBSERVED: {0} AWS account COST budget(s) <= 10 USD (verify alert recipients, scope and existing spend manually)." -f $budget10.Count)
}
Write-Host 'END: read-only preflight. Do NOT apply before separate plan/IAM/cost review.'
