from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("pilotaggio", "0009_runtime_tick_config"),
    ]

    operations = [
        migrations.AddField(
            model_name="pilotruntimeconfig",
            name="login_required_console",
            field=models.BooleanField(
                default=False,
                help_text="Se attivo, la console richiede login ticket/QR. Default disattivo (utile in dev).",
            ),
        ),
    ]
