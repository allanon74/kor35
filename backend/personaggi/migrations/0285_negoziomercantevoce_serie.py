# Voce negozio mercante: tipo SER (pezzo di SerieCollezione)

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0284_serie_inventario_eventi_duplicati"),
    ]

    operations = [
        migrations.AddField(
            model_name="negoziomercantevoce",
            name="serie",
            field=models.ForeignKey(
                blank=True,
                help_text=(
                    "Serie collezione: all'acquisto assegna un pezzo via inventario serie "
                    "(non zaino)."
                ),
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="voci_negozio_mercante",
                to="personaggi.seriecollezione",
            ),
        ),
        migrations.AlterField(
            model_name="negoziomercantevoce",
            name="tipo_voce",
            field=models.CharField(
                choices=[
                    ("OGB", "Oggetto base (template)"),
                    ("OGG", "Oggetto (istanza unica)"),
                    ("ABL", "Abilità"),
                    ("INF", "Infusione"),
                    ("TES", "Tessitura"),
                    ("CER", "Cerimoniale"),
                    ("CON", "Consumabile (lotto)"),
                    ("SER", "Serie (pezzo collezione)"),
                ],
                db_index=True,
                max_length=3,
            ),
        ),
    ]
