# Allineamento al modello attuale: user_agent con blank=True senza default stringa vuota obbligatoria.
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("webpush", "0005_auto_20230614_1529"),
    ]

    operations = [
        migrations.AlterField(
            model_name="subscriptioninfo",
            name="user_agent",
            field=models.CharField(blank=True, max_length=500),
        ),
    ]
