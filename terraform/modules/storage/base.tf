variable "environment" {
  type    = string
  default = "production"
}

locals {
  qualifier = var.environment == "production" ? "" : "-${var.environment}"
}

output "iam_access_key_id" {
  value = aws_iam_access_key.server_user.id
}

output "iam_access_key_secret" {
  value = aws_iam_access_key.server_user.secret
}

output "blobs_bucket" {
  value = aws_s3_bucket.server_blobs.bucket
}

output "upload_role_arn" {
  value = aws_iam_role.server_upload.arn
}
