from django.conf import settings
from django.db import models
from django.db.models import F, Q
from django.db.models.functions import Lower

from apps.food.domain import (
    InvalidOrderTransition,
    InvalidRestaurantTransition,
    OrderStatus,
)
from apps.rides.models import Ride
from apps.shared.domain import ApprovalStatus

OWNER_UNIQUE_CONSTRAINT = "restaurant_one_per_owner"
MENU_ITEM_NAME_CONSTRAINT = "menu_item_unique_name"
MAX_PRICE_VND = 10_000_000
MAX_QUANTITY = 20


class Restaurant(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="restaurants",
        db_index=False,
    )
    name = models.CharField(max_length=120)
    phone = models.CharField(max_length=20)
    address = models.CharField(max_length=255)
    latitude = models.FloatField()
    longitude = models.FloatField()

    approval_status = models.CharField(
        max_length=20,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.PENDING,
    )
    is_open = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["approval_status", "created_at"],
                name="restaurant_status_created_idx",
            ),
            models.Index(
                fields=["latitude", "longitude"],
                name="restaurant_lat_lng_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(fields=["owner"], name=OWNER_UNIQUE_CONSTRAINT),
            models.CheckConstraint(
                condition=Q(approval_status__in=ApprovalStatus.values),
                name="restaurant_valid_approval_status",
            ),
            models.CheckConstraint(
                condition=Q(
                    latitude__gte=-90,
                    latitude__lte=90,
                    longitude__gte=-180,
                    longitude__lte=180,
                ),
                name="restaurant_valid_coordinates",
            ),
            models.CheckConstraint(
                condition=Q(is_open=False) | Q(approval_status=ApprovalStatus.APPROVED),
                name="restaurant_open_requires_approval",
            ),
        ]

    def __str__(self) -> str:
        return self.name

    def approve(self) -> None:
        if self.approval_status != ApprovalStatus.PENDING:
            raise InvalidRestaurantTransition(
                "Only pending restaurants can be approved."
            )

        self.approval_status = ApprovalStatus.APPROVED

    def reject(self) -> None:
        if self.approval_status != ApprovalStatus.PENDING:
            raise InvalidRestaurantTransition(
                "Only pending restaurants can be rejected."
            )

        self.approval_status = ApprovalStatus.REJECTED

    def suspend(self) -> None:
        if self.approval_status != ApprovalStatus.APPROVED:
            raise InvalidRestaurantTransition(
                "Only approved restaurants can be suspended."
            )

        self.approval_status = ApprovalStatus.SUSPENDED
        self.is_open = False

    def reinstate(self) -> None:
        if self.approval_status != ApprovalStatus.SUSPENDED:
            raise InvalidRestaurantTransition(
                "Only suspended restaurants can be reinstated."
            )

        self.approval_status = ApprovalStatus.APPROVED

    def update_profile(
        self,
        *,
        name: str,
        phone: str,
        address: str,
        latitude: float,
        longitude: float,
    ) -> None:
        if self.approval_status not in (
            ApprovalStatus.PENDING,
            ApprovalStatus.REJECTED,
        ):
            raise InvalidRestaurantTransition(
                "Approved restaurants cannot be edited. Contact support to change them."
            )

        self.name = name
        self.phone = phone
        self.address = address
        self.latitude = latitude
        self.longitude = longitude
        self.approval_status = ApprovalStatus.PENDING

    def open(self) -> None:
        if self.approval_status != ApprovalStatus.APPROVED:
            raise InvalidRestaurantTransition(
                "Restaurant must be approved before opening."
            )

        self.is_open = True

    def close(self) -> None:
        self.is_open = False


class MenuItem(models.Model):
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="menu_items",
        db_index=False,
    )
    name = models.CharField(max_length=120)
    description = models.CharField(max_length=500, blank=True)
    price = models.PositiveIntegerField()
    is_available = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                "restaurant",
                Lower("name"),
                name=MENU_ITEM_NAME_CONSTRAINT,
            ),
            models.CheckConstraint(
                condition=Q(price__gt=0, price__lte=MAX_PRICE_VND),
                name="menu_item_price_in_range",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.price})"


class FoodOrder(models.Model):
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="food_orders",
        db_index=False,
    )
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.PROTECT,
        related_name="orders",
        db_index=False,
    )
    status = models.CharField(
        max_length=20,
        choices=OrderStatus.choices,
        default=OrderStatus.PLACED,
    )
    delivery = models.OneToOneField(
        Ride,
        on_delete=models.PROTECT,
        related_name="food_order",
        null=True,
        blank=True,
    )

    delivery_latitude = models.FloatField()
    delivery_longitude = models.FloatField()
    delivery_address = models.CharField(max_length=255, blank=True)
    note = models.CharField(max_length=300, blank=True)

    subtotal = models.PositiveIntegerField()
    delivery_fee = models.PositiveIntegerField()
    total = models.PositiveIntegerField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["customer", "-created_at"], name="order_customer_recent_idx"
            ),
            models.Index(
                fields=["restaurant", "status", "-created_at"],
                name="order_restaurant_status_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(status__in=OrderStatus.values),
                name="order_valid_status",
            ),
            models.CheckConstraint(
                condition=Q(subtotal__gt=0, total=F("subtotal") + F("delivery_fee")),
                name="order_total_adds_up",
            ),
            models.CheckConstraint(
                condition=Q(
                    delivery_latitude__gte=-90,
                    delivery_latitude__lte=90,
                    delivery_longitude__gte=-180,
                    delivery_longitude__lte=180,
                ),
                name="order_valid_coordinates",
            ),
            models.CheckConstraint(
                condition=Q(delivery__isnull=True) | Q(status=OrderStatus.ACCEPTED),
                name="order_delivery_requires_acceptance",
            ),
            models.CheckConstraint(
                condition=Q(status=OrderStatus.ACCEPTED, accepted_at__isnull=False)
                | (~Q(status=OrderStatus.ACCEPTED) & Q(accepted_at__isnull=True)),
                name="order_accepted_at_matches_status",
            ),
            models.CheckConstraint(
                condition=Q(
                    status__in=[OrderStatus.REJECTED, OrderStatus.CANCELLED],
                    closed_at__isnull=False,
                )
                | (
                    Q(status__in=[OrderStatus.PLACED, OrderStatus.ACCEPTED])
                    & Q(closed_at__isnull=True)
                ),
                name="order_closed_at_matches_status",
            ),
        ]

    def __str__(self) -> str:
        return f"Order {self.pk} ({self.status})"

    def accept(self, at) -> None:
        if self.status != OrderStatus.PLACED:
            raise InvalidOrderTransition("Only new orders can be accepted.")

        self.status = OrderStatus.ACCEPTED
        self.accepted_at = at

    def reject(self, at) -> None:
        if self.status != OrderStatus.PLACED:
            raise InvalidOrderTransition("Only new orders can be rejected.")

        self.status = OrderStatus.REJECTED
        self.closed_at = at

    def cancel(self, at) -> None:
        if self.status != OrderStatus.PLACED:
            raise InvalidOrderTransition(
                "The restaurant already took this order, so it cannot be cancelled."
            )

        self.status = OrderStatus.CANCELLED
        self.closed_at = at


class OrderLine(models.Model):
    order = models.ForeignKey(
        FoodOrder, on_delete=models.CASCADE, related_name="lines", db_index=False
    )
    menu_item = models.ForeignKey(
        MenuItem,
        on_delete=models.SET_NULL,
        related_name="order_lines",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=120)
    unit_price = models.PositiveIntegerField()
    quantity = models.PositiveSmallIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["order", "menu_item"], name="order_line_unique_item"
            ),
            models.CheckConstraint(
                condition=Q(quantity__gte=1, quantity__lte=MAX_QUANTITY),
                name="order_line_quantity_in_range",
            ),
            models.CheckConstraint(
                condition=Q(unit_price__gt=0),
                name="order_line_positive_price",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.quantity} x {self.name}"

    @property
    def line_total(self) -> int:
        return self.unit_price * self.quantity
