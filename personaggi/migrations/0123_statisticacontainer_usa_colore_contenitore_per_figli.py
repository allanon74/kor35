from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0122_statistica_containers"),
    ]

    operations = [
        migrations.AddField(
            model_name="statisticacontainer",
            name="usa_colore_contenitore_per_figli",
            field=models.BooleanField(
                default=True,
                help_text="Se attivo, le statistiche contenute usano il colore del contenitore in scheda.",
                verbose_name="Forza colore contenitore sui figli",
            ),
        ),
    ]

