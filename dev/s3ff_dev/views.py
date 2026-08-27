from __future__ import annotations

from django.forms import Form, ModelForm
from django.urls import reverse_lazy
from django.views import generic

from .models import Resource


class ResourceList(generic.ListView[Resource]):
    model = Resource


class ResourceCreate(generic.CreateView[Resource, ModelForm[Resource]]):
    model = Resource
    fields = "__all__"


class ResourceUpdate(generic.UpdateView[Resource, ModelForm[Resource]]):
    model = Resource
    fields = "__all__"


class ResourceDelete(generic.DeleteView[Resource, Form]):
    model = Resource
    success_url = reverse_lazy("resource-list")
