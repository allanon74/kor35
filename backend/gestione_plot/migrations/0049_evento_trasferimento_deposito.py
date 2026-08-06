# Generated manually for EventoTrasferimentoDeposito

import uuid
from decimal import Decimal

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("gestione_plot", "0048_evento_prestigio_base_inizio"),
        ("personaggi", "0250_campagna_moduli_accesso"),
    ]

    operations = [
        migrations.CreateModel(
            name="EventoTrasferimentoDeposito",
            fields=[
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "importo",
                    models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12),
                ),
                (
                    "evento",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="trasferimenti_deposito",
                        to="gestione_plot.evento",
                    ),
                ),
                (
                    "personaggio",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="trasferimenti_deposito_evento",
                        to="personaggi.personaggio",
                    ),
                ),
            ],
            options={
                "verbose_name": "Trasferimento deposito evento",
                "verbose_name_plural": "Trasferimenti deposito evento",
            },
        ),
        migrations.AddConstraint(
            model_name="eventotrasferimentodeposito",
            constraint=models.UniqueConstraint(
                fields=("evento", "personaggio"),
                name="uq_evento_trasferimento_deposito_pg",
            ),
        ),
    ]
