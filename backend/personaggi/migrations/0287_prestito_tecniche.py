# Prestito negozio: tecniche temporanee + oggetto opzionale

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0286_negozio_prestiti"),
    ]

    operations = [
        migrations.AlterField(
            model_name="negoziomercanteprestito",
            name="oggetto",
            field=models.ForeignKey(
                blank=True,
                help_text="Oggetto fisico in prestito (OGB/OGG/INF-istanza/stock).",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="prestiti_negozio_mercante",
                to="personaggi.oggetto",
            ),
        ),
        migrations.AddField(
            model_name="negoziomercanteprestito",
            name="abilita",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="prestiti_negozio_mercante",
                to="personaggi.abilita",
            ),
        ),
        migrations.AddField(
            model_name="negoziomercanteprestito",
            name="infusione",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="prestiti_negozio_mercante",
                to="personaggi.infusione",
            ),
        ),
        migrations.AddField(
            model_name="negoziomercanteprestito",
            name="tessitura",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="prestiti_negozio_mercante",
                to="personaggi.tessitura",
            ),
        ),
        migrations.AddField(
            model_name="negoziomercanteprestito",
            name="cerimoniale",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="prestiti_negozio_mercante",
                to="personaggi.cerimoniale",
            ),
        ),
        migrations.RemoveConstraint(
            model_name="negoziomercanteprestito",
            name="uniq_oggetto_prestito_attivo",
        ),
        migrations.AddConstraint(
            model_name="negoziomercanteprestito",
            constraint=models.UniqueConstraint(
                condition=models.Q(("oggetto__isnull", False), ("stato", "ATT")),
                fields=("oggetto",),
                name="uniq_oggetto_prestito_attivo",
            ),
        ),
    ]
