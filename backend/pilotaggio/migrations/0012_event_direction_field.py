from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("pilotaggio", "0011_tune_subsystems_v1"),
    ]

    operations = [
        migrations.AddField(
            model_name="eventoattivosessione",
            name="direzione_evento",
            field=models.CharField(
                blank=True,
                choices=[
                    ("", "Nessuna"),
                    ("avanti", "Avanti"),
                    ("indietro", "Indietro"),
                    ("su", "Su"),
                    ("giu", "Giu"),
                    ("destra", "Destra"),
                    ("sinistra", "Sinistra"),
                ],
                default="",
                max_length=16,
            ),
        ),
    ]
