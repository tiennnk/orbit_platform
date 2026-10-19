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
