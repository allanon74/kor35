# Generated manually: effetto pool Materia/Mod da Infusione-matrice

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0266_manifesto_condizioni_pool_loot_effects"),
    ]

    operations = [
        migrations.AlterField(
            model_name="randomqrpooleffect",
            name="tipo",
            field=models.CharField(
                choices=[
                    ("testo", "Testo"),
                    ("nodo", "Nodo"),
                    ("trappola", "Trappola"),
                    ("serie", "Serie"),
                    ("manifesto", "Manifesto"),
                    ("oggetto_base", "Oggetto (listino)"),
                    ("da_infusione", "Materia/Mod (da Infusione)"),
                    ("tessitura", "Tessitura"),
                    ("infusione", "Infusione (ricetta)"),
                    ("cerimoniale", "Cerimoniale"),
                    ("attivata", "Attivata"),
                ],
                db_index=True,
                max_length=16,
            ),
        ),
    ]
