from datetime import datetime

from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.drivers.models import MAX_RATING, MIN_RATING, Driver
from apps.rides.domain import (
    DRIVER_ACTIVE_STATUSES,
    RIDER_ACTIVE_STATUSES,
    STATUSES_WITH_DRIVER,
    InvalidRideTransition,
    OfferStatus,
    RideStatus,
)

RIDER_ACTIVE_RIDE_CONSTRAINT = "ride_one_active_per_rider"
DRIVER_ACTIVE_RIDE_CONSTRAINT = "ride_one_active_per_driver"
RIDE_PENDING_OFFER_CONSTRAINT = "offer_one_pending_per_ride"
DRIVER_PENDING_OFFER_CONSTRAINT = "offer_one_pending_per_driver"


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
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=20,
        choices=RideStatus.choices,
        default=RideStatus.SEARCHING,
    )

    pickup_latitude = models.FloatField()
    pickup_longitude = models.FloatField()
    dropoff_latitude = models.FloatField()
    dropoff_longitude = models.FloatField()
    estimated_distance_km = models.FloatField()
    estimated_fare = models.PositiveIntegerField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    assigned_at = models.DateTimeField(null=True, blank=True)
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
                condition=~Q(status__in=STATUSES_WITH_DRIVER)
                | Q(driver__isnull=False, assigned_at__isnull=False),
                name="ride_driver_set_once_assigned",
            ),
            models.CheckConstraint(
                condition=Q(
                    status__in=[RideStatus.IN_PROGRESS, RideStatus.COMPLETED],
                    started_at__isnull=False,
                )
                | (
                    ~Q(status__in=[RideStatus.IN_PROGRESS, RideStatus.COMPLETED])
                    & Q(started_at__isnull=True)
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
                condition=Q(status__in=RIDER_ACTIVE_STATUSES),
                name=RIDER_ACTIVE_RIDE_CONSTRAINT,
            ),
            models.UniqueConstraint(
                fields=["driver"],
                condition=Q(status__in=DRIVER_ACTIVE_STATUSES),
                name=DRIVER_ACTIVE_RIDE_CONSTRAINT,
            ),
        ]

    def __str__(self) -> str:
        return f"Ride {self.pk} ({self.status})"

    @property
    def is_active(self) -> bool:
        return self.status in RIDER_ACTIVE_STATUSES

    def assign(self, driver: Driver, at: datetime) -> None:
        if self.status != RideStatus.SEARCHING:
            raise InvalidRideTransition(
                "Only rides that are searching can be assigned."
            )

        self.status = RideStatus.ASSIGNED
        self.driver = driver
        self.assigned_at = at

    def give_up(self) -> None:
        if self.status != RideStatus.SEARCHING:
            raise InvalidRideTransition("Only rides that are searching can give up.")

        self.status = RideStatus.NO_DRIVER

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
        if self.status not in (RideStatus.SEARCHING, RideStatus.ASSIGNED):
            raise InvalidRideTransition(
                "Only rides that have not started can be cancelled."
            )

        self.status = RideStatus.CANCELLED
        self.cancelled_at = at


class RideOffer(models.Model):
    ride = models.ForeignKey(
        Ride, on_delete=models.CASCADE, related_name="offers", db_index=False
    )
    driver = models.ForeignKey(
        Driver, on_delete=models.CASCADE, related_name="ride_offers", db_index=False
    )
    status = models.CharField(
        max_length=20,
        choices=OfferStatus.choices,
        default=OfferStatus.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["ride", "created_at"], name="offer_ride_idx"),
            models.Index(fields=["driver", "-created_at"], name="offer_driver_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(status__in=OfferStatus.values),
                name="offer_valid_status",
            ),
            models.CheckConstraint(
                condition=Q(expires_at__gt=models.F("created_at")),
                name="offer_expires_after_created",
            ),
            models.UniqueConstraint(
                fields=["ride", "driver"],
                name="offer_once_per_driver_per_ride",
            ),
            models.UniqueConstraint(
                fields=["ride"],
                condition=Q(status=OfferStatus.PENDING),
                name=RIDE_PENDING_OFFER_CONSTRAINT,
            ),
            models.UniqueConstraint(
                fields=["driver"],
                condition=Q(status=OfferStatus.PENDING),
                name=DRIVER_PENDING_OFFER_CONSTRAINT,
            ),
        ]

    def __str__(self) -> str:
        return f"Offer {self.pk} ride={self.ride_id} driver={self.driver_id} ({self.status})"

    def is_expired(self, now: datetime) -> bool:
        return now >= self.expires_at

    def accept(self, now: datetime) -> None:
        self._respond(OfferStatus.ACCEPTED, now)

    def decline(self, now: datetime) -> None:
        self._respond(OfferStatus.DECLINED, now)

    def expire(self, now: datetime) -> None:
        self._respond(OfferStatus.EXPIRED, now)

    def _respond(self, status: OfferStatus, now: datetime) -> None:
        if self.status != OfferStatus.PENDING:
            raise InvalidRideTransition("This offer was already answered.")

        self.status = status
        self.responded_at = now


class RideRating(models.Model):
    ride = models.OneToOneField(
        Ride, on_delete=models.CASCADE, primary_key=True, related_name="rating"
    )
    driver = models.ForeignKey(
        Driver, on_delete=models.CASCADE, related_name="ratings", db_index=False
    )
    score = models.PositiveSmallIntegerField()
    comment = models.TextField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["driver", "-created_at"], name="rating_driver_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(score__gte=MIN_RATING, score__lte=MAX_RATING),
                name="rating_score_in_range",
            ),
        ]

    def __str__(self) -> str:
        return f"Rating {self.score} for ride {self.ride_id}"
