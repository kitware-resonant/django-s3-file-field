from __future__ import annotations

from django.forms import ClearableFileInput, ModelForm

from .models import Resource


class ResourceForm(ModelForm[Resource]):
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
    class Meta(ResourceForm.Meta):
        widgets = DAISYUI_WIDGETS


class DaisyUIResourceCreateForm(ResourceCreateForm):
    class Meta(ResourceCreateForm.Meta):
        widgets = DAISYUI_WIDGETS
