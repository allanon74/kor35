import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0227_espansioni_carte"),
    ]

    operations = [
        migrations.CreateModel(
            name="KeywordCarta",
            fields=[
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("codice", models.CharField(db_index=True, help_text="Identificatore univoco per campagna, es. EVOCAZIONE", max_length=40)),
                ("nome", models.CharField(help_text="Forma visualizzata nel testo (es. Evocazione).", max_length=80)),
                ("testo_regola", models.TextField(help_text="Testo completo mostrato al tap/click.")),
                (
                    "reminder_breve",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text="Promemoria inline tra parentesi, se c'è spazio.",
                        max_length=120,
                    ),
                ),
                (
                    "priorita",
                    models.PositiveSmallIntegerField(
                        default=0,
                        help_text="Priorità match (più alto = preferito su overlap).",
                    ),
                ),
                ("attiva", models.BooleanField(db_index=True, default=True)),
                (
                    "campagna",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="keyword_carte",
                        to="personaggi.campagna",
                    ),
                ),
            ],
            options={
                "verbose_name": "Keyword carta",
                "verbose_name_plural": "Keyword carte",
                "ordering": ["-priorita", "nome"],
                "unique_together": {("campagna", "codice")},
            },
        ),
    ]
