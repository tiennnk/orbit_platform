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
from apps.shared.db import violated_constraint


def register_driver(*, user: AbstractBaseUser, full_name: str, phone: str) -> Driver:
    full_name = full_name.strip()
    phone = phone.strip()

    try:
        with transaction.atomic():
            return Driver.objects.create(user=user, full_name=full_name, phone=phone)
    except IntegrityError as exc:
        constraint = violated_constraint(exc)
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


def reject_driver(*, driver_id: int) -> Driver:
    with transaction.atomic():
        driver = _get_driver_for_update(driver_id)
        driver.reject()
        driver.save(update_fields=["approval_status", "updated_at"])

    return driver


def suspend_driver(*, driver_id: int) -> Driver:
    with transaction.atomic():
        driver = _get_driver_for_update(driver_id)
        driver.suspend()
        driver.save(update_fields=["approval_status", "is_online", "updated_at"])

    return driver


def reinstate_driver(*, driver_id: int) -> Driver:
    with transaction.atomic():
        driver = _get_driver_for_update(driver_id)
        driver.reinstate()
        driver.save(update_fields=["approval_status", "updated_at"])

    return driver


def update_driver_profile(*, driver_id: int, full_name: str, phone: str) -> Driver:
    full_name = full_name.strip()
    phone = phone.strip()

    try:
        with transaction.atomic():
            driver = _get_driver_for_update(driver_id)
            driver.update_profile(full_name=full_name, phone=phone)
            driver.save(
                update_fields=["full_name", "phone", "approval_status", "updated_at"]
            )
    except IntegrityError as exc:
        if violated_constraint(exc) == PHONE_UNIQUE_CONSTRAINT:
            raise DriverAlreadyExists(
                f"Driver with phone {phone} already exists."
            ) from exc
        raise

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
