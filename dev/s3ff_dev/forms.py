from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError
from django.forms import BooleanField, ClearableFileInput, ModelForm

from .models import Resource


class ResourceForm(ModelForm[Resource]):
    # A non-model field, to make the server reject a submission on demand
    fail = BooleanField(
        required=False,
        label="Fail validation",
        help_text="Reject this submission, to show how the widgets redisplay their state",
    )

    # Disable these fields always, to exercise that state of the widget
    s3ff_disabled_blob = Resource._meta.get_field("s3ff_disabled_blob").formfield(disabled=True)
    s3ff_disabled_existing_blob = Resource._meta.get_field("s3ff_disabled_existing_blob").formfield(
        disabled=True
    )

    class Meta:
        model = Resource
        fields = [
            "legacy_optional_blob",
            "s3ff_mandatory_blob",
            "s3ff_optional_blob",
            "s3ff_optional_limited_blob",
            "s3ff_disabled_blob",
            "s3ff_disabled_existing_blob",
        ]

    def clean_fail(self) -> bool:
        fail: bool = self.cleaned_data["fail"]
        if fail:
            raise ValidationError("Failed, as requested.", code="requested")
        return fail


class ResourceCreateForm(ResourceForm):
    # A disabled field with an existing value only makes sense when editing; since it's declared
    # explicitly, it must also be removed explicitly
    s3ff_disabled_existing_blob = None

    class Meta(ResourceForm.Meta):
        fields = [
            "legacy_optional_blob",
            "s3ff_mandatory_blob",
            "s3ff_optional_blob",
            "s3ff_optional_limited_blob",
            "s3ff_disabled_blob",
        ]


# DaisyUI's classes for Django's native widgets; the s3-file-input is styled by its own element
DAISYUI_WIDGETS = {
    "legacy_optional_blob": ClearableFileInput(attrs={"class": "file-input"}),
}


class DaisyUIResourceForm(ResourceForm):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["fail"].widget.attrs["class"] = "checkbox"

    class Meta(ResourceForm.Meta):
        widgets = DAISYUI_WIDGETS


class DaisyUIResourceCreateForm(ResourceCreateForm):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["fail"].widget.attrs["class"] = "checkbox"

    class Meta(ResourceCreateForm.Meta):
        widgets = DAISYUI_WIDGETS
