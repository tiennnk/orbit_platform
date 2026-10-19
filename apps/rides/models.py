from datetime import datetime

from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.drivers.models import Driver
from apps.rides.domain import ACTIVE_RIDE_STATUSES, InvalidRideTransition, RideStatus

RIDER_ACTIVE_RIDE_CONSTRAINT = "ride_one_active_per_rider"
DRIVER_ACTIVE_RIDE_CONSTRAINT = "ride_one_active_per_driver"


class Ride(models.Model):
    rider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="rides",
        db_index=False,
    )
    driver = models.ForeignKey(
        Driver,
        on_delete=models.PROTECT,
        related_name="rides",
        db_index=False,
    )
    status = models.CharField(
        max_length=20,
        choices=RideStatus.choices,
        default=RideStatus.ASSIGNED,
    )

    pickup_latitude = models.FloatField()
    pickup_longitude = models.FloatField()
    dropoff_latitude = models.FloatField()
    dropoff_longitude = models.FloatField()
    estimated_distance_km = models.FloatField()
    estimated_fare = models.PositiveIntegerField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["rider", "-created_at"], name="ride_rider_recent_idx"),
            models.Index(
                fields=["driver", "-created_at"], name="ride_driver_recent_idx"
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(status__in=RideStatus.values),
                name="ride_valid_status",
            ),
            models.CheckConstraint(
                condition=Q(
                    pickup_latitude__gte=-90,
                    pickup_latitude__lte=90,
                    dropoff_latitude__gte=-90,
                    dropoff_latitude__lte=90,
                    pickup_longitude__gte=-180,
                    pickup_longitude__lte=180,
                    dropoff_longitude__gte=-180,
                    dropoff_longitude__lte=180,
                ),
                name="ride_valid_coordinates",
            ),
            models.CheckConstraint(
                condition=Q(
                    status__in=[RideStatus.IN_PROGRESS, RideStatus.COMPLETED],
                    started_at__isnull=False,
                )
                | Q(
                    status__in=[RideStatus.ASSIGNED, RideStatus.CANCELLED],
                    started_at__isnull=True,
                ),
                name="ride_started_at_matches_status",
            ),
            models.CheckConstraint(
                condition=Q(status=RideStatus.COMPLETED, completed_at__isnull=False)
                | (~Q(status=RideStatus.COMPLETED) & Q(completed_at__isnull=True)),
                name="ride_completed_at_matches_status",
            ),
            models.CheckConstraint(
                condition=Q(status=RideStatus.CANCELLED, cancelled_at__isnull=False)
                | (~Q(status=RideStatus.CANCELLED) & Q(cancelled_at__isnull=True)),
                name="ride_cancelled_at_matches_status",
            ),
            models.UniqueConstraint(
                fields=["rider"],
                condition=Q(status__in=ACTIVE_RIDE_STATUSES),
                name=RIDER_ACTIVE_RIDE_CONSTRAINT,
            ),
            models.UniqueConstraint(
                fields=["driver"],
                condition=Q(status__in=ACTIVE_RIDE_STATUSES),
                name=DRIVER_ACTIVE_RIDE_CONSTRAINT,
            ),
        ]

    def __str__(self) -> str:
        return f"Ride {self.pk} ({self.status})"

    @property
    def is_active(self) -> bool:
        return self.status in ACTIVE_RIDE_STATUSES

    def start(self, at: datetime) -> None:
        if self.status != RideStatus.ASSIGNED:
            raise InvalidRideTransition("Only assigned rides can be started.")

        self.status = RideStatus.IN_PROGRESS
        self.started_at = at

    def complete(self, at: datetime) -> None:
        if self.status != RideStatus.IN_PROGRESS:
            raise InvalidRideTransition("Only rides in progress can be completed.")

        self.status = RideStatus.COMPLETED
        self.completed_at = at

    def cancel(self, at: datetime) -> None:
        if self.status != RideStatus.ASSIGNED:
            raise InvalidRideTransition("Only assigned rides can be cancelled.")

        self.status = RideStatus.CANCELLED
        self.cancelled_at = at
