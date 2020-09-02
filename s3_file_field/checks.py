import io
import json
import logging
from pathlib import PurePosixPath
from time import time
from typing import List, Optional

from botocore.client import Config
from botocore.exceptions import ConnectionError
from django.core.checks import Error, Warning, register

from . import constants
from .boto import client_factory
from .constants import S3FF_STORAGE_PROVIDER, StorageProvider

# TODO: this should only add a handler when running the check command
logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())


TEST_OBJECT_KEY = str(constants.S3FF_UPLOAD_PREFIX / PurePosixPath('.s3-file-field-test-file'))


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
E005 = Error('Unable to determine the underlying storage provider.', id='s3_file_field.E005')


@register(deploy=True)
def check_supported_storage_provider(app_configs: Optional[List], **kwargs) -> List:
    return [] if S3FF_STORAGE_PROVIDER != StorageProvider.UNSUPPORTED else [E005]


@register()
def determine_storage_provider(app_configs: Optional[List], **kwargs) -> List:
    return [] if S3FF_STORAGE_PROVIDER != StorageProvider.UNSUPPORTED else [W001]


@register()
def test_bucket_access(app_configs: Optional[List], **kwargs) -> List:
    # ignore bucket access checks when in development mode
    if S3FF_STORAGE_PROVIDER == StorageProvider.UNSUPPORTED:
        return []

    # Use a short timeout to quickly fail on connection misconfigurations
    client = client_factory('s3', config=Config(connect_timeout=5, retries={'max_attempts': 0}))

    try:
        client.upload_fileobj(io.BytesIO(), constants.S3FF_BUCKET, TEST_OBJECT_KEY)
    except ConnectionError:
        logger.exception('Failed to connect to storage bucket')
        return [E001]
    except Exception:
        logger.exception('Failed to put an object into the storage bucket.')
        return [E002]

    try:
        client.delete_object(Bucket=constants.S3FF_BUCKET, Key=TEST_OBJECT_KEY)
    except ConnectionError:
        logger.exception('Failed to connect to storage bucket')
        return [E001]
    except Exception:
        logger.exception('Failed to delete an object from the storage bucket.')
        return [E003]

    return []


@register()
def test_assume_role_configuration(app_configs: Optional[List], **kwargs) -> List:
    # ignore assume role checks when in development mode
    if S3FF_STORAGE_PROVIDER == StorageProvider.UNSUPPORTED:
        return []

    client = client_factory('sts', config=Config(connect_timeout=5, retries={'max_attempts': 0}))

    try:
        client.assume_role(
            RoleArn=constants.S3FF_UPLOAD_STS_ARN,
            RoleSessionName=f'file-upload-{int(time())}',
            Policy=json.dumps(
                {
                    'Version': '2012-10-17',
                    'Statement': [
                        {
                            'Effect': 'Allow',
                            'Action': ['s3:PutObject'],
                            'Resource': f'arn:aws:s3:::{constants.S3FF_BUCKET}/{TEST_OBJECT_KEY}',
                        }
                    ],
                }
            ),
            DurationSeconds=constants.S3FF_UPLOAD_DURATION,
        )
    except ConnectionError:
        logger.exception('Failed to connect to storage bucket')
        return [E001]
    except Exception:
        logger.exception('Failed to assume STS role.')
        return [E004]

    return []


# TODO: investigate a possible check for CORS misconfigurations
