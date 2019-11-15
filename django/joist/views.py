from django.contrib.auth.models import User
from django.http.response import HttpResponseBase
from rest_framework import viewsets
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import JSONParser
from rest_framework.request import Request
from rest_framework.response import Response

from .models import Blob
from .serializers import BlobSerializer


class BlobViewSet(viewsets.ModelViewSet):
    queryset = Blob.objects.all()
    serializer_class = BlobSerializer


# @authentication_classes([TokenAuthentication])
# @permission_classes([IsAuthenticated])
@api_view(['POST'])
@parser_classes([JSONParser])
def save_blob(request: Request) -> HttpResponseBase:
    creator = request.user if not request.user.is_anonymous else User.objects.first()
    blob = Blob(creator=creator, resource=request.data['name'])
    blob.save()
    return Response(BlobSerializer(blob).data)
