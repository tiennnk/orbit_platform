import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.drivers.domain import Availability
from apps.drivers.models import Driver, DriverLocation
from apps.rides.models import Ride
from apps.shared.domain import ApprovalStatus

USERNAME_PREFIX = "seed_driver_"
CENTER_LAT, CENTER_LNG = 10.7769, 106.7009
SPREAD_DEG = 0.25
BATCH_SIZE = 2000


class Command(BaseCommand):
    help = "Create fake drivers with locations around Ho Chi Minh City"

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=200)
        parser.add_argument("--seed", type=int, default=42)
        parser.add_argument("--clear", action="store_true")

    def handle(self, *args, count: int, seed: int, clear: bool, **options):
        rng = random.Random(seed)
        User = get_user_model()
        now = timezone.now()

        if clear:
            with transaction.atomic():
                deleted = self._delete_previous(User)
            self.stdout.write(self.style.SUCCESS(f"Deleted {deleted} seeded drivers"))
            return

        with transaction.atomic():
            self._delete_previous(User)

            password = make_password(None)
            users = User.objects.bulk_create(
                [
                    User(username=f"{USERNAME_PREFIX}{i}", password=password)
                    for i in range(count)
                ],
                batch_size=BATCH_SIZE,
            )

            drivers = Driver.objects.bulk_create(
                [self._make_driver(rng, user, i) for i, user in enumerate(users)],
                batch_size=BATCH_SIZE,
            )

            DriverLocation.objects.bulk_create(
                [
                    DriverLocation(
                        driver=driver,
                        latitude=CENTER_LAT + rng.uniform(-SPREAD_DEG, SPREAD_DEG),
                        longitude=CENTER_LNG + rng.uniform(-SPREAD_DEG, SPREAD_DEG),
                        recorded_at=now,
                    )
                    for driver in drivers
                ],
                batch_size=BATCH_SIZE,
            )

            offline_ids = [d.id for d in drivers if not d.is_online]
            DriverLocation.objects.filter(driver_id__in=offline_ids).update(
                updated_at=now - timedelta(hours=2),
                recorded_at=now - timedelta(hours=2),
            )

        self.stdout.write(self.style.SUCCESS(f"Seeded {count} drivers"))

    def _delete_previous(self, User) -> int:
        seeded = User.objects.filter(username__startswith=USERNAME_PREFIX)
        drivers = Driver.objects.filter(user__in=seeded)
        Ride.objects.filter(driver__in=drivers).delete()
        deleted = drivers.count()
        drivers.delete()
        seeded.delete()
        return deleted

    def _make_driver(self, rng: random.Random, user, i: int) -> Driver:
        roll = rng.random()
        driver = Driver(
            user=user,
            full_name=f"Seed Driver {i}",
            phone=f"09{i:08d}",
            approval_status=ApprovalStatus.APPROVED,
        )
        if roll < 0.6:
            driver.is_online = True
        elif roll < 0.75:
            driver.is_online = True
            driver.availability = Availability.ON_TRIP
        elif roll < 0.9:
            driver.is_online = False
        else:
            driver.approval_status = ApprovalStatus.PENDING
        return driver
