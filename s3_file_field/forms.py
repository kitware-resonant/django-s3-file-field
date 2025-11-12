from __future__ import annotations

from typing import Any

from django.conf import settings
from django.contrib.admin.widgets import AdminFileWidget
from django.core.files.storage import Storage
from django.forms import FileField, Widget
from django.forms.widgets import FileInput
from django.utils.module_loading import import_string

from .widgets import AdminS3FileInput, S3FileInput, S3FileInputMixin, S3ImageFileInput


class S3FormFileField(FileField):
    """Form field used by render an model.S3FileField."""

    widget: type[S3FileInputMixin] = S3FileInput

    def __init__(
        self,
        *,
        model_field_id: str,
        widget: type[Widget] | Widget | None = None,
        **kwargs,
    ) -> None:
        self.model_field_id = model_field_id

        # For form fields created under django.contrib.admin.options.BaseModelAdmin, any form
        # field representing a model.FileField subclass will request a
        # django.contrib.admin.widgets.AdminFileWidget as a 'widget' parameter override
        # Custom subclasses of BaseModelAdmin can use formfield_overrides to change
        # the default widget for their forms, but this is burdensome
        # So, instead change any requests for an AdminFileWidget to a S3AdminFileInput
        if widget:
            if isinstance(widget, type):
                # widget is a type
                if issubclass(widget, AdminFileWidget):
                    widget = AdminS3FileInput
            else:
                # widget is an instance
                if isinstance(widget, AdminFileWidget):
                    # We can't easily re-instantiate the Widget, since we need its initial
                    # parameters, so attempt to rebuild the constructor parameters
                    widget = AdminS3FileInput(attrs={"type": widget.input_type, **widget.attrs})

        super().__init__(widget=widget, **kwargs)

    def widget_attrs(self, widget: Widget) -> dict[str, Any]:
        attrs = super().widget_attrs(widget)
        attrs.update(
            {
                "data-field-id": self.model_field_id,
                "data-s3fileinput": "",
            }
        )
        # 'data-s3fileinput' cannot be determined at this point, during app startup.
        # It will be added at render-time by "S3FileInput.get_context".
        return attrs


class BaseStorageProtocol:
    endpoint_url: str
    bucket_name: str


class MinioStorageProcotol(BaseStorageProtocol):
    base_url: str


class S3StorageProtocol(BaseStorageProtocol):
    url_protocol: str


def default_get_storage_url(storage: MinioStorageProcotol | S3StorageProtocol) -> str:
    # django-storages
    if url_protocol := getattr(storage, "url_protocol", None):
        # Use the custom domain if set, otherwise, tweak the endpoint_url to be a workable URL
        if custom_domain := getattr(storage, "custom_domain", None):
            return f"{url_protocol}//{custom_domain}"
        else:
            return storage.endpoint_url.replace(
                "https://",
                f"{url_protocol}//{storage.bucket_name}.",
            )
    else:
        return storage.endpoint_url


get_storage_url = import_string(
    getattr(
        settings,
        "S3_FILE_FIELD_STORAGE_URL",
        "s3_file_field.forms.default_get_storage_url",
    )
)


class S3FormImageFileField(S3FormFileField):
    """Form field used by render a model.S3ImageField."""

    widget = S3ImageFileInput

    def __init__(self, storage: Storage, *args, **kwargs):
        self.storage = storage
        super().__init__(*args, **kwargs)

    def widget_attrs(self, widget):
        attrs = super().widget_attrs(widget)
        attrs.update(
            {
                "storage_url": get_storage_url(self.storage),
                "data-s3imageinput": True,
            }
        )
        if isinstance(widget, FileInput) and "accept" not in widget.attrs:
            attrs.setdefault("accept", "image/*")
        return attrs
