from rest_framework import serializers

from apps.food.models import (
    MAX_PRICE_VND,
    MAX_QUANTITY,
    FoodOrder,
    MenuItem,
    OrderLine,
    Restaurant,
)
from apps.rides.api.serializers import RideDriverSerializer
from apps.rides.domain import RideStatus
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


class OrderItemInputSerializer(serializers.Serializer):
    menu_item_id = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1, max_value=MAX_QUANTITY)


class OrderCreateSerializer(serializers.Serializer):
    restaurant_id = serializers.IntegerField(min_value=1)
    items = OrderItemInputSerializer(many=True, allow_empty=False, max_length=30)
    delivery_latitude = serializers.FloatField(min_value=-90, max_value=90)
    delivery_longitude = serializers.FloatField(min_value=-180, max_value=180)
    delivery_address = serializers.CharField(
        max_length=255, allow_blank=True, required=False, default=""
    )
    note = serializers.CharField(
        max_length=300, allow_blank=True, required=False, default=""
    )

    def validate_items(self, items):
        ids = [item["menu_item_id"] for item in items]
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError("Each dish can only appear once.")
        return items


class DeliveryQuoteQuerySerializer(serializers.Serializer):
    latitude = serializers.FloatField(min_value=-90, max_value=90)
    longitude = serializers.FloatField(min_value=-180, max_value=180)


class DeliveryQuoteSerializer(serializers.Serializer):
    distance_km = serializers.FloatField()
    delivery_fee = serializers.IntegerField()
    deliverable = serializers.BooleanField()


class OrderLineSerializer(serializers.ModelSerializer):
    line_total = serializers.IntegerField(read_only=True)

    class Meta:
        model = OrderLine
        fields = ["name", "unit_price", "quantity", "line_total"]
        read_only_fields = fields


class OrderRestaurantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Restaurant
        fields = ["id", "name", "address", "phone", "latitude", "longitude"]
        read_only_fields = fields


class OrderDeliverySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    status = serializers.ChoiceField(choices=RideStatus.choices)
    driver = RideDriverSerializer(allow_null=True)


class OrderSerializer(serializers.ModelSerializer):
    restaurant = OrderRestaurantSerializer(read_only=True)
    lines = OrderLineSerializer(many=True, read_only=True)
    delivery = OrderDeliverySerializer(allow_null=True, read_only=True)

    class Meta:
        model = FoodOrder
        fields = [
            "id",
            "status",
            "customer_id",
            "restaurant",
            "lines",
            "subtotal",
            "delivery_fee",
            "total",
            "delivery_latitude",
            "delivery_longitude",
            "delivery_address",
            "note",
            "delivery",
            "created_at",
            "accepted_at",
            "closed_at",
        ]
        read_only_fields = fields


class RestaurantOrdersQuerySerializer(serializers.Serializer):
    active = serializers.BooleanField(default=True)
