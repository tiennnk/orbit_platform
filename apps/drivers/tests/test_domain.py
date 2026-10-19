import pytest

from apps.drivers.domain import ApprovalStatus, Availability, InvalidStateTransition
from apps.drivers.models import Driver


def make_driver() -> Driver:
    return Driver(full_name="Nguyen Van A", phone="0901234567")


def make_online_driver() -> Driver:
    driver = make_driver()
    driver.approve()
    driver.go_online()
    return driver


def test_new_driver_is_pending_offline_and_available():
    driver = make_driver()
    assert driver.approval_status == ApprovalStatus.PENDING
    assert driver.is_online is False
    assert driver.availability == Availability.AVAILABLE


def test_approve_pending_driver():
    driver = make_driver()
    driver.approve()
    assert driver.approval_status == ApprovalStatus.APPROVED


def test_cannot_approve_twice():
    driver = make_driver()
    driver.approve()
    with pytest.raises(InvalidStateTransition):
        driver.approve()


def test_pending_driver_cannot_go_online():
    with pytest.raises(InvalidStateTransition):
        make_driver().go_online()


def test_approved_online_driver_can_accept_ride():
    assert make_online_driver().can_accept_ride() is True


def test_approved_offline_driver_cannot_accept_ride():
    driver = make_driver()
    driver.approve()
    assert driver.can_accept_ride() is False


def test_cannot_start_trip_when_offline():
    driver = make_driver()
    driver.approve()
    with pytest.raises(InvalidStateTransition):
        driver.start_trip()


def test_driver_on_trip_cannot_accept_ride_or_go_offline():
    driver = make_online_driver()
    driver.start_trip()
    assert driver.availability == Availability.ON_TRIP
    assert driver.can_accept_ride() is False
    with pytest.raises(InvalidStateTransition):
        driver.go_offline()


def test_finish_trip_makes_driver_available_again():
    driver = make_online_driver()
    driver.start_trip()
    driver.finish_trip()
    assert driver.can_accept_ride() is True
