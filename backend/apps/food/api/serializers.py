from rest_framework import serializers

from apps.food.models import MAX_PRICE_VND, MenuItem, Restaurant
from apps.shared.domain import ApprovalStatus


class RestaurantProfileSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    phone = serializers.CharField(max_length=20)
    address = serializers.CharField(max_length=255)
    latitude = serializers.FloatField(min_value=-90, max_value=90)
    longitude = serializers.FloatField(min_value=-180, max_value=180)


class MenuItemInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    description = serializers.CharField(
        max_length=500, allow_blank=True, required=False, default=""
    )
    price = serializers.IntegerField(min_value=1, max_value=MAX_PRICE_VND)
    is_available = serializers.BooleanField(required=False, default=True)


class MenuItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = MenuItem
        fields = ["id", "name", "description", "price", "is_available"]
        read_only_fields = fields


class RestaurantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Restaurant
        fields = [
            "id",
            "name",
            "phone",
            "address",
            "latitude",
            "longitude",
            "approval_status",
            "is_open",
            "created_at",
        ]
        read_only_fields = fields


class RestaurantDetailSerializer(RestaurantSerializer):
    menu = MenuItemSerializer(source="menu_items", many=True, read_only=True)

    class Meta(RestaurantSerializer.Meta):
        fields = [*RestaurantSerializer.Meta.fields, "menu"]
        read_only_fields = fields


class RestaurantListQuerySerializer(serializers.Serializer):
    approval_status = serializers.ChoiceField(
        choices=ApprovalStatus.choices, required=False
    )


class NearbyRestaurantsQuerySerializer(serializers.Serializer):
    latitude = serializers.FloatField(min_value=-90, max_value=90)
    longitude = serializers.FloatField(min_value=-180, max_value=180)
    radius_km = serializers.FloatField(min_value=0.5, max_value=20, default=5.0)
    limit = serializers.IntegerField(min_value=1, max_value=50, default=20)
    q = serializers.CharField(
        max_length=100, required=False, default="", allow_blank=True
    )


class NearbyRestaurantSerializer(serializers.Serializer):
    id = serializers.IntegerField(source="restaurant.id")
    name = serializers.CharField(source="restaurant.name")
    address = serializers.CharField(source="restaurant.address")
    latitude = serializers.FloatField(source="restaurant.latitude")
    longitude = serializers.FloatField(source="restaurant.longitude")
    is_open = serializers.BooleanField(source="restaurant.is_open")
    distance_km = serializers.FloatField()
