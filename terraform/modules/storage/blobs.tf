resource "aws_s3_bucket" "server_blobs" {
  bucket = "blobs${local.qualifier}"
  acl    = "private"

  versioning {
    enabled = true
  }

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["POST", "PUT"]

    allowed_origins = ["*"]

    expose_headers = [
      # https://docs.aws.amazon.com/AmazonS3/latest/API/RESTCommonResponseHeaders.html
      "Content-Length",
      "Connection",
      "Date",
      "ETag",
      "Server",
      "x-amz-delete-marker",
      "x-amz-version-id",
    ]

    # Exclude "x-amz-request-id" and "x-amz-id-2", as they are only for debugging
    max_age_seconds = 600
  }

  force_destroy = true
}
