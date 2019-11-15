provider "aws" {
  region = "us-east-1"
}

terraform {
  backend "s3" {
    bucket = "joist-remote-state"
    key    = "dev"
    region = "us-east-1"
  }
}

# This is a hacky way of requiring a non-default workspace be used. It uses the file function
# on a non-existent path to trigger an error.
# See: https://github.com/hashicorp/terraform/issues/15469
locals {
  assert_not_default_workspace = terraform.workspace == "default" ? file("ERROR: default workspace not allowed") : null
}
data "aws_region" "joist" {}

module "storage" {
  source      = "./modules/storage"
  environment = "${terraform.workspace}"
}

output "AWS_REGION" {
  value = data.aws_region.joist.name
}

output "AWS_STORAGE_BUCKET_NAME" {
  value = module.storage.blobs_bucket
}

output "AWS_ACCESS_KEY_ID" {
  value = module.storage.iam_access_key_id
}

output "AWS_SECRET_ACCESS_KEY" {
  value = module.storage.iam_access_key_secret
}

output "UPLOAD_STS_ARN" {
  value = module.storage.upload_role_arn
}
