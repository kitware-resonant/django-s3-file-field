from typing import Optional

import boto3

from . import settings


def _get_endpoint_url() -> Optional[str]:
    if settings._JOIST_ENDPOINT:
        return f'http{"s" if settings._JOIST_USE_SSL else ""}://{settings._JOIST_ENDPOINT}'


def client_factory(service: str, **kwargs):
    client_kwargs = {
        'region_name': settings._JOIST_REGION,
        'aws_access_key_id': settings._JOIST_ACCESS_KEY,
        'aws_secret_access_key': settings._JOIST_SECRET_KEY,
    }

    if settings._JOIST_ENDPOINT:
        client_kwargs['endpoint_url'] = _get_endpoint_url()

    client_kwargs.update(kwargs)

    return boto3.client(service, **client_kwargs)
