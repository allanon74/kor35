import uuid

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pilotaggio", "0042_ticket_ruolo_ingegneria"),
    ]

    operations = [
        migrations.CreateModel(
            name="PercorsoVolo",
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
                ("nome", models.CharField(max_length=120)),
                (
                    "distanza_minima",
                    models.PositiveIntegerField(
                        help_text="Distanza minima del viaggio (inclusa).",
                        validators=[django.core.validators.MinValueValidator(1)],
                    ),
                ),
                (
                    "distanza_massima",
                    models.PositiveIntegerField(
                        help_text="Distanza massima del viaggio (inclusa).",
                        validators=[django.core.validators.MinValueValidator(1)],
                    ),
                ),
                ("ordine", models.PositiveIntegerField(default=0)),
                ("attivo", models.BooleanField(db_index=True, default=True)),
            ],
            options={
                "verbose_name": "Percorso di volo",
                "verbose_name_plural": "Percorsi di volo",
                "ordering": ["ordine", "nome"],
            },
        ),
        migrations.AddField(
            model_name="sessionevolo",
            name="percorso",
            field=models.ForeignKey(
                blank=True,
                help_text="Tratta scelta all'avvio. La distanza è estratta dal suo intervallo.",
                null=True,
                on_delete=models.SET_NULL,
                related_name="sessioni",
                to="pilotaggio.percorsovolo",
            ),
        ),
    ]
