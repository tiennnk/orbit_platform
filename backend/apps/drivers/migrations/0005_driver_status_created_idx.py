from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('drivers', '0004_driver_location_lat_lng_idx'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddIndex(
            model_name='driver',
            index=models.Index(fields=['approval_status', 'created_at'], name='driver_status_created_idx'),
        ),
    ]
