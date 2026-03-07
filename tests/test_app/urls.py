from django.urls import include, path
from ninja import NinjaAPI

from .ninja import router

api = NinjaAPI()
api.add_router("/resources/", router)

urlpatterns = [
    path("api/ninja/", api.urls),
    # Make this distinct from typical production values, to ensure it works dynamically
    path("api/s3ff_test/", include("s3_file_field.urls")),
]
