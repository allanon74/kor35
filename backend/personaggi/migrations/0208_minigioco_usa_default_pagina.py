from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0207_propostatecnica_permetti_vendita"),
    ]

    operations = [
        migrations.AddField(
            model_name="minigiocoqrconfig",
            name="usa_default_pagina",
            field=models.BooleanField(
                default=False,
                help_text="Se True, la config segue il template minigioco di pagina staff (copiato in DB al toggle).",
            ),
        ),
    ]
