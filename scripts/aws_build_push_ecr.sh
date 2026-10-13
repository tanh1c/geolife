#!/usr/bin/env bash
# Build and push the synthetic-only demo image to an EXISTING ECR repo.
# Explicitly does not create AWS resources, deploy or upload data.
set -euo pipefail

: "${AWS_REGION:?Set AWS_REGION, e.g. ap-southeast-1}"
: "${ECR_REPOSITORY_URL:?Set ECR_REPOSITORY_URL from Terraform output}"
: "${EXPECTED_AWS_ACCOUNT_ID:?Set EXPECTED_AWS_ACCOUNT_ID after verifying sts identity}"

ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
if [ "$ACCOUNT_ID" != "$EXPECTED_AWS_ACCOUNT_ID" ]; then
  echo "Account mismatch. Refusing ECR push." >&2
  exit 2
fi

case "$ECR_REPOSITORY_URL" in
  "$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/"*) ;;
  *) echo "ECR repo URL does not match account or region" >&2; exit 2 ;;
esac
SHA="$(git rev-parse --short=12 HEAD)"
TAG="rev-$SHA"
REGISTRY="$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

echo "Building image tag $TAG (no GeoLife files in Docker build allowlist)"
docker build --pull -t "geolife-api:$TAG" .
docker tag "geolife-api:$TAG" "$ECR_REPOSITORY_URL:$TAG"
aws ecr get-login-password --region "$AWS_REGION" |
  docker login --username AWS --password-stdin "$REGISTRY"
docker push "$ECR_REPOSITORY_URL:$TAG"

REPO_NAME="$(echo "$ECR_REPOSITORY_URL" | cut -d/ -f2-)"
DIGEST="$(aws ecr describe-images --region "$AWS_REGION" \
  --repository-name "$REPO_NAME" --image-ids "imageTag=$TAG" \
  --query 'imageDetails[0].imageDigest' --output text)"
case "$DIGEST" in sha256:*) ;; *) echo "Failed to retrieve digest" >&2; exit 3;; esac

echo "Immutable deploy image:"
echo "$ECR_REPOSITORY_URL@$DIGEST"
echo "Save this digest for the SSM instance runbook and rollback."
