import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("drivers", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="driver",
            name="user",
            field=models.ForeignKey(
                db_index=False,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="driver_profiles",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="driver",
            name="phone",
            field=models.CharField(max_length=20),
        ),
        migrations.AddConstraint(
            model_name="driver",
            constraint=models.UniqueConstraint(
                fields=("phone",), name="driver_unique_phone"
            ),
        ),
        migrations.AddConstraint(
            model_name="driver",
            constraint=models.UniqueConstraint(
                fields=("user",), name="driver_unique_user"
            ),
        ),
    ]
