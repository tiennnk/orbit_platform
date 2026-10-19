from django.db import models

from apps.shared.exceptions import ConflictError, NotFoundError


class InvalidRestaurantTransition(ConflictError):
    pass


class RestaurantAlreadyExists(ConflictError):
    pass


class RestaurantNotFound(NotFoundError):
    pass


class MenuItemNotFound(NotFoundError):
    pass


class MenuItemNameTaken(ConflictError):
    pass


class OrderStatus(models.TextChoices):
    PLACED = "placed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class OrderNotFound(NotFoundError):
    pass


class InvalidOrderTransition(ConflictError):
    pass


class RestaurantNotAcceptingOrders(ConflictError):
    pass


class InvalidOrder(ConflictError):
    pass
