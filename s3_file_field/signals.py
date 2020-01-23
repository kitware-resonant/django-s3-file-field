import django.dispatch


s3_file_field_upload_prepare = django.dispatch.Signal(providing_args=['name', 'object_key'])
s3_file_field_upload_finalize = django.dispatch.Signal(
    providing_args=['name', 'object_key', 'status']
)
