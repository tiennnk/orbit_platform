from rest_framework import serializers

from apps.drivers.models import MAX_RATING, MIN_RATING
from apps.rides.domain import RideRole
from apps.rides.models import Ride, RideOffer, RideRating
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
    rating_average = serializers.FloatField(allow_null=True)
    rating_count = serializers.IntegerField()


class RideRatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = RideRating
        fields = ["score", "comment", "created_at"]
        read_only_fields = fields


class RideRatingCreateSerializer(serializers.Serializer):
    score = serializers.IntegerField(min_value=MIN_RATING, max_value=MAX_RATING)
    comment = serializers.CharField(
        max_length=500, allow_blank=True, required=False, default=""
    )


class RideSerializer(serializers.ModelSerializer):
    driver = RideDriverSerializer(allow_null=True)
    rating = RideRatingSerializer(allow_null=True, read_only=True)

    class Meta:
        model = Ride
        fields = [
            "id",
            "status",
            "service",
            "rider_id",
            "driver",
            "pickup_latitude",
            "pickup_longitude",
            "dropoff_latitude",
            "dropoff_longitude",
            "pickup_label",
            "dropoff_label",
            "estimated_distance_km",
            "estimated_fare",
            "created_at",
            "assigned_at",
            "started_at",
            "completed_at",
            "cancelled_at",
            "rating",
        ]
        read_only_fields = fields

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        if request is None or request.user.pk != instance.rider_id:
            data["rating"] = None
        return data


class RideHistoryQuerySerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=RideRole.choices, default=RideRole.RIDER)


class RideOfferSerializer(serializers.ModelSerializer):
    ride = RideSerializer()

    class Meta:
        model = RideOffer
        fields = ["id", "ride", "created_at", "expires_at"]
        read_only_fields = fields


class DriverPositionSerializer(serializers.Serializer):
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()
    recorded_at = serializers.DateTimeField()
    heading_to = serializers.ChoiceField(choices=["pickup", "dropoff"])
    distance_km = serializers.FloatField()
    eta_minutes = serializers.IntegerField()
