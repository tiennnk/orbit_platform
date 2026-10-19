from django.urls import path

from apps.places.api.views import PlaceSearchView

urlpatterns = [
    path("search/", PlaceSearchView.as_view(), name="place-search"),
]
