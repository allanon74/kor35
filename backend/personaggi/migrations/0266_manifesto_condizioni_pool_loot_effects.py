# Generated manually for manifesto testo condizionale + effetti pool loot

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0265_personaggio_punti_allineamento"),
    ]

    operations = [
        migrations.AddField(
            model_name="manifesto",
            name="testo_condizionato",
            field=models.TextField(
                blank=True,
                default="",
                help_text="HTML mostrato in aggiunta al testo base se le condizioni_testo sono soddisfatte.",
            ),
        ),
        migrations.AddField(
            model_name="manifesto",
            name="condizioni_testo",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text='Gruppo requisiti AND/OR: {"operator":"AND"|"OR","requisiti":[...]}. Vuoto = nessun testo condizionale.',
            ),
        ),
        migrations.AddField(
            model_name="randomqrpooleffect",
            name="manifesto",
            field=models.ForeignKey(
                blank=True,
                help_text="Effetto manifesto: riusa testo base + testo condizionale del catalogo.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="pool_effetti",
                to="personaggi.manifesto",
            ),
        ),
        migrations.AddField(
            model_name="randomqrpooleffect",
            name="oggetto_base",
            field=models.ForeignKey(
                blank=True,
                help_text="Effetto loot: crea istanza da listino e la mette in inventario.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="pool_effetti",
                to="personaggi.oggettobase",
            ),
        ),
        migrations.AddField(
            model_name="randomqrpooleffect",
            name="tessitura",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="pool_effetti",
                to="personaggi.tessitura",
            ),
        ),
        migrations.AddField(
            model_name="randomqrpooleffect",
            name="infusione",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="pool_effetti",
                to="personaggi.infusione",
            ),
        ),
        migrations.AddField(
            model_name="randomqrpooleffect",
            name="cerimoniale",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="pool_effetti",
                to="personaggi.cerimoniale",
            ),
        ),
        migrations.AddField(
            model_name="randomqrpooleffect",
            name="attivata",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="pool_effetti",
                to="personaggi.attivata",
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
                    ("tessitura", "Tessitura"),
                    ("infusione", "Infusione"),
                    ("cerimoniale", "Cerimoniale"),
                    ("attivata", "Attivata"),
                ],
                db_index=True,
                max_length=16,
            ),
        ),
    ]
