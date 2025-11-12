from django.db import models

from s3_file_field.fields import S3FileField, S3ImageField


class Resource(models.Model):
    blob = S3FileField()


class MultiResource(models.Model):
    blob = S3FileField()
    optional_blob = S3FileField(blank=True)


def get_acl(field, request):
    return "public-read"


class ImageResource(models.Model):
    private = S3ImageField()
    public = S3ImageField(acl=get_acl)
    optional_public = S3ImageField(acl="public-read", blank=True)
