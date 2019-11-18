from uuid import uuid4

from django.contrib.admin.widgets import AdminFileWidget
from django.db.models import FileField

from .widgets import S3AdminFileInput, S3FormFileField


class S3FileField(FileField):
    description = 'A file field which is uploaded to <randomuuid>/filename.'

    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = kwargs.get('max_length', 200)
        kwargs['upload_to'] = self.uuid_prefix_filename
        super().__init__(*args, **kwargs)

    @staticmethod
    def uuid_prefix_filename(instance, filename):
        print(instance)
        return f'{uuid4()}/{filename}'

    def formfield(self, **kwargs):
        print(kwargs, kwargs.get('widget') == AdminFileWidget)
        copy = kwargs.copy()
        if copy.get('widget') == AdminFileWidget:
            # replace for admin
            copy['widget'] = S3AdminFileInput
        copy.setdefault('form_class', S3FormFileField)
        return super().formfield(**copy)

    def save(self, name, content, save=True):
        return super().save(name, content, save)
        # name = self.field.generate_filename(self.instance, name)
        # self.name = self.storage.save(name, content, max_length=self.field.max_length)
        # setattr(self.instance, self.field.name, self.name)
        # self._committed = True

        # # Save the object because it has changed, unless save is False
        # if save:
        #     self.instance.save()
