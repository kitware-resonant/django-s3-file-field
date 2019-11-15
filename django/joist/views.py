from django.contrib.auth.models import User
from django.http.response import HttpResponseBase
from rest_framework import viewsets
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import JSONParser
from rest_framework.request import Request
from rest_framework.response import Response

from django.shortcuts import render
from django.views import generic

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
    names = request.data.get('names', [])
    out = []
    for name in names:
        blob = Blob(creator=creator, resource=name)
        blob.save()
        out.append(BlobSerializer(blob).data)
    return Response(out)


class IndexView(generic.ListView):
    template_name = 'blob/index.html'

    def get_queryset(self):
        return Blob.objects.all()


class DetailView(generic.DetailView):
    model = Blob
    template_name = 'blob/detail.html'


def newBlob(request: Request) -> HttpResponseBase:
    context = {}
    return render(request, 'blob/new.html', context)
