from typing import cast, Optional, Type, Union

from django.contrib.admin.widgets import AdminFileWidget
from django.core.signing import BadSignature, Signer
from django.forms import FileField, ValidationError, Widget

from . import settings
from .configuration import StorageProvider
from .widgets import S3AdminFileInput, S3FakeFile, S3FileInput


class S3FormFileField(FileField):
    """Form field used by render an model.S3FileField."""

    widget = S3FileInput

    def __init__(self, widget: Optional[Union[Type[Widget], Widget]] = None, **kwargs):
        if settings._S3FF_STORAGE_PROVIDER != StorageProvider.UNSUPPORTED:
            # For form fields created under django.contrib.admin.options.BaseModelAdmin, any form
            # field representing a model.FileField subclass will request a
            # django.contrib.admin.widgets.AdminFileWidget as a 'widget' parameter override
            # Custom subclasses of BaseModelAdmin can use formfield_overrides to change
            # the default widget for their forms, but this is burdensome
            # So, instead change any requests for an AdminFileWidget to a S3AdminFileInput
            if widget:
                if isinstance(widget, type):
                    # widget is a type
                    if issubclass(widget, AdminFileWidget):
                        widget = S3AdminFileInput
                else:
                    # widget is an instance
                    if isinstance(widget, AdminFileWidget):
                        # We can't easily re-instantiate the Widget, since we need its initial
                        # parameters, so attempt to rebuild the constructor parameters
                        widget = S3AdminFileInput(attrs={'type': widget.input_type, **widget.attrs})

        super().__init__(widget=widget, **kwargs)

    def validate(self, value):
        super().validate(value)

        if isinstance(value, S3FakeFile):
            # verify signature
            signer = Signer()
            try:
                expected = signer.unsign(value.signature)
                if value.name != expected:
                    raise ValidationError('Signature tempering detected')
            except BadSignature:
                raise ValidationError('Signature tempering detected')
