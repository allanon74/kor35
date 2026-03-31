from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0123_statisticacontainer_usa_colore_contenitore_per_figli"),
    ]

    operations = [
        migrations.AddField(
            model_name="statisticacontainer",
            name="dimensione",
            field=models.CharField(
                choices=[
                    ("badge", "Badge"),
                    ("xs", "Extra Small"),
                    ("s", "Small"),
                    ("m", "Medium"),
                    ("l", "Large"),
                    ("xl", "Extra Large"),
                ],
                default="s",
                help_text="Dimensione di rendering dell'intestazione contenitore in scheda.",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="statisticacontaineritem",
            name="dimensione",
            field=models.CharField(
                choices=[
                    ("badge", "Badge"),
                    ("xs", "Extra Small"),
                    ("s", "Small"),
                    ("m", "Medium"),
                    ("l", "Large"),
                    ("xl", "Extra Large"),
                ],
                default="s",
                help_text="Dimensione di rendering della statistica nel contenitore.",
                max_length=10,
            ),
        ),
    ]

