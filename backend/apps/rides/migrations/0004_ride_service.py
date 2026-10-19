from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('drivers', '0006_driver_rating'),
        ('rides', '0003_ride_rating'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='ride',
            name='ride_one_active_per_rider',
        ),
        migrations.AddField(
            model_name='ride',
            name='dropoff_label',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='ride',
            name='pickup_label',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='ride',
            name='service',
            field=models.CharField(choices=[('ride', 'Ride'), ('food', 'Food')], default='ride', max_length=20),
        ),
        migrations.AddConstraint(
            model_name='ride',
            constraint=models.CheckConstraint(condition=models.Q(('service__in', ['ride', 'food'])), name='ride_valid_service'),
        ),
        migrations.AddConstraint(
            model_name='ride',
            constraint=models.UniqueConstraint(condition=models.Q(('service', 'ride'), ('status__in', ('searching', 'assigned', 'in_progress'))), fields=('rider',), name='ride_one_active_per_rider'),
        ),
    ]
