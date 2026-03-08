from django.forms import ModelForm

from .models import ImageResource, Resource


class ResourceForm(ModelForm):
    class Meta:
        model = Resource
        fields = "__all__"


class ImageResourceForm(ModelForm):
    class Meta:
        model = ImageResource
        fields = "__all__"
