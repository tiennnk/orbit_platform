from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.drivers.api.serializers import DriverCreateSerializer, DriverSerializer
from apps.drivers.domain import (
    DriverAlreadyExists,
    DriverNotFound,
    InvalidStateTransition,
)
from apps.drivers.models import Driver
from apps.drivers.services import approve_driver, register_driver


class DriverCreateView(APIView):
    def post(self, request):
        serializer = DriverCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            driver = register_driver(**serializer.validated_data)
        except DriverAlreadyExists as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)

        return Response(DriverSerializer(driver).data, status=status.HTTP_201_CREATED)


class DriverDetailView(APIView):
    def get(self, request, pk: int):
        driver = get_object_or_404(Driver, pk=pk)
        return Response(DriverSerializer(driver).data)


class DriverApproveView(APIView):
    def post(self, request, pk: int):
        try:
            driver = approve_driver(driver_id=pk)
        except DriverNotFound as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        except InvalidStateTransition as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)

        return Response(DriverSerializer(driver).data)
