from uuid import uuid4

from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone


class CollisionSafeFileField(models.FileField):
    description = 'A file field which is uploaded to <randomuuid>/filename.'

    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = kwargs.get('max_length', 200)
        kwargs['upload_to'] = self.uuid_prefix_filename
        super().__init__(*args, **kwargs)

    @staticmethod
    def uuid_prefix_filename(instance, filename):
        return f'{uuid4()}/{filename}'


class Blob(models.Model):
    created = models.DateTimeField(default=timezone.now)
    creator = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    resource = CollisionSafeFileField()
