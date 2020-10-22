from django.db import models

from s3_file_field.fields import S3FileField


class Resource(models.Model):
    blob = S3FileField()
