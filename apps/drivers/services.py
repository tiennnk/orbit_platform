from datetime import datetime

from django.contrib.auth.models import AbstractBaseUser
from django.db import IntegrityError, transaction

from apps.drivers.domain import DriverAlreadyExists, DriverNotFound, DriverNotOnline
from apps.drivers.models import (
    PHONE_UNIQUE_CONSTRAINT,
    USER_UNIQUE_CONSTRAINT,
    Driver,
    DriverLocation,
)


def _violated_constraint(exc: IntegrityError) -> str | None:
    diag = getattr(exc.__cause__, "diag", None)
    return getattr(diag, "constraint_name", None)


def register_driver(*, user: AbstractBaseUser, full_name: str, phone: str) -> Driver:
    full_name = full_name.strip()
    phone = phone.strip()

    try:
        with transaction.atomic():
            return Driver.objects.create(user=user, full_name=full_name, phone=phone)
    except IntegrityError as exc:
        constraint = _violated_constraint(exc)
        if constraint == PHONE_UNIQUE_CONSTRAINT:
            raise DriverAlreadyExists(
                f"Driver with phone {phone} already exists."
            ) from exc
        if constraint == USER_UNIQUE_CONSTRAINT:
            raise DriverAlreadyExists(
                "This account already has a driver profile."
            ) from exc
        raise


def _get_driver_for_update(driver_id: int) -> Driver:
    try:
        return Driver.objects.select_for_update().get(pk=driver_id)
    except Driver.DoesNotExist as exc:
        raise DriverNotFound(f"Driver {driver_id} not found.") from exc


def approve_driver(*, driver_id: int) -> Driver:
    with transaction.atomic():
        driver = _get_driver_for_update(driver_id)
        driver.approve()
        driver.save(update_fields=["approval_status", "updated_at"])

    return driver


def go_online(*, driver_id: int) -> Driver:
    with transaction.atomic():
        driver = _get_driver_for_update(driver_id)
        driver.go_online()
        driver.save(update_fields=["is_online", "updated_at"])

    return driver


def go_offline(*, driver_id: int) -> Driver:
    with transaction.atomic():
        driver = _get_driver_for_update(driver_id)
        driver.go_offline()
        driver.save(update_fields=["is_online", "updated_at"])

    return driver


def update_location(
    *, driver: Driver, latitude: float, longitude: float, recorded_at: datetime
) -> DriverLocation:
    if not driver.is_online:
        raise DriverNotOnline("Driver must be online to report location.")

    with transaction.atomic():
        location, created = DriverLocation.objects.select_for_update().get_or_create(
            driver=driver,
            defaults={
                "latitude": latitude,
                "longitude": longitude,
                "recorded_at": recorded_at,
            },
        )
        if created or recorded_at <= location.recorded_at:
            return location

        location.latitude = latitude
        location.longitude = longitude
        location.recorded_at = recorded_at
        location.save(
            update_fields=["latitude", "longitude", "recorded_at", "updated_at"]
        )

    return location
