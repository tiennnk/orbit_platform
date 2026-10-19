import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('drivers', '0005_driver_status_created_idx'),
        ('rides', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='RideOffer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('accepted', 'Accepted'), ('declined', 'Declined'), ('expired', 'Expired')], default='pending', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('expires_at', models.DateTimeField()),
                ('responded_at', models.DateTimeField(blank=True, null=True)),
            ],
        ),
        migrations.RemoveConstraint(
            model_name='ride',
            name='ride_valid_status',
        ),
        migrations.RemoveConstraint(
            model_name='ride',
            name='ride_started_at_matches_status',
        ),
        migrations.RemoveConstraint(
            model_name='ride',
            name='ride_one_active_per_rider',
        ),
        migrations.AddField(
            model_name='ride',
            name='assigned_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='ride',
            name='driver',
            field=models.ForeignKey(blank=True, db_index=False, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='rides', to='drivers.driver'),
        ),
        migrations.AlterField(
            model_name='ride',
            name='status',
            field=models.CharField(choices=[('searching', 'Searching'), ('assigned', 'Assigned'), ('in_progress', 'In Progress'), ('completed', 'Completed'), ('cancelled', 'Cancelled'), ('no_driver', 'No Driver')], default='searching', max_length=20),
        ),
        migrations.AddConstraint(
            model_name='ride',
            constraint=models.CheckConstraint(condition=models.Q(('status__in', ['searching', 'assigned', 'in_progress', 'completed', 'cancelled', 'no_driver'])), name='ride_valid_status'),
        ),
        migrations.RunSQL(
            "UPDATE rides_ride SET assigned_at = created_at "
            "WHERE driver_id IS NOT NULL AND assigned_at IS NULL",
            migrations.RunSQL.noop,
        ),
        migrations.AddConstraint(
            model_name='ride',
            constraint=models.CheckConstraint(condition=models.Q(models.Q(('status__in', ('assigned', 'in_progress', 'completed')), _negated=True), models.Q(('assigned_at__isnull', False), ('driver__isnull', False)), _connector='OR'), name='ride_driver_set_once_assigned'),
        ),
        migrations.AddConstraint(
            model_name='ride',
            constraint=models.CheckConstraint(condition=models.Q(models.Q(('started_at__isnull', False), ('status__in', ['in_progress', 'completed'])), models.Q(models.Q(('status__in', ['in_progress', 'completed']), _negated=True), ('started_at__isnull', True)), _connector='OR'), name='ride_started_at_matches_status'),
        ),
        migrations.AddConstraint(
            model_name='ride',
            constraint=models.UniqueConstraint(condition=models.Q(('status__in', ('searching', 'assigned', 'in_progress'))), fields=('rider',), name='ride_one_active_per_rider'),
        ),
        migrations.AddField(
            model_name='rideoffer',
            name='driver',
            field=models.ForeignKey(db_index=False, on_delete=django.db.models.deletion.CASCADE, related_name='ride_offers', to='drivers.driver'),
        ),
        migrations.AddField(
            model_name='rideoffer',
            name='ride',
            field=models.ForeignKey(db_index=False, on_delete=django.db.models.deletion.CASCADE, related_name='offers', to='rides.ride'),
        ),
        migrations.AddIndex(
            model_name='rideoffer',
            index=models.Index(fields=['ride', 'created_at'], name='offer_ride_idx'),
        ),
        migrations.AddIndex(
            model_name='rideoffer',
            index=models.Index(fields=['driver', '-created_at'], name='offer_driver_idx'),
        ),
        migrations.AddConstraint(
            model_name='rideoffer',
            constraint=models.CheckConstraint(condition=models.Q(('status__in', ['pending', 'accepted', 'declined', 'expired'])), name='offer_valid_status'),
        ),
        migrations.AddConstraint(
            model_name='rideoffer',
            constraint=models.CheckConstraint(condition=models.Q(('expires_at__gt', models.F('created_at'))), name='offer_expires_after_created'),
        ),
        migrations.AddConstraint(
            model_name='rideoffer',
            constraint=models.UniqueConstraint(fields=('ride', 'driver'), name='offer_once_per_driver_per_ride'),
        ),
        migrations.AddConstraint(
            model_name='rideoffer',
            constraint=models.UniqueConstraint(condition=models.Q(('status', 'pending')), fields=('ride',), name='offer_one_pending_per_ride'),
        ),
        migrations.AddConstraint(
            model_name='rideoffer',
            constraint=models.UniqueConstraint(condition=models.Q(('status', 'pending')), fields=('driver',), name='offer_one_pending_per_driver'),
        ),
    ]
