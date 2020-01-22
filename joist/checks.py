import io
import json
import logging
import os
from pathlib import PurePosixPath
from time import time
from typing import List, Optional

from botocore.client import Config
from botocore.exceptions import ConnectionError
import boto3
from django.core.checks import Error, register, Warning

from .boto import client_factory
from .configuration import get_storage_provider
from . import settings


# TODO: this should only add a handler when running the check command
logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())


W001 = Warning(
    "Unable to determine the underlying storage provider. "
    "joist will use the filesystem for storing all files.",
    id='joist.W001',
)

E001 = Error("Unable to connect to the specified storage bucket.", id='joist.E001')
E002 = Error("Unable to put objects into the specified storage bucket.", id='joist.E002')
E003 = Error("Unable to delete objects from the specified storage bucket.", id='joist.E003')
E004 = Error("Unable to assume STS role for issuing temporary credentials.", id='joist.E004')


@register()
def determine_storage_provider(app_configs: Optional[List], **kwargs) -> List:
    return [] if get_storage_provider() else [W001]


@register()
def test_bucket_access(app_configs: Optional[List], **kwargs) -> List:
    # Use a short timeout to quickly fail on connection misconfigurations
    client = client_factory('s3', config=Config(connect_timeout=5, retries={'max_attempts': 0}))
    test_object_key = str(settings.JOIST_UPLOAD_PREFIX / PurePosixPath('.joist-test-file'))

    try:
        response = client.upload_fileobj(io.BytesIO(), settings._JOIST_BUCKET, test_object_key)
    except ConnectionError:
        logger.exception('Failed to connect to storage bucket')
        return [E001]
    except Exception:
        logger.exception('Failed to put an object into the storage bucket.')
        return [E002]

    try:
        response = client.delete_object(Bucket=settings._JOIST_BUCKET, Key=test_object_key)
    except ConnectionError:
        logger.exception('Failed to connect to storage bucket')
        return [E001]
    except Exception:
        logger.exception('Failed to delete an object from the storage bucket.')
        return [E003]

    return []


@register()
def test_assume_role_configuration(app_configs: Optional[List], **kwargs) -> List:
    client = client_factory('sts', config=Config(connect_timeout=5, retries={'max_attempts': 0}))

    try:
        resp = client.assume_role(
            RoleArn=settings.JOIST_UPLOAD_STS_ARN,
            RoleSessionName=f'file-upload-{int(time())}',
            Policy=json.dumps(
                {
                    'Version': '2012-10-17',
                    'Statement': [
                        {
                            'Effect': 'Allow',
                            'Action': ['s3:PutObject'],
                            'Resource': f'arn:aws:s3:::{settings._JOIST_BUCKET}/.joist-test-file',
                        }
                    ],
                }
            ),
            DurationSeconds=settings._JOIST_UPLOAD_DURATION,
        )
    except ConnectionError:
        logger.exception('Failed to connect to storage bucket')
        return [E001]
    except Exception:
        logger.exception('Failed to assume STS role.')
        return [E004]

    return []


# TODO: investigate a possible check for CORS misconfigurations
