import boto3

from . import constants


def client_factory(service: str, **kwargs):
    client_kwargs = {
        'region_name': constants.S3FF_REGION,
        'aws_access_key_id': constants.S3FF_ACCESS_KEY,
        'aws_secret_access_key': constants.S3FF_SECRET_KEY,
    }

    if constants.S3FF_ENDPOINT_URL:
        client_kwargs['endpoint_url'] = constants.S3FF_ENDPOINT_URL

    client_kwargs.update(kwargs)

    return boto3.client(service, **client_kwargs)
