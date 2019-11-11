resource "aws_iam_access_key" "server_user" {
  user = aws_iam_user.server_user.name
}

resource "aws_iam_user" "server_user" {
  name = "server${local.qualifier}"
}

resource "aws_iam_user_policy" "server_user_policy_s3_blobs" {
  user   = aws_iam_user.server_user.id
  name   = "s3-blobs${local.qualifier}"
  policy = data.aws_iam_policy_document.server_user_policy_s3_blobs.json
}
data "aws_iam_policy_document" "server_user_policy_s3_blobs" {
  statement {
    actions = [
      # TODO Figure out minimal set of permissions django storages needs for S3
      "s3:*",
    ]
    resources = [
      aws_s3_bucket.server_blobs.arn,
      "${aws_s3_bucket.server_blobs.arn}/*",
    ]
  }
}
