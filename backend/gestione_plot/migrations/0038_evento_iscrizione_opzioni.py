# Opzioni accessorie iscrizione evento

import uuid

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("gestione_plot", "0037_configurazionesito_staff_dashboard_layout"),
    ]

    operations = [
        migrations.CreateModel(
            name="EventoIscrizioneOpzione",
            fields=[
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("nome", models.CharField(max_length=120)),
                ("descrizione", models.TextField(blank=True)),
                (
                    "costo_euro",
                    models.DecimalField(
                        decimal_places=2,
                        default=0,
                        max_digits=8,
                        validators=[django.core.validators.MinValueValidator(0)],
                        verbose_name="Costo (EUR)",
                    ),
                ),
                ("ordine", models.PositiveIntegerField(default=0)),
                (
                    "scelta_giocatore",
                    models.BooleanField(
                        default=True,
                        help_text="Se disattivo, l'opzione è inclusa automaticamente in ogni iscrizione.",
                        verbose_name="Scelta del giocatore",
                    ),
                ),
                (
                    "obbligatoria",
                    models.BooleanField(
                        default=False,
                        help_text="Con «scelta del giocatore» attivo: il giocatore deve selezionarla per iscriversi.",
                        verbose_name="Obbligatoria (se a scelta)",
                    ),
                ),
                (
                    "posti_limite",
                    models.PositiveIntegerField(
                        blank=True,
                        help_text="Vuoto = posti illimitati. I posti occupati includono ordini in attesa di pagamento.",
                        null=True,
                        verbose_name="Posti disponibili",
                    ),
                ),
                ("attiva", models.BooleanField(default=True)),
                (
                    "evento",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="iscrizione_opzioni",
                        to="gestione_plot.evento",
                    ),
                ),
            ],
            options={
                "verbose_name": "Opzione iscrizione evento",
                "verbose_name_plural": "Opzioni iscrizione evento",
                "ordering": ["ordine", "nome"],
            },
        ),
        migrations.AddField(
            model_name="iscrizioneeventopagamento",
            name="tipo_ordine",
            field=models.CharField(
                choices=[("ISCRIZIONE", "Iscrizione iniziale"), ("INTEGRA", "Integrazione opzioni")],
                default="ISCRIZIONE",
                max_length=12,
            ),
        ),
        migrations.CreateModel(
            name="IscrizioneEventoPagamentoOpzione",
            fields=[
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("costo_euro", models.DecimalField(decimal_places=2, max_digits=8)),
                (
                    "opzione",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="acquisti",
                        to="gestione_plot.eventoiscrizioneopzione",
                    ),
                ),
                (
                    "pagamento",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="righe_opzioni",
                        to="gestione_plot.iscrizioneeventopagamento",
                    ),
                ),
            ],
            options={
                "verbose_name": "Opzione pagamento iscrizione",
                "verbose_name_plural": "Opzioni pagamento iscrizione",
            },
        ),
        migrations.AddConstraint(
            model_name="iscrizioneeventopagamentoopzione",
            constraint=models.UniqueConstraint(
                fields=("pagamento", "opzione"),
                name="uniq_iscrizione_pagamento_opzione",
            ),
        ),
    ]
