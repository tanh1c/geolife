# Terraform — GeoLife AWS foundation

This directory satisfies the Track B1 Week 1 requirement to set up Terraform without
prematurely creating paid AWS infrastructure.

Current scope is intentionally **foundation only**:

- pin Terraform and the AWS provider;
- define development region/project/environment variables;
- apply consistent default AWS tags;
- validate the configuration in CI.

No EC2, Lambda, API Gateway, SQS, S3, IAM, CloudWatch, or networking resources are
created in Checkpoint 1. Those resources belong to the deployment/serving checkpoints.

## Local commands

```bash
terraform -chdir=infra/terraform fmt -check
terraform -chdir=infra/terraform init -backend=false
terraform -chdir=infra/terraform validate
```

To use custom development values:

```bash
cp infra/terraform/terraform.tfvars.example infra/terraform/terraform.tfvars
```

`terraform.tfvars`, state files, and the local `.terraform/` directory are ignored by git.

## Why there is no remote backend yet

Checkpoint 1 only asks for repository/environment/Terraform setup. Remote state,
locking, IAM roles and real AWS resources should be introduced together with the
Checkpoint 2 deployment design so the project does not pretend that an AWS deployment
already exists.

## Planned Checkpoint 2 extension

The same foundation can later own either:

- EC2 + container deployment; or
- Lambda + API Gateway for the lightweight FastAPI/classification path.

Model artifacts/version metadata and deploy-strategy infrastructure will be added only
after that architecture is chosen.
