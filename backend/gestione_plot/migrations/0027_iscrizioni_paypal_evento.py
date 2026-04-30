# Generated manually for iscrizioni PayPal evento

import uuid

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("gestione_plot", "0026_wikitierwidget_show_runtime_filters"),
        ("personaggi", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="evento",
            name="iscrizione_apertura",
            field=models.DateTimeField(
                blank=True,
                help_text="Inizio finestra iscrizione (incluso). Lasciare vuoto per disattivare l'iscrizione online.",
                null=True,
                verbose_name="Iscrizione: apertura",
            ),
        ),
        migrations.AddField(
            model_name="evento",
            name="iscrizione_chiusura",
            field=models.DateTimeField(
                blank=True,
                help_text="Fine finestra iscrizione (incluso).",
                null=True,
                verbose_name="Iscrizione: chiusura",
            ),
        ),
        migrations.AddField(
            model_name="evento",
            name="iscrizione_costo_euro",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                max_digits=8,
                validators=[django.core.validators.MinValueValidator(0)],
                verbose_name="Costo iscrizione (EUR)",
                help_text="Importo addebitato via PayPal (es. 45.00). Deve essere > 0 per abilitare il pagamento.",
            ),
        ),
        migrations.AddField(
            model_name="evento",
            name="iscrizione_test_attiva",
            field=models.BooleanField(
                default=False,
                help_text="Se attivo, l'evento compare solo a Master/Head Master della campagna principale (slug kor35) per provare PayPal in sandbox.",
                verbose_name="Test iscrizione (solo Master campagna principale)",
            ),
        ),
        migrations.CreateModel(
            name="PayPalImpostazioniGlobali",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "use_sandbox",
                    models.BooleanField(
                        default=True,
                        help_text="Se vero, ordini e token usano api-m.sandbox.paypal.com (credenziali sandbox).",
                        verbose_name="Usa ambiente Sandbox",
                    ),
                ),
                (
                    "sandbox_client_id",
                    models.CharField(blank=True, max_length=255, verbose_name="Sandbox Client ID"),
                ),
                ("sandbox_client_secret", models.TextField(blank=True, verbose_name="Sandbox Secret")),
                ("live_client_id", models.CharField(blank=True, max_length=255, verbose_name="Live Client ID")),
                ("live_client_secret", models.TextField(blank=True, verbose_name="Live Secret")),
            ],
            options={
                "verbose_name": "Impostazioni PayPal (globale)",
                "verbose_name_plural": "Impostazioni PayPal (globale)",
            },
        ),
        migrations.CreateModel(
            name="IscrizioneEventoPagamento",
            fields=[
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("paypal_order_id", models.CharField(db_index=True, max_length=80, unique=True)),
                ("paypal_capture_id", models.CharField(blank=True, max_length=80)),
                (
                    "stato",
                    models.CharField(
                        choices=[
                            ("PENDING", "In attesa di pagamento"),
                            ("CAPTURED", "Pagato e iscritto"),
                            ("FAILED", "Fallito"),
                            ("CANCELLED", "Annullato"),
                        ],
                        default="PENDING",
                        max_length=20,
                    ),
                ),
                ("importo_euro", models.DecimalField(decimal_places=2, max_digits=10)),
                (
                    "sandbox_usato",
                    models.BooleanField(default=False, help_text="True se l'ordine è stato creato in sandbox."),
                ),
                ("ultimo_errore", models.TextField(blank=True)),
                (
                    "evento",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="iscrizioni_paypal",
                        to="gestione_plot.evento",
                    ),
                ),
                (
                    "personaggio",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="iscrizioni_evento_paypal",
                        to="personaggi.personaggio",
                    ),
                ),
                (
                    "utente",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="iscrizioni_evento_paypal",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Iscrizione evento (PayPal)",
                "verbose_name_plural": "Iscrizioni evento (PayPal)",
                "ordering": ["-created_at"],
            },
        ),
    ]
