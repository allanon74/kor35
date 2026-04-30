# PayPal UI toggles

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("gestione_plot", "0028_evento_pc_crediti_premio_presenza"),
    ]

    operations = [
        migrations.AddField(
            model_name="paypalimpostazioniglobali",
            name="mostra_pulsante_carta",
            field=models.BooleanField(
                default=False,
                help_text="Se attivo, nel checkout PayPal puo comparire anche il pulsante carta.",
                verbose_name="Mostra pulsante Carta",
            ),
        ),
        migrations.AddField(
            model_name="paypalimpostazioniglobali",
            name="mostra_pulsante_mybank",
            field=models.BooleanField(
                default=False,
                help_text="Se attivo, nel checkout PayPal puo comparire anche MyBank (quando supportato).",
                verbose_name="Mostra pulsante MyBank",
            ),
        ),
    ]
