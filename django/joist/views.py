from django.contrib.auth.models import User
from django.http.response import HttpResponseBase
from django.shortcuts import HttpResponseRedirect, render
from django.views import generic
from rest_framework import viewsets
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import JSONParser
from rest_framework.request import Request
from rest_framework.response import Response

from .forms import BlobForm
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


def new_blob(request: Request) -> HttpResponseBase:
    form = BlobForm(request.POST, request.FILES) if request.method == 'POST' else BlobForm()
    if request.method == 'POST':
        # check whether it's valid:
        if form.is_valid():
            form.save()
            # process the data in form.cleaned_data as required
            # ...
            # redirect to a new URL:
            return HttpResponseRedirect('/blob/')
    return render(request, 'blob/new.html', {'form': form})
