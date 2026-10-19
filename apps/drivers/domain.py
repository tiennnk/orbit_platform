from django.db import models


class ApprovalStatus(models.TextChoices):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUSPENDED = "suspended"


class Availability(models.TextChoices):
    AVAILABLE = "available"
    ON_TRIP = "on_trip"


class InvalidStateTransition(Exception):
    pass


class DriverAlreadyExists(Exception):
    pass


class DriverNotFound(Exception):
    pass
