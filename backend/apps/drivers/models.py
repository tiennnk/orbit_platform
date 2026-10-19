from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.drivers.domain import ApprovalStatus, Availability, InvalidStateTransition

PHONE_UNIQUE_CONSTRAINT = "driver_unique_phone"
USER_UNIQUE_CONSTRAINT = "driver_unique_user"


class Driver(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="driver_profiles",
        db_index=False,
    )
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)

    approval_status = models.CharField(
        max_length=20,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.PENDING,
    )

    is_online = models.BooleanField(default=False)

    availability = models.CharField(
        max_length=20,
        choices=Availability.choices,
        default=Availability.AVAILABLE,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["approval_status", "created_at"],
                name="driver_status_created_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(fields=["phone"], name=PHONE_UNIQUE_CONSTRAINT),
            models.UniqueConstraint(fields=["user"], name=USER_UNIQUE_CONSTRAINT),
            models.CheckConstraint(
                condition=Q(approval_status__in=ApprovalStatus.values),
                name="driver_valid_approval_status",
            ),
            models.CheckConstraint(
                condition=Q(availability__in=Availability.values),
                name="driver_valid_availability",
            ),
            models.CheckConstraint(
                condition=(
                    Q(is_online=False) | Q(approval_status=ApprovalStatus.APPROVED)
                ),
                name="driver_online_requires_approval",
            ),
            models.CheckConstraint(
                condition=(~Q(availability=Availability.ON_TRIP) | Q(is_online=True)),
                name="driver_on_trip_requires_online",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.full_name} ({self.phone})"

    def approve(self) -> None:
        if self.approval_status != ApprovalStatus.PENDING:
            raise InvalidStateTransition("Only pending drivers can be approved.")

        self.approval_status = ApprovalStatus.APPROVED

    def go_online(self) -> None:
        if self.approval_status != ApprovalStatus.APPROVED:
            raise InvalidStateTransition("Driver must be approved before going online.")

        self.is_online = True

    def go_offline(self) -> None:
        if self.availability == Availability.ON_TRIP:
            raise InvalidStateTransition("Driver cannot go offline during a trip.")

        self.is_online = False

    def start_trip(self) -> None:
        if not self.can_accept_ride():
            raise InvalidStateTransition("Driver is not eligible to accept a ride.")

        self.availability = Availability.ON_TRIP

    def finish_trip(self) -> None:
        if self.availability != Availability.ON_TRIP:
            raise InvalidStateTransition("Driver is not currently on a trip.")

        self.availability = Availability.AVAILABLE

    def can_accept_ride(self) -> bool:
        return (
            self.approval_status == ApprovalStatus.APPROVED
            and self.is_online
            and self.availability == Availability.AVAILABLE
        )


class DriverLocation(models.Model):
    driver = models.OneToOneField(
        Driver,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="location",
    )
    latitude = models.FloatField()
    longitude = models.FloatField()
    recorded_at = models.DateTimeField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["latitude", "longitude"],
                name="driver_location_lat_lng_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(latitude__gte=-90, latitude__lte=90),
                name="driver_location_valid_latitude",
            ),
            models.CheckConstraint(
                condition=Q(longitude__gte=-180, longitude__lte=180),
                name="driver_location_valid_longitude",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.driver_id} @ ({self.latitude}, {self.longitude})"
