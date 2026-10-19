import django.db.models.expressions
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('drivers', '0005_driver_status_created_idx'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='driver',
            name='rating_count',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='driver',
            name='rating_total',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddConstraint(
            model_name='driver',
            constraint=models.CheckConstraint(condition=models.Q(('rating_total__gte', django.db.models.expressions.CombinedExpression(models.F('rating_count'), '*', models.Value(1))), ('rating_total__lte', django.db.models.expressions.CombinedExpression(models.F('rating_count'), '*', models.Value(5)))), name='driver_rating_total_in_range'),
        ),
    ]
