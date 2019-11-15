from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

from core.models import CollisionSafeFileField


class Blob(models.Model):
    created = models.DateTimeField(default=timezone.now)
    creator = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    resource = CollisionSafeFileField()
