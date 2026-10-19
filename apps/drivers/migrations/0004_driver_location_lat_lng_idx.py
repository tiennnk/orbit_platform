from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('drivers', '0003_driver_location'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='driverlocation',
            index=models.Index(fields=['latitude', 'longitude'], name='driver_location_lat_lng_idx'),
        ),
    ]
