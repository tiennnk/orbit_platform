from django.db import models

from apps.shared.exceptions import ConflictError, NotFoundError, UnavailableError


class RideStatus(models.TextChoices):
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


ACTIVE_RIDE_STATUSES = (RideStatus.ASSIGNED, RideStatus.IN_PROGRESS)


class RideRole(models.TextChoices):
    RIDER = "rider"
    DRIVER = "driver"


class InvalidRideTransition(ConflictError):
    pass


class RideNotFound(NotFoundError):
    pass


class RiderHasActiveRide(ConflictError):
    pass


class NoDriverAvailable(UnavailableError):
    pass
