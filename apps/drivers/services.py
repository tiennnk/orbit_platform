from django.db import IntegrityError, transaction

from apps.drivers.domain import DriverAlreadyExists, DriverNotFound
from apps.drivers.models import Driver


def register_driver(*, full_name: str, phone: str) -> Driver:
    full_name = full_name.strip()
    phone = phone.strip()

    try:
        with transaction.atomic():
            return Driver.objects.create(full_name=full_name, phone=phone)
    except IntegrityError as exc:
        raise DriverAlreadyExists(
            f"Driver with phone {phone} already exists."
        ) from exc


def approve_driver(*, driver_id: int) -> Driver:
    with transaction.atomic():
        try:
            driver = Driver.objects.select_for_update().get(pk=driver_id)
        except Driver.DoesNotExist as exc:
            raise DriverNotFound(f"Driver {driver_id} not found.") from exc

        driver.approve()
        driver.save(update_fields=["approval_status", "updated_at"])

    return driver
