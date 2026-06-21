from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pilotaggio", "0025_evento_scadenza_critica"),
    ]

    operations = [
        migrations.AddField(
            model_name="sessionevolo",
            name="ultimo_tick_motore_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
                help_text="Timestamp dell'ultimo tick motore applicato (throttle poll API / worker).",
            ),
        ),
    ]
