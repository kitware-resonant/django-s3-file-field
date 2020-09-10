from typing import Dict, Optional, Type, Union

from django.contrib.admin.widgets import AdminFileWidget
from django.core.signing import BadSignature, Signer
from django.forms import FileField, ValidationError, Widget

from .widgets import AdminS3FileInput, S3FakeFile, S3FileInput


class S3FormFileField(FileField):
    """Form field used by render an model.S3FileField."""

    widget = S3FileInput

    def __init__(
        self, *, model_field_id: str, widget: Optional[Union[Type[Widget], Widget]] = None, **kwargs
    ):
        self.model_field_id = model_field_id

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
                    widget = AdminS3FileInput
            else:
                # widget is an instance
                if isinstance(widget, AdminFileWidget):
                    # We can't easily re-instantiate the Widget, since we need its initial
                    # parameters, so attempt to rebuild the constructor parameters
                    widget = AdminS3FileInput(attrs={'type': widget.input_type, **widget.attrs})

        super().__init__(widget=widget, **kwargs)

    def widget_attrs(self, widget: Widget) -> Dict[str, str]:
        attrs = super().widget_attrs(widget)
        attrs.update(
            {
                'data-auto-upload': True,
                'data-field-id': self.model_field_id,
                'data-s3fileinput': '',
            }
        )
        # 'data-s3fileinput' cannot be determined at this point, during app startup.
        # It will be added at render-time by "S3FileInput.get_context".
        return attrs

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
