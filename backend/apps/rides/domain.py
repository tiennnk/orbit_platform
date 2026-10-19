from django.db import models

from apps.shared.exceptions import ConflictError, NotFoundError, UnavailableError


class RideStatus(models.TextChoices):
    SEARCHING = "searching"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_DRIVER = "no_driver"


RIDER_ACTIVE_STATUSES = (
    RideStatus.SEARCHING,
    RideStatus.ASSIGNED,
    RideStatus.IN_PROGRESS,
)
DRIVER_ACTIVE_STATUSES = (RideStatus.ASSIGNED, RideStatus.IN_PROGRESS)
STATUSES_WITH_DRIVER = (
    RideStatus.ASSIGNED,
    RideStatus.IN_PROGRESS,
    RideStatus.COMPLETED,
)


class OfferStatus(models.TextChoices):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"


class RideRole(models.TextChoices):
    RIDER = "rider"
    DRIVER = "driver"


class InvalidRideTransition(ConflictError):
    pass


class RideNotFound(NotFoundError):
    pass


class OfferNotFound(NotFoundError):
    pass


class DriverLocationUnavailable(NotFoundError):
    pass


class OfferNoLongerAvailable(ConflictError):
    pass


class RiderHasActiveRide(ConflictError):
    pass


class NoDriverAvailable(UnavailableError):
    pass
