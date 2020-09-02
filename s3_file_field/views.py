import json
import time
import uuid

from django.core.signing import BadSignature, Signer, TimestampSigner
from django.http import HttpResponse, JsonResponse
from django.http.response import HttpResponseBase
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import JSONParser
from rest_framework.request import Request

from . import constants, signals
from .boto import client_factory


# @authentication_classes([TokenAuthentication])
# @permission_classes([IsAuthenticated])
@api_view(['POST'])
@parser_classes([JSONParser])
def upload_finalize(request: Request) -> HttpResponseBase:
    name: str = request.data['name']
    status: str = request.data['status']
    object_id: str = request.data['id']
    upload_sig: str = request.data['signature']

    # check if upload_prepare signed this less than max age ago
    tsigner = TimestampSigner()
    if object_id != tsigner.unsign(upload_sig, max_age=constants.S3FF_UPLOAD_DURATION):
        raise BadSignature()

    signals.s3_file_field_upload_finalize.send(
        sender=upload_finalize, name=name, status=status, object_key=object_id
    )

    signer = Signer()
    sig = signer.sign(object_id)

    # can be one of aborted|uploaded
    # TODO move file to where it belongs and return the new name

    return JsonResponse({'name': name, 'status': status, 'id': object_id, 'signature': sig})


# @authentication_classes([TokenAuthentication])
# @permission_classes([IsAuthenticated])
@api_view(['POST'])
@parser_classes([JSONParser])
def upload_prepare(request: Request) -> HttpResponseBase:
    name = request.data['name']
    object_key = str(constants.S3FF_UPLOAD_PREFIX / str(uuid.uuid4()) / name)

    bucket_arn = f'arn:aws:s3:::{constants.S3FF_BUCKET}'
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
    client = client_factory('sts')

    resp = client.assume_role(
        RoleArn=constants.S3FF_UPLOAD_STS_ARN,
        RoleSessionName=f'file-upload-{int(time.time())}',
        Policy=json.dumps(upload_policy),
        DurationSeconds=constants.S3FF_UPLOAD_DURATION,
    )

    credentials = resp['Credentials']
    s3_options = {
        'apiVersion': '2006-03-01',
        'accessKeyId': credentials['AccessKeyId'],
        'secretAccessKey': credentials['SecretAccessKey'],
        'sessionToken': credentials['SessionToken'],
        # MinIO uses path style URLs instead of the subdomain style typical of AWS
        's3ForcePathStyle': constants.S3FF_STORAGE_PROVIDER == constants.StorageProvider.MINIO,
    }
    if constants.S3FF_PUBLIC_ENDPOINT_URL:
        s3_options['endpoint'] = constants.S3FF_PUBLIC_ENDPOINT_URL

    signals.s3_file_field_upload_prepare.send(
        sender=upload_prepare, name=name, object_key=object_key
    )

    signer = TimestampSigner()
    sig = signer.sign(object_key)

    return JsonResponse(
        {
            's3Options': s3_options,
            'bucketName': constants.S3FF_BUCKET,
            'objectKey': object_key,
            'signature': sig,
        }
    )


# @authentication_classes([TokenAuthentication])
# @permission_classes([IsAuthenticated])
@api_view(['POST'])
@parser_classes([JSONParser])
def multipart_upload_prepare(request: Request) -> HttpResponseBase:
    name = request.data['name']
    content_length = request.data['content_length']
    max_part_length = request.data.get('max_part_length')
    # Use 1GB parts as a default
    if not max_part_length:
        max_part_length = 1_000_000_000
    # AWS does not allow part length less than 5MB
    if max_part_length < 5_000_000:
        raise ValueError('max_part_length must be greater than 5MB')

    object_key = str(constants.S3FF_UPLOAD_PREFIX / str(uuid.uuid4()) / name)

    client = client_factory('s3')

    resp = client.create_multipart_upload(Bucket=constants.S3FF_BUCKET, Key=object_key)
    upload_id = resp['UploadId']

    def presign_part(part_number, content_length):
        url = client.generate_presigned_url(
            'upload_part',
            Params={
                'Bucket': constants.S3FF_BUCKET,
                'ContentLength': content_length,
                'Key': object_key,
                'PartNumber': part_number,
                'UploadId': upload_id,
            },
        )
        return {'url': url, 'part_number': part_number, 'content_length': content_length}

    parts = []
    # How many parts are filled to capacity
    full_parts = content_length // max_part_length
    for part_number in range(0, full_parts):
        parts.append(presign_part(part_number, max_part_length))
    # The last part contains any leftover bytes, if any
    if content_length % max_part_length > 0:
        parts.append(presign_part(full_parts, content_length % max_part_length))

    return JsonResponse({'parts': parts, 'key': object_key, 'upload_id': upload_id})


# @authentication_classes([TokenAuthentication])
# @permission_classes([IsAuthenticated])
@api_view(['POST'])
@parser_classes([JSONParser])
def multipart_upload_finalize(request: Request) -> HttpResponseBase:
    object_key = request.data['key']
    upload_id = request.data['upload_id']
    parts = request.data['parts']
    parts = [{'PartNumber': part['part_number'], 'ETag': part['etag']} for part in parts]
    client = client_factory('s3')

    client.complete_multipart_upload(
        Bucket=constants.S3FF_BUCKET,
        Key=object_key,
        UploadId=upload_id,
        MultipartUpload={'Parts': parts},
    )
    return HttpResponse(status=201)
