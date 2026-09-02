from __future__ import annotations

import django.dispatch

s3_file_field_upload_initiate = django.dispatch.Signal()
s3_file_field_upload_finalize = django.dispatch.Signal()
