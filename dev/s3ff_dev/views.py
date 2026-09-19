from __future__ import annotations

from django.urls import reverse_lazy
from django.views import generic

from .forms import ResourceCreateForm, ResourceForm
from .models import Resource


class ResourceList(generic.ListView[Resource]):
    model = Resource


class ResourceCreate(generic.CreateView[Resource, ResourceCreateForm]):
    model = Resource
    form_class = ResourceCreateForm


class ResourceUpdate(generic.UpdateView[Resource, ResourceForm]):
    model = Resource
    form_class = ResourceForm


class ResourceDelete(generic.DeleteView[Resource]):
    model = Resource
    success_url = reverse_lazy("resource-list")
