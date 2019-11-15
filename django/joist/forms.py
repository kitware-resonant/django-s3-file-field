from django.forms import ModelForm

from .models import Blob
from core.widgets import S3FileInput


class BlobForm(ModelForm):
    class Meta:
        model = Blob
        fields = ['creator', 'created', 'resource']
        widgets = {
            'resource': S3FileInput(),
        }
