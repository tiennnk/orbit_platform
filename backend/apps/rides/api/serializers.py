from rest_framework import serializers

from apps.rides.domain import RideRole
from apps.rides.models import Ride
from apps.shared.geo import haversine_km

MIN_TRIP_KM = 0.2


class RideCreateSerializer(serializers.Serializer):
    pickup_latitude = serializers.FloatField(min_value=-90, max_value=90)
    pickup_longitude = serializers.FloatField(min_value=-180, max_value=180)
    dropoff_latitude = serializers.FloatField(min_value=-90, max_value=90)
    dropoff_longitude = serializers.FloatField(min_value=-180, max_value=180)

    def validate(self, attrs):
        distance = haversine_km(
            attrs["pickup_latitude"],
            attrs["pickup_longitude"],
            attrs["dropoff_latitude"],
            attrs["dropoff_longitude"],
        )
        if distance < MIN_TRIP_KM:
            raise serializers.ValidationError(
                "Pickup and dropoff are too close to each other."
            )
        return attrs


class RideDriverSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    full_name = serializers.CharField()
    phone = serializers.CharField()


class RideSerializer(serializers.ModelSerializer):
    driver = RideDriverSerializer()

    class Meta:
        model = Ride
        fields = [
            "id",
            "status",
            "rider_id",
            "driver",
            "pickup_latitude",
            "pickup_longitude",
            "dropoff_latitude",
            "dropoff_longitude",
            "estimated_distance_km",
            "estimated_fare",
            "created_at",
            "started_at",
            "completed_at",
            "cancelled_at",
        ]
        read_only_fields = fields


class RideHistoryQuerySerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=RideRole.choices, default=RideRole.RIDER)
