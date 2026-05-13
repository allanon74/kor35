# Generated manually for EVENTO_ESITO_GUASTO_CA

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pilotaggio", "0022_sottosistemanave_ordine_gruppo"),
    ]

    operations = [
        migrations.AlterField(
            model_name="eventoattivosessione",
            name="esito",
            field=models.CharField(
                choices=[
                    ("pending", "In attesa"),
                    ("risolto", "Risolto"),
                    ("parziale", "Parziale"),
                    ("fallito", "Fallito"),
                    ("timeout", "Timeout"),
                    ("precipizio", "Precipizio"),
                    ("guasto_ca", "CA: guasto sottosistema"),
                ],
                db_index=True,
                default="pending",
                max_length=16,
            ),
        ),
    ]
