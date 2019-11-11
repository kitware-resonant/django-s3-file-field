provider "aws" {
  region = "us-east-1"
}

terraform {
  backend "s3" {
    bucket = "joist-remote-state"
    key    = "example"
    region = "us-east-1"
  }
}

data "aws_region" "joist" {}

module "storage" {
  source      = "./modules/storage"
  environment = "example"
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
