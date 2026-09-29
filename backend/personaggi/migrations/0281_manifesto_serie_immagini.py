# Generated manually — manifesto immagine + immagini serie QR

import django.core.validators
import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0280_modello_prototipo_carica_minima"),
    ]

    operations = [
        migrations.AddField(
            model_name="manifesto",
            name="immagine_file",
            field=models.ImageField(
                blank=True,
                help_text="Immagine opzionale mostrata alla scansione con testo/audio/video. Compressa al salvataggio.",
                null=True,
                upload_to="manifesti/immagini/%Y/%m/",
                validators=[
                    django.core.validators.FileExtensionValidator(
                        allowed_extensions=["jpg", "jpeg", "png", "webp", "gif"]
                    )
                ],
            ),
        ),
        migrations.CreateModel(
            name="SerieImmagine",
            fields=[
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "sync_id",
                    models.UUIDField(
                        db_index=True, default=uuid.uuid4, editable=False, unique=True
                    ),
                ),
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
                    "immagine",
                    models.ImageField(
                        upload_to="serie/immagini/%Y/%m/",
                        validators=[
                            django.core.validators.FileExtensionValidator(
                                allowed_extensions=["jpg", "jpeg", "png", "webp", "gif"]
                            )
                        ],
                    ),
                ),
                (
                    "nome_file_originale",
                    models.CharField(
                        blank=True,
                        db_index=True,
                        default="",
                        help_text="Basename originale usato per l'ordinamento alfabetico all'assegnazione.",
                        max_length=255,
                    ),
                ),
                (
                    "serie",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="immagini",
                        to="personaggi.seriecollezione",
                    ),
                ),
            ],
            options={
                "verbose_name": "Immagine serie",
                "verbose_name_plural": "Immagini serie",
                "ordering": ["nome_file_originale", "created_at"],
            },
        ),
        migrations.AddField(
            model_name="serieassegnazione",
            name="immagine",
            field=models.ForeignKey(
                blank=True,
                help_text="Immagine assegnata a questo pezzo (se la collezione ne ha).",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="assegnazioni",
                to="personaggi.serieimmagine",
            ),
        ),
    ]
