from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("gestione_plot", "0051_paginaregolamento_visibile_solo_autenticati"),
    ]

    operations = [
        migrations.AddField(
            model_name="missione",
            name="allineamento",
            field=models.CharField(
                choices=[
                    ("LUMINOSA", "Luminosa"),
                    ("OSCURA", "Oscura"),
                    ("GRIGIA", "Grigia"),
                ],
                db_index=True,
                default="GRIGIA",
                help_text=(
                    "Luminosa / Oscura / Grigia. Alla risoluzione incrementa il "
                    "punteggio corrispondente sul personaggio."
                ),
                max_length=10,
                verbose_name="Allineamento",
            ),
        ),
    ]
