import boto3

from . import settings


def _get_endpoint_url():
    if settings._S3FF_ENDPOINT:
        return f'http{"s" if settings._S3FF_USE_SSL else ""}://{settings._S3FF_ENDPOINT}'


def client_factory(service: str, **kwargs):
    client_kwargs = {
        'region_name': settings._S3FF_REGION,
        'aws_access_key_id': settings._S3FF_ACCESS_KEY,
        'aws_secret_access_key': settings._S3FF_SECRET_KEY,
    }

    if settings._S3FF_ENDPOINT:
        client_kwargs['endpoint_url'] = _get_endpoint_url()

    client_kwargs.update(kwargs)

    return boto3.client(service, **client_kwargs)
