from django.conf import settings
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower

from apps.food.domain import InvalidRestaurantTransition
from apps.shared.domain import ApprovalStatus

OWNER_UNIQUE_CONSTRAINT = "restaurant_one_per_owner"
MENU_ITEM_NAME_CONSTRAINT = "menu_item_unique_name"
MAX_PRICE_VND = 10_000_000


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
