import django.db.models.deletion
import django.db.models.functions.text
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Restaurant',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=120)),
                ('phone', models.CharField(max_length=20)),
                ('address', models.CharField(max_length=255)),
                ('latitude', models.FloatField()),
                ('longitude', models.FloatField()),
                ('approval_status', models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected'), ('suspended', 'Suspended')], default='pending', max_length=20)),
                ('is_open', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('owner', models.ForeignKey(db_index=False, on_delete=django.db.models.deletion.PROTECT, related_name='restaurants', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='MenuItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=120)),
                ('description', models.CharField(blank=True, max_length=500)),
                ('price', models.PositiveIntegerField()),
                ('is_available', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('restaurant', models.ForeignKey(db_index=False, on_delete=django.db.models.deletion.CASCADE, related_name='menu_items', to='food.restaurant')),
            ],
        ),
        migrations.AddIndex(
            model_name='restaurant',
            index=models.Index(fields=['approval_status', 'created_at'], name='restaurant_status_created_idx'),
        ),
        migrations.AddIndex(
            model_name='restaurant',
            index=models.Index(fields=['latitude', 'longitude'], name='restaurant_lat_lng_idx'),
        ),
        migrations.AddConstraint(
            model_name='restaurant',
            constraint=models.UniqueConstraint(fields=('owner',), name='restaurant_one_per_owner'),
        ),
        migrations.AddConstraint(
            model_name='restaurant',
            constraint=models.CheckConstraint(condition=models.Q(('approval_status__in', ['pending', 'approved', 'rejected', 'suspended'])), name='restaurant_valid_approval_status'),
        ),
        migrations.AddConstraint(
            model_name='restaurant',
            constraint=models.CheckConstraint(condition=models.Q(('latitude__gte', -90), ('latitude__lte', 90), ('longitude__gte', -180), ('longitude__lte', 180)), name='restaurant_valid_coordinates'),
        ),
        migrations.AddConstraint(
            model_name='restaurant',
            constraint=models.CheckConstraint(condition=models.Q(('is_open', False), ('approval_status', 'approved'), _connector='OR'), name='restaurant_open_requires_approval'),
        ),
        migrations.AddConstraint(
            model_name='menuitem',
            constraint=models.UniqueConstraint(models.F('restaurant'), django.db.models.functions.text.Lower('name'), name='menu_item_unique_name'),
        ),
        migrations.AddConstraint(
            model_name='menuitem',
            constraint=models.CheckConstraint(condition=models.Q(('price__gt', 0), ('price__lte', 10000000)), name='menu_item_price_in_range'),
        ),
    ]
