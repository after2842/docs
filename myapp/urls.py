from .views import get_file, search_file, get_signed_url
from django.urls import path
urlpatterns=[
    path("api/upload/", get_file),
    path("api/search", search_file),
    path('api/download', get_signed_url)
]