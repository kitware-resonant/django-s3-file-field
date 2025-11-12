from ninja import Router, Schema

from s3_file_field.ninja import S3FileFieldValue

from .models import Resource

router = Router()


class ResourceSchema(Schema):
    blob: S3FileFieldValue


class ResourceResponseSchema(Schema):
    id: int
    blob: str


@router.post("/", response={201: ResourceResponseSchema})
def create_resource(request, data: ResourceSchema):
    resource = Resource.objects.create(**data.dict())
    return 201, resource
