# Dettaglio scambi completati (contropartita + commissione)

import django.core.validators
import django.db.models.deletion
from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0236_offerta_scambio_carte"),
    ]

    operations = [
        migrations.AddField(
            model_name="offertascambiocarte",
            name="carta_contropartita",
            field=models.ForeignKey(
                blank=True,
                help_text="Copia ceduta dall'accettante al completamento (se richiesta carta).",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="offerte_scambio_contropartita",
                to="personaggi.cartaposseduta",
            ),
        ),
        migrations.AddField(
            model_name="offertascambiocarte",
            name="commissione_crediti",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=10,
                null=True,
                validators=[django.core.validators.MinValueValidator(Decimal("0"))],
            ),
        ),
        migrations.AddField(
            model_name="offertascambiocarte",
            name="crediti_trasferiti",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Crediti netti ricevuti dall'offerente dopo commissione.",
                max_digits=10,
                null=True,
                validators=[django.core.validators.MinValueValidator(Decimal("0"))],
            ),
        ),
    ]
