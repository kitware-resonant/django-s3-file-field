from django.db import models
from django.urls import reverse

from s3_file_field.fields import S3FileField


class Resource(models.Model):
    legacy_optional_blob = models.FileField(blank=True)
    s3ff_mandatory_blob = S3FileField()
    s3ff_optional_blob = S3FileField(blank=True)

    def get_absolute_url(self):
        return reverse('resource-update', kwargs={'pk': self.pk})
