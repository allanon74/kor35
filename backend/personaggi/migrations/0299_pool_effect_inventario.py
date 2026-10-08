# Effetto pool random: apre un inventario contenitore (stesse regole di visibilità QR).

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0298_rename_inventario_crediti_contenuti"),
    ]

    operations = [
        migrations.AddField(
            model_name="randomqrpooleffect",
            name="inventario",
            field=models.ForeignKey(
                blank=True,
                help_text=(
                    "Effetto: alla scansione il giocatore apre questo inventario "
                    "(non un personaggio), con le stesse regole di visibilità degli inventari QR."
                ),
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="pool_effetti",
                to="personaggi.inventario",
            ),
        ),
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
                    ("negozio_mercante", "Negozio mercante"),
                    ("crediti", "Crediti deposito"),
                    ("inventario", "Inventario"),
                ],
                db_index=True,
                max_length=32,
            ),
        ),
    ]
