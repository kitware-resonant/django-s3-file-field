from django.contrib import admin

from core.models import Blob


@admin.register(Blob)
class BlobAdmin(admin.ModelAdmin):
    pass
