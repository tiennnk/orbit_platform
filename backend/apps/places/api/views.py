from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.places.api.serializers import PlaceSearchQuerySerializer, PlaceSerializer
from apps.places.services import search_places
from apps.shared.serializers import ErrorSerializer


class PlaceSearchView(APIView):
    throttle_scope = "places"

    @extend_schema(
        tags=["places"],
        operation_id="searchPlaces",
        parameters=[PlaceSearchQuerySerializer],
        responses={200: PlaceSerializer(many=True), 503: ErrorSerializer},
    )
    def get(self, request):
        query = PlaceSearchQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        data = query.validated_data

        near = None
        if "latitude" in data:
            near = (data["latitude"], data["longitude"])
        places = search_places(query=data["q"], near=near)
        return Response(PlaceSerializer(places, many=True).data)
