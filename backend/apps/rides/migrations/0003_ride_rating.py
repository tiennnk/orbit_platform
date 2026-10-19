import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('drivers', '0006_driver_rating'),
        ('rides', '0002_ride_offers'),
    ]

    operations = [
        migrations.CreateModel(
            name='RideRating',
            fields=[
                ('ride', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, related_name='rating', serialize=False, to='rides.ride')),
                ('score', models.PositiveSmallIntegerField()),
                ('comment', models.TextField(blank=True, max_length=500)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('driver', models.ForeignKey(db_index=False, on_delete=django.db.models.deletion.CASCADE, related_name='ratings', to='drivers.driver')),
            ],
            options={
                'indexes': [models.Index(fields=['driver', '-created_at'], name='rating_driver_idx')],
                'constraints': [models.CheckConstraint(condition=models.Q(('score__gte', 1), ('score__lte', 5)), name='rating_score_in_range')],
            },
        ),
    ]
