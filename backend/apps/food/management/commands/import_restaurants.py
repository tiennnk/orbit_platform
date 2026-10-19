import time
from urllib.error import URLError

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.food import osm
from apps.food.models import MenuItem, Restaurant
from apps.places.services import PlaceSearchUnavailable, reverse_address
from apps.shared.domain import ApprovalStatus

USERNAME_PREFIX = "osm_"
CENTER_LAT, CENTER_LNG = 10.7769, 106.7009
REVERSE_DELAY_SECONDS = 0.5


class Command(BaseCommand):
    help = "Import real restaurants from OpenStreetMap around a point"

    def add_arguments(self, parser):
        parser.add_argument("--latitude", type=float, default=CENTER_LAT)
        parser.add_argument("--longitude", type=float, default=CENTER_LNG)
        parser.add_argument("--radius-km", type=float, default=3.0)
        parser.add_argument("--limit", type=int, default=100)
        parser.add_argument("--skip-reverse", action="store_true")
        parser.add_argument("--clear", action="store_true")

    def handle(self, *args, **options):
        User = get_user_model()

        if options["clear"]:
            with transaction.atomic():
                deleted = self._delete_imported(User)
            self.stdout.write(
                self.style.SUCCESS(f"Deleted {deleted} imported restaurants")
            )
            return

        self.stdout.write("Fetching restaurants from OpenStreetMap...")
        try:
            places = osm.fetch_restaurants(
                latitude=options["latitude"],
                longitude=options["longitude"],
                radius_km=options["radius_km"],
                limit=options["limit"],
            )
        except (URLError, TimeoutError, ValueError) as exc:
            raise CommandError(f"Could not reach Overpass: {exc}") from exc

        created = updated = 0
        password = make_password(None)
        for place in places:
            address = place.address
            if address is None and not options["skip_reverse"]:
                address = self._lookup_address(place)

            with transaction.atomic():
                user, _ = User.objects.get_or_create(
                    username=f"{USERNAME_PREFIX}{place.key}",
                    defaults={"password": password},
                )
                restaurant, is_new = Restaurant.objects.update_or_create(
                    owner=user,
                    defaults={
                        "name": place.name,
                        "phone": place.phone,
                        "address": (address or "")[:255],
                        "latitude": place.latitude,
                        "longitude": place.longitude,
                        "approval_status": ApprovalStatus.APPROVED,
                        "is_open": True,
                    },
                )
                if is_new:
                    MenuItem.objects.bulk_create(
                        MenuItem(restaurant=restaurant, name=name, price=price)
                        for name, price in osm.MENUS[place.kind]
                    )
            created += is_new
            updated += not is_new

        self.stdout.write(
            self.style.SUCCESS(
                f"Imported {len(places)} restaurants ({created} new, {updated} updated)"
            )
        )

    def _lookup_address(self, place: osm.OsmRestaurant) -> str | None:
        time.sleep(REVERSE_DELAY_SECONDS)
        try:
            return reverse_address(latitude=place.latitude, longitude=place.longitude)
        except PlaceSearchUnavailable:
            return None

    def _delete_imported(self, User) -> int:
        imported = User.objects.filter(username__startswith=USERNAME_PREFIX)
        restaurants = Restaurant.objects.filter(owner__in=imported)
        deleted = restaurants.count()
        restaurants.delete()
        imported.delete()
        return deleted
