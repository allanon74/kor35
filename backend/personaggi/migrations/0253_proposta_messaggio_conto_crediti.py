# Generated manually: conto crediti su proposte P2P e messaggi

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0252_migrate_riserva_to_deposito"),
    ]

    operations = [
        migrations.AddField(
            model_name="propostatransazione",
            name="conto_crediti",
            field=models.CharField(
                choices=[("CORRENTE", "Conto corrente"), ("DEPOSITO", "Conto di deposito")],
                db_index=True,
                default="CORRENTE",
                help_text=(
                    "Conto da cui partono i crediti_da_dare; il destinatario li riceve sullo stesso conto "
                    "(corrente resta corrente, deposito resta deposito)."
                ),
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="messaggio",
            name="conto_crediti_allegati",
            field=models.CharField(
                blank=True,
                choices=[("CORRENTE", "Conto corrente"), ("DEPOSITO", "Conto di deposito")],
                default="CORRENTE",
                help_text="Conto usato per crediti_allegati (mittente e destinatario sullo stesso conto).",
                max_length=16,
            ),
        ),
    ]
