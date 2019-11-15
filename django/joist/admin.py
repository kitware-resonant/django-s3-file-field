from django.contrib import admin

from .models import Blob
from .forms import BlobForm


@admin.register(Blob)
class BlobAdmin(admin.ModelAdmin):
    form = BlobForm
