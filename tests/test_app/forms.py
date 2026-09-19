from __future__ import annotations

from django.forms import ModelForm

from s3_file_field.forms import S3FormFileField

from .models import LimitedResource, MultiResource, OptionalResource, Resource


class ResourceForm(ModelForm[Resource]):
    class Meta:
        model = Resource
        fields = "__all__"


class DisabledResourceForm(ModelForm[Resource]):
    """A form whose S3FormFileField is unconditionally disabled."""

    blob = S3FormFileField(disabled=True, model_field=Resource._meta.get_field("blob"))

    class Meta:
        model = Resource
        fields = "__all__"


class OptionalResourceForm(ModelForm[OptionalResource]):
    class Meta:
        model = OptionalResource
        fields = "__all__"


class MultiResourceForm(ModelForm[MultiResource]):
    class Meta:
        model = MultiResource
        fields = "__all__"


class LimitedResourceForm(ModelForm[LimitedResource]):
    class Meta:
        model = LimitedResource
        fields = "__all__"
