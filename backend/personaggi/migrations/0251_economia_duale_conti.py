# Generated manually for economia duale (conto corrente / deposito) — schema only

from decimal import Decimal

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0250_campagna_moduli_accesso"),
        ("gestione_plot", "0048_evento_prestigio_base_inizio"),
    ]

    operations = [
        migrations.AddField(
            model_name="campagna",
            name="economia_config",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text=(
                    "Config economia duale (conto deposito): frazione_trasferimento_stipendio, "
                    "fattore_valore_deposito, categorie_spesa_deposito. Chiavi assenti → default codice."
                ),
            ),
        ),
        migrations.AddField(
            model_name="creditomovimento",
            name="conto",
            field=models.CharField(
                choices=[("CORRENTE", "Conto corrente"), ("DEPOSITO", "Conto di deposito")],
                db_index=True,
                default="CORRENTE",
                help_text="Conto corrente (stipendio) o deposito (altri guadagni / ex-riserva).",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="creditomovimento",
            name="evento",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="movimenti_credito",
                to="gestione_plot.evento",
            ),
        ),
        migrations.AlterField(
            model_name="personaggio",
            name="riserva",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("0.00"),
                help_text=(
                    "Deprecato: assorbita nel conto deposito. Tenuto a 0 dopo migrazione; "
                    "usare crediti_deposito / economia_crediti."
                ),
                max_digits=12,
                verbose_name="Riserva scommesse (legacy)",
            ),
        ),
    ]
