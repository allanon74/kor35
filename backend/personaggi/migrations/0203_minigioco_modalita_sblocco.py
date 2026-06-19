from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0202_personaggio_eliminato_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="minigiocoqrconfig",
            name="modalita_sblocco",
            field=models.CharField(
                choices=[
                    ("ogni_scansione", "Minigioco a ogni scansione"),
                    ("permanente", "Una volta risolto, per sempre"),
                    ("temporaneo", "Sblocco temporaneo (N secondi)"),
                ],
                default="permanente",
                help_text="Per quanto tempo, dopo la vittoria, il PG può saltare il minigioco su questo QR.",
                max_length=24,
            ),
        ),
        migrations.AddField(
            model_name="minigiocoqrconfig",
            name="sblocco_secondi",
            field=models.PositiveIntegerField(
                blank=True,
                help_text="Durata sblocco in secondi (solo modalità temporaneo).",
                null=True,
            ),
        ),
    ]
