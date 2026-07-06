import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0237_offerta_scambio_dettaglio"),
    ]

    operations = [
        migrations.CreateModel(
            name="TagCarta",
            fields=[
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "codice",
                    models.CharField(
                        db_index=True,
                        help_text="Identificatore univoco per campagna, es. CAVALIERE",
                        max_length=40,
                    ),
                ),
                ("nome", models.CharField(help_text="Nome mostrato, es. Cavaliere", max_length=80)),
                (
                    "descrizione",
                    models.TextField(
                        blank=True,
                        default="",
                        help_text="Spiegazione per staff / glossario.",
                    ),
                ),
                (
                    "colore",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text="Colore UI opzionale (#RRGGBB).",
                        max_length=7,
                    ),
                ),
                ("attiva", models.BooleanField(db_index=True, default=True)),
                (
                    "campagna",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="tag_carte",
                        to="personaggi.campagna",
                    ),
                ),
            ],
            options={
                "verbose_name": "Tag carta",
                "verbose_name_plural": "Tag carte",
                "ordering": ["nome"],
                "unique_together": {("campagna", "codice")},
            },
        ),
        migrations.AddField(
            model_name="cartacollezionabile",
            name="tags",
            field=models.ManyToManyField(
                blank=True,
                help_text="Tag meccanici (Cavaliere, Orda, …) usati da keyword ed effetti.",
                related_name="carte",
                to="personaggi.tagcarta",
            ),
        ),
    ]
