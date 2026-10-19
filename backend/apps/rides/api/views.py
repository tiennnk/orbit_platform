from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.rides.api.serializers import (
    DriverPositionSerializer,
    RideCreateSerializer,
    RideHistoryQuerySerializer,
    RideOfferSerializer,
    RideRatingCreateSerializer,
    RideRatingSerializer,
    RideSerializer,
)
from apps.rides.selectors import (
    get_driver_position,
    get_ride_for_participant,
    list_ride_history,
)
from apps.rides.services import (
    accept_offer,
    cancel_ride,
    complete_ride,
    decline_offer,
    get_current_offer,
    rate_ride,
    refresh_current_ride,
    request_ride,
    start_ride,
)
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
        ride = refresh_current_ride(user=request.user)
        return Response(RideSerializer(ride).data)


class RideDetailView(APIView):
    @extend_schema(
        tags=["rides"],
        operation_id="getRide",
        responses={200: RideSerializer, 404: ErrorSerializer},
    )
    def get(self, request, pk: int):
        ride = get_ride_for_participant(ride_id=pk, user=request.user)
        return Response(RideSerializer(ride, context={"request": request}).data)


class RideRatingView(APIView):
    @extend_schema(
        tags=["rides"],
        operation_id="rateRide",
        request=RideRatingCreateSerializer,
        responses={
            201: RideRatingSerializer,
            404: ErrorSerializer,
            409: ErrorSerializer,
        },
    )
    def post(self, request, pk: int):
        serializer = RideRatingCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        rating = rate_ride(ride_id=pk, user=request.user, **serializer.validated_data)
        return Response(
            RideRatingSerializer(rating).data, status=status.HTTP_201_CREATED
        )


class RideDriverPositionView(APIView):
    @extend_schema(
        tags=["rides"],
        operation_id="getRideDriverPosition",
        responses={200: DriverPositionSerializer, 404: ErrorSerializer},
    )
    def get(self, request, pk: int):
        position = get_driver_position(ride_id=pk, user=request.user)
        return Response(DriverPositionSerializer(position).data)


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


class CurrentOfferView(APIView):
    @extend_schema(
        tags=["rides"],
        operation_id="getCurrentOffer",
        responses={200: RideOfferSerializer, 404: ErrorSerializer},
    )
    def get(self, request):
        offer = get_current_offer(user=request.user)
        return Response(RideOfferSerializer(offer).data)


class OfferAcceptView(APIView):
    @extend_schema(
        tags=["rides"],
        operation_id="acceptOffer",
        request=None,
        responses=RIDE_ACTION_RESPONSES,
    )
    def post(self, request, pk: int):
        ride = accept_offer(offer_id=pk, user=request.user)
        return Response(RideSerializer(ride).data)


class OfferDeclineView(APIView):
    @extend_schema(
        tags=["rides"],
        operation_id="declineOffer",
        request=None,
        responses={204: None, 404: ErrorSerializer, 409: ErrorSerializer},
    )
    def post(self, request, pk: int):
        decline_offer(offer_id=pk, user=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)
