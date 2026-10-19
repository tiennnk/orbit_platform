from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.drivers.api.serializers import (
    DriverCreateSerializer,
    DriverListQuerySerializer,
    DriverLocationSerializer,
    DriverProfileUpdateSerializer,
    DriverSerializer,
    LocationUpdateSerializer,
    NearbyDriverSerializer,
    NearbyDriversQuerySerializer,
)
from apps.drivers.selectors import (
    find_nearby_drivers,
    get_driver_by_id,
    get_driver_for_user,
    list_drivers,
)
from apps.drivers.services import (
    approve_driver,
    go_offline,
    go_online,
    register_driver,
    reinstate_driver,
    reject_driver,
    suspend_driver,
    update_driver_profile,
    update_location,
)
from apps.shared.pagination import DefaultPagination
from apps.shared.serializers import ErrorSerializer


class DriverListCreateView(ListAPIView):
    serializer_class = DriverSerializer
    pagination_class = DefaultPagination

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAdminUser()]
        return super().get_permissions()

    def get_queryset(self):
        query = DriverListQuerySerializer(data=self.request.query_params)
        query.is_valid(raise_exception=True)
        return list_drivers(**query.validated_data)

    @extend_schema(
        tags=["admin"],
        operation_id="listDrivers",
        parameters=[DriverListQuerySerializer],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        tags=["drivers"],
        operation_id="registerDriver",
        request=DriverCreateSerializer,
        responses={201: DriverSerializer, 409: ErrorSerializer},
    )
    def post(self, request):
        serializer = DriverCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        driver = register_driver(user=request.user, **serializer.validated_data)
        return Response(DriverSerializer(driver).data, status=status.HTTP_201_CREATED)


class MyDriverView(APIView):
    @extend_schema(
        tags=["drivers"],
        operation_id="getMyDriver",
        responses={200: DriverSerializer, 404: ErrorSerializer},
    )
    def get(self, request):
        driver = get_driver_for_user(user=request.user)
        return Response(DriverSerializer(driver).data)

    @extend_schema(
        tags=["drivers"],
        operation_id="updateMyDriver",
        request=DriverProfileUpdateSerializer,
        responses={200: DriverSerializer, 404: ErrorSerializer, 409: ErrorSerializer},
    )
    def put(self, request):
        serializer = DriverProfileUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        driver = get_driver_for_user(user=request.user)
        driver = update_driver_profile(driver_id=driver.id, **serializer.validated_data)
        return Response(DriverSerializer(driver).data)


class MyDriverGoOnlineView(APIView):
    @extend_schema(
        tags=["drivers"],
        operation_id="goOnline",
        request=None,
        responses={200: DriverSerializer, 404: ErrorSerializer, 409: ErrorSerializer},
    )
    def post(self, request):
        driver = get_driver_for_user(user=request.user)
        driver = go_online(driver_id=driver.id)
        return Response(DriverSerializer(driver).data)


class MyDriverGoOfflineView(APIView):
    @extend_schema(
        tags=["drivers"],
        operation_id="goOffline",
        request=None,
        responses={200: DriverSerializer, 404: ErrorSerializer, 409: ErrorSerializer},
    )
    def post(self, request):
        driver = get_driver_for_user(user=request.user)
        driver = go_offline(driver_id=driver.id)
        return Response(DriverSerializer(driver).data)


class MyDriverLocationView(APIView):
    @extend_schema(
        tags=["drivers"],
        operation_id="updateMyLocation",
        request=LocationUpdateSerializer,
        responses={
            200: DriverLocationSerializer,
            404: ErrorSerializer,
            409: ErrorSerializer,
        },
    )
    def put(self, request):
        serializer = LocationUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        driver = get_driver_for_user(user=request.user)
        location = update_location(driver=driver, **serializer.validated_data)
        return Response(DriverLocationSerializer(location).data)


class DriverDetailView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        tags=["admin"],
        operation_id="getDriver",
        responses={200: DriverSerializer, 404: ErrorSerializer},
    )
    def get(self, request, pk: int):
        driver = get_driver_by_id(driver_id=pk)
        return Response(DriverSerializer(driver).data)


class DriverApproveView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        tags=["admin"],
        operation_id="approveDriver",
        request=None,
        responses={200: DriverSerializer, 404: ErrorSerializer, 409: ErrorSerializer},
    )
    def post(self, request, pk: int):
        driver = approve_driver(driver_id=pk)
        return Response(DriverSerializer(driver).data)


ADMIN_ACTION_RESPONSES = {
    200: DriverSerializer,
    404: ErrorSerializer,
    409: ErrorSerializer,
}


class DriverRejectView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        tags=["admin"],
        operation_id="rejectDriver",
        request=None,
        responses=ADMIN_ACTION_RESPONSES,
    )
    def post(self, request, pk: int):
        driver = reject_driver(driver_id=pk)
        return Response(DriverSerializer(driver).data)


class DriverSuspendView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        tags=["admin"],
        operation_id="suspendDriver",
        request=None,
        responses=ADMIN_ACTION_RESPONSES,
    )
    def post(self, request, pk: int):
        driver = suspend_driver(driver_id=pk)
        return Response(DriverSerializer(driver).data)


class DriverReinstateView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        tags=["admin"],
        operation_id="reinstateDriver",
        request=None,
        responses=ADMIN_ACTION_RESPONSES,
    )
    def post(self, request, pk: int):
        driver = reinstate_driver(driver_id=pk)
        return Response(DriverSerializer(driver).data)


class NearbyDriversView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        tags=["admin"],
        operation_id="findNearbyDrivers",
        parameters=[NearbyDriversQuerySerializer],
        responses={200: NearbyDriverSerializer(many=True)},
    )
    def get(self, request):
        query = NearbyDriversQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)

        nearby = find_nearby_drivers(**query.validated_data)
        return Response(NearbyDriverSerializer(nearby, many=True).data)
