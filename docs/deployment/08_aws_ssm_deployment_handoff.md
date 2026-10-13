# AWS Checkpoint 2 — SSM-only single-host deployment handoff

**Status: IaC + authenticated-canary code prepared. No AWS resources created.**

**Free plan operator:** If creating an AWS Organization would forfeit your remaining Free Tier credits, do not enable IAM Identity Center's organization instance. Instead use the existing scoped IAM user, MFA and temporary `aws login` from the [Free-plan IAM alternative](10_aws_free_plan_iam_user_bootstrap.md). The Identity Center setup below is only for already-established AWS Organizations.
The design is a **short-lived internal research demonstration**, deliberately not a public HTTPS API.

Architecture:

```text
Local browser / benchmark -> AWS CLI + SSM encrypted port forwarding
                                     |
                              EC2 (t3.medium)
                              no inbound SG
                              Docker :127.0.0.1:8000
                                     |
                      FastAPI /demo, /v2/me/* (Bearer)
                        2 variants + account-sticky canary
                          |                        |
                     ECR immutable image      CloudWatch Logs
```

**Phase 1 uses only a synthetic trajectory. No Microsoft GeoLife user-level cache,
coordinates, passwords or credentials are uploaded to AWS.** Dataset mode should
return HTTP 503 until a separate **privacy/permission decision** authorizes private
data transfer. GeoLife user IDs are dataset pseudonyms and cannot authenticate the
original participants. The local SSM tunnel prevents opening port 80/443/8000 to
the internet; there is **no public endpoint**.

## 0. Operator prerequisites — local / IAM

1. Install AWS CLI v2, Terraform 1.9.8, Docker, and the AWS Session Manager Plugin.
2. Use **IAM Identity Center / SSO in existing Organizations, OR Free-plan IAM user with MFA and temporary browser-based `aws login`**; don't paste
   access keys in chat or commit them. Set your expected AWS account ID and region.
3. Create the scoped SSO deployment and operator permission sets from
   `docs/deployment/09_aws_iam_identity_center_bootstrap.md`. Get IAM permissions
   (least privilege, account- and resource-scoped where possible)
   for EC2/VPC reads + RunInstances/TerminateInstances/CreateTags; EBS;
   ECR CreateRepository/UploadImage/DescribeImages (and optional image cleanup);
   IAM only GetRole/GetInstanceProfile and **PassRole on exactly the project role**;
   CloudWatch Logs CreateLogGroup/PutRetentionPolicy/DeleteLogGroup;
   SSM GetParameter (AL2023 public AMI), DescribeInstanceInformation/StartSession; and Terraform state.
   No IAM creation/update permissions are granted to the deployer: see
   `docs/deployment/09_aws_iam_identity_center_bootstrap.md` for SSO, permission
   sets and the one-time pre-created EC2 role.
   Don't attach AdministratorAccess to the EC2 instance.
4. Configure an **AWS Budget alert** and check region, instance pricing, public
   IPv4 address fees, EBS, ECR, CloudWatch log ingestion/storage, and transfer
   charges **before apply**. AWS budgets are alerts, not an automatic spending
   cutoff. Destroy resources after the demo.

Check locally:

```bash
aws --version
terraform version
docker --version
session-manager-plugin --version

export AWS_PROFILE=geolife-ops  # Free plan IAM user; see section on credential_process
export AWS_REGION=ap-southeast-1
aws login --profile geolife-ops  # Free plan alternative; AWS CLI >= 2.32.0
# If already on an existing AWS Organization with SSO, use:
# aws sso login --profile "$AWS_PROFILE"
aws sts get-caller-identity
```

Don't proceed until the printed account ID matches **your intended account**.

Find a VPC and a **public subnet** in your region; the subnet must route
`0.0.0.0/0` to an Internet Gateway. Don't assume the default VPC exists:

```bash
aws ec2 describe-vpcs --region "$AWS_REGION" \
    --query 'Vpcs[].{VpcId:VpcId,Default:IsDefault,CIDR:CidrBlock}' --output table
aws ec2 describe-subnets --region "$AWS_REGION" \
    --query 'Subnets[].{SubnetId:SubnetId,VpcId:VpcId,AZ:AvailabilityZone}' --output table
aws ec2 describe-route-tables --region "$AWS_REGION" \
    --query 'RouteTables[].{RouteTable:RouteTableId,VpcId:VpcId,Routes:Routes[].GatewayId}' --output json
```

The instance has a public IPv4 **solely for outbound HTTPS**, so an Internet
Gateway is needed without NAT charges. Security group has **zero inbound rules**
and outbound TCP/443 only. Access is IAM-authenticated SSM; no SSH keys.
Do not open inbound ports, even if the instance has a public address.

## 1. Terraform plan (local, read and approve resource/cost changes)

```bash
git fetch origin
git switch feature/track-b1-aws-deployment
git pull --ff-only origin feature/track-b1-aws-deployment

cp infra/terraform/terraform.tfvars.example infra/terraform/terraform.tfvars
# Edit ONLY local terraform.tfvars: vpc_id, subnet_id, region, environment.
# instance_profile_name must match the EC2 role created once in AWS IAM Console.
terraform -chdir=infra/terraform fmt -check
terraform -chdir=infra/terraform init
terraform -chdir=infra/terraform validate
terraform -chdir=infra/terraform plan -out=tfplan
terraform -chdir=infra/terraform show tfplan
```

Terraform config creates: ECR private image repository (immutable tags, scanning),
one **non-publicly reachable** EC2 host running Docker (AL2023, encrypted 20GiB
gp3 EBS, IMDSv2 required), zero-inbound SG, and CloudWatch log group with
7-day retention. **EC2 IAM role/instance profile must be pre-created by the IAM
administrator via the Console**, not by Terraform. **No IAM roles or instance profiles, Secrets Manager, S3 bucket,
NAT gateway, ELB, public DNS or real GeoLife cache are created.** AMI uses the
AWS AL2023 SSM public parameter, so update and patch on future deployments.

**Handoff gate to operator:** only after reviewing projected resources/cost,
run `terraform -chdir=infra/terraform apply tfplan`. This is a user operation,
**not** performed automatically by ChatGPT.

```bash
export EC2_INSTANCE_ID="$(terraform -chdir=infra/terraform output -raw ec2_instance_id)"
export ECR_REPOSITORY_URL="$(terraform -chdir=infra/terraform output -raw ecr_repository_url)"
export CLOUDWATCH_LOG_GROUP="$(terraform -chdir=infra/terraform output -raw cloudwatch_log_group)"
export EXPECTED_AWS_ACCOUNT_ID="$(terraform -chdir=infra/terraform output -raw aws_account_id)"

aws ssm describe-instance-information --region "$AWS_REGION" \
  --filters "Key=InstanceIds,Values=$EC2_INSTANCE_ID" \
  --query 'InstanceInformationList[].{InstanceId:InstanceId,Ping:PingStatus}' --output table
```

SSM should say `Online`; otherwise check instance profile, AL2023 SSM agent,
outbound 443/DNS and subnet's Internet Gateway.

## 2. Push image from LOCAL (no historical data)

```bash
bash scripts/aws_build_push_ecr.sh
```

Requires `AWS_REGION`, `ECR_REPOSITORY_URL`,
`EXPECTED_AWS_ACCOUNT_ID` exported above. The script checks account+registry,
builds from Docker's allowlisted sources, pushes an immutable `rev-<git-SHA>`
tag, and prints a **digest-pinned image URL**. **Save the digest URL.**
The instance pulls it using its pre-created ECR pull-only role; AWS credentials are
never copied to the container.

## 3. Start EC2 via SSM and provision a SYNTHETIC demo account

From your local terminal:

```bash
aws ssm start-session --region "$AWS_REGION" --target "$EC2_INSTANCE_ID"
```

Inside the instance's SSM shell, use the values from Terraform/ECR.
Do **not** include passwords/salts in the AWS CLI `send-command`,
`user_data`, cloud-init, command-line arguments, or chat.

```bash
sudo -i
export REGION=ap-southeast-1
export IMAGE='PASTE_THE_DIGEST_PINNED_ECR_IMAGE_FROM_STEP_2'

# Instance role supplies temporary ECR auth; no access keys.
ACCOUNT="$(aws sts get-caller-identity --query Account --output text)"
aws ecr get-login-password --region "$REGION" |
    docker login --username AWS --password-stdin "$ACCOUNT.dkr.ecr.$REGION.amazonaws.com"
docker pull "$IMAGE"

install -d -m 0700 -o 10001 -g 10001 /opt/geolife-private
docker run --rm -it \
  --mount type=bind,source=/opt/geolife-private,target=/private \
  "$IMAGE" python -c 'from pathlib import Path; import getpass; from geolife.api.demo_auth import provision_account; provision_account(Path("/private/auth.sqlite3"),"demo_000","000",getpass.getpass("Synthetic demo password: "))'
```

Use **a newly generated** password of at least 12 characters, not the
previously shared local test password.

Create runtime-only settings; no source code or passwords inside them:

```bash
umask 077
read -r -s -p 'Private canary routing salt (random 32+ chars): ' SALT
echo
printf 'GEOLIFE_PRIVATE_DEMO=1\nGEOLIFE_DEMO_AUTH_DB=/private/auth.sqlite3\nGEOLIFE_ROLLOUT_MODE=baseline\nGEOLIFE_CANARY_PERCENT=10\nGEOLIFE_CANARY_SALT=%s\nGEOLIFE_RELEASE_ID=aws-ssm-demo\n' "$SALT" > /opt/geolife-private/runtime.env
unset SALT
chmod 600 /opt/geolife-private/runtime.env
```

Run the image privately on loopback, logging only request metadata to
CloudWatch. The Docker image disables default Uvicorn access logs to avoid recording URL user IDs; CloudWatch will contain only app/system logs. **Never log GPS bodies or the generated auth file.**

```bash
docker run -d --name geolife-api --restart unless-stopped \
  -p 127.0.0.1:8000:8000 \
  --cpus=2 --memory=3g --read-only \
  --tmpfs /tmp:rw,nosuid,size=64m \
  --cap-drop ALL --security-opt no-new-privileges \
  --mount type=bind,source=/opt/geolife-private,target=/private \
  --env-file /opt/geolife-private/runtime.env \
  --log-driver awslogs --log-opt awslogs-region="$REGION" \
  --log-opt awslogs-group=/geolife/dev/api --log-opt awslogs-stream=geolife-demo \
  "$IMAGE"

docker ps --filter name=geolife-api
curl --fail http://127.0.0.1:8000/health
curl -s -o /dev/null -w '%{http_code}\n' -X POST http://127.0.0.1:8000/v2/me/dataset-inferences
# Expected 401 without login (no private dataset is mounted).
```

For `environment != dev`, replace the CloudWatch log group name accordingly.
**Do not** run multiple EC2 replicas with this SQLite account database design.

## 4. Local browser through encrypted SSM port forwarding

Back in a LOCAL terminal (leave it running):

```bash
aws ssm start-session --region "$AWS_REGION" \
  --target "$EC2_INSTANCE_ID" \
  --document-name AWS-StartPortForwardingSession \
  --parameters '{"portNumber":["8000"],"localPortNumber":["18000"]}'
```

Open **http://127.0.0.1:18000/demo** and log in with the synthetic demo
account. Upload the synthetic GeoLife-like trajectory: test HOME/abstain/map.
`POST /v2/me/dataset-inferences` returns 503 until a trusted private cache is
**separately approved** and mounted; this is intentional.

The browser talks to local port 18000; SSM tunnels to EC2. There is **no public
HTTPS endpoint** or API Gateway in this stage. SSM session access must be
restricted to trusted IAM principals. See the official AWS [Session Manager
port-forwarding documentation](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-sessions-start.html).

## 5. Canary and rollback — local/manual operations on EC2

The two authenticated `/v2/me/*` endpoints use stable HMAC routing for the
**demo account**. `baseline` always selects complete-link 200m;
`canary` partitions by `GEOLIFE_CANARY_PERCENT` between baseline and
DBSCAN 100m. The response explicitly includes `model_version`,
`routing_mode` and `release_id`. Sticky routing is per synthetic demo
account: a single account doesn't reproduce 90/10 proportions, so use a
sufficient set of separately provisioned synthetic accounts for traffic split.

For 10% canary, edit the root-only `runtime.env` to
`GEOLIFE_ROLLOUT_MODE=canary`, then **recreate** the container using the same
`docker run` command (changing a file does not update the environment of a
running process). Never put salts in command-line parameters.

**Rollback:** change `GEOLIFE_ROLLOUT_MODE=baseline`, then recreate the same
container with the last-known-good digest; verify `/v2/model-info` and
authenticated inference output. This is **app-level routing after a restart**,
not ALB weighted traffic or zero-downtime rolling canary.

## 5b. Measure authenticated latency (from LOCAL over SSM tunnel)

With the port forward still open on `http://127.0.0.1:18000`, run the
synthetic-only benchmark. Password is prompted, never stored in CLI argv;
bearer token is not included in the aggregate JSON output.

```bash
python scripts/benchmark_authenticated_demo.py \
  --url http://127.0.0.1:18000 \
  --account demo_000 --requests 50 --warmup 5
```

The benchmark records sync client-observed p50/p95/p99 and model counts after
authentication, and revokes the token at completion. The SSM tunnel contributes
network overhead. **One sticky account samples only its selected variant**.
To compare baseline/canary, repeat across multiple synthetic accounts and with
the explicitly restarted `GEOLIFE_ROLLOUT_MODE` configuration. Don't claim
an actual 90/10 traffic split from just one account or invent latency results.

## 6. Monitor and tear down

```bash
aws logs describe-log-streams --region "$AWS_REGION" \
  --log-group-name "$CLOUDWATCH_LOG_GROUP" --output table
```

Log stream creation assumes EC2 pre-created EC2 IAM role is attached and outbound 443 is
available. Metrics `/internal/metrics` are Prometheus-format and private;
**a CloudWatch dashboard/latency collector is NOT deployed yet**. Do not
publish fake p95 latency without measuring the real SSM-hosted deployment.

After the demo, remove the container, optionally revoke/delete ephemeral demo
account data, then run `terraform -chdir=infra/terraform destroy` from the
operator local machine after reviewing its destroy plan. ECR images must first
be explicitly deleted by an authorized operator if ECR repository is not empty;
`force_delete=false` is deliberate. Verify AWS EC2/ECR/EBS/CloudWatch billing
items and don't leave the t3.medium instance on indefinitely.

## Required operator handoff, in order

- [ ] IAM login bootstrap: **choose one**: [Free-plan IAM user + MFA + temporary aws login](10_aws_free_plan_iam_user_bootstrap.md), or [Identity Center with an existing Organization](09_aws_iam_identity_center_bootstrap.md). Never create an Organization just to enable SSO while relying on Free Tier credits.
- [ ] IAM administrator separately creates narrow EC2 service role/instance profile.
- [ ] Confirm intended AWS account and region via `sts get-caller-identity`.
- [ ] Set budget alert; verify role authorization and costs (EC2 + public IPv4).
- [ ] Pick VPC/public subnet and review Terraform plan; **user runs apply**.
- [ ] Verify SSM instance Online; **user runs ECR push**.
- [ ] Provision synthetic account and launch container inside a private SSM shell.
- [ ] Open local SSM port forward and report sanitized 401/200 + latency outputs.
- [ ] Review whether *historical* GeoLife private cache transfer is permitted
      before any data upload (not part of phase 1).
- [ ] Shut down/destroy paid resources when not testing.

AWS deployment must not be confused with ground-truth Home/Office accuracy or
authorization of the original GeoLife research subjects.
