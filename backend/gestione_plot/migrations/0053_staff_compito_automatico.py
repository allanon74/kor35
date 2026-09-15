# Generated manually: compiti automatici (verifica proposte)

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("personaggi", "0259_minigioco_pattern_sezione_default"),
        ("gestione_plot", "0052_missione_allineamento"),
    ]

    operations = [
        migrations.CreateModel(
            name="StaffCompitoAutomatico",
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
                    "codice",
                    models.CharField(
                        choices=[
                            ("verifica_proposte_tessiture", "Verifica proposte tessiture"),
                            ("verifica_proposte_infusioni", "Verifica proposte infusioni"),
                            ("verifica_proposte_cerimoniali", "Verifica proposte cerimoniali"),
                        ],
                        db_index=True,
                        max_length=64,
                    ),
                ),
                ("attivo", models.BooleanField(db_index=True, default=True)),
                (
                    "campagna",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="staff_compiti_automatici",
                        to="personaggi.campagna",
                    ),
                ),
            ],
            options={
                "verbose_name": "Compito automatico staff",
                "verbose_name_plural": "Compiti automatici staff",
                "ordering": ["codice"],
            },
        ),
        migrations.CreateModel(
            name="StaffCompitoAutomaticoAssegnazione",
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
                    "config",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="assegnazioni",
                        to="gestione_plot.staffcompitoautomatico",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="staff_compiti_automatici_assegnati",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Assegnazione compito automatico",
                "verbose_name_plural": "Assegnazioni compiti automatici",
                "ordering": ["config_id", "user_id"],
            },
        ),
        migrations.AddConstraint(
            model_name="staffcompitoautomatico",
            constraint=models.UniqueConstraint(
                fields=("campagna", "codice"),
                name="uq_staff_compito_automatico_campagna_codice",
            ),
        ),
        migrations.AddConstraint(
            model_name="staffcompitoautomaticoassegnazione",
            constraint=models.UniqueConstraint(
                fields=("config", "user"),
                name="uq_staff_compito_automatico_assegnazione_user",
            ),
        ),
    ]
