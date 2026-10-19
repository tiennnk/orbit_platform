from datetime import datetime, timedelta

from django.contrib.auth.models import AbstractBaseUser
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.drivers.models import Driver
from apps.drivers.selectors import find_nearby_drivers
from apps.rides.domain import (
    RATING_WINDOW,
    RIDER_ACTIVE_STATUSES,
    InvalidRideTransition,
    NoDriverAvailable,
    OfferNoLongerAvailable,
    OfferNotFound,
    OfferStatus,
    RideAlreadyRated,
    RideNotFound,
    RideNotRatable,
    RiderHasActiveRide,
    RideService,
    RideStatus,
)
from apps.rides.models import (
    DRIVER_PENDING_OFFER_CONSTRAINT,
    RIDER_ACTIVE_RIDE_CONSTRAINT,
    Ride,
    RideOffer,
    RideRating,
)
from apps.rides.pricing import estimate_fare, estimate_road_distance_km
from apps.rides.selectors import get_current_ride
from apps.shared.db import violated_constraint
from apps.shared.geo import haversine_km

DISPATCH_RADIUS_KM = 5.0
DISPATCH_CANDIDATES = 10
OFFER_TTL = timedelta(seconds=15)
SEARCH_TIMEOUT = timedelta(minutes=2)


def _own_driver_ids(user_id: int) -> frozenset[int]:
    return frozenset(
        Driver.objects.filter(user_id=user_id).values_list("id", flat=True)
    )


def _drivers_with_pending_offer() -> frozenset[int]:
    return frozenset(
        RideOffer.objects.filter(status=OfferStatus.PENDING).values_list(
            "driver_id", flat=True
        )
    )


def request_ride(
    *,
    rider: AbstractBaseUser,
    pickup_latitude: float,
    pickup_longitude: float,
    dropoff_latitude: float,
    dropoff_longitude: float,
) -> Ride:
    if Ride.objects.filter(
        rider=rider, status__in=RIDER_ACTIVE_STATUSES, service=RideService.RIDE
    ).exists():
        raise RiderHasActiveRide("You already have an active ride.")

    candidates = find_nearby_drivers(
        latitude=pickup_latitude,
        longitude=pickup_longitude,
        radius_km=DISPATCH_RADIUS_KM,
        limit=1,
        exclude_driver_ids=_own_driver_ids(rider.pk) | _drivers_with_pending_offer(),
    )
    if not candidates:
        raise NoDriverAvailable("No driver is available near the pickup point.")

    try:
        with transaction.atomic():
            ride = _create_ride(
                rider=rider,
                service=RideService.RIDE,
                pickup=(pickup_latitude, pickup_longitude),
                dropoff=(dropoff_latitude, dropoff_longitude),
            )
    except IntegrityError as exc:
        if violated_constraint(exc) == RIDER_ACTIVE_RIDE_CONSTRAINT:
            raise RiderHasActiveRide("You already have an active ride.") from exc
        raise

    return advance_dispatch(ride_id=ride.id)


def estimate_trip(
    *, pickup: tuple[float, float], dropoff: tuple[float, float]
) -> tuple[float, int]:
    distance_km = estimate_road_distance_km(haversine_km(*pickup, *dropoff))
    return round(distance_km, 3), estimate_fare(distance_km=distance_km)


def _create_ride(
    *,
    rider: AbstractBaseUser,
    service: str,
    pickup: tuple[float, float],
    dropoff: tuple[float, float],
    pickup_label: str = "",
    dropoff_label: str = "",
) -> Ride:
    distance_km, fare = estimate_trip(pickup=pickup, dropoff=dropoff)
    return Ride.objects.create(
        rider=rider,
        service=service,
        pickup_latitude=pickup[0],
        pickup_longitude=pickup[1],
        dropoff_latitude=dropoff[0],
        dropoff_longitude=dropoff[1],
        pickup_label=pickup_label[:255],
        dropoff_label=dropoff_label[:255],
        estimated_distance_km=distance_km,
        estimated_fare=fare,
    )


def request_delivery(
    *,
    customer: AbstractBaseUser,
    pickup: tuple[float, float],
    dropoff: tuple[float, float],
    pickup_label: str,
    dropoff_label: str,
) -> Ride:
    return _create_ride(
        rider=customer,
        service=RideService.FOOD,
        pickup=pickup,
        dropoff=dropoff,
        pickup_label=pickup_label,
        dropoff_label=dropoff_label,
    )


def advance_dispatch(*, ride_id: int, now: datetime | None = None) -> Ride:
    now = now or timezone.now()
    with transaction.atomic():
        ride = Ride.objects.select_for_update().get(pk=ride_id)
        if ride.status != RideStatus.SEARCHING:
            return ride

        pending = (
            RideOffer.objects.select_for_update()
            .filter(ride=ride, status=OfferStatus.PENDING)
            .first()
        )
        if pending is not None:
            if not pending.is_expired(now):
                return ride
            pending.expire(now)
            pending.save(update_fields=["status", "responded_at"])

        if (
            now - ride.created_at >= SEARCH_TIMEOUT
            or _offer_next_driver(ride, now) is None
        ):
            ride.give_up()
            ride.save(update_fields=["status", "updated_at"])

    return ride


def _offer_next_driver(ride: Ride, now: datetime) -> RideOffer | None:
    tried = frozenset(ride.offers.values_list("driver_id", flat=True))
    candidates = find_nearby_drivers(
        latitude=ride.pickup_latitude,
        longitude=ride.pickup_longitude,
        radius_km=DISPATCH_RADIUS_KM,
        limit=DISPATCH_CANDIDATES,
        exclude_driver_ids=tried
        | _own_driver_ids(ride.rider_id)
        | _drivers_with_pending_offer(),
    )

    for candidate in candidates:
        try:
            with transaction.atomic():
                driver = (
                    Driver.objects.select_for_update(skip_locked=True)
                    .filter(pk=candidate.driver.id)
                    .first()
                )
                if driver is None or not driver.can_accept_ride():
                    continue
                return RideOffer.objects.create(
                    ride=ride, driver=driver, expires_at=now + OFFER_TTL
                )
        except IntegrityError as exc:
            if violated_constraint(exc) == DRIVER_PENDING_OFFER_CONSTRAINT:
                continue
            raise

    return None


def refresh_current_ride(*, user: AbstractBaseUser) -> Ride:
    ride = get_current_ride(user=user)
    if ride.status == RideStatus.SEARCHING:
        ride = advance_dispatch(ride_id=ride.id)
    return ride


def _driver_offer(offer_id: int, user: AbstractBaseUser) -> RideOffer:
    try:
        return RideOffer.objects.get(pk=offer_id, driver__user=user)
    except RideOffer.DoesNotExist as exc:
        raise OfferNotFound(f"Offer {offer_id} not found.") from exc


def get_current_offer(*, user: AbstractBaseUser) -> RideOffer:
    offer = (
        RideOffer.objects.select_related("ride")
        .filter(driver__user=user, status=OfferStatus.PENDING)
        .first()
    )
    if offer is None:
        raise OfferNotFound("You have no pending offer.")
    if offer.is_expired(timezone.now()):
        advance_dispatch(ride_id=offer.ride_id)
        raise OfferNotFound("You have no pending offer.")
    return offer


def accept_offer(*, offer_id: int, user: AbstractBaseUser) -> Ride:
    now = timezone.now()
    offer = _driver_offer(offer_id, user)
    with transaction.atomic():
        ride = Ride.objects.select_for_update().get(pk=offer.ride_id)
        driver = Driver.objects.select_for_update().get(pk=offer.driver_id)
        offer = RideOffer.objects.select_for_update().get(pk=offer.pk)

        if (
            offer.status != OfferStatus.PENDING
            or offer.is_expired(now)
            or ride.status != RideStatus.SEARCHING
        ):
            raise OfferNoLongerAvailable("This offer is no longer available.")
        if not driver.can_accept_ride():
            raise OfferNoLongerAvailable("You cannot take rides right now.")

        offer.accept(now)
        offer.save(update_fields=["status", "responded_at"])
        driver.start_trip()
        driver.save(update_fields=["availability", "updated_at"])
        ride.assign(driver, now)
        ride.save(update_fields=["status", "driver", "assigned_at", "updated_at"])

    return ride


def decline_offer(*, offer_id: int, user: AbstractBaseUser) -> None:
    now = timezone.now()
    offer = _driver_offer(offer_id, user)
    with transaction.atomic():
        Ride.objects.select_for_update().get(pk=offer.ride_id)
        offer = RideOffer.objects.select_for_update().get(pk=offer.pk)
        if offer.status != OfferStatus.PENDING:
            raise OfferNoLongerAvailable("This offer is no longer available.")
        offer.decline(now)
        offer.save(update_fields=["status", "responded_at"])

    advance_dispatch(ride_id=offer.ride_id)


def _get_ride_for_update(ride_id: int) -> Ride:
    try:
        return (
            Ride.objects.select_for_update(of=("self",))
            .select_related("driver")
            .get(pk=ride_id)
        )
    except Ride.DoesNotExist as exc:
        raise RideNotFound(f"Ride {ride_id} not found.") from exc


def _release_driver(driver_id: int) -> None:
    driver = Driver.objects.select_for_update().get(pk=driver_id)
    driver.finish_trip()
    driver.save(update_fields=["availability", "updated_at"])


def _ensure_driver_of(ride: Ride, user: AbstractBaseUser) -> None:
    if ride.driver is None or ride.driver.user_id != user.pk:
        raise RideNotFound(f"Ride {ride.pk} not found.")


def start_ride(*, ride_id: int, user: AbstractBaseUser) -> Ride:
    with transaction.atomic():
        ride = _get_ride_for_update(ride_id)
        _ensure_driver_of(ride, user)

        ride.start(timezone.now())
        ride.save(update_fields=["status", "started_at", "updated_at"])

    return ride


def complete_ride(*, ride_id: int, user: AbstractBaseUser) -> Ride:
    with transaction.atomic():
        ride = _get_ride_for_update(ride_id)
        _ensure_driver_of(ride, user)

        ride.complete(timezone.now())
        ride.save(update_fields=["status", "completed_at", "updated_at"])
        _release_driver(ride.driver_id)

    return ride


def cancel_ride(*, ride_id: int, user: AbstractBaseUser) -> Ride:
    now = timezone.now()
    with transaction.atomic():
        ride = _get_ride_for_update(ride_id)
        if ride.rider_id != user.pk:
            raise RideNotFound(f"Ride {ride_id} not found.")
        if ride.service != RideService.RIDE:
            raise InvalidRideTransition("Deliveries are managed through the order.")

        had_driver = ride.status == RideStatus.ASSIGNED
        ride.cancel(now)
        ride.save(update_fields=["status", "cancelled_at", "updated_at"])

        RideOffer.objects.filter(ride=ride, status=OfferStatus.PENDING).update(
            status=OfferStatus.EXPIRED, responded_at=now
        )
        if had_driver:
            _release_driver(ride.driver_id)

    return ride


def rate_ride(
    *, ride_id: int, user: AbstractBaseUser, score: int, comment: str = ""
) -> RideRating:
    now = timezone.now()
    with transaction.atomic():
        ride = Ride.objects.select_for_update().filter(pk=ride_id, rider=user).first()
        if ride is None:
            raise RideNotFound(f"Ride {ride_id} not found.")
        if ride.status != RideStatus.COMPLETED:
            raise RideNotRatable("Only completed rides can be rated.")
        if now - ride.completed_at > RATING_WINDOW:
            raise RideNotRatable("The time to rate this ride has passed.")
        if RideRating.objects.filter(ride=ride).exists():
            raise RideAlreadyRated("You already rated this ride.")

        rating = RideRating.objects.create(
            ride=ride, driver_id=ride.driver_id, score=score, comment=comment
        )
        driver = Driver.objects.select_for_update().get(pk=ride.driver_id)
        driver.add_rating(score)
        driver.save(update_fields=["rating_count", "rating_total", "updated_at"])

    return rating
