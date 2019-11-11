resource "aws_iam_role" "server_upload" {
  name                 = "upload-sts${local.qualifier}"
  max_session_duration = 12 * 60 * 60 # 12 hours
  assume_role_policy   = data.aws_iam_policy_document.server_upload_assumeRolePolicy.json
}

data "aws_iam_policy_document" "server_upload_assumeRolePolicy" {
  statement {
    principals {
      type = "AWS"
      identifiers = [
        aws_iam_user.server_user.arn,
      ]
    }
    actions = [
      "sts:AssumeRole",
    ]
  }
}

resource "aws_iam_role_policy" "server_upload" {
  name   = "s3-blobs-upload${local.qualifier}"
  role   = aws_iam_role.server_upload.name
  policy = data.aws_iam_policy_document.server_upload.json
}
data "aws_iam_policy_document" "server_upload" {
  statement {
    actions = [
      "s3:PutObject",
    ]
    resources = [
      "${aws_s3_bucket.server_blobs.arn}/*",
    ]
  }
}
