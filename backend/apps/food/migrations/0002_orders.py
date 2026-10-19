import django.db.models.deletion
import django.db.models.expressions
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('food', '0001_initial'),
        ('rides', '0004_ride_service'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='FoodOrder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('placed', 'Placed'), ('accepted', 'Accepted'), ('rejected', 'Rejected'), ('cancelled', 'Cancelled')], default='placed', max_length=20)),
                ('delivery_latitude', models.FloatField()),
                ('delivery_longitude', models.FloatField()),
                ('delivery_address', models.CharField(blank=True, max_length=255)),
                ('note', models.CharField(blank=True, max_length=300)),
                ('subtotal', models.PositiveIntegerField()),
                ('delivery_fee', models.PositiveIntegerField()),
                ('total', models.PositiveIntegerField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('accepted_at', models.DateTimeField(blank=True, null=True)),
                ('closed_at', models.DateTimeField(blank=True, null=True)),
                ('customer', models.ForeignKey(db_index=False, on_delete=django.db.models.deletion.PROTECT, related_name='food_orders', to=settings.AUTH_USER_MODEL)),
                ('delivery', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='food_order', to='rides.ride')),
                ('restaurant', models.ForeignKey(db_index=False, on_delete=django.db.models.deletion.PROTECT, related_name='orders', to='food.restaurant')),
            ],
        ),
        migrations.CreateModel(
            name='OrderLine',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=120)),
                ('unit_price', models.PositiveIntegerField()),
                ('quantity', models.PositiveSmallIntegerField()),
                ('menu_item', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='order_lines', to='food.menuitem')),
                ('order', models.ForeignKey(db_index=False, on_delete=django.db.models.deletion.CASCADE, related_name='lines', to='food.foodorder')),
            ],
        ),
        migrations.AddIndex(
            model_name='foodorder',
            index=models.Index(fields=['customer', '-created_at'], name='order_customer_recent_idx'),
        ),
        migrations.AddIndex(
            model_name='foodorder',
            index=models.Index(fields=['restaurant', 'status', '-created_at'], name='order_restaurant_status_idx'),
        ),
        migrations.AddConstraint(
            model_name='foodorder',
            constraint=models.CheckConstraint(condition=models.Q(('status__in', ['placed', 'accepted', 'rejected', 'cancelled'])), name='order_valid_status'),
        ),
        migrations.AddConstraint(
            model_name='foodorder',
            constraint=models.CheckConstraint(condition=models.Q(('subtotal__gt', 0), ('total', django.db.models.expressions.CombinedExpression(models.F('subtotal'), '+', models.F('delivery_fee')))), name='order_total_adds_up'),
        ),
        migrations.AddConstraint(
            model_name='foodorder',
            constraint=models.CheckConstraint(condition=models.Q(('delivery_latitude__gte', -90), ('delivery_latitude__lte', 90), ('delivery_longitude__gte', -180), ('delivery_longitude__lte', 180)), name='order_valid_coordinates'),
        ),
        migrations.AddConstraint(
            model_name='foodorder',
            constraint=models.CheckConstraint(condition=models.Q(('delivery__isnull', True), ('status', 'accepted'), _connector='OR'), name='order_delivery_requires_acceptance'),
        ),
        migrations.AddConstraint(
            model_name='foodorder',
            constraint=models.CheckConstraint(condition=models.Q(models.Q(('accepted_at__isnull', False), ('status', 'accepted')), models.Q(models.Q(('status', 'accepted'), _negated=True), ('accepted_at__isnull', True)), _connector='OR'), name='order_accepted_at_matches_status'),
        ),
        migrations.AddConstraint(
            model_name='foodorder',
            constraint=models.CheckConstraint(condition=models.Q(models.Q(('closed_at__isnull', False), ('status__in', ['rejected', 'cancelled'])), models.Q(('status__in', ['placed', 'accepted']), ('closed_at__isnull', True)), _connector='OR'), name='order_closed_at_matches_status'),
        ),
        migrations.AddConstraint(
            model_name='orderline',
            constraint=models.UniqueConstraint(fields=('order', 'menu_item'), name='order_line_unique_item'),
        ),
        migrations.AddConstraint(
            model_name='orderline',
            constraint=models.CheckConstraint(condition=models.Q(('quantity__gte', 1), ('quantity__lte', 20)), name='order_line_quantity_in_range'),
        ),
        migrations.AddConstraint(
            model_name='orderline',
            constraint=models.CheckConstraint(condition=models.Q(('unit_price__gt', 0)), name='order_line_positive_price'),
        ),
    ]
