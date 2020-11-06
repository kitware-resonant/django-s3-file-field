from django.urls import reverse_lazy
from django.views import generic

from .models import Resource


class ResourceList(generic.ListView):
    model = Resource


class ResourceCreate(generic.CreateView):
    model = Resource
    fields = '__all__'


class ResourceUpdate(generic.UpdateView):
    model = Resource
    fields = '__all__'


class ResourceDelete(generic.DeleteView):
    model = Resource
    success_url = reverse_lazy('resource-list')
