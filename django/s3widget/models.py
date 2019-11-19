from typing import Any, cast
from uuid import uuid4

from django.contrib.admin.widgets import AdminFileWidget
from django.db.models.fields.files import FieldFile, FileField

from .widgets import S3AdminFileInput, S3FakeFile, S3FormFileField


class S3FieldFile(FieldFile):
    def save(self, name, content, save=True):
        if not isinstance(content, S3FakeFile):
            return super().save(name, content, save)

        self.name = content.name
        setattr(self.instance, self.field.name, self.name)
        self._committed = True

        # Save the object because it has changed, unless save is False
        if save:
            self.instance.save()

    cast(Any, save).alters_data = True


class S3FileField(FileField):
    attr_class = S3FieldFile
    description = 'A file field which is uploaded to <randomuuid>/filename.'

    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = kwargs.get('max_length', 200)
        kwargs['upload_to'] = self.uuid_prefix_filename
        super().__init__(*args, **kwargs)

    def get_internal_type(self):
        return 'S3FieldFile'

    @staticmethod
    def uuid_prefix_filename(instance, filename):
        return f'{uuid4()}/{filename}'

    def formfield(self, **kwargs):
        copy = kwargs.copy()
        if copy.get('widget') == AdminFileWidget:
            # replace for admin
            copy['widget'] = S3AdminFileInput
        copy.setdefault('form_class', S3FormFileField)
        return super().formfield(**copy)
