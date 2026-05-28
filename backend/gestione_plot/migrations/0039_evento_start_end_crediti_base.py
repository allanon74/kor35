from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("gestione_plot", "0038_evento_iscrizione_opzioni"),
    ]

    operations = [
        migrations.AddField(
            model_name="evento",
            name="crediti_base_inizio_evento",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("0.00"),
                help_text="Quota fissa crediti assegnata a ogni PG partecipante all'avvio ufficiale evento.",
                max_digits=12,
                validators=[MinValueValidator(0)],
                verbose_name="Crediti base inizio evento",
            ),
        ),
        migrations.AddField(
            model_name="evento",
            name="ended_at",
            field=models.DateTimeField(
                blank=True,
                help_text="Timestamp di chiusura ufficiale evento (pulsante staff «Termina evento»).",
                null=True,
                verbose_name="Evento terminato il",
            ),
        ),
        migrations.AddField(
            model_name="evento",
            name="started_at",
            field=models.DateTimeField(
                blank=True,
                help_text="Timestamp di avvio ufficiale evento (pulsante staff «Inizia evento»).",
                null=True,
                verbose_name="Evento iniziato il",
            ),
        ),
    ]

