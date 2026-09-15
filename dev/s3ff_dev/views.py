from __future__ import annotations

from typing import TYPE_CHECKING, Any, override

from django.forms import ModelForm
from django.urls import reverse, reverse_lazy
from django.views import generic

from .forms import (
    DaisyUIResourceCreateForm,
    DaisyUIResourceForm,
    ResourceCreateForm,
    ResourceForm,
)
from .models import Resource

if TYPE_CHECKING:
    from django.http import HttpRequest


# The built-in themes of DaisyUI 5, for the chooser in its UI mode
DAISYUI_THEMES = [
    "light", "dark", "cupcake", "bumblebee", "emerald", "corporate", "synthwave", "retro",
    "cyberpunk", "valentine", "halloween", "garden", "forest", "aqua", "lofi", "pastel",
    "fantasy", "wireframe", "black", "luxury", "dracula", "cmyk", "autumn", "business", "acid",
    "lemonade", "night", "coffee", "winter", "dim", "nord", "sunset", "caramellatte", "abyss",
    "silk",
]  # fmt: skip


class ResourceList(generic.ListView[Resource]):
    model = Resource


class ResourceCreate(generic.CreateView[Resource, ResourceCreateForm]):
    model = Resource
    form_class = ResourceCreateForm


class ResourceUpdate(generic.UpdateView[Resource, ResourceForm]):
    model = Resource
    form_class = ResourceForm


class DaisyUIMixin(
    generic.base.TemplateResponseMixin, generic.edit.ModelFormMixin[Resource, ModelForm[Resource]]
):
    request: HttpRequest
    object: Resource | None
    template_name = "s3ff_dev/resource_form_daisyui.html"

    @override
    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        theme = self.request.GET.get("theme")
        return super().get_context_data(
            daisyui_themes=DAISYUI_THEMES,
            theme=theme if theme in DAISYUI_THEMES else "light",
            **kwargs,
        )

    @override
    def get_success_url(self) -> str:
        # Stay on the DaisyUI page (with its query string) after saving
        if self.object is None:
            raise RuntimeError("object is not set")
        url = reverse("resource-update-daisyui", kwargs={"pk": self.object.pk})
        query = self.request.GET.urlencode()
        return f"{url}?{query}" if query else url


class ResourceCreateDaisyUI(DaisyUIMixin, generic.CreateView[Resource, DaisyUIResourceCreateForm]):
    model = Resource
    form_class = DaisyUIResourceCreateForm


class ResourceUpdateDaisyUI(DaisyUIMixin, generic.UpdateView[Resource, DaisyUIResourceForm]):
    object: Resource
    model = Resource
    form_class = DaisyUIResourceForm


class ResourceDelete(generic.DeleteView[Resource]):
    model = Resource
    success_url = reverse_lazy("resource-list")
