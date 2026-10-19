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


def test_pending_driver_can_be_rejected():
    driver = make_driver()
    driver.reject()
    assert driver.approval_status == ApprovalStatus.REJECTED


def test_approved_driver_cannot_be_rejected():
    driver = make_driver()
    driver.approve()
    with pytest.raises(InvalidStateTransition):
        driver.reject()


def test_suspend_forces_driver_offline():
    driver = make_online_driver()
    driver.suspend()
    assert driver.approval_status == ApprovalStatus.SUSPENDED
    assert driver.is_online is False
    assert driver.can_accept_ride() is False


def test_cannot_suspend_driver_on_trip():
    driver = make_online_driver()
    driver.start_trip()
    with pytest.raises(InvalidStateTransition):
        driver.suspend()
    assert driver.approval_status == ApprovalStatus.APPROVED


def test_cannot_suspend_pending_driver():
    with pytest.raises(InvalidStateTransition):
        make_driver().suspend()


def test_reinstated_driver_is_approved_but_offline():
    driver = make_online_driver()
    driver.suspend()
    driver.reinstate()
    assert driver.approval_status == ApprovalStatus.APPROVED
    assert driver.is_online is False


def test_reinstate_only_from_suspended():
    with pytest.raises(InvalidStateTransition):
        make_driver().reinstate()


def test_pending_driver_can_edit_profile():
    driver = make_driver()
    driver.update_profile(full_name="New Name", phone="0911111111")
    assert (driver.full_name, driver.phone) == ("New Name", "0911111111")
    assert driver.approval_status == ApprovalStatus.PENDING


def test_rejected_driver_editing_profile_resubmits():
    driver = make_driver()
    driver.reject()
    driver.update_profile(full_name="Fixed Name", phone="0911111111")
    assert driver.approval_status == ApprovalStatus.PENDING


def test_approved_driver_cannot_edit_profile():
    driver = make_driver()
    driver.approve()
    with pytest.raises(InvalidStateTransition):
        driver.update_profile(full_name="X", phone="0911111111")
    assert driver.full_name == "Nguyen Van A"
