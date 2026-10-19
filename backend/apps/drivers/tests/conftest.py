import pytest

from apps.drivers.models import Driver
from apps.drivers.services import approve_driver, go_online, register_driver


@pytest.fixture
def driver(user) -> Driver:
    return register_driver(user=user, full_name="Nguyen Van A", phone="0901234567")


@pytest.fixture
def online_driver(driver) -> Driver:
    approve_driver(driver_id=driver.id)
    return go_online(driver_id=driver.id)
