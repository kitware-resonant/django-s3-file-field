from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone
from s3widget.models import S3FileField


class Blob(models.Model):
    created = models.DateTimeField(default=timezone.now)
    creator = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    resource = S3FileField()
    r2 = models.FileField(null=True)

    def __str__(self):
        return str(self.resource)
