from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0194_minigioco_random"),
    ]

    operations = [
        migrations.AddField(
            model_name="minigiocoqrconfig",
            name="esclusioni_minigioco",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="Lista gruppi {operator, requisiti}: se uno matcha, salta il minigioco (effetto QR diretto).",
            ),
        ),
        migrations.AddField(
            model_name="minigiocoqrconfig",
            name="regole_difficolta",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="Regole {operator, requisiti, difficolta}: se matchano, usa la difficoltà più favorevole al PG.",
            ),
        ),
        migrations.AlterField(
            model_name="minigiocoqrconfig",
            name="difficolta",
            field=models.PositiveSmallIntegerField(
                default=4,
                help_text="Difficoltà predefinita (1–4) se nessuna regola condizionale applica.",
            ),
        ),
        migrations.AlterField(
            model_name="minigiocoqrconfig",
            name="difficolta_min",
            field=models.PositiveSmallIntegerField(
                default=1,
                help_text="Legacy: non usato se sono definite regole_difficolta.",
            ),
        ),
        migrations.AlterField(
            model_name="minigiocoqrconfig",
            name="requisiti_attivazione",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="Mostra minigioco solo se il PG soddisfa questi requisiti (vuoto = sempre).",
            ),
        ),
    ]
