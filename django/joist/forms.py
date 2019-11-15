from django.forms import ModelForm

from .models import Blob


class BlobForm(ModelForm):
    class Meta:
        model = Blob
        fields = ['resource', 'creator', 'created']
