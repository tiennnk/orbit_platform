from django.contrib.auth.models import AbstractBaseUser

from apps.drivers.domain import DriverNotFound
from apps.drivers.models import Driver


def get_driver_by_id(*, driver_id: int) -> Driver:
    try:
        return Driver.objects.get(pk=driver_id)
    except Driver.DoesNotExist as exc:
        raise DriverNotFound(f"Driver {driver_id} not found.") from exc


def get_driver_for_user(*, user: AbstractBaseUser) -> Driver:
    try:
        return Driver.objects.get(user=user)
    except Driver.DoesNotExist as exc:
        raise DriverNotFound("This account has no driver profile.") from exc
