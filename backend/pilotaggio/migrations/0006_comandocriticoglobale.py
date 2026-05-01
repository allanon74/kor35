# Generated manually

import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pilotaggio", "0005_statoallertapilot"),
    ]

    operations = [
        migrations.CreateModel(
            name="ComandoCriticoGlobale",
            fields=[
                (
                    "sync_id",
                    models.UUIDField(
                        db_index=True, default=uuid.uuid4, editable=False, unique=True
                    ),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "pattern",
                    models.CharField(
                        help_text='Es. "XX9", "ML(4-9)", "_Z3"',
                        max_length=48,
                    ),
                ),
                ("nome", models.CharField(blank=True, default="", max_length=120)),
                ("attivo", models.BooleanField(db_index=True, default=True)),
            ],
            options={
                "verbose_name": "Comando critico globale",
                "verbose_name_plural": "Comandi critici globali",
                "ordering": ["nome", "pattern"],
            },
        ),
    ]
