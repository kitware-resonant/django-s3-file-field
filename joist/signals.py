import django.dispatch


joist_upload_prepare = django.dispatch.Signal(providing_args=['name', 'object_key'])
joist_upload_finalize = django.dispatch.Signal(providing_args=['name', 'object_key', 'status'])
