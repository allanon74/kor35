import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0187_negozio_mercante"),
        ("gestione_plot", "0042_manualepdf_generazione_batch"),
    ]

    operations = [
        migrations.AddField(
            model_name="questvista",
            name="negozio_mercante",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="quest_viste",
                to="personaggi.negoziomercante",
            ),
        ),
        migrations.AlterField(
            model_name="questvista",
            name="tipo",
            field=models.CharField(
                choices=[
                    ("PG", "Personaggio"),
                    ("PNG", "Personaggio Non Giocante"),
                    ("INV", "Inventario"),
                    ("OGG", "Oggetto"),
                    ("TES", "Tessitura"),
                    ("INF", "Infusione"),
                    ("CER", "Cerimoniale"),
                    ("MAN", "Manifesto"),
                    ("NEG", "Negozio alternativo"),
                ],
                max_length=3,
            ),
        ),
    ]
