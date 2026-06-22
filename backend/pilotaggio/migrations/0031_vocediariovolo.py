import uuid

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("pilotaggio", "0030_eventoattivosessione_reazione_fino_at"),
    ]

    operations = [
        migrations.CreateModel(
            name="VoceDiarioVolo",
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
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("categoria", models.CharField(db_index=True, max_length=32)),
                ("messaggio", models.TextField()),
                ("defcon_pre", models.SmallIntegerField(blank=True, null=True)),
                ("defcon_post", models.SmallIntegerField(blank=True, null=True)),
                ("dati_json", models.JSONField(blank=True, default=dict)),
                (
                    "evento_attivo",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="voci_diario",
                        to="pilotaggio.eventoattivosessione",
                    ),
                ),
                (
                    "sessione",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="diario_voci",
                        to="pilotaggio.sessionevolo",
                    ),
                ),
            ],
            options={
                "verbose_name": "Voce diario volo",
                "verbose_name_plural": "Voci diario volo",
                "ordering": ["created_at"],
                "indexes": [
                    models.Index(
                        fields=["sessione", "created_at"],
                        name="pilotaggio__session_0a8f2d_idx",
                    ),
                    models.Index(
                        fields=["sessione", "categoria"],
                        name="pilotaggio__session_7c3e91_idx",
                    ),
                ],
            },
        ),
    ]
