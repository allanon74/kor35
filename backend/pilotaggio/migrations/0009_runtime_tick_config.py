from django.db import migrations, models


def create_runtime_singleton(apps, schema_editor):
    Model = apps.get_model("pilotaggio", "PilotRuntimeConfig")
    Model.objects.get_or_create(singleton_id=1, defaults={"tick_enabled": False, "tick_interval_secondi": 5.0})


class Migration(migrations.Migration):
    dependencies = [
        ("pilotaggio", "0008_event_rules_and_seed_defaults"),
    ]

    operations = [
        migrations.CreateModel(
            name="PilotRuntimeConfig",
            fields=[
                ("singleton_id", models.PositiveSmallIntegerField(default=1, editable=False, primary_key=True, serialize=False)),
                ("tick_enabled", models.BooleanField(default=False)),
                ("tick_interval_secondi", models.FloatField(default=5.0)),
                ("tick_last_heartbeat", models.DateTimeField(blank=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Runtime pilotaggio",
                "verbose_name_plural": "Runtime pilotaggio",
            },
        ),
        migrations.RunPython(create_runtime_singleton, migrations.RunPython.noop),
    ]
