from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.rides.api.serializers import (
    RideCreateSerializer,
    RideHistoryQuerySerializer,
    RideSerializer,
)
from apps.rides.selectors import (
    get_current_ride,
    get_ride_for_participant,
    list_ride_history,
)
from apps.rides.services import cancel_ride, complete_ride, request_ride, start_ride
from apps.shared.pagination import DefaultPagination
from apps.shared.serializers import ErrorSerializer

RIDE_ACTION_RESPONSES = {
    200: RideSerializer,
    404: ErrorSerializer,
    409: ErrorSerializer,
}


class RideRequestView(APIView):
    @extend_schema(
        tags=["rides"],
        operation_id="requestRide",
        request=RideCreateSerializer,
        responses={201: RideSerializer, 409: ErrorSerializer, 503: ErrorSerializer},
    )
    def post(self, request):
        serializer = RideCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ride = request_ride(rider=request.user, **serializer.validated_data)
        return Response(RideSerializer(ride).data, status=status.HTTP_201_CREATED)


class RideHistoryView(ListAPIView):
    serializer_class = RideSerializer
    pagination_class = DefaultPagination

    def get_queryset(self):
        query = RideHistoryQuerySerializer(data=self.request.query_params)
        query.is_valid(raise_exception=True)
        return list_ride_history(user=self.request.user, **query.validated_data)

    @extend_schema(
        tags=["rides"],
        operation_id="listRideHistory",
        parameters=[RideHistoryQuerySerializer],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class CurrentRideView(APIView):
    @extend_schema(
        tags=["rides"],
        operation_id="getCurrentRide",
        responses={200: RideSerializer, 404: ErrorSerializer},
    )
    def get(self, request):
        ride = get_current_ride(user=request.user)
        return Response(RideSerializer(ride).data)


class RideDetailView(APIView):
    @extend_schema(
        tags=["rides"],
        operation_id="getRide",
        responses={200: RideSerializer, 404: ErrorSerializer},
    )
    def get(self, request, pk: int):
        ride = get_ride_for_participant(ride_id=pk, user=request.user)
        return Response(RideSerializer(ride).data)


class RideStartView(APIView):
    @extend_schema(
        tags=["rides"],
        operation_id="startRide",
        request=None,
        responses=RIDE_ACTION_RESPONSES,
    )
    def post(self, request, pk: int):
        ride = start_ride(ride_id=pk, user=request.user)
        return Response(RideSerializer(ride).data)


class RideCompleteView(APIView):
    @extend_schema(
        tags=["rides"],
        operation_id="completeRide",
        request=None,
        responses=RIDE_ACTION_RESPONSES,
    )
    def post(self, request, pk: int):
        ride = complete_ride(ride_id=pk, user=request.user)
        return Response(RideSerializer(ride).data)


class RideCancelView(APIView):
    @extend_schema(
        tags=["rides"],
        operation_id="cancelRide",
        request=None,
        responses=RIDE_ACTION_RESPONSES,
    )
    def post(self, request, pk: int):
        ride = cancel_ride(ride_id=pk, user=request.user)
        return Response(RideSerializer(ride).data)
