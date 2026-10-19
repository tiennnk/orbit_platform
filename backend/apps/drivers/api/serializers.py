from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

from apps.drivers.domain import ApprovalStatus
from apps.drivers.models import Driver, DriverLocation


class DriverCreateSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=255)
    phone = serializers.CharField(max_length=20)


class DriverSerializer(serializers.ModelSerializer):
    class Meta:
        model = Driver
        fields = [
            "id",
            "full_name",
            "phone",
            "approval_status",
            "is_online",
            "availability",
            "created_at",
        ]
        read_only_fields = fields


class LocationUpdateSerializer(serializers.Serializer):
    MAX_CLOCK_SKEW = timedelta(minutes=1)

    latitude = serializers.FloatField(min_value=-90, max_value=90)
    longitude = serializers.FloatField(min_value=-180, max_value=180)
    recorded_at = serializers.DateTimeField()

    def validate_recorded_at(self, value):
        if value > timezone.now() + self.MAX_CLOCK_SKEW:
            raise serializers.ValidationError("recorded_at cannot be in the future.")
        return value


class DriverLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = DriverLocation
        fields = ["latitude", "longitude", "recorded_at", "updated_at"]
        read_only_fields = fields


class NearbyDriversQuerySerializer(serializers.Serializer):
    latitude = serializers.FloatField(min_value=-90, max_value=90)
    longitude = serializers.FloatField(min_value=-180, max_value=180)
    radius_km = serializers.FloatField(min_value=0.1, max_value=20, default=3.0)
    limit = serializers.IntegerField(min_value=1, max_value=50, default=10)


class NearbyDriverSerializer(serializers.Serializer):
    driver_id = serializers.IntegerField(source="driver.id")
    full_name = serializers.CharField(source="driver.full_name")
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()
    distance_km = serializers.FloatField()


class DriverListQuerySerializer(serializers.Serializer):
    approval_status = serializers.ChoiceField(
        choices=ApprovalStatus.choices, required=False
    )
