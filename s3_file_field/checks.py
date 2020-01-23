import io
import json
import logging
from pathlib import PurePosixPath
from time import time
from typing import List, Optional

from botocore.client import Config
from botocore.exceptions import ConnectionError
from django.core.checks import Error, register, Warning

from . import settings
from .boto import client_factory
from .configuration import get_storage_provider


# TODO: this should only add a handler when running the check command
logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())


TEST_OBJECT_KEY = str(settings.S3FF_UPLOAD_PREFIX / PurePosixPath('.s3-file-field-test-file'))


W001 = Warning(
    'Unable to determine the underlying storage provider. '
    's3_file_field will use the filesystem for storing all files.',
    id='s3_file_field.W001',
)

E001 = Error('Unable to connect to the specified storage bucket.', id='s3_file_field.E001')
E002 = Error('Unable to put objects into the specified storage bucket.', id='s3_file_field.E002')
E003 = Error('Unable to delete objects from the specified storage bucket.', id='s3_file_field.E003')
E004 = Error(
    'Unable to assume STS role for issuing temporary credentials.', id='s3_file_field.E004'
)


@register()
def determine_storage_provider(app_configs: Optional[List], **kwargs) -> List:
    return [] if get_storage_provider() else [W001]


@register()
def test_bucket_access(app_configs: Optional[List], **kwargs) -> List:
    # Use a short timeout to quickly fail on connection misconfigurations
    client = client_factory('s3', config=Config(connect_timeout=5, retries={'max_attempts': 0}))

    try:
        client.upload_fileobj(io.BytesIO(), settings._S3FF_BUCKET, TEST_OBJECT_KEY)
    except ConnectionError:
        logger.exception('Failed to connect to storage bucket')
        return [E001]
    except Exception:
        logger.exception('Failed to put an object into the storage bucket.')
        return [E002]

    try:
        client.delete_object(Bucket=settings._S3FF_BUCKET, Key=TEST_OBJECT_KEY)
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
        client.assume_role(
            RoleArn=settings.S3FF_UPLOAD_STS_ARN,
            RoleSessionName=f'file-upload-{int(time())}',
            Policy=json.dumps(
                {
                    'Version': '2012-10-17',
                    'Statement': [
                        {
                            'Effect': 'Allow',
                            'Action': ['s3:PutObject'],
                            'Resource': f'arn:aws:s3:::{settings._S3FF_BUCKET}/{TEST_OBJECT_KEY}',
                        }
                    ],
                }
            ),
            DurationSeconds=settings._S3FF_UPLOAD_DURATION,
        )
    except ConnectionError:
        logger.exception('Failed to connect to storage bucket')
        return [E001]
    except Exception:
        logger.exception('Failed to assume STS role.')
        return [E004]

    return []


# TODO: investigate a possible check for CORS misconfigurations
