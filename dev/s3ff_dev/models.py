from __future__ import annotations

from typing import ClassVar, Self

from django.db import models
from django.urls import reverse

from s3_file_field.fields import S3FileField


class Resource(models.Model):
    # Annotate this type, since mypy_django_plugin isn't configured to load this app
    objects: ClassVar[models.Manager[Self]]

    legacy_optional_blob = models.FileField(blank=True)
    s3ff_mandatory_blob = S3FileField()
    s3ff_optional_blob = S3FileField(blank=True)

    def __str__(self) -> str:
        return f"Resource {self.pk}"

    def get_absolute_url(self) -> str:
        return reverse("resource-update", kwargs={"pk": self.pk})
