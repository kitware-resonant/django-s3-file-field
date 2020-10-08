from django.contrib import admin

from .models import Blob


@admin.register(Blob)
class BlobAdmin(admin.ModelAdmin):
    pass
