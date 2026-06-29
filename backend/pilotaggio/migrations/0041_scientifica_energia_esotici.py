# Energia R/S/T → velocità coerenza e carica interventi

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pilotaggio", "0040_scientifica_fase2"),
    ]

    operations = [
        migrations.AddField(
            model_name="scientificostatonave",
            name="carica_intervento",
            field=models.PositiveSmallIntegerField(
                default=0,
                help_text="Carica campo 0–100: si ricarica con l'energia inviata a R/S/T; serve per interventi.",
            ),
        ),
        migrations.AddField(
            model_name="pilotruntimeconfig",
            name="scientifica_energia_per_coerenza",
            field=models.FloatField(
                default=4.0,
                help_text="Unità energia R/S/T (per tick) necessarie per +1 coerenza.",
            ),
        ),
        migrations.AddField(
            model_name="pilotruntimeconfig",
            name="scientifica_carica_intervento_soglia",
            field=models.PositiveSmallIntegerField(
                default=100,
                help_text="Carica minima (0–100) per eseguire un intervento attivo.",
            ),
        ),
        migrations.AddField(
            model_name="pilotruntimeconfig",
            name="scientifica_carica_per_energia",
            field=models.FloatField(
                default=5.0,
                help_text="Punti carica guadagnati per tick per ogni unità energia su R/S/T.",
            ),
        ),
    ]
