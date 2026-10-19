from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.drivers.api.serializers import (
    DriverCreateSerializer,
    DriverLocationSerializer,
    DriverSerializer,
    LocationUpdateSerializer,
    NearbyDriverSerializer,
    NearbyDriversQuerySerializer,
)
from apps.drivers.selectors import (
    find_nearby_drivers,
    get_driver_by_id,
    get_driver_for_user,
)
from apps.drivers.services import (
    approve_driver,
    go_offline,
    go_online,
    register_driver,
    update_location,
)


class DriverCreateView(APIView):
    def post(self, request):
        serializer = DriverCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        driver = register_driver(user=request.user, **serializer.validated_data)
        return Response(DriverSerializer(driver).data, status=status.HTTP_201_CREATED)


class MyDriverView(APIView):
    def get(self, request):
        driver = get_driver_for_user(user=request.user)
        return Response(DriverSerializer(driver).data)


class MyDriverGoOnlineView(APIView):
    def post(self, request):
        driver = get_driver_for_user(user=request.user)
        driver = go_online(driver_id=driver.id)
        return Response(DriverSerializer(driver).data)


class MyDriverGoOfflineView(APIView):
    def post(self, request):
        driver = get_driver_for_user(user=request.user)
        driver = go_offline(driver_id=driver.id)
        return Response(DriverSerializer(driver).data)


class MyDriverLocationView(APIView):
    def put(self, request):
        serializer = LocationUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        driver = get_driver_for_user(user=request.user)
        location = update_location(driver=driver, **serializer.validated_data)
        return Response(DriverLocationSerializer(location).data)


class DriverDetailView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, pk: int):
        driver = get_driver_by_id(driver_id=pk)
        return Response(DriverSerializer(driver).data)


class DriverApproveView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, pk: int):
        driver = approve_driver(driver_id=pk)
        return Response(DriverSerializer(driver).data)


class NearbyDriversView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        query = NearbyDriversQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)

        nearby = find_nearby_drivers(**query.validated_data)
        return Response(NearbyDriverSerializer(nearby, many=True).data)
