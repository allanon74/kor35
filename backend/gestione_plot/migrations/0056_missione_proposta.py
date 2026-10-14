import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("gestione_plot", "0055_evento_premio_avvio_at"),
    ]

    operations = [
        migrations.CreateModel(
            name="MissioneProposta",
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
                ("testo", models.TextField(verbose_name="Soluzione")),
                (
                    "stato",
                    models.CharField(
                        choices=[
                            ("IN_ATTESA", "In attesa"),
                            ("ACCETTATA", "Accettata"),
                            ("RIFIUTATA", "Rifiutata"),
                        ],
                        db_index=True,
                        default="IN_ATTESA",
                        max_length=12,
                    ),
                ),
                ("messaggio_rifiuto", models.TextField(blank=True, default="")),
                ("risposta_at", models.DateTimeField(blank=True, null=True)),
                (
                    "evento",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="proposte_missioni",
                        to="gestione_plot.evento",
                    ),
                ),
                (
                    "missione",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="proposte",
                        to="gestione_plot.missione",
                    ),
                ),
                (
                    "personaggio",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="proposte_missioni",
                        to="personaggi.personaggio",
                    ),
                ),
                (
                    "risoluzione",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="proposte",
                        to="gestione_plot.missionerisoluzione",
                    ),
                ),
                (
                    "risposta_da",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="proposte_missioni_risposte",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Soluzione task",
                "verbose_name_plural": "Soluzioni task",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["stato", "evento"], name="missprop_stato_evento_idx"),
                    models.Index(
                        fields=["personaggio", "missione", "evento"],
                        name="missprop_pg_miss_evt_idx",
                    ),
                ],
            },
        ),
    ]
