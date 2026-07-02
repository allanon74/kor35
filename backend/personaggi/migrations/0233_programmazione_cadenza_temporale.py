from datetime import time

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0232_scommesse_classifica_programmazione"),
    ]

    operations = [
        migrations.AddField(
            model_name="programmazionetorneoscommesse",
            name="data_ancora_cadenza",
            field=models.DateTimeField(
                blank=True,
                help_text="Prima data di riferimento del ciclo (opzionale; default creazione programmazione).",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="programmazionetorneoscommesse",
            name="giorni_apertura",
            field=models.PositiveSmallIntegerField(
                default=12,
                help_text="Giorni di apertura scommesse prima della pubblicazione risultati.",
            ),
        ),
        migrations.AddField(
            model_name="programmazionetorneoscommesse",
            name="intervallo_giorni",
            field=models.PositiveSmallIntegerField(
                default=14,
                help_text="Giorni tra una giornata automatica e la successiva (default 14).",
            ),
        ),
        migrations.AddField(
            model_name="programmazionetorneoscommesse",
            name="ora_risoluzione",
            field=models.TimeField(
                default=time(18, 0),
                help_text="Ora locale di pubblicazione risultati per le giornate a cadenza.",
            ),
        ),
        migrations.AddField(
            model_name="programmazionetorneoscommesse",
            name="sfasamento_giorni",
            field=models.PositiveSmallIntegerField(
                default=0,
                help_text="Ritardo in giorni rispetto all'ancora per sfalsare gli sport tra loro.",
            ),
        ),
        migrations.AlterField(
            model_name="programmazionetorneoscommesse",
            name="auto_genera",
            field=models.BooleanField(
                default=True,
                help_text="Crea automaticamente calendari sulla cadenza temporale (cron/sync).",
            ),
        ),
    ]
