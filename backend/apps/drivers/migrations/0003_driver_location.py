import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("drivers", "0002_driver_user_and_named_unique"),
    ]

    operations = [
        migrations.CreateModel(
            name="DriverLocation",
            fields=[
                (
                    "driver",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        primary_key=True,
                        related_name="location",
                        serialize=False,
                        to="drivers.driver",
                    ),
                ),
                ("latitude", models.FloatField()),
                ("longitude", models.FloatField()),
                ("recorded_at", models.DateTimeField()),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(
                            ("latitude__gte", -90), ("latitude__lte", 90)
                        ),
                        name="driver_location_valid_latitude",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            ("longitude__gte", -180), ("longitude__lte", 180)
                        ),
                        name="driver_location_valid_longitude",
                    ),
                ],
            },
        ),
    ]
