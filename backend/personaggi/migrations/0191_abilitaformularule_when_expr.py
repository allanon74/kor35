from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0190_acquisto_costi_pagati"),
    ]

    operations = [
        migrations.AddField(
            model_name="abilitaformularule",
            name="when_expr",
            field=models.CharField(
                blank=True,
                help_text=(
                    "Condizione opzionale (es. chop > 0, dmg_mischia > 0, aura_sacra > 0). "
                    "Se valorizzata, la regola si applica solo quando l'espressione è vera nel contesto formula."
                ),
                max_length=255,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="abilitaformularule",
            name="rule_type",
            field=models.CharField(
                choices=[
                    ("SOURCE_OVERRIDE", "Sostituisci sorgente"),
                    ("SOURCE_APPEND", "Aggiungi sorgente/elemento"),
                    ("AURA_REPLACE", "Sostituisci aura"),
                    ("AURA_APPEND", "Aggiungi aura alternativa"),
                    ("ELEMENT_REPLACE", "Sostituisci elemento"),
                ],
                max_length=30,
            ),
        ),
    ]
