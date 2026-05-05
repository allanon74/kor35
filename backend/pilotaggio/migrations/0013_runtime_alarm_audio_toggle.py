from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("pilotaggio", "0012_event_direction_field"),
    ]

    operations = [
        migrations.AddField(
            model_name="pilotruntimeconfig",
            name="alarm_audio_enabled",
            field=models.BooleanField(
                default=False,
                help_text="Abilita beep allarme lato console quando ci sono sottosistemi critici con tick attivo.",
            ),
        ),
    ]
