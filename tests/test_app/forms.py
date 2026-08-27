from __future__ import annotations

from django.forms import ModelForm

from .models import Resource


class ResourceForm(ModelForm[Resource]):
    class Meta:
        model = Resource
        fields = "__all__"
