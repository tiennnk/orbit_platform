from django.db import models

from apps.shared.exceptions import ConflictError, NotFoundError


class ApprovalStatus(models.TextChoices):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUSPENDED = "suspended"


class Availability(models.TextChoices):
    AVAILABLE = "available"
    ON_TRIP = "on_trip"


class InvalidStateTransition(ConflictError):
    pass


class DriverAlreadyExists(ConflictError):
    pass


class DriverNotFound(NotFoundError):
    pass


class DriverNotOnline(ConflictError):
    pass
