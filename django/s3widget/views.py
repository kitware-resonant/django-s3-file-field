import json
import time
import uuid

import boto3
from django.conf import settings
from django.http import JsonResponse
from django.http.response import HttpResponseBase
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import JSONParser
from rest_framework.request import Request


# @authentication_classes([TokenAuthentication])
# @permission_classes([IsAuthenticated])
@api_view(['POST'])
@parser_classes([JSONParser])
def finalize_upload(request: Request) -> HttpResponseBase:
    name: str = request.data['name']
    status: str = request.data['status']
    # can be one of aborted|uploaded
    # TODO move file to where it belongs and return the new name
    return JsonResponse({'name': name, 'status': status})


# @authentication_classes([TokenAuthentication])
# @permission_classes([IsAuthenticated])
@api_view(['POST'])
@parser_classes([JSONParser])
def prepare_upload(request: Request) -> HttpResponseBase:
    bucket_arn = f'arn:aws:s3:::{settings.AWS_STORAGE_BUCKET_NAME}'
    name = request.data['name']
    object_key = f'{uuid.uuid4()}/{name}'
    upload_policy = {
        'Version': '2012-10-17',
        'Statement': [
            {
                'Effect': 'Allow',
                'Action': ['s3:PutObject'],
                'Resource': f'{bucket_arn}/{object_key}',
            }
        ],
    }

    # Get temporary security credentials with permission to upload into the
    # object in the S3 bucket. The AWS Security Token Service (STS) provides
    # the credentials when the machine assumes the upload role.
    client = boto3.client(
        'sts',
        region_name=settings.AWS_REGION,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )
    resp = client.assume_role(
        RoleArn=settings.UPLOAD_STS_ARN,
        RoleSessionName=f'file-upload-{int(time.time())}',
        Policy=json.dumps(upload_policy),
        DurationSeconds=settings.S3_WIDGET_UPLOAD_DURATION,
    )

    credentials = resp['Credentials']

    return JsonResponse(
        {
            'accessKeyId': credentials['AccessKeyId'],
            'secretAccessKey': credentials['SecretAccessKey'],
            'sessionToken': credentials['SessionToken'],
            'bucketName': settings.AWS_STORAGE_BUCKET_NAME,
            'objectKey': object_key,
        }
    )
