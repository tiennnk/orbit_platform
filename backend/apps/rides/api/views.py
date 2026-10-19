from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.rides.api.serializers import RideRequestSerializer, RideSerializer
from apps.rides.selectors import get_current_ride, get_ride_for_participant
from apps.rides.services import cancel_ride, complete_ride, request_ride, start_ride


class RideRequestView(APIView):
    def post(self, request):
        serializer = RideRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ride = request_ride(rider=request.user, **serializer.validated_data)
        return Response(RideSerializer(ride).data, status=status.HTTP_201_CREATED)


class CurrentRideView(APIView):
    def get(self, request):
        ride = get_current_ride(user=request.user)
        return Response(RideSerializer(ride).data)


class RideDetailView(APIView):
    def get(self, request, pk: int):
        ride = get_ride_for_participant(ride_id=pk, user=request.user)
        return Response(RideSerializer(ride).data)


class RideStartView(APIView):
    def post(self, request, pk: int):
        ride = start_ride(ride_id=pk, user=request.user)
        return Response(RideSerializer(ride).data)


class RideCompleteView(APIView):
    def post(self, request, pk: int):
        ride = complete_ride(ride_id=pk, user=request.user)
        return Response(RideSerializer(ride).data)


class RideCancelView(APIView):
    def post(self, request, pk: int):
        ride = cancel_ride(ride_id=pk, user=request.user)
        return Response(RideSerializer(ride).data)
